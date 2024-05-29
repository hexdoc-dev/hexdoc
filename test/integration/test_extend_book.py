from pathlib import Path
from typing import Any

import pytest
from hexdoc._hooks import HexdocPlugin
from hexdoc.cli.utils.load import init_context
from hexdoc.core import I18n, ModResourceLoader, PathResourceDir, PluginResourceDir
from hexdoc.core.compat import MinecraftVersion
from hexdoc.core.properties import EnvironmentVariableProps, Properties, TexturesProps
from hexdoc.core.resource import ResourceLocation
from hexdoc.graphics.loader import ImageLoader
from hexdoc.graphics.renderer import ModelRenderer
from hexdoc.patchouli.book import Book
from hexdoc.patchouli.book_context import BookContext
from hexdoc.patchouli.text import FormattingContext
from hexdoc.plugin import PluginManager
from pytest import MonkeyPatch
from yarl import URL

from ..tree import write_file_tree


@pytest.fixture(scope="session", autouse=True)
def patch_session(monkeysession: MonkeyPatch):
    monkeysession.setattr(MinecraftVersion, "MINECRAFT_VERSION", "1.19.2")


@pytest.fixture
def pm(empty_pm: PluginManager):
    empty_pm.register(HexdocPlugin, "hexdoc")
    return empty_pm


@pytest.fixture
def parent_props(tmp_path: Path):
    parent_path = tmp_path / "parent_resources"

    write_file_tree(
        parent_path,
        {
            "assets/parent/lang/en_us.json": {
                "item.minecraft.stone": "Stone",
                "parent.book": "parent book",
                "parent.category": "parent category",
                "parent.description": "parent description",
                "parent.entry": "parent entry",
                "parent.landing_text": "parent landing text",
            },
            "data/parent/patchouli_books/parentbook": {
                "en_us/categories/parent_category.json": {
                    "name": "parent.category",
                    "description": "parent.description",
                    "icon": "minecraft:stone",
                },
                "en_us/entries/parent_entry.json": {
                    "name": "parent.entry",
                    "category": "parent:parent_category",
                    "icon": "minecraft:stone",
                    "pages": [],
                },
                "book.json": {
                    "name": "parent.book",
                    "landing_text": "parent.landing_text",
                },
            },
        },
    )

    return Properties(
        props_dir=parent_path,
        modid="parent",
        book=ResourceLocation("parent", "parentbook"),
        default_lang="en_us",
        resource_dirs=[
            PathResourceDir.model_construct(path=parent_path, external=False),
            PluginResourceDir(modid="hexdoc"),
        ],
        textures=TexturesProps(
            strict=False,
        ),
        default_branch="",
        env=EnvironmentVariableProps(
            github_repository="",
            github_sha="",
            github_pages_url=URL("https://example.com"),
        ),
    )


@pytest.fixture
def child_props(tmp_path: Path, parent_props: Properties):
    parent_path = parent_props.props_dir
    child_path = tmp_path / "child_resources"

    write_file_tree(
        child_path,
        {
            "assets/child/lang/en_us.json": {
                "child.book": "child book",
                "child.entry": "child entry",
                "child.landing_text": "child landing text",
            },
            "data/child/patchouli_books/childbook": {
                "en_us/entries/child_entry.json": {
                    "name": "child.entry",
                    "category": "parent:parent_category",
                    "icon": "minecraft:stone",
                    "pages": [],
                },
                "book.json": {
                    "extend": "parent:parentbook",
                    "name": "child.book",
                    "landing_text": "child.landing_text",
                },
            },
        },
    )

    return Properties(
        props_dir=child_path,
        modid="child",
        book=ResourceLocation("child", "childbook"),
        default_lang="en_us",
        resource_dirs=[
            PathResourceDir.model_construct(path=child_path, external=False),
            PathResourceDir.model_construct(path=parent_path, external=True),
            PluginResourceDir(modid="hexdoc"),
        ],
        textures=TexturesProps(
            strict=False,
        ),
        default_branch="",
        env=EnvironmentVariableProps(
            github_repository="",
            github_sha="",
            github_pages_url=URL("https://example.com"),
        ),
    )


@pytest.fixture
def parent_loader(parent_props: Properties, pm: PluginManager):
    with ModResourceLoader.load_all(parent_props, pm) as loader:
        yield loader


@pytest.fixture
def child_loader(child_props: Properties, pm: PluginManager):
    with ModResourceLoader.load_all(child_props, pm) as loader:
        yield loader


@pytest.fixture
def parent_renderer(parent_loader: ModResourceLoader):
    with ModelRenderer(loader=parent_loader) as renderer:
        yield renderer


@pytest.fixture
def child_renderer(child_loader: ModResourceLoader):
    with ModelRenderer(loader=child_loader) as renderer:
        yield renderer


@pytest.fixture
def parent_book(
    tmp_path: Path,
    pm: PluginManager,
    parent_loader: ModResourceLoader,
    parent_renderer: ModelRenderer,
):
    parent_props = parent_loader.props
    assert parent_props.book_id

    image_loader = ImageLoader(
        loader=parent_loader,
        renderer=parent_renderer,
        site_dir=tmp_path,
        site_url=URL(),
    )

    book_plugin = pm.book_plugin(parent_props.book_type)

    book_id, book_data = book_plugin.load_book_data(parent_props.book_id, parent_loader)

    i18n = I18n.load(
        parent_loader,
        enabled=book_plugin.is_i18n_enabled(book_data),
        lang=parent_props.default_lang,
    )

    with init_context(
        book_id=book_id,
        book_data=book_data,
        pm=pm,
        loader=parent_loader,
        image_loader=image_loader,
        i18n=i18n,
        all_metadata={},
    ) as context:
        book = book_plugin.validate_book(book_data, context=context)
        yield book, context


@pytest.fixture
def child_book(
    tmp_path: Path,
    pm: PluginManager,
    child_loader: ModResourceLoader,
    child_renderer: ModelRenderer,
):
    child_props = child_loader.props
    assert child_props.book_id

    image_loader = ImageLoader(
        loader=child_loader,
        renderer=child_renderer,
        site_dir=tmp_path,
        site_url=URL(),
    )

    book_plugin = pm.book_plugin(child_props.book_type)

    book_id, book_data = book_plugin.load_book_data(child_props.book_id, child_loader)

    i18n = I18n.load(
        child_loader,
        enabled=book_plugin.is_i18n_enabled(book_data),
        lang=child_props.default_lang,
    )

    with init_context(
        book_id=book_id,
        book_data=book_data,
        pm=pm,
        loader=child_loader,
        image_loader=image_loader,
        i18n=i18n,
        all_metadata={},
    ) as context:
        book = book_plugin.validate_book(book_data, context=context)
        yield book, context


def test_parent_ids(parent_book: tuple[Book, dict[str, Any]]):
    want_id = ResourceLocation("parent", "parentbook")

    _, context = parent_book
    book_ctx = BookContext.of(context)

    assert want_id == Properties.of(context).book_id
    assert want_id == FormattingContext.of(context).book_id
    assert want_id == book_ctx.book_id


def test_child_parent_ids(child_book: tuple[Book, dict[str, Any]]):
    want_id = ResourceLocation("parent", "parentbook")

    _, context = child_book
    book_ctx = BookContext.of(context)

    assert want_id == FormattingContext.of(context).book_id
    assert want_id == book_ctx.book_id


def test_child_child_ids(child_book: tuple[Book, dict[str, Any]]):
    want_id = ResourceLocation("child", "childbook")

    _, context = child_book

    assert want_id == Properties.of(context).book_id
