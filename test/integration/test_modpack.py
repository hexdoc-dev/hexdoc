from pathlib import Path
from typing import Any

import pytest
from hexdoc._hooks import HexdocPlugin
from hexdoc.cli.utils.load import load_book
from hexdoc.core import ModResourceLoader
from hexdoc.core.compat import MinecraftVersion
from hexdoc.core.properties import Properties
from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft import I18n
from hexdoc.patchouli.book import Book
from hexdoc.patchouli.text import FormatTree
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
def props(tmp_path: Path):
    write_file_tree(
        tmp_path,
        {
            "doc": {},  # lie
            "patchouli_books/modpackbook": {
                "en_us/categories/modpack_category.json": {
                    "name": "category name",
                    "description": "category description",
                    "icon": "minecraft:stone",
                },
                "en_us/entries/modpack_entry.json": {
                    "name": "entry name",
                    "category": "patchouli:modpack_category",
                    "icon": "minecraft:stone",
                    "pages": [],
                },
                "book.json": {
                    "name": "book name",
                    "landing_text": "book landing text",
                    "i18n": False,
                },
            },
            "resources/assets/minecraft/lang/en_us.json": {
                "item.minecraft.stone": "Stone",
            },
        },
    )

    return Properties.load_data(
        props_dir=tmp_path / "doc",
        data={
            "modid": "patchouli",
            "book": "patchouli:modpackbook",
            "default_lang": "en_us",
            "default_branch": "main",
            "resource_dirs": [
                {"patchouli_books": "../patchouli_books"},
                {"modid": "hexdoc"},
            ],
            "textures": {
                "missing": ["minecraft:stone"],
            },
        },
    )


@pytest.fixture
def loader(props: Properties, pm: PluginManager):
    with ModResourceLoader.load_all(props, pm) as loader:
        yield loader


@pytest.fixture
def book_and_context(pm: PluginManager, loader: ModResourceLoader):
    props = loader.props
    assert props.book_id

    book_data = Book.load_book_json(loader, props.book_id)

    i18n = I18n.load(loader, book_data, props.default_lang)

    yield load_book(
        book_data=book_data,
        pm=pm,
        loader=loader,
        i18n=i18n,
        all_metadata={},
    )


def test_book_name(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    assert book.name == "book name"


def test_book_landing_text(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    match book.landing_text:
        case FormatTree(children=[FormatTree(children=["book landing text"])]):
            pass
        case _:
            raise AssertionError(book.landing_text)


def test_number_of_categories(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    assert len(book.categories) == 1


def test_category_id(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    id, category = book.categories.popitem()

    assert category.id == id == ResourceLocation("patchouli", "modpack_category")


def test_category_name(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    _, category = book.categories.popitem()

    assert category.name == "category name"


def test_number_of_entries(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    _, category = book.categories.popitem()

    assert len(category.entries) == 1


def test_entry_name(book_and_context: tuple[Book, dict[str, Any]]):
    book, _ = book_and_context

    _, category = book.categories.popitem()
    _, entry = category.entries.popitem()

    assert entry.name == "entry name"
