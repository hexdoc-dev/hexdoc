from __future__ import annotations

import logging
import re
from functools import cached_property
from pathlib import Path
from typing import (
    Annotated,
    ClassVar,
    Generic,
    Iterator,
    Literal,
    Protocol,
    Self,
    TypeVar,
)

from minecraft_render import require
from pydantic import (
    AfterValidator,
    Field,
    TypeAdapter,
    model_validator,
)

from hexdoc.core import ItemStack, ModResourceLoader, Properties, ResourceLocation
from hexdoc.core.loader import LoaderContext
from hexdoc.model import HexdocModel, InlineItemModel, InlineModel
from hexdoc.model.base import DEFAULT_CONFIG, ValidationContext
from hexdoc.utils import isinstance_or_raise

from ..i18n import I18nContext, LocalizedStr
from ..tags import Tag
from .constants import MISSING_TEXTURE, TAG_TEXTURE

logger = logging.getLogger(__name__)

_T = TypeVar("_T", contravariant=True)


class Texture(InlineModel):
    url: str | None

    # @classmethod
    # def load_all(cls, root: Path, loader: ModResourceLoader):
    #     """Load all textures from all internal resource dirs.

    #     This is generally only called once.
    #     """
    #     for resource_dir, id, path in loader.find_resources(
    #         "assets",
    #         namespace="*",
    #         folder="textures",
    #         glob="**/*.png",
    #         allow_missing=True,
    #     ):
    #         # don't reexport external textures, since they won't be in this repo
    #         if resource_dir.external:
    #             continue

    #         relative_path = path.resolve().relative_to(root)
    #         url = f"{loader.props.env.asset_url}/{relative_path.as_posix()}"

    #         meta_path = path.with_suffix(".png.mcmeta")
    #         if meta_path.is_file():
    #             yield AnimatedTexture(
    #                 file_id=id,
    #                 url=url,
    #                 meta=AnimationMeta.model_validate_json(meta_path.read_bytes()),
    #             )
    #         else:
    #             yield Texture(file_id=id, url=url)

    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, TextureContext)
        id = TextureLocationAdapter.validate_python(id)
        try:
            return cls.find(id, props=context.props, textures=context.png_textures)
        except ValueError:
            return MinecraftTexture.load_or_render_unknown(id, context)

    @classmethod
    def find(
        cls,
        *ids: ResourceLocation,
        props: Properties,
        textures: dict[TextureLocation, Texture],
    ):
        """Returns the first existing texture from the lookup table, or the "missing
        texture" texture if it's in `props.texture.missing`, or raises `KeyError`.

        This is called frequently and does not load any files.
        """
        for id in ids:
            id = TextureLocationAdapter.validate_python(id)
            if id in textures:
                return textures[id]

        # fallback/error
        message = f"No texture for {', '.join(str(i) for i in ids)}"

        for missing_id in props.textures.missing:
            for id in ids:
                if id.match(missing_id):
                    logger.warning(message)
                    return Texture(file_id=id, url=MISSING_TEXTURE)

        raise ValueError(message)

    @classmethod
    def render_block(cls, id: ResourceLocation, loader: ModResourceLoader):
        id = TextureLocationAdapter.validate_python(id)
        render_id = require().ResourceLocation(id.namespace, id.path)

        if loader.book_output_dir is not None:
            # TODO: try to extract variants/overrides?
            path = loader.renderer.renderToFile(render_id)
            logger.info(f"Rendered {id} to {path}")

        # TODO: update minecraft_render to pass this into renderToFile
        url = f"assets/{id.namespace}/textures/{id.path}.png"

        return cls(file_id=id, url=url)


