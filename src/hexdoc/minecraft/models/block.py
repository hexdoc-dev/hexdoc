from __future__ import annotations

from typing import Self

from typing_extensions import override

from hexdoc.core import ModResourceLoader, ResourceLocation

from .base_model import BaseMinecraftModel


class BlockModel(BaseMinecraftModel):
    """Represents a Minecraft block model.

    https://minecraft.wiki/w/Tutorials/Models#Block_models
    """

    ambientocclusion: bool = True
    """Whether to use ambient occlusion or not.

    Note: only works on parent file.
    """
    render_type: ResourceLocation | None = None
    """Sets the rendering type for this model.

    https://docs.minecraftforge.net/en/latest/rendering/modelextensions/rendertypes/
    """

    @override
    def apply_parent(self, parent: Self):
        super().apply_parent(parent)
        self.ambientocclusion = parent.ambientocclusion
        self.render_type = self.render_type or parent.render_type

    def load_parents_and_apply(self, loader: ModResourceLoader):
        while self.parent:
            _, parent = loader.load_resource(
                "assets",
                "models",
                self.parent,
                decode=self.model_validate_json,
            )
            self.apply_parent(parent)

    def resolve_texture_variables(self):
        textures = dict[str, ResourceLocation]()
        for name, value in self.textures.items():
            while not isinstance(value, ResourceLocation):
                value = value.lstrip("#")
                if value == name:
                    raise ValueError(f"Cyclic texture variable detected: {name}")
                value = self.textures[value]
            textures[name] = value
        return textures
