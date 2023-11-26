from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import (
    Annotated,
    Any,
    Generic,
    Iterable,
    Self,
    TypeVar,
)

from pydantic import Field, SerializeAsAny
from typing_extensions import override

from hexdoc.core import ResourceLocation
from hexdoc.model import (
    InlineModel,
    ValidationContext,
)
from hexdoc.utils import isinstance_or_raise

from .constants import MISSING_TEXTURE_URL

logger = logging.getLogger(__name__)


class BaseTexture(InlineModel, ABC):
    @classmethod
    @abstractmethod
    def from_url(cls, url: str, pixelated: bool) -> Self:
        ...

    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, TextureContext)
        return cls.lookup(
            id,
            lookups=context.textures,  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
            allowed_missing=context.allowed_missing_textures,
        )

    @classmethod
    def lookup(
        cls,
        id: ResourceLocation,
        lookups: TextureLookups[Any],
        allowed_missing: Iterable[ResourceLocation],
    ) -> Self:
        """Returns the texture from the lookup table if it exists, or the "missing
        texture" texture if it's in `props.texture.missing`, or raises `ValueError`.

        This is called frequently and does not load any files.
        """
        textures = cls.get_lookup(lookups)
        if id in textures:
            return textures[id]

        if any(id.match(pattern) for pattern in allowed_missing):
            logger.warning(f"No {cls.__name__} for {id}, using default missing texture")
            return cls.from_url(MISSING_TEXTURE_URL, pixelated=True)

        raise ValueError(f"No {cls.__name__} for {id}")

    @classmethod
    def get_lookup(cls, lookups: TextureLookups[Any]) -> TextureLookup[Self]:
        return lookups[cls.__name__]

    def insert_texture(self, lookups: TextureLookups[Any], id: ResourceLocation):
        textures = self.get_lookup(lookups)
        textures[id] = self


class PNGTexture(BaseTexture):
    url: str
    pixelated: bool

    @classmethod
    def from_url(cls, url: str, pixelated: bool) -> Self:
        return cls(url=url, pixelated=pixelated)


_T_BaseTexture = TypeVar("_T_BaseTexture", bound=BaseTexture)

TextureLookup = dict[ResourceLocation, SerializeAsAny[_T_BaseTexture]]
"""dict[id, texture]"""

TextureLookups = defaultdict[
    str,
    Annotated[TextureLookup[_T_BaseTexture], Field(default_factory=dict)],
]
"""dict[type(texture).__name__, TextureLookup]"""


class TextureContext(ValidationContext, Generic[_T_BaseTexture]):
    textures: TextureLookups[_T_BaseTexture]
    allowed_missing_textures: set[ResourceLocation]
