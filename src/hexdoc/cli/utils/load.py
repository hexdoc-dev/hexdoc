import logging
from pathlib import Path
from textwrap import indent
from typing import Any, Literal, overload

from hexdoc.core import (
    MinecraftVersion,
    ModResourceLoader,
    Properties,
    ResourceLocation,
)
from hexdoc.data import HexdocMetadata, load_metadata_textures
from hexdoc.minecraft import I18n, Tag
from hexdoc.minecraft.assets import (
    AnimatedTexture,
    HexdocAssetLoader,
    PNGTexture,
    Texture,
    TextureContext,
    TextureLookups,
)
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
        logger.info(f"Loading and rendering textures to {asset_loader.render_dir}.")
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


# TODO: refactor a lot of this out
def init_context(
    *,
    book_id: ResourceLocation,
    book_data: dict[str, Any],
    pm: PluginManager,
    loader: ModResourceLoader,
    i18n: I18n,
    all_metadata: dict[str, HexdocMetadata],
):
    props = loader.props

    context = dict[str, Any]()

    for item in [
        props,
        pm,
        loader,
        i18n,
        TextureContext(
            textures=load_metadata_textures(all_metadata),
            allowed_missing_textures=props.textures.missing,
        ),
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
        ),
    ]:
        item.add_to_context(context)

    for item in pm.update_context(context):
        item.add_to_context(context)

    return context
