from __future__ import annotations

from importlib.resources import Package
from typing import TYPE_CHECKING, Any, Protocol

import pluggy

from hexdoc.utils import ValidationContext

from .book_plugin import BookPlugin
from .mod_plugin import ModPlugin
from .types import HookReturn, HookReturns

if TYPE_CHECKING:
    from hexdoc.core import Properties, ResourceLocation
    from hexdoc.minecraft import I18n
    from hexdoc.patchouli import FormatTree

HEXDOC_PROJECT_NAME = "hexdoc"

hookspec = pluggy.HookspecMarker(HEXDOC_PROJECT_NAME)


class PluginSpec(Protocol):
    @staticmethod
    @hookspec
    def hexdoc_book_plugin() -> HookReturns[BookPlugin[Any]]: ...

    @staticmethod
    @hookspec
    def hexdoc_mod_plugin(branch: str, props: Properties) -> HookReturns[ModPlugin]: ...

    @staticmethod
    @hookspec
    def hexdoc_validate_format_tree(
        tree: FormatTree,
        macros: dict[str, str],
        i18n: I18n,
        book_id: ResourceLocation,
        is_0_black: bool,
        link_overrides: dict[str, str],
    ) -> None: ...

    @staticmethod
    @hookspec
    def hexdoc_update_context(
        context: dict[str, Any],
    ) -> HookReturns[ValidationContext]: ...

    @staticmethod
    @hookspec
    def hexdoc_update_template_args(template_args: dict[str, Any]) -> None: ...

    @staticmethod
    @hookspec
    def hexdoc_load_tagged_unions() -> HookReturns[Package]: ...


# mmmmmm, interfaces


class PluginImpl(Protocol):
    """Interface for an implementation of a hexdoc plugin hook.

    These protocols are optional - they gives better type checking, but everything will
    work fine with a standard pluggy hook implementation.
    """


class BookPluginImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_book_plugin() -> HookReturn[BookPlugin[Any]]:
        """If your plugin represents a book system (like Patchouli), this must return an
        instance of a subclass of `BookPlugin` with all abstract methods implemented."""
        ...


class ModPluginImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_mod_plugin(branch: str) -> HookReturn[ModPlugin]:
        """If your plugin represents a Minecraft mod, this must return an instance of a
        subclass of `ModPlugin` or `ModPluginWithBook`, with all abstract methods
        implemented."""
        ...


class ModPluginImplWithProps(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_mod_plugin(branch: str, props: Properties) -> HookReturn[ModPlugin]:
        """If your plugin represents a Minecraft mod, this must return an instance of a
        subclass of `ModPlugin` or `ModPluginWithBook`, with all abstract methods
        implemented."""
        ...


class ValidateFormatTreeImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_validate_format_tree(
        tree: FormatTree,
        macros: dict[str, str],
        book_id: ResourceLocation,
        i18n: I18n,
        is_0_black: bool,
        link_overrides: dict[str, str],
    ) -> None:
        """This is called as the last step when a FormatTree (styled Patchouli text) is
        generated. You can use this to modify or validate the text and styles.

        For example, Hex Casting uses this to ensure all $(action) styles are in a link.
        """
        ...


class UpdateContextImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_update_context(context: dict[str, Any]) -> HookReturn[ValidationContext]:
        """Modify the book validation context.

        For example, Hex Casting uses this to add pattern data needed by pattern pages.
        """
        ...


class UpdateTemplateArgsImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_update_template_args(template_args: dict[str, Any]) -> None:
        """Add extra template args (global variables for the Jinja templates)."""
        ...


class LoadTaggedUnionsImpl(PluginImpl, Protocol):
    @staticmethod
    def hexdoc_load_tagged_unions() -> HookReturn[Package]:
        """Return the module(s) which contain your plugin's tagged union subtypes."""
        ...
