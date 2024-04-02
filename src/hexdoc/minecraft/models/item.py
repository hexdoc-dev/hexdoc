from __future__ import annotations

from typing import Self

from typing_extensions import override

from hexdoc.core import ResourceLocation
from hexdoc.model import HexdocModel

from .base_model import BaseMinecraftModel


class ItemModel(BaseMinecraftModel):
    """Represents a Minecraft item model.

    https://minecraft.wiki/w/Tutorials/Models#Item_models
    """

    overrides: list[ItemModelOverride] | None = None
    """Determines cases in which a different model should be used based on item tags.

    All cases are evaluated in order from top to bottom and last predicate that matches
    overrides. However, overrides are ignored if it has been already overridden once,
    for example this avoids recursion on overriding to the same model.
    """

    @override
    def apply_parent(self, parent: Self):
        super().apply_parent(parent)


class ItemModelOverride(HexdocModel):
    """An item model override case.

    https://minecraft.wiki/w/Tutorials/Models#Item_models
    """

    model: ResourceLocation
    """The path to the model to use if the case is met."""
    predicate: dict[ResourceLocation, float]
    """Item predicates that must be true for this model to be used."""