class MinecraftTexture(Texture):
    @classmethod
    def load_or_render(cls, id: ResourceLocation, context: TextureContext) -> Self:
        id = TextureLocationAdapter.validate_python(id)
        if id.namespace != "minecraft":
            raise ValueError(f"Invalid namespace, expected minecraft: {id}")

        from javascript.errors import JavaScriptError

        try:
            return cls.render_block(id, context.loader)
        except JavaScriptError:
            pass

        url = context.loader.minecraft_loader.buildURL(f"{id.namespace}/{id.path}.png")
        texture = context.png_textures[id] = MinecraftTexture(file_id=id, url=url)
        return texture

    @classmethod
    def load_or_render_unknown(cls, id: ResourceLocation, context: TextureContext):
        id = TextureLocationAdapter.validate_python(id)
        stripped_id = id.with_path(id.path.removeprefix("block/").removeprefix("item/"))

        # TODO: ew.
        from javascript.errors import JavaScriptError

        for texture_id in [
            id,
            "block" / stripped_id,
            "item" / stripped_id,
        ]:
            try:
                print(texture_id)
                return cls.load_or_render(texture_id, context)
            except JavaScriptError:
                pass

        raise ValueError(f"Failed to load or render Minecraft texture: {id}")


def get_item_texture(
    item: ResourceLocation | ItemStack,
    item_textures: dict[ResourceLocation, Texture],
) -> Texture:
    if item.id not in item_textures:
        raise ValueError(f"No texture loaded for item: {item}")
    return item_textures[item.id]


class ItemWithNormalTexture(InlineItemModel):
    id: ItemStack
    name: LocalizedStr
    texture: Texture

    @classmethod
    def load_id(cls, item: ItemStack, context: ValidationContext):
        """Implements InlineModel."""
        assert isinstance_or_raise(context, TextureI18nContext)
        return cls(
            id=item,
            name=context.i18n.localize_item(item),
            texture=get_item_texture(item, context.item_textures),
        )

    @property
    def gaslighting(self):
        return False


class ItemWithMinecraftTexture(ItemWithNormalTexture):
    @classmethod
    def load_id(cls, item: ItemStack, context: ValidationContext):
        """Implements InlineModel."""
        assert isinstance_or_raise(context, TextureI18nContext)

        texture_id = TextureLocationAdapter.validate_python(item.id)

        return cls(
            id=item,
            name=context.i18n.localize_item(item),
            texture=MinecraftTexture.load_or_render_unknown(texture_id, context),
        )


class ItemWithGaslightingTexture(InlineItemModel):
    id: ItemStack
    name: LocalizedStr
    textures: list[Texture]

    @classmethod
    def load_id(cls, item: ItemStack, context: ValidationContext):
        """Implements InlineModel."""
        assert isinstance_or_raise(context, TextureI18nContext)
        if item.id not in context.gaslighting_items:
            raise ValueError("Item does not have a gaslighting texture")
        return cls(
            id=item,
            name=context.i18n.localize_item(item),
            textures=list(cls._get_gaslit_ids(item, context.item_textures)),
        )

    @classmethod
    def _get_gaslit_ids(
        cls,
        item: ItemStack,
        item_textures: dict[ResourceLocation, Texture],
    ) -> Iterator[Texture]:
        for index in range(NUM_GASLIGHTING_TEXTURES):
            gaslit_id = item.id + f"_{index}"
            texture_id = TextureLocationAdapter.validate_python("item" / gaslit_id)
            yield get_item_texture(texture_id, item_textures)

    @property
    def gaslighting(self):
        return True


# order is important here!
# Minecraft should be last, since it renders a new image
ItemWithTexture = (
    ItemWithGaslightingTexture | ItemWithNormalTexture | ItemWithMinecraftTexture
)


class TagWithTexture(InlineModel):
    id: ResourceLocation
    name: LocalizedStr
    texture: Texture

    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, I18nContext)
        return cls(
            id=id,
            name=context.i18n.localize_item_tag(id),
            texture=Texture(file_id=id, url=TAG_TEXTURE),
        )

    @property
    def gaslighting(self):
        return False


class TextureContext(LoaderContext):
    png_textures: dict[ResourceLocation, Texture] = Field(default_factory=dict)
    item_textures: dict[ResourceLocation, Texture] = Field(default_factory=dict)
    gaslighting_items: set[ResourceLocation] = Field(default_factory=set)
    gaslighting_textures: dict[ResourceLocation, list[Texture]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def _post_root(self) -> Self:
        self.gaslighting_items |= Tag.GASLIGHTING_ITEMS.load(self.loader).value_ids_set

        return self


class TextureI18nContext(TextureContext, I18nContext):
    pass
