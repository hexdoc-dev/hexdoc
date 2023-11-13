from __future__ import annotations

import logging

from hexdoc.core import (
    ItemStack,
    ResourceLocation,
)
from hexdoc.model import (
    InlineItemModel,
    InlineModel,
    ValidationContext,
)
from hexdoc.utils import isinstance_or_raise

from ..i18n import I18nContext, LocalizedStr
from .load_assets import Texture
from .textures import TAG_TEXTURE, ItemTexture, TextureContext

logger = logging.getLogger(__name__)


class TextureI18nContext(TextureContext, I18nContext):
    pass


class ItemWithTexture(InlineItemModel):
    id: ItemStack
    name: LocalizedStr
    texture: Texture | list[Texture]

    @classmethod
    def load_id(cls, item: ItemStack, context: ValidationContext):
        """Implements InlineModel."""
        assert isinstance_or_raise(context, TextureI18nContext)
        return cls(
            id=item,
            name=context.i18n.localize_item(item),
            texture=ItemTexture.load_id(item, context),
        )

    @property
    def gaslighting(self):
        return isinstance(self.texture, list)

    @property
    def textures(self):
        if not self.gaslighting:
            raise TypeError(f"Item {self.id} only has one texture")
        return self.texture


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
            texture=TAG_TEXTURE,
        )

    @property
    def gaslighting(self):
        return False
