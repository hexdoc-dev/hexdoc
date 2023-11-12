from collections.abc import Set
from typing import Iterator

from minecraft_render import require

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.model import HexdocTypeAdapter

from ..tags import Tag
from .animated import AnimatedTexture, AnimationMeta
from .models import FoundNormalTexture, ModelItem
from .textures import ItemTexture, MultiItemTexture, PNGTexture, Texture


def TextureAdapter():
    return HexdocTypeAdapter(
        PNGTexture | ItemTexture | MultiItemTexture | AnimatedTexture
    )


# def load_png_textures(loader: ModResourceLoader):
#     for _, item_id, data in loader.load_resources(
#         "assets",
#         namespace="*",
#         folder="textures",
#         internal_only=True,
#         allow_missing=True,
#         export=False,  # we're exporting the urls as metadata, so we can skip this
#     ):


def load_and_render_internal_items(
    loader: ModResourceLoader,
    *,
    asset_url: str,
    book_version_url: str,
) -> Iterator[tuple[ResourceLocation, Texture]]:
    """For all item/block models in all internal resource dirs, yields the item id
    (eg. `hexcasting:focus`) and some kind of texture that we can use in the book."""

    gaslighting_items = Tag.GASLIGHTING_ITEMS.load(loader).value_ids_set

    found_items_from_models = set[ResourceLocation]()
    missing_items = set[ResourceLocation]()

    for _, item_id, data in loader.load_resources(
        "assets",
        namespace="*",
        folder="models/item",
        internal_only=True,
        allow_missing=True,
        export=False,  # we're exporting the urls as metadata, so we can skip this
    ):
        model = ModelItem.load_data("item" / item_id, data)
        if result := load_and_render_item(
            model,
            loader,
            gaslighting_items,
            asset_url=asset_url,
            book_version_url=book_version_url,
        ):
            found_items_from_models.add(item_id)
            yield item_id, result
        else:
            missing_items.add(item_id)

    for _, block_id, _ in loader.find_resources(
        "assets",
        namespace="*",
        folder="blockstates",
        internal_only=True,
        allow_missing=True,
    ):
        if block_id in missing_items:
            missing_items.remove(block_id)
        if block_id in found_items_from_models:
            continue
        yield block_id, render_block(block_id, loader, book_version_url)

    if missing_items:
        raise FileNotFoundError(
            "Failed to find a texture for some items: "
            + ", ".join(str(item) for item in missing_items)
        )


def load_and_render_item(
    model: ModelItem,
    loader: ModResourceLoader,
    gaslighting_items: Set[ResourceLocation],
    *,
    asset_url: str,
    book_version_url: str,
) -> Texture | None:
    match model.find_texture(loader, gaslighting_items):
        case None:
            return None

        case "gaslighting", found_textures:
            textures = list(
                render_item(
                    found_texture,
                    loader,
                    asset_url=asset_url,
                    book_version_url=book_version_url,
                ).inner
                for found_texture in found_textures
            )
            return MultiItemTexture(inner=textures, gaslighting=True)

        case found_texture:
            texture = render_item(
                found_texture,
                loader,
                asset_url=asset_url,
                book_version_url=book_version_url,
            )
            return texture


# TODO: move to methods on a class returned by find_texture?
def render_item(
    found_texture: FoundNormalTexture,
    loader: ModResourceLoader,
    *,
    asset_url: str,
    book_version_url: str,
) -> ItemTexture:
    match found_texture:
        case "texture", texture_id:
            try:
                path_stub = texture_id.file_path_stub("assets")
                _, path = loader.find_resource(path_stub)
                url = f"{asset_url}/{path.relative_to(loader.repo_root).as_posix()}"

                meta_path = path.with_suffix(".png.mcmeta")
                if meta_path.is_file():
                    texture = AnimatedTexture(
                        url=url,
                        css_class=texture_id.css_class,
                        meta=AnimationMeta.model_validate_json(meta_path.read_bytes()),
                    )
                    return ItemTexture(inner=texture)

            except FileNotFoundError:
                stripped_id = texture_id.removeprefix("textures/")
                url = loader.minecraft_loader.buildURL(
                    f"{stripped_id.namespace}/{stripped_id.path}"
                )

            return ItemTexture(inner=PNGTexture(url=url))

        case "block_model", model_id:
            return render_block(model_id, loader, book_version_url)


def render_block(
    id: ResourceLocation,
    loader: ModResourceLoader,
    book_version_url: str,
):
    render_id = require().ResourceLocation(id.namespace, id.path)

    id += ".png"
    if id.path.startswith("block/"):
        loader.renderer.renderToFile(render_id)
    else:
        id = "block" / id
        loader.renderer.renderToFile(render_id, id.path)

    path_stub = id.file_path_stub("assets", "textures")
    url = f"{book_version_url}/{path_stub.as_posix()}"
    return ItemTexture(inner=PNGTexture(url=url))
