from __future__ import annotations

import logging
from abc import ABC
from collections import defaultdict
from typing import (
    Annotated,
    Any,
    Iterable,
    Self,
    TypeVar,
    cast,
)

from pydantic import Field, SerializeAsAny
from typing_extensions import override

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
from .constants import MISSING_TEXTURE, TAG_TEXTURE

logger = logging.getLogger(__name__)


class Texture(InlineModel, ABC):
    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext) -> Texture:
        assert isinstance_or_raise(context, TextureContext)

        if cls is not Texture:  # handle subclasses
            return cls.lookup(id, context.textures, context.allowed_missing_textures)

        # i don't really feel like fixing the circular imports right now :)
        # but long-term this should use something like TypeTaggedUnion probably
        from .load import TextureAdapter

        return TextureAdapter().validate_python(id, context=cast(Any, context))

    @classmethod
    def lookup(
        cls,
        id: ResourceLocation,
        lookups: TextureLookups,
        allowed_missing: Iterable[ResourceLocation],
    ) -> Texture:
        """Returns the texture from the lookup table if it exists, or the "missing
        texture" texture if it's in `props.texture.missing`, or raises `KeyError`.

        This is called frequently and does not load any files.
        """
        textures = cls.get_textures(lookups)
        if id in textures:
            return textures[id]

        if any(id.match(pattern) for pattern in allowed_missing):
            logger.warning(f"No {cls.__name__} for {id}, using default missing texture")
            return PNGTexture(url=MISSING_TEXTURE)

        raise ValueError(f"No {cls.__name__} for {id}")

    @classmethod
    def get_textures(cls, lookups: TextureLookups) -> TextureLookup[Self]:
        return lookups[cls.__name__]


class PNGTexture(Texture):
    url: str


class ItemTexture(Texture):
    inner: PNGTexture

    @classmethod
    def load_id(cls, id: ResourceLocation | ItemStack, context: ValidationContext):
        return super().load_id(id.id, context)


class MultiItemTexture(Texture):
    inner: list[PNGTexture]
    gaslighting: bool

    @classmethod
    def load_id(cls, id: ResourceLocation | ItemStack, context: ValidationContext):
        return super().load_id(id.id, context)


AnyTexture = TypeVar("AnyTexture", bound=Texture)


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
            texture=PNGTexture(url=TAG_TEXTURE),
        )

    @property
    def gaslighting(self):
        return False


TextureLookup = dict[ResourceLocation, SerializeAsAny[AnyTexture]]
"""dict[id, texture]"""

TextureLookups = defaultdict[
    str,
    Annotated[TextureLookup[Any], Field(default_factory=dict)],
]
"""dict[type(texture).__name__, TextureLookup]"""


class TextureContext(ValidationContext):
    textures: TextureLookups
    allowed_missing_textures: set[ResourceLocation]


class TextureI18nContext(TextureContext, I18nContext):
    pass
