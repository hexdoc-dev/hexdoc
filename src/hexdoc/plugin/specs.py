from __future__ import annotations

from importlib.resources import Package
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

import pluggy
from jinja2.sandbox import SandboxedEnvironment

if TYPE_CHECKING:
    from hexdoc.core import ResourceLocation
    from hexdoc.minecraft import I18n
    from hexdoc.patchouli import BookContext, FormatTree

HEXDOC_PROJECT_NAME = "hexdoc"

hookspec = pluggy.HookspecMarker(HEXDOC_PROJECT_NAME)


_T = TypeVar("_T")

HookReturn = _T | list[_T]

HookReturns = list[HookReturn[_T]]


class PluginSpec(Protocol):
    @staticmethod
    @hookspec(firstresult=True)
    def hexdoc_mod_version() -> str | None:
        ...

    @staticmethod
    @hookspec
    def hexdoc_minecraft_version() -> list[str]:
        ...

    @staticmethod
    @hookspec
    def hexdoc_validate_format_tree(
        tree: FormatTree,
        macros: dict[str, str],
        i18n: I18n,
        book_id: ResourceLocation,
        is_0_black: bool,
    ) -> None:
        ...

    @staticmethod
    @hookspec
    def hexdoc_update_context(context: BookContext) -> None:
        ...

    @staticmethod
    @hookspec
    def hexdoc_update_jinja_env(env: SandboxedEnvironment) -> None:
        ...

    @staticmethod
    @hookspec
    def hexdoc_update_template_args(template_args: dict[str, Any]) -> None:
        ...

    @staticmethod
    @hookspec
    def hexdoc_load_resource_dirs() -> HookReturns[Package]:
        ...

    @staticmethod
    @hookspec
    def hexdoc_load_tagged_unions() -> HookReturns[Package]:
        ...

    @staticmethod
    @hookspec
    def hexdoc_load_jinja_templates() -> HookReturns[tuple[Package, str]]:
        ...


# mmmmmm, interfaces


class PluginImpl(Protocol):
    """Interface for an implementation of a hexdoc plugin hook.

    These protocols are optional - they gives better type checking, but everything will
    work fine with a standard pluggy hook implementation.
    """


class ModVersionImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_mod_version() -> str:
        """Return your plugin's mod version (eg. `0.10.3` for Hex Casting).

        This should generally use a constant from `__gradle_version__.py`.
        """
        ...


class MinecraftVersionImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_minecraft_version() -> str:
        """Return the version of Minecraft supported by this version of your plugin.

        This should generally use a constant from `__gradle_version__.py`.
        """
        ...


class ValidateFormatTreeImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_validate_format_tree(
        tree: FormatTree,
        macros: dict[str, str],
        book_id: ResourceLocation,
        i18n: I18n,
        is_0_black: bool,
    ) -> None:
        """This is called as the last step when a FormatTree (styled Patchouli text) is
        generated. You can use this to modify or validate the text and styles.

        For example, Hex Casting uses this to ensure all $(action) styles are in a link.
        """
        ...


class UpdateContextImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_update_context(context: BookContext) -> None:
        """Modify the book validation context.

        For example, Hex Casting uses this to add pattern data needed by pattern pages.
        """
        ...


class UpdateJinjaEnvImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_update_jinja_env(env: SandboxedEnvironment) -> None:
        """Modify the Jinja environment/configuration.

        This is called after hexdoc is done setting up the Jinja environment, before
        rendering the book.
        """
        ...


class UpdateTemplateArgsImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_update_template_args(template_args: dict[str, Any]) -> None:
        """Add extra template args (global variables for the Jinja templates)."""
        ...


class LoadResourceDirsImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_load_resource_dirs() -> HookReturn[Package]:
        """Return the module(s) which contain your plugin's exported book resources."""
        ...


class LoadTaggedUnionsImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_load_tagged_unions() -> HookReturn[Package]:
        """Return the module(s) which contain your plugin's tagged union subtypes."""
        ...


class LoadJinjaTemplatesImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_load_jinja_templates() -> HookReturn[tuple[Package, str]]:
        """Return the module that contains the folder with your plugin's Jinja
        templates, and the name of that folder.

        For example:
        ```py
        @hookimpl
        def hexdoc_load_jinja_templates():
            return hexdoc, "_templates"
        ```
        """
        ...
