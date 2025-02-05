from __future__ import annotations

import logging
from typing import Generic, TypeVar

from pydantic import field_validator

from hexdoc.core import (
    ItemStack,
    ResourceLocation,
)
from hexdoc.core.resource import BaseResourceLocation
from hexdoc.model import (
    HexdocModel,
    InlineItemModel,
    InlineModel,
)
from hexdoc.utils import ContextSource

from ..i18n import I18n, LocalizedStr
from .animated import AnimatedTexture
from .constants import TAG_TEXTURE_URL
from .items import ImageTexture, ItemTexture, MultiItemTexture, SingleItemTexture
from .load_assets import Texture
from .textures import PNGTexture

logger = logging.getLogger(__name__)

_T_BaseResourceLocation = TypeVar("_T_BaseResourceLocation", bound=BaseResourceLocation)

_T_Texture = TypeVar("_T_Texture", bound=Texture)


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
    def load_id(cls, item: ItemStack, context: ContextSource):
        """Implements InlineModel."""

        i18n = I18n.of(context)
        if (name := item.get_name()) is not None:
            pass
        elif item.path.startswith("texture"):
            name = i18n.localize_texture(item.id)
        else:
            name = i18n.localize_item(item)

        return {
            "id": item,
            "name": name,
            "texture": item.id,  # TODO: fix InlineModel (ItemTexture), then remove .id
        }


class TagWithTexture(InlineModel, BaseWithTexture[ResourceLocation, Texture]):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ContextSource):
        i18n = I18n.of(context)
        return cls(
            id=id,
            name=i18n.localize_item_tag(id),
            texture=PNGTexture.from_url(TAG_TEXTURE_URL, pixelated=True),
        )

    @field_validator("id", mode="after")
    @classmethod
    def _validate_id(cls, id: ResourceLocation):
        assert id.is_tag, f"Expected tag id, got {id}"
        return id


class NamedTexture(InlineModel, BaseWithTexture[ResourceLocation, ImageTexture]):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ContextSource):
        i18n = I18n.of(context)
        return {
            "id": id,
            "name": i18n.localize_texture(id, silent=True),
            "texture": id,
        }
