from typing import Any, Mapping

from hexdoc.core.loader import ModResourceLoader
from hexdoc.core.metadata import HexdocMetadata
from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft import I18n
from hexdoc.model import init_context
from hexdoc.patchouli import Book
from hexdoc.patchouli.book_context import BookContext
from hexdoc.plugin import PluginManager
from hexdoc.utils.deserialize import cast_or_raise


def load_hex_book(
    data: Mapping[str, Any],
    pm: PluginManager,
    loader: ModResourceLoader,
    i18n: I18n,
    all_metadata: dict[str, HexdocMetadata],
):
    with init_context(data):
        context = BookContext(
            pm=pm,
            loader=loader,
            i18n=i18n,
            # this SHOULD be set (as a ResourceLocation) by Book.get_book_json
            book_id=cast_or_raise(data["id"], ResourceLocation),
            all_metadata=all_metadata,
        )
    return Book.load_all_from_data(data, context)
