from typing import Iterator

from minecraft_render import require

from hexdoc.core import ModResourceLoader, ResourceLocation

from ..tags import Tag
from .animated import AnimatedTexture, AnimationMeta
from .models import FoundNormalTexture, ModelItem
from .textures import Texture


def load_and_render_internal_items(
    loader: ModResourceLoader,
    *,
    asset_url: str,
    book_version_url: str,
) -> Iterator[tuple[ResourceLocation, Texture | list[Texture]]]:
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
        export=False,  # we're exporting the urls as metadata, so we can skip this
    ):
        model = ModelItem.load_data("item" / item_id, data)

        match model.find_texture(loader, gaslighting_items):
            case None:
                missing_items.add(item_id)
                continue

            case "gaslighting", found_textures:
                textures = list(
                    _maybe_render_item(
                        found_texture,
                        loader,
                        asset_url=asset_url,
                        book_version_url=book_version_url,
                    )
                    for found_texture in found_textures
                )
                yield item_id, textures

            case found_texture:
                texture = _maybe_render_item(
                    found_texture,
                    loader,
                    asset_url=asset_url,
                    book_version_url=book_version_url,
                )
                yield item_id, texture

        found_items_from_models.add(item_id)

    for _, block_id, _ in loader.find_resources(
        "assets",
        namespace="*",
        folder="blockstates",
        internal_only=True,
    ):
        if block_id in missing_items:
            missing_items.remove(block_id)
        if block_id in found_items_from_models:
            continue
        yield block_id, _render_block(block_id, loader, book_version_url)

    if missing_items:
        raise FileNotFoundError(
            "Failed to find a texture for some items: "
            + ", ".join(str(item) for item in missing_items)
        )


# TODO: move to methods on a class returned by find_texture
def _maybe_render_item(
    found_texture: FoundNormalTexture,
    loader: ModResourceLoader,
    *,
    asset_url: str,
    book_version_url: str,
) -> Texture:
    match found_texture:
        case "texture", texture_id:
            try:
                path_stub = texture_id.file_path_stub("assets")
                _, path = loader.find_resource(path_stub)
                url = f"{asset_url}/{path.as_posix()}"

                meta_path = path.with_suffix(".png.mcmeta")
                if meta_path.is_file():
                    return AnimatedTexture(
                        url=url,
                        css_class=texture_id.css_class,
                        meta=AnimationMeta.model_validate_json(meta_path.read_bytes()),
                    )

            except FileNotFoundError:
                stripped_id = texture_id.removeprefix("textures/")
                url = loader.minecraft_loader.buildURL(
                    f"{stripped_id.namespace}/{stripped_id.path}"
                )

            return Texture(url=url)

        case "block_model", model_id:
            return _render_block(model_id, loader, book_version_url)


def _render_block(
    id: ResourceLocation,
    loader: ModResourceLoader,
    book_version_url: str,
):
    render_id = require().ResourceLocation(id.namespace, id.path)
    if id.path.startswith("block/"):
        loader.renderer.renderToFile(render_id)
    else:
        id = "block" / id + ".png"
        loader.renderer.renderToFile(render_id, id.path)

    path_stub = id.file_path_stub("assets", "textures")
    url = f"{book_version_url}/{path_stub.as_posix()}"
    return Texture(url=url)
