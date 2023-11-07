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
    Never,
    ParamSpec,
    Sequence,
    TypeVar,
    overload,
)

import pluggy
from jinja2 import PackageLoader
from jinja2.sandbox import SandboxedEnvironment

from hexdoc.utils import PydanticOrderedSet

if TYPE_CHECKING:
    from hexdoc.core import ResourceLocation
    from hexdoc.minecraft import I18n
    from hexdoc.patchouli import BookContext, FormatTree

from .specs import HEXDOC_PROJECT_NAME, HookReturns, PluginSpec

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

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> Never:
        ...


class PluginManager:
    """Custom hexdoc plugin manager with helpers and stronger typing."""

    def __init__(self) -> None:
        self.inner = pluggy.PluginManager(HEXDOC_PROJECT_NAME)
        self.inner.add_hookspecs(PluginSpec)
        self.inner.load_setuptools_entrypoints(HEXDOC_PROJECT_NAME)
        self.inner.check_pending()

    def mod_version(self, modid: str):
        return self._hook_caller(PluginSpec.hexdoc_mod_version, modid)()

    def minecraft_version(self) -> str:
        versions = dict[str, str]()

        for modid, caller in self._all_callers(PluginSpec.hexdoc_minecraft_version):
            caller_versions = set(caller.try_call() or [])
            if not caller_versions:
                continue

            if len(caller_versions) > 1:
                raise ValueError(
                    f"{modid} returned multiple Minecraft versions, expected at most 1: "
                    + ", ".join(caller_versions)
                )

            versions[modid] = caller_versions.pop()

        match len(set(versions.values())):
            case 0:
                raise ValueError("No plugins implement hexdoc_minecraft_version")
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
    ):
        caller = self._hook_caller(PluginSpec.hexdoc_validate_format_tree)
        caller.try_call(
            tree=tree,
            macros=macros,
            book_id=book_id,
            i18n=i18n,
            is_0_black=is_0_black,
        )
        return tree

    def update_context(self, context: BookContext):
        caller = self._hook_caller(PluginSpec.hexdoc_update_context)
        caller.try_call(context=context)
        return context

    def update_jinja_env(self, env: SandboxedEnvironment):
        caller = self._hook_caller(PluginSpec.hexdoc_update_jinja_env)
        caller.try_call(env=env)
        return env

    def update_template_args(self, template_args: dict[str, Any]):
        caller = self._hook_caller(PluginSpec.hexdoc_update_template_args)
        caller.try_call(template_args=template_args)
        return template_args

    def load_resources(self, modid: str) -> Iterator[ModuleType]:
        yield from self._import_from_hook(PluginSpec.hexdoc_load_resource_dirs, modid)

    def load_tagged_unions(self, modid: str | None = None) -> Iterator[ModuleType]:
        yield from self._import_from_hook(PluginSpec.hexdoc_load_tagged_unions, modid)

    def load_jinja_templates(self, modids: Sequence[str]):
        """modid -> PackageLoader"""
        included = dict[str, PackageLoader]()
        extra = dict[str, PackageLoader]()

        modid_set = set(modids)
        for modid, caller in self._all_callers(
            PluginSpec.hexdoc_load_jinja_templates, modids
        ):
            try:
                package, package_path = caller()[0]
            except PluginNotFoundError:
                if modid in modid_set:
                    raise
                continue

            package_name = import_package(package).__name__
            loader = PackageLoader(package_name, package_path)

            if modid in modid_set:
                included[modid] = loader
            else:
                extra[modid] = loader

        return included, extra

    def default_rendered_templates(self, modids: Iterable[str]) -> dict[Path, str]:
        templates = dict[str | Path, str]()
        for modid in modids:
            self._hook_caller(
                spec=PluginSpec.hexdoc_default_rendered_templates,
                modid=modid,
            ).try_call(templates=templates)
        return {Path(path): template for path, template in templates.items()}

    def _import_from_hook(
        self,
        __spec: Callable[_P, HookReturns[Package]],
        __modid: str | None = None,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Iterator[ModuleType]:
        packages = self._hook_caller(__spec, __modid)(*args, **kwargs)
        for package in flatten(packages):
            yield import_package(package)

    def _all_callers(
        self,
        spec: Callable[_P, _R | None],
        preferred_modids: Sequence[str] = (),
    ) -> Iterator[tuple[str, TypedHookCaller[_P, _R]]]:
        # if provided, always return preferred callers first in the given order
        preferred_modids = PydanticOrderedSet(preferred_modids)
        for modid, _ in self.inner.list_name_plugin():
            preferred_modids.add(modid)

        for modid in preferred_modids:
            caller = self._hook_caller(spec, modid)
            yield modid, caller

    @overload
    def _hook_caller(
        self,
        spec: Callable[_P, None],
        modid: str | None = None,
    ) -> _NoCallTypedHookCaller[_P]:
        ...

    @overload
    def _hook_caller(
        self,
        spec: Callable[_P, _R | None],
        modid: str | None = None,
    ) -> TypedHookCaller[_P, _R]:
        ...

    def _hook_caller(
        self,
        spec: Callable[_P, _R | None],
        modid: str | None = None,
    ) -> TypedHookCaller[_P, _R]:
        """Returns a hook caller for the named method which only manages calls to a
        specific modid (aka plugin name)."""

        if modid is None:
            remove_plugins = []
        else:
            if not self.inner.has_plugin(modid):
                raise PluginNotFoundError(f"Plugin {modid} does not exist")
            remove_plugins = [
                plugin
                for name, plugin in self.inner.list_name_plugin()
                if name != modid
            ]

        caller = self.inner.subset_hook_caller(spec.__name__, remove_plugins)

        return TypedHookCaller(modid, caller)


def flatten(values: list[list[_T] | _T]) -> Iterator[_T]:
    for value in values:
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
