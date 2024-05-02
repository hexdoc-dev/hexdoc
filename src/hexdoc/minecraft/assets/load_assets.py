import logging
import textwrap
from collections.abc import Set
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable, Iterator, TypeVar, cast

from pydantic import TypeAdapter
from yarl import URL

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.core.properties import (
    PNGTextureOverride,
    TextureTextureOverride,
)
from hexdoc.graphics.render import BlockRenderer
from hexdoc.utils import PydanticURL
from hexdoc.utils.context import ContextSource

from ..tags import Tag
from .animated import AnimatedTexture, AnimationMeta
from .constants import MISSING_TEXTURE_URL
from .items import (
    ImageTexture,
    ItemTexture,
    MultiItemTexture,
    SingleItemTexture,
)
from .models import FoundNormalTexture, ModelItem
from .textures import PNGTexture

logger = logging.getLogger(__name__)

Texture = ImageTexture | ItemTexture

_T_Texture = TypeVar("_T_Texture", bound=Texture)


def validate_texture(
    value: Any,
    *,
    context: ContextSource,
    model_type: type[_T_Texture] | Any = Texture,
) -> _T_Texture:
    ta = TypeAdapter(model_type)
    return ta.validate_python(
        value,
        context=cast(dict[str, Any], context),  # lie
    )


class TextureNotFoundError(FileNotFoundError):
    def __init__(self, id_type: str, id: ResourceLocation):
        self.message = f"No texture found for {id_type} id: {id}"
        super().__init__(self.message)


@dataclass(kw_only=True)
class HexdocAssetLoader:
    loader: ModResourceLoader
    site_url: PydanticURL
    asset_url: PydanticURL
    render_dir: Path

    @cached_property
    def gaslighting_items(self):
        return Tag.GASLIGHTING_ITEMS.load(self.loader).value_ids_set

    @property
    def texture_props(self):
        return self.loader.props.textures

    def can_be_missing(self, id: ResourceLocation):
        if self.texture_props.missing == "*":
            return True
        return any(id.match(pattern) for pattern in self.texture_props.missing)

    def get_override(
        self,
        id: ResourceLocation,
        image_textures: dict[ResourceLocation, ImageTexture],
    ) -> Texture | None:
        match self.texture_props.override.get(id):
            case PNGTextureOverride(url=url, pixelated=pixelated):
                return PNGTexture(url=url, pixelated=pixelated)
            case TextureTextureOverride(texture=texture):
                return image_textures[texture]
            case None:
                return None

    def find_image_textures(
        self,
    ) -> Iterable[tuple[ResourceLocation, Path | ImageTexture]]:
        for resource_dir, texture_id, path in self.loader.find_resources(
            "assets",
            namespace="*",
            folder="textures",
            glob="**/*.png",
            internal_only=True,
            allow_missing=True,
        ):
            if resource_dir:
                self.loader.export_raw(
                    path=path.relative_to(resource_dir.path),
                    data=path.read_bytes(),
                )
            yield texture_id, path

    def load_item_models(self) -> Iterable[tuple[ResourceLocation, ModelItem]]:
        for _, item_id, data in self.loader.load_resources(
            "assets",
            namespace="*",
            folder="models/item",
            internal_only=True,
            allow_missing=True,
        ):
            model = ModelItem.load_data("item" / item_id, data)
            yield item_id, model

    @cached_property
    def renderer(self):
        return BlockRenderer(
            loader=self.loader,
            output_dir=self.render_dir,
        )

    def fallback_texture(self, item_id: ResourceLocation) -> ItemTexture | None:
        return None

    def load_and_render_internal_textures(
        self,
        image_textures: dict[ResourceLocation, ImageTexture],
    ) -> Iterator[tuple[ResourceLocation, Texture]]:
        """For all item/block models in all internal resource dirs, yields the item id
        (eg. `hexcasting:focus`) and some kind of texture that we can use in the book."""

        # images
        for texture_id, value in self.find_image_textures():
            if not texture_id.path.startswith("textures"):
                texture_id = "textures" / texture_id

            match value:
                case Path() as path:
                    texture = load_texture(
                        texture_id,
                        path=path,
                        repo_root=self.loader.props.repo_root,
                        asset_url=self.asset_url,
                        strict=self.texture_props.strict,
                    )

                case PNGTexture() | AnimatedTexture() as texture:
                    pass

            image_textures[texture_id] = texture
            yield texture_id, texture

        found_items_from_models = set[ResourceLocation]()
        missing_items = set[ResourceLocation]()

        missing_item_texture = SingleItemTexture.from_url(
            MISSING_TEXTURE_URL, pixelated=True
        )

        # items
        for item_id, model in self.load_item_models():
            if result := self.get_override(item_id, image_textures):
                yield item_id, result
            elif result := load_and_render_item(
                model,
                self.loader,
                self.renderer,
                self.gaslighting_items,
                image_textures,
                self.site_url,
            ):
                found_items_from_models.add(item_id)
                yield item_id, result
            else:
                missing_items.add(item_id)

        for item_id in list(missing_items):
            if result := self.fallback_texture(item_id):
                logger.warning(f"Using fallback texture for item: {item_id}")
            elif self.can_be_missing(item_id):
                logger.warning(f"Using missing texture for item: {item_id}")
                result = missing_item_texture
            else:
                continue
            missing_items.remove(item_id)
            yield item_id, result

        # oopsies
        if missing_items:
            raise FileNotFoundError(
                "Failed to find a texture for some items: "
                + ", ".join(sorted(str(item) for item in missing_items))
            )


