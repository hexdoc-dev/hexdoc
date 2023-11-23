from pathlib import Path

import pytest
from hexdoc._hooks import HexdocPlugin
from hexdoc.cli.utils.load import load_book
from hexdoc.core import ModResourceLoader, PathResourceDir, PluginResourceDir
from hexdoc.core.compat import MinecraftVersion
from hexdoc.core.properties import EnvironmentVariableProps, Properties, TexturesProps
from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft import I18n
from hexdoc.patchouli.book import Book
from hexdoc.patchouli.book_context import BookContext
from hexdoc.plugin import PluginManager
from pytest import MonkeyPatch

from ..conftest import write_file_tree


@pytest.fixture(scope="session", autouse=True)
def patch_session(monkeysession: MonkeyPatch):
    monkeysession.setattr(MinecraftVersion, "MINECRAFT_VERSION", "1.19.2")


@pytest.fixture
def pm(empty_pm: PluginManager):
    empty_pm.inner.register(HexdocPlugin, "hexdoc")
    empty_pm.init_mod_plugins()
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
            "data/hexdoc/tags/advancements/spoilered.json": {
                "values": [],
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
            missing=set([ResourceLocation("minecraft", "stone")]),
        ),
        default_branch="",
        env=EnvironmentVariableProps(
            github_repository="",
            github_sha="",
            github_pages_url="",
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
            missing=set([ResourceLocation("minecraft", "stone")]),
        ),
        default_branch="",
        env=EnvironmentVariableProps(
            github_repository="",
            github_sha="",
            github_pages_url="",
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
def parent_book(pm: PluginManager, parent_loader: ModResourceLoader):
    parent_props = parent_loader.props
    assert parent_props.book_id

    i18n = I18n.load(parent_loader, parent_props.default_lang)

    return load_book(
        book_id=parent_props.book_id,
        pm=pm,
        loader=parent_loader,
        i18n=i18n,
        all_metadata={},
    )


@pytest.fixture
def child_book(pm: PluginManager, child_loader: ModResourceLoader):
    child_props = child_loader.props
    assert child_props.book_id

    i18n = I18n.load(child_loader, child_props.default_lang)

    return load_book(
        book_id=child_props.book_id,
        pm=pm,
        loader=child_loader,
        i18n=i18n,
        all_metadata={},
    )


def test_parent_ids(parent_book: tuple[Book, BookContext]):
    book, context = parent_book

    want_id = ResourceLocation("parent", "parentbook")

    assert want_id == context.props.book_id
    assert want_id == context.book_id
    assert want_id == book.id


def test_child_parent_ids(child_book: tuple[Book, BookContext]):
    book, context = child_book

    want_id = ResourceLocation("parent", "parentbook")

    assert want_id == context.book_id
    assert want_id == book.id


def test_child_child_ids(child_book: tuple[Book, BookContext]):
    _, context = child_book

    want_id = ResourceLocation("child", "childbook")

    assert want_id == context.props.book_id
