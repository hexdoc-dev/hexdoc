import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, overload

from hexdoc.core import (
    MinecraftVersion,
    ModResourceLoader,
    Properties,
    ResourceLocation,
)
from hexdoc.data import HexdocMetadata
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import (
    HexdocAssetLoader,
    Texture,
    TextureLookups,
)
from hexdoc.model import init_context
from hexdoc.patchouli import Book, BookContext
from hexdoc.plugin import PluginManager
from hexdoc.utils import cast_or_raise

from .logging import setup_logging

logger = logging.getLogger(__name__)


def load_common_data(props_file: Path, verbosity: int):
    """props, pm, version"""
    setup_logging(verbosity)

    props = Properties.load(props_file)
    pm = PluginManager()

    version = load_version(props, pm)
    minecraft_version = MinecraftVersion.MINECRAFT_VERSION = pm.minecraft_version()
    if minecraft_version is None:
        logger.warning(
            "No plugins implement hexdoc_minecraft_version, "
            "per-version validation will fail"
        )

    return props, pm, version


def load_version(props: Properties, pm: PluginManager):
    version = pm.mod_version(props.modid)
    logger.info(f"Loading hexdoc for {props.modid} {version}")
    return version


def export_metadata(
    props: Properties,
    pm: PluginManager,
    loader: ModResourceLoader,
    asset_loader: HexdocAssetLoader,
):
    lookups = TextureLookups[Texture](dict)

    for texture_id, texture in asset_loader.load_and_render_internal_textures():
        texture.insert_texture(lookups, texture_id)

    # this mod's metadata
    version = pm.mod_version(props.modid)

    metadata = HexdocMetadata(
        book_url=f"{props.url}/v/{version}" if version else None,
        asset_url=props.env.asset_url,
        textures=lookups,
    )

    loader.export(
        metadata.path(props.modid),
        metadata.model_dump_json(
            by_alias=True,
            warnings=False,
            exclude_defaults=True,
            round_trip=True,
        ),
        cache=True,
    )

    return metadata


@overload
def load_book(
    book_id: ResourceLocation,
    props: Properties,
    pm: PluginManager,
    loader: ModResourceLoader,
    lang: str | None,
    allow_missing: bool,
) -> tuple[str, Book, I18n, BookContext]:
    ...


@overload
def load_book(
    book_id: None,
    props: Properties,
    pm: PluginManager,
    loader: ModResourceLoader,
    lang: str | None,
    allow_missing: bool,
) -> tuple[str, None, I18n, None]:
    ...


def load_book(
    book_id: ResourceLocation | None,
    props: Properties,
    pm: PluginManager,
    loader: ModResourceLoader,
    lang: str | None,
    allow_missing: bool,
) -> tuple[str, Book | None, I18n, BookContext | None]:
    """lang, book, i18n"""
    if lang is None:
        lang = props.default_lang

    all_metadata = loader.load_metadata(model_type=HexdocMetadata)
    i18n = _load_i18n(loader, None, allow_missing)[lang]

    if book_id:
        data = Book.load_book_json(loader, book_id)
        book, context = _load_book(data, pm, loader, i18n, all_metadata)
    else:
        book = None
        context = None

    return lang, book, i18n, context


def load_books(
    book_id: ResourceLocation,
    props: Properties,
    pm: PluginManager,
    lang: str | None,
    allow_missing: bool,
):
    """books, all_metadata"""
    with ModResourceLoader.load_all(props, pm) as loader:
        all_metadata = loader.load_metadata(model_type=HexdocMetadata)

        book_data = Book.load_book_json(loader, book_id)
        books = dict[str, tuple[Book, I18n, BookContext]]()

        for lang, i18n in _load_i18n(loader, lang, allow_missing).items():
            book, context = _load_book(book_data, pm, loader, i18n, all_metadata)
            books[lang] = (book, i18n, context)
            loader.export_dir = None  # only export the first (default) book

        return books, all_metadata


def _load_book(
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
            textures=defaultdict(dict),
            allowed_missing_textures=loader.props.textures.missing,
        )
        pm.update_context(context)
    return Book.load_all_from_data(data, context), context


def _load_i18n(
    loader: ModResourceLoader,
    lang: str | None,
    allow_missing: bool,
) -> dict[str, I18n]:
    # only load the specified language
    if lang is not None:
        i18n = I18n.load(
            loader,
            lang=lang,
            allow_missing=allow_missing,
        )
        return {lang: i18n}

    # load everything
    per_lang_i18n = I18n.load_all(
        loader,
        allow_missing=allow_missing,
    )

    # ensure the default lang is loaded first
    default_lang = loader.props.default_lang
    default_i18n = per_lang_i18n.pop(default_lang)

    return {default_lang: default_i18n} | per_lang_i18n
