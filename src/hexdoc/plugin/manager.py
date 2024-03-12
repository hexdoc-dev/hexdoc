from __future__ import annotations

import importlib
from dataclasses import dataclass
from importlib.resources import Package
from pathlib import Path
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    Never,
    ParamSpec,
    Sequence,
    TypeVar,
    overload,
)

import pluggy
from jinja2 import BaseLoader, ChoiceLoader, PackageLoader
from jinja2.sandbox import SandboxedEnvironment

from hexdoc.utils import ContextSource, ValidationContext

if TYPE_CHECKING:
    from hexdoc.core import Properties, ResourceLocation
    from hexdoc.minecraft import I18n
    from hexdoc.patchouli import FormatTree

from .book_plugin import BookPlugin
from .mod_plugin import DefaultRenderedTemplates, ModPlugin, ModPluginWithBook
from .specs import HEXDOC_PROJECT_NAME, PluginSpec
from .types import HookReturns

_T = TypeVar("_T")

_P = ParamSpec("_P")
_R = TypeVar("_R", covariant=True)


class PluginNotFoundError(RuntimeError):
    pass


@dataclass
class TypedHookCaller(Generic[_P, _R]):
    plugin_name: str | None
    caller: pluggy.HookCaller

    @property
    def name(self):
        return self.caller.name

    @property
    def plugin_display_name(self):
        if self.plugin_name is None:
            return HEXDOC_PROJECT_NAME

        return f"Plugin {HEXDOC_PROJECT_NAME}-{self.plugin_name}"

    def try_call(self, *args: _P.args, **kwargs: _P.kwargs) -> _R | None:
        result = self.caller(*args, **kwargs)
        match result:
            case None | []:
                return None
            case _:
                return result

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        result = self.try_call(*args, **kwargs)
        if result is None:
            raise PluginNotFoundError(
                f"{self.plugin_display_name} does not implement hook {self.name}"
            )
        return result


class _NoCallTypedHookCaller(TypedHookCaller[_P, None]):
    """Represents a TypedHookCaller which returns None. This will always raise, so the
    return type of __call__ is set to Never."""

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> Never: ...