def load_texture(
    id: ResourceLocation,
    *,
    path: Path,
    repo_root: Path,
    asset_url: URL,
    strict: bool,
) -> ImageTexture:
    # FIXME: is_relative_to is only false when reading zip archives. ideally we would
    # permalink to the gh-pages branch and copy all textures there, but we can't get
    # that commit until we build the book, so it's a bit of a circular dependency.
    if path.is_relative_to(repo_root):
        url = asset_url.joinpath(*path.relative_to(repo_root).parts)
    else:
        level = logging.WARNING if strict else logging.DEBUG
        logger.log(level, f"Failed to find relative path for {id}: {path}")
        url = None

    meta_path = path.with_suffix(".png.mcmeta")
    if meta_path.is_file():
        try:
            meta = AnimationMeta.model_validate_json(meta_path.read_bytes())
        except ValueError as e:
            logger.debug(f"Failed to parse AnimationMeta for {id}\n{e}")
        else:
            return AnimatedTexture(
                url=url,
                pixelated=True,
                css_class=id.css_class,
                meta=meta,
            )

    return PNGTexture(url=url, pixelated=True)


def load_and_render_item(
    model: ModelItem,
    loader: ModResourceLoader,
    renderer: BlockRenderer,
    gaslighting_items: Set[ResourceLocation],
    image_textures: dict[ResourceLocation, ImageTexture],
    site_url: URL,
) -> ItemTexture | None:
    try:
        match model.find_texture(loader, gaslighting_items):
            case None:
                return None

            case "gaslighting", found_textures:
                textures = list(
                    lookup_or_render_single_item(
                        found_texture,
                        renderer,
                        image_textures,
                        site_url,
                    ).inner
                    for found_texture in found_textures
                )
                return MultiItemTexture(inner=textures, gaslighting=True)

            case found_texture:
                texture = lookup_or_render_single_item(
                    found_texture,
                    renderer,
                    image_textures,
                    site_url,
                )
                return texture
    except TextureNotFoundError as e:
        logger.warning(e.message)
        return None


# TODO: move to methods on a class returned by find_texture?
def lookup_or_render_single_item(
    found_texture: FoundNormalTexture,
    renderer: BlockRenderer,
    image_textures: dict[ResourceLocation, ImageTexture],
    site_url: URL,
) -> SingleItemTexture:
    match found_texture:
        case "texture", texture_id:
            if texture_id not in image_textures:
                raise TextureNotFoundError("item", texture_id)
            return SingleItemTexture(inner=image_textures[texture_id])

        case "block_model", model_id:
            return render_block(model_id, renderer, site_url)


def render_block(
    id: ResourceLocation,
    renderer: BlockRenderer,
    site_url: URL,
) -> SingleItemTexture:
    # FIXME: hack
    id_out_path = id.path
    if id.path.startswith("item/"):
        id_out_path = "block/" + id.path.removeprefix("item/")
    elif not id.path.startswith("block/"):
        id = "block" / id

    out_path = f"assets/{id.namespace}/textures/{id_out_path}.png"

    try:
        renderer.render_block_model(id, out_path)
    except Exception as e:
        if renderer.loader.props.textures.strict:
            raise
        message = textwrap.indent(f"{e.__class__.__name__}: {e}", "  ")
        logger.error(f"Failed to render block {id}:\n{message}")
        raise TextureNotFoundError("block", id)

    logger.debug(f"Rendered {id} to {out_path}")

    # TODO: ideally we shouldn't be using site_url here, in case the site is moved
    # but I'm not sure what else we could do...
    return SingleItemTexture.from_url(site_url / out_path, pixelated=False)
