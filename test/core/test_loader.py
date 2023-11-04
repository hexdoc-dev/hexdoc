import json
from contextlib import ExitStack
from pathlib import Path
from typing import Literal

from hexdoc.core.loader import ModResourceLoader
from hexdoc.core.properties import Properties
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir


def patchi_book(
    resources: Path,
    book_id: ResourceLocation,
    lang: str,
    folder: Literal["categories", "entries", "templates"],
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

    props = Properties.model_construct(
        modid="hexal",
        book=hexal_id,
        default_lang="en_us",
        extra_books=[hexgloop_id],
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

        assets = list(
            data
            for _, _, data in loader.load_book_assets(
                book_id=hexal_id,
                folder="categories",
                use_resource_pack=False,
            )
        )

        sorted_assets = sorted(assets, key=lambda v: str(v["id"]))
        assert sorted_assets == [
            {"id": str(hexal_id)},
            {"id": str(hexcasting_id)},
            {"id": str(hexgloop_id)},
        ]