# TODO: convert to dataclass
class PluginManager(ValidationContext):
    """Custom hexdoc plugin manager with helpers and stronger typing."""

    def __init__(self, branch: str, props: Properties, load: bool = True) -> None:
        """Initialize the hexdoc plugin manager.

        If `load` is true (the default), calls `init_entrypoints` and `init_mod_plugins`.
        """
        self.branch = branch
        self.props = props
        self.inner = pluggy.PluginManager(HEXDOC_PROJECT_NAME)
        self.mod_plugins: dict[str, ModPlugin] = {}
        self.book_plugins: dict[str, BookPlugin[Any]] = {}

        self.inner.add_hookspecs(PluginSpec)
        if load:
            self.init_entrypoints()
            self.init_plugins()

    def init_entrypoints(self):
        self.inner.load_setuptools_entrypoints(HEXDOC_PROJECT_NAME)
        self.inner.check_pending()

    def init_plugins(self):
        self._init_book_plugins()
        self._init_mod_plugins()

    def _init_book_plugins(self):
        caller = self._hook_caller(PluginSpec.hexdoc_book_plugin)
        for plugin in flatten(caller.try_call()):
            self.book_plugins[plugin.modid] = plugin

    def _init_mod_plugins(self):
        caller = self._hook_caller(PluginSpec.hexdoc_mod_plugin)
        for plugin in flatten(
            caller.try_call(
                branch=self.branch,
                props=self.props,
            )
        ):
            self.mod_plugins[plugin.modid] = plugin

    def register(self, plugin: Any, name: str | None = None):
        self.inner.register(plugin, name)
        self.init_plugins()

    def book_plugin(self, modid: str):
        plugin = self.book_plugins.get(modid)
        if plugin is None:
            raise ValueError(f"No BookPlugin registered for modid: {modid}")
        return plugin

    @overload
    def mod_plugin(self, modid: str, book: Literal[True]) -> ModPluginWithBook: ...

    @overload
    def mod_plugin(self, modid: str, book: bool = False) -> ModPlugin: ...

    def mod_plugin(self, modid: str, book: bool = False):
        plugin = self.mod_plugins.get(modid)
        if plugin is None:
            raise ValueError(f"No ModPlugin registered for modid: {modid}")

        if book and not isinstance(plugin, ModPluginWithBook):
            raise ValueError(
                f"ModPlugin registered for modid `{modid}`"
                f" does not inherit from ModPluginWithBook: {plugin}"
            )

        return plugin

    def mod_plugin_with_book(self, modid: str):
        return self.mod_plugin(modid, book=True)

    def minecraft_version(self) -> str | None:
        versions = dict[str, str]()

        for modid, plugin in self.mod_plugins.items():
            version = plugin.compat_minecraft_version
            if version is not None:
                versions[modid] = version

        match len(set(versions.values())):
            case 0:
                return None
            case 1:
                return versions.popitem()[1]
            case n:
                raise ValueError(
                    f"Got {n} Minecraft versions, expected 1: "
                    + ", ".join(
                        f"{modid}={version}" for modid, version in versions.items()
                    )
                )

    def validate_format_tree(
        self,
        tree: FormatTree,
        macros: dict[str, str],
        book_id: ResourceLocation,
        i18n: I18n,
        is_0_black: bool,
        link_overrides: dict[str, str],
    ):
        caller = self._hook_caller(PluginSpec.hexdoc_validate_format_tree)
        caller.try_call(
            tree=tree,
            macros=macros,
            book_id=book_id,
            i18n=i18n,
            is_0_black=is_0_black,
            link_overrides=link_overrides,
        )
        return tree

    def update_context(self, context: dict[str, Any]) -> Iterator[ValidationContext]:
        caller = self._hook_caller(PluginSpec.hexdoc_update_context)
        if returns := caller.try_call(context=context):
            yield from flatten(returns)

    def update_jinja_env(self, env: SandboxedEnvironment, modids: Sequence[str]):
        for modid in modids:
            plugin = self.mod_plugin(modid)
            plugin.update_jinja_env(env)
        return env

    def update_template_args(self, template_args: dict[str, Any]):
        caller = self._hook_caller(PluginSpec.hexdoc_update_template_args)
        caller.try_call(template_args=template_args)
        return template_args

    def load_resources(self, modid: str) -> Iterator[ModuleType]:
        plugin = self.mod_plugin(modid)
        for package in flatten([plugin.resource_dirs()]):
            yield import_package(package)

    def load_tagged_unions(self) -> Iterator[ModuleType]:
        yield from self._import_from_hook(PluginSpec.hexdoc_load_tagged_unions)

    def load_jinja_templates(self, modids: Sequence[str]):
        """modid -> PackageLoader"""
        extra_modids = set(self.mod_plugins.keys()) - set(modids)

        included = self._package_loaders_for(modids)
        extra = self._package_loaders_for(extra_modids)

        return included, extra

    def _package_loaders_for(self, modids: Iterable[str]):
        loaders = dict[str, BaseLoader]()

        for modid in modids:
            plugin = self.mod_plugin(modid)

            result = plugin.jinja_template_root()
            if not result:
                continue

            loaders[modid] = ChoiceLoader(
                [
                    PackageLoader(
                        package_name=import_package(package).__name__,
                        package_path=package_path,
                    )
                    for package, package_path in flatten([result])
                ]
            )

        return loaders

    def default_rendered_templates(
        self,
        modids: Iterable[str],
        book: Any,
        context: ContextSource,
    ):
        templates: DefaultRenderedTemplates = {}
        for modid in modids:
            plugin = self.mod_plugin(modid)
            templates |= plugin.default_rendered_templates()
            templates |= plugin.default_rendered_templates_v2(book, context)

        result = dict[Path, tuple[str, Mapping[str, Any]]]()
        for path, value in templates.items():
            match value:
                case str(template):
                    args = dict[str, Any]()
                case (template, args):
                    pass
            result[Path(path)] = (template, args)

        return result

    def _import_from_hook(
        self,
        __spec: Callable[_P, HookReturns[Package]],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Iterator[ModuleType]:
        packages = self._hook_caller(__spec)(*args, **kwargs)
        for package in flatten(packages):
            yield import_package(package)

    @overload
    def _hook_caller(self, spec: Callable[_P, None]) -> _NoCallTypedHookCaller[_P]: ...

    @overload
    def _hook_caller(
        self, spec: Callable[_P, _R | None]
    ) -> TypedHookCaller[_P, _R]: ...

    def _hook_caller(self, spec: Callable[_P, _R | None]) -> TypedHookCaller[_P, _R]:
        caller = self.inner.hook.__dict__[spec.__name__]
        return TypedHookCaller(None, caller)


def flatten(values: list[list[_T] | _T] | None) -> Iterator[_T]:
    for value in values or []:
        if isinstance(value, list):
            yield from value
        else:
            yield value


def import_package(package: Package) -> ModuleType:
    match package:
        case ModuleType():
            return package
        case str():
            return importlib.import_module(package)
