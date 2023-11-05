import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable

from hexdoc.core.loader import BookFolder, ModResourceLoader
from hexdoc.core.properties import Properties
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir
from hexdoc.utils.deserialize.json import JSONDict


def patchi_book(
    resources: Path,
    book_id: ResourceLocation,
    lang: str,
    folder: BookFolder,
):
    path = (
        resources
        / "data"
        / book_id.namespace
        / "patchouli_books"
        / book_id.path
        / lang
        / folder
    )
    path.mkdir(parents=True)
    return path


def load_book_assets(
    loader: ModResourceLoader,
    book_id: ResourceLocation,
    folder: BookFolder,
    key: Callable[[JSONDict], Any],
):
    assets = list(
        data
        for _, _, data in loader.load_book_assets(
            book_id=book_id,
            folder=folder,
            use_resource_pack=False,
        )
    )
    return sorted(assets, key=key)


def test_multi_book(tmp_path: Path):
    resources = tmp_path / "resources"

    resource_dirs = [
        PathResourceDir.model_construct(path=resources),
    ]

    hexcasting_id = ResourceLocation("hexcasting", "thehexbook")
    hexal_id = ResourceLocation("hexal", "hexalbook")
    hexgloop_id = ResourceLocation("hexgloop", "hexgloopbook")

    for book_id in [hexcasting_id, hexal_id, hexgloop_id]:
        data = {"id": str(book_id)}

        path = patchi_book(resources, book_id, "en_us", "categories")
        with open(path / "tmp.json", "w") as f:
            json.dump(data, f)

    def sortkey(v: JSONDict) -> str:
        return str(v["id"])

    props = Properties.model_construct(
        modid="hexal",
        book=hexal_id,
        default_lang="en_us",
        extra_books=[],
        resource_dirs=resource_dirs,
    )

    with ExitStack() as stack:
        loader = ModResourceLoader(
            props=props,
            root_book_id=hexcasting_id,
            export_dir=None,
            resource_dirs=resource_dirs,
            _stack=stack,
        )

        assert load_book_assets(loader, hexal_id, "categories", key=sortkey) == [
            {"id": str(hexal_id)},
            {"id": str(hexcasting_id)},
        ]

        props.extra_books.append(hexgloop_id)

        assert load_book_assets(loader, hexal_id, "categories", key=sortkey) == [
            {"id": str(hexal_id)},
            {"id": str(hexcasting_id)},
            {"id": str(hexgloop_id)},
        ]
