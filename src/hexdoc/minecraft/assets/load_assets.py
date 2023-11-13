import logging
from collections.abc import Set
from pathlib import Path
from typing import Iterator

from minecraft_render import js

from hexdoc.core import ModResourceLoader, ResourceLocation

from ..tags import Tag
from .animated import AnimatedTexture, AnimationMeta
from .items import (
    ImageTexture,
    ItemTexture,
    MultiItemTexture,
    SingleItemTexture,
)
from .models import FoundNormalTexture, ModelItem
from .textures import (
    MISSING_TEXTURE,
    PNGTexture,
)

logger = logging.getLogger(__name__)

Texture = ImageTexture | ItemTexture


class TextureNotFoundError(FileNotFoundError):
    def __init__(self, id: ResourceLocation):
        self.message = f"No texture found for id: {id}"
        super().__init__(self.message)


def load_and_render_internal_textures(
    loader: ModResourceLoader,
    *,
    asset_url: str,
    book_version_url: str,
) -> Iterator[tuple[ResourceLocation, Texture]]:
    """For all item/block models in all internal resource dirs, yields the item id
    (eg. `hexcasting:focus`) and some kind of texture that we can use in the book."""

    # images
    image_textures = dict[ResourceLocation, ImageTexture]()
    for _, texture_id, path in loader.find_resources(
        "assets",
        namespace="*",
        folder="textures",
        glob="**/*.png",
        internal_only=True,
        allow_missing=True,
    ):
        texture_id = "textures" / texture_id
        texture = image_textures[texture_id] = load_texture(
            texture_id,
            path=path,
            repo_root=loader.repo_root,
            asset_url=asset_url,
        )
        yield texture_id, texture

    gaslighting_items = Tag.GASLIGHTING_ITEMS.load(loader).value_ids_set

    found_items_from_models = set[ResourceLocation]()
    missing_items = set[ResourceLocation]()

    # items
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
            image_textures,
            book_version_url,
        ):
            found_items_from_models.add(item_id)
            yield item_id, result
        elif item_id in loader.props.textures.missing:
            yield item_id, SingleItemTexture.from_url(MISSING_TEXTURE)
        else:
            missing_items.add(item_id)

    # blocks that didn't get covered by the items
    for _, block_id, _ in loader.find_resources(
        "assets",
        namespace="*",
        folder="blockstates",
        internal_only=True,
        allow_missing=True,
    ):
        if block_id in found_items_from_models:
            continue

        try:
            yield block_id, render_block(block_id, loader, book_version_url)
        except TextureNotFoundError:
            if block_id in loader.props.textures.missing:
                yield block_id, SingleItemTexture.from_url(MISSING_TEXTURE)
            else:
                missing_items.add(block_id)
        else:
            if block_id in missing_items:
                missing_items.remove(block_id)

    # oopsies
    if missing_items:
        raise FileNotFoundError(
            "Failed to find a texture for some items: "
            + ", ".join(str(item) for item in missing_items)
        )


def load_texture(
    id: ResourceLocation,
    *,
    path: Path,
    repo_root: Path,
    asset_url: str,
) -> ImageTexture:
    url = f"{asset_url}/{path.relative_to(repo_root).as_posix()}"
    meta_path = path.with_suffix(".png.mcmeta")

    if meta_path.is_file():
        return AnimatedTexture(
            url=url,
            css_class=id.css_class,
            meta=AnimationMeta.model_validate_json(meta_path.read_bytes()),
        )

    return PNGTexture(url=url)


def load_and_render_item(
    model: ModelItem,
    loader: ModResourceLoader,
    gaslighting_items: Set[ResourceLocation],
    image_textures: dict[ResourceLocation, ImageTexture],
    book_version_url: str,
) -> ItemTexture | None:
    try:
        match model.find_texture(loader, gaslighting_items):
            case None:
                return None

            case "gaslighting", found_textures:
                textures = list(
                    lookup_or_render_single_item(
                        found_texture,
                        loader,
                        image_textures,
                        book_version_url,
                    ).inner
                    for found_texture in found_textures
                )
                return MultiItemTexture(inner=textures, gaslighting=True)

            case found_texture:
                texture = lookup_or_render_single_item(
                    found_texture,
                    loader,
                    image_textures,
                    book_version_url,
                )
                return texture
    except TextureNotFoundError as e:
        logger.warning(e.message)
        return None


# TODO: move to methods on a class returned by find_texture?
def lookup_or_render_single_item(
    found_texture: FoundNormalTexture,
    loader: ModResourceLoader,
    image_textures: dict[ResourceLocation, ImageTexture],
    book_version_url: str,
) -> SingleItemTexture:
    match found_texture:
        case "texture", texture_id:
            if texture_id not in image_textures:
                raise TextureNotFoundError(texture_id)
            return SingleItemTexture(inner=image_textures[texture_id])

        case "block_model", model_id:
            return render_block(model_id, loader, book_version_url)


def render_block(
    id: ResourceLocation,
    loader: ModResourceLoader,
    book_version_url: str,
) -> SingleItemTexture:
    render_id = js.ResourceLocation(id.namespace, id.path)
    file_id = id + ".png"

    if file_id.path.startswith("block/"):
        # model
        result = loader.renderer.renderToFile(render_id)
    else:
        # blockstate
        file_id = "block" / file_id
        result = loader.renderer.renderToFile(render_id, file_id.path)

    if not result:
        raise TextureNotFoundError(id)

    # TODO: use logger after fixing the log levels
    out_root, out_path = result
    print(f"Rendered {id} to {out_path} (in {out_root})")

    url = f"{book_version_url}/{out_path}"
    return SingleItemTexture.from_url(url)
