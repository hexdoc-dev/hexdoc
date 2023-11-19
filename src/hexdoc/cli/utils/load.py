import logging
from collections import defaultdict
from pathlib import Path
from typing import Literal, overload

from hexdoc.core import (
    MinecraftVersion,
    ModResourceLoader,
    Properties,
    ResourceLocation,
)
from hexdoc.data import HexdocMetadata
from hexdoc.data.metadata import load_metadata_textures
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import (
    HexdocAssetLoader,
    Texture,
    TextureLookups,
)
from hexdoc.minecraft.assets.animated import AnimatedTexture
from hexdoc.minecraft.assets.textures import PNGTexture
from hexdoc.model import init_context
from hexdoc.patchouli import Book, BookContext
from hexdoc.plugin import ModPlugin, ModPluginWithBook, PluginManager
from hexdoc.utils import cast_or_raise

from .logging import setup_logging

logger = logging.getLogger(__name__)


@overload
def load_common_data(
    props_file: Path,
    verbosity: int,
    branch: str,
    book: Literal[True],
) -> tuple[Properties, PluginManager, ModPluginWithBook]:
    ...


@overload
def load_common_data(
    props_file: Path,
    verbosity: int,
    branch: str,
    book: bool = False,
) -> tuple[Properties, PluginManager, ModPlugin]:
    ...


def load_common_data(
    props_file: Path,
    verbosity: int,
    branch: str,
    book: bool = False,
) -> tuple[Properties, PluginManager, ModPlugin]:
    setup_logging(verbosity)

    props = Properties.load(props_file)
    pm = PluginManager(branch)

    plugin = pm.mod_plugin(props.modid, book=book)
    logging.getLogger(__name__).info(
        f"Loading hexdoc for {props.modid} {plugin.full_version}"
    )

    minecraft_version = MinecraftVersion.MINECRAFT_VERSION = pm.minecraft_version()
    if minecraft_version is None:
        logging.getLogger(__name__).warning(
            "No plugins implement minecraft_version. All versions may be used."
        )

    return props, pm, plugin


def render_textures_and_export_metadata(
    loader: ModResourceLoader,
    asset_loader: HexdocAssetLoader,
):
    all_metadata = loader.load_metadata(model_type=HexdocMetadata)

    all_lookups = load_metadata_textures(all_metadata)
    image_textures = {
        id: texture
        for texture_type in [PNGTexture, AnimatedTexture]
        for id, texture in texture_type.get_lookup(all_lookups).items()
    }

    internal_lookups = TextureLookups[Texture](dict)
    for id, texture in asset_loader.load_and_render_internal_textures(image_textures):
        texture.insert_texture(internal_lookups, id)

    # this mod's metadata
    metadata = HexdocMetadata(
        book_url=asset_loader.site_url,
        asset_url=loader.props.env.asset_url,
        textures=internal_lookups,
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


def load_book(
    *,
    book_id: ResourceLocation,
    pm: PluginManager,
    loader: ModResourceLoader,
    i18n: I18n,
    all_metadata: dict[str, HexdocMetadata],
):
    book_data = Book.load_book_json(loader, book_id)

    with init_context(book_data):
        context = BookContext(
            pm=pm,
            loader=loader,
            i18n=i18n,
            # id is inserted by Book.load_book_json
            book_id=cast_or_raise(book_data["id"], ResourceLocation),
            all_metadata=all_metadata,
            textures=defaultdict(dict),
            allowed_missing_textures=loader.props.textures.missing,
        )
        pm.update_context(context)

    book = Book.load_all_from_data(book_data, context)

    return book, context
