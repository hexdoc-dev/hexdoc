import logging
from contextlib import contextmanager
from pathlib import Path
from textwrap import indent
from typing import Any, Literal, overload

from yarl import URL

from hexdoc.core import (
    I18n,
    MinecraftVersion,
    ModResourceLoader,
    Properties,
    ResourceLocation,
)
from hexdoc.data import HexdocMetadata
from hexdoc.graphics.loader import ImageLoader
from hexdoc.minecraft import Tag
from hexdoc.model import init_context as set_init_context
from hexdoc.patchouli import BookContext
from hexdoc.patchouli.text import DEFAULT_MACROS, FormattingContext
from hexdoc.plugin import BookPlugin, ModPlugin, ModPluginWithBook, PluginManager

from .info import get_header

logger = logging.getLogger(__name__)


@overload
def load_common_data(
    props_file: Path,
    branch: str,
    *,
    book: Literal[True],
) -> tuple[Properties, PluginManager, BookPlugin[Any], ModPluginWithBook]: ...


@overload
def load_common_data(
    props_file: Path,
    branch: str,
    *,
    book: bool = False,
) -> tuple[Properties, PluginManager, BookPlugin[Any], ModPlugin]: ...


def load_common_data(
    props_file: Path,
    branch: str,
    *,
    book: bool = False,
) -> tuple[Properties, PluginManager, BookPlugin[Any], ModPlugin]:
    props = Properties.load(props_file)
    pm = PluginManager(branch, props)

    book_plugin = pm.book_plugin(props.book_type)
    mod_plugin = pm.mod_plugin(props.modid, book=book)

    header = get_header(props, pm, mod_plugin)
    logger.info(f"Loading hexdoc.\n{indent(header, '  ')}")

    minecraft_version = MinecraftVersion.MINECRAFT_VERSION = pm.minecraft_version()
    if minecraft_version is None:
        logger.warning(
            "No plugins implement minecraft_version. All versions may be used."
        )

    return props, pm, book_plugin, mod_plugin


def export_metadata(loader: ModResourceLoader, site_url: URL):
    all_metadata = loader.load_metadata(model_type=HexdocMetadata)

    # this mod's metadata
    metadata = HexdocMetadata(
        book_url=site_url / loader.props.default_lang,
        asset_url=loader.props.env.asset_url,
    )

    loader.export(
        metadata.path(loader.props.modid),
        metadata.model_dump_json(
            by_alias=True,
            warnings=False,
            exclude_defaults=True,
            round_trip=True,
        ),
        cache=True,
    )

    return all_metadata | {loader.props.modid: metadata}


# TODO: refactor a lot of this out
@contextmanager
def init_context(
    *,
    book_id: ResourceLocation,
    book_data: dict[str, Any],
    pm: PluginManager,
    loader: ModResourceLoader,
    image_loader: ImageLoader,
    i18n: I18n,
    all_metadata: dict[str, HexdocMetadata],
):
    """This is only a contextmanager so it can call `hexdoc.model.init_context`."""

    props = loader.props

    context = dict[str, Any]()

    for item in [
        props,
        pm,
        loader,
        image_loader,
        i18n,
        FormattingContext(
            book_id=book_id,
            macros=DEFAULT_MACROS | book_data.get("macros", {}) | props.macros,
        ),
        BookContext(
            modid=props.modid,
            book_id=book_id,
            spoilered_advancements=Tag.SPOILERED_ADVANCEMENTS.load(
                loader
            ).value_ids_set,
            all_metadata=all_metadata,
            flags=pm.load_flags(),
        ),
    ]:
        item.add_to_context(context)

    for item in pm.update_context(context):
        item.add_to_context(context)

    with set_init_context(context):
        yield context
