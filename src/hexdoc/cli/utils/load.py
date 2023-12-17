import logging
from pathlib import Path
from typing import Any, Literal, overload

from hexdoc.core import (
    MinecraftVersion,
    ModResourceLoader,
    Properties,
    ResourceLocation,
)
from hexdoc.data import HexdocMetadata
from hexdoc.data.metadata import load_metadata_textures
from hexdoc.minecraft import I18n, Tag
from hexdoc.minecraft.assets import (
    HexdocAssetLoader,
    Texture,
    TextureLookups,
)
from hexdoc.minecraft.assets.animated import AnimatedTexture
from hexdoc.minecraft.assets.textures import PNGTexture, TextureContext
from hexdoc.patchouli import Book, BookContext
from hexdoc.patchouli.text import DEFAULT_MACROS, FormattingContext
from hexdoc.plugin import ModPlugin, ModPluginWithBook, PluginManager
from hexdoc.utils import cast_or_raise

logger = logging.getLogger(__name__)


@overload
def load_common_data(
    props_file: Path,
    branch: str,
    *,
    book: Literal[True],
) -> tuple[Properties, PluginManager, ModPluginWithBook]:
    ...


@overload
def load_common_data(
    props_file: Path,
    branch: str,
    *,
    book: bool = False,
) -> tuple[Properties, PluginManager, ModPlugin]:
    ...


def load_common_data(
    props_file: Path,
    branch: str,
    *,
    book: bool = False,
) -> tuple[Properties, PluginManager, ModPlugin]:
    props = Properties.load(props_file)
    pm = PluginManager(branch, props)

    plugin = pm.mod_plugin(props.modid, book=book)
    logging.getLogger(__name__).info(
        f"Loading hexdoc for {props.modid} {plugin.full_version}."
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
    if loader.props.textures.enabled:
        logger.info("Loading and rendering textures.")
        for id, texture in asset_loader.load_and_render_internal_textures(
            image_textures
        ):
            texture.insert_texture(internal_lookups, id)

    # this mod's metadata
    metadata = HexdocMetadata(
        book_url=asset_loader.site_url / loader.props.default_lang,
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
    props = loader.props

    context = dict[str, Any]()
    for item in [pm, loader, props, i18n]:
        item.add_to_context(context)

    TextureContext(
        textures=load_metadata_textures(all_metadata),
        allowed_missing_textures=props.textures.missing,
    ).add_to_context(context)

    book_data = Book.load_book_json(loader, book_id)
    BookContext(
        modid=props.modid,
        spoilered_advancements=Tag.SPOILERED_ADVANCEMENTS.load(loader).value_ids_set,
        all_metadata=all_metadata,
    ).add_to_context(context)

    FormattingContext(
        book_id=cast_or_raise(book_data["id"], ResourceLocation),
        macros=DEFAULT_MACROS | book_data.get("macros", {}) | props.macros,
    ).add_to_context(context)

    for item in pm.update_context(context):
        item.add_to_context(context)

    book = Book.load_all_from_data(book_data, context=context)

    return book, context
