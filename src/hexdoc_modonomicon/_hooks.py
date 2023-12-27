# pyright: reportPrivateUsage=false

from importlib.resources import Package
from typing import Any, Mapping

from hexdoc.core import ModResourceLoader, ResourceLocation

# from hexdoc.patchouli import BookContext
from hexdoc.plugin import (
    BookPlugin,
    BookPluginImpl,
    HookReturn,
    LoadTaggedUnionsImpl,
    hookimpl,
)
from hexdoc.utils import ContextSource, JSONDict, cast_context

from hexdoc_modonomicon.book import Modonomicon


class ModonomiconPlugin(LoadTaggedUnionsImpl, BookPluginImpl):
    @staticmethod
    @hookimpl
    def hexdoc_book_plugin() -> BookPlugin[Any]:
        return ModonomiconBookPlugin()

    @staticmethod
    @hookimpl
    def hexdoc_load_tagged_unions() -> HookReturn[Package]:
        return []


class ModonomiconBookPlugin(BookPlugin[Modonomicon]):
    @property
    def modid(self):
        return "modonomicon"

    def load_book_data(
        self,
        book_id: ResourceLocation,
        loader: ModResourceLoader,
    ) -> tuple[ResourceLocation, JSONDict]:
        _, data = loader.load_resource("data", "modonomicon", book_id / "book")
        return book_id, data

    def is_i18n_enabled(self, book_data: Mapping[str, Any]):
        return True

    def validate_book(
        self,
        book_data: Mapping[str, Any],
        *,
        context: ContextSource,
    ):
        # loader = ModResourceLoader.of(context)
        # book_ctx = BookContext.of(context)

        book = Modonomicon.model_validate(book_data, context=cast_context(context))
        # book._load_categories(context, book_ctx)
        # book._load_entries(context, book_ctx, loader)

        return book
