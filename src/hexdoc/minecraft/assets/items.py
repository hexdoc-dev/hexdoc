from __future__ import annotations

from typing import Self

from hexdoc.core import ItemStack, ResourceLocation
from hexdoc.model import ValidationContext

from .animated import AnimatedTexture
from .textures import BaseTexture, PNGTexture

ImageTexture = PNGTexture | AnimatedTexture


class SingleItemTexture(BaseTexture):
    inner: ImageTexture

    @classmethod
    def from_url(cls, url: str) -> Self:
        return cls(inner=PNGTexture(url=url))

    @classmethod
    def load_id(cls, id: ResourceLocation | ItemStack, context: ValidationContext):
        return super().load_id(id.id, context)


class MultiItemTexture(BaseTexture):
    inner: list[ImageTexture]
    gaslighting: bool

    @classmethod
    def from_url(cls, url: str) -> Self:
        return cls(
            inner=[PNGTexture(url=url)],
            gaslighting=False,
        )

    @classmethod
    def load_id(cls, id: ResourceLocation | ItemStack, context: ValidationContext):
        return super().load_id(id.id, context)


ItemTexture = SingleItemTexture | MultiItemTexture
