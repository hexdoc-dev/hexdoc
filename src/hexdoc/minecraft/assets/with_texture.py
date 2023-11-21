from __future__ import annotations

import logging
from typing import Generic, TypeVar

from hexdoc.core import (
    ItemStack,
    ResourceLocation,
)
from hexdoc.core.resource import BaseResourceLocation
from hexdoc.model import (
    InlineItemModel,
    InlineModel,
    ValidationContext,
)
from hexdoc.model.base import HexdocModel
from hexdoc.utils import isinstance_or_raise

from ..i18n import I18nContext, LocalizedStr
from .animated import AnimatedTexture
from .constants import TAG_TEXTURE_URL
from .items import ImageTexture, ItemTexture, MultiItemTexture, SingleItemTexture
from .load_assets import Texture
from .textures import PNGTexture, TextureContext

logger = logging.getLogger(__name__)

_T_BaseResourceLocation = TypeVar("_T_BaseResourceLocation", bound=BaseResourceLocation)

_T_Texture = TypeVar("_T_Texture", bound=Texture)


class TextureI18nContext(TextureContext[Texture], I18nContext):
    pass


class BaseWithTexture(HexdocModel, Generic[_T_BaseResourceLocation, _T_Texture]):
    id: _T_BaseResourceLocation
    name: LocalizedStr
    texture: Texture

    @property
    def image_texture(self) -> ImageTexture | None:
        match self.texture:
            case PNGTexture() | AnimatedTexture():
                return self.texture
            case SingleItemTexture():
                return self.texture.inner
            case MultiItemTexture():
                return None

    @property
    def image_textures(self) -> list[ImageTexture] | None:
        match self.texture:
            case MultiItemTexture():
                return self.texture.inner
            case PNGTexture() | AnimatedTexture() | SingleItemTexture():
                return None

    @property
    def gaslighting(self) -> bool:
        match self.texture:
            case MultiItemTexture():
                return self.texture.gaslighting
            case PNGTexture() | AnimatedTexture() | SingleItemTexture():
                return False


class ItemWithTexture(InlineItemModel, BaseWithTexture[ItemStack, ItemTexture]):
    @classmethod
    def load_id(cls, item: ItemStack, context: ValidationContext):
        """Implements InlineModel."""
        assert isinstance_or_raise(context, TextureI18nContext)

        if item.path.startswith("texture"):
            name = context.i18n.localize_texture(item.id)
        else:
            name = context.i18n.localize_item(item)

        return {
            "id": item,
            "name": name,
            "texture": item.id,  # TODO: fix InlineModel (ItemTexture), then remove .id
        }


class TagWithTexture(InlineModel, BaseWithTexture[ResourceLocation, Texture]):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, I18nContext)
        return cls(
            id=id,
            name=context.i18n.localize_item_tag(id),
            texture=PNGTexture.from_url(TAG_TEXTURE_URL, pixelated=True),
        )


class NamedTexture(InlineModel, BaseWithTexture[ResourceLocation, ImageTexture]):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, I18nContext)
        return {
            "id": id,
            "name": context.i18n.localize_texture(id),
            "texture": id,
        }
