from __future__ import annotations

from typing import Self

from typing_extensions import override

from .base import BaseMinecraftModel


class BlockModel(BaseMinecraftModel):
    """Represents a Minecraft block model.

    https://minecraft.wiki/w/Tutorials/Models#Block_models
    """

    ambientocclusion: bool = True
    """Whether to use ambient occlusion or not.

    Note: only works on parent file.
    """

    @override
    def apply_parent(self, parent: Self):
        super().apply_parent(parent)
        self.ambientocclusion = parent.ambientocclusion
