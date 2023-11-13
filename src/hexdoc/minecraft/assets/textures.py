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
)

from pydantic import Field, SerializeAsAny
from typing_extensions import override

from hexdoc.core import (
    ItemStack,
    ResourceLocation,
)
from hexdoc.model import (
    InlineModel,
    ValidationContext,
)
from hexdoc.utils import isinstance_or_raise

from .constants import MISSING_TEXTURE_URL, TAG_TEXTURE_URL

logger = logging.getLogger(__name__)


class BaseTexture(InlineModel, ABC):
    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, TextureContext)
        return cls.lookup(id, context.textures, context.allowed_missing_textures)

    @classmethod
    def lookup(
        cls,
        id: ResourceLocation,
        lookups: TextureLookups,
        allowed_missing: Iterable[ResourceLocation],
    ):
        """Returns the texture from the lookup table if it exists, or the "missing
        texture" texture if it's in `props.texture.missing`, or raises `KeyError`.

        This is called frequently and does not load any files.
        """
        textures = cls.get_textures(lookups)
        if id in textures:
            return textures[id]

        if any(id.match(pattern) for pattern in allowed_missing):
            logger.warning(f"No {cls.__name__} for {id}, using default missing texture")
            return MISSING_TEXTURE

        raise ValueError(f"No {cls.__name__} for {id}")

    @classmethod
    def get_textures(cls, lookups: TextureLookups) -> TextureLookup[Self]:
        return lookups[cls.__name__]

    def insert_texture(self, lookups: TextureLookups, id: ResourceLocation):
        textures = self.get_textures(lookups)
        textures[id] = self


class PNGTexture(BaseTexture):
    url: str


MISSING_TEXTURE = PNGTexture(url=MISSING_TEXTURE_URL)

TAG_TEXTURE = PNGTexture(url=TAG_TEXTURE_URL)


class ItemTexture(BaseTexture):
    inner: SerializeAsAny[PNGTexture]

    @classmethod
    def load_id(cls, id: ResourceLocation | ItemStack, context: ValidationContext):
        return super().load_id(id.id, context)


class MultiItemTexture(BaseTexture):
    inner: list[SerializeAsAny[PNGTexture]]
    gaslighting: bool

    @classmethod
    def load_id(cls, id: ResourceLocation | ItemStack, context: ValidationContext):
        return super().load_id(id.id, context)


AnyTexture = TypeVar("AnyTexture", bound=BaseTexture)

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
