from hexdoc.core import ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.model import HexdocModel
from pydantic import Field

from .condition import Condition


def _gui_texture(name: str):
    return ResourceLocation("modonomicon", f"textures/gui/{name}.png")


class ParallaxLayer(HexdocModel):
    """https://klikli-dev.github.io/modonomicon/docs/basics/structure/categories#background_parallax_layers-json-array-of-json-objects-optional"""

    background: ResourceLocation
    speed: float
    vanish_zoom: float = 1


class Category(HexdocModel):
    """https://klikli-dev.github.io/modonomicon/docs/basics/structure/categories"""

    name: LocalizedStr
    icon: ItemWithTexture | NamedTexture

    sort_number: int = -1
    condition: Condition | None = None
    background: ResourceLocation = _gui_texture("dark_slate_seamless")
    background_parallax_layers: list[ParallaxLayer] = Field(default_factory=list)
    background_height: int = 512
    background_width: int = 512
    entry_textures: ResourceLocation = _gui_texture("entry_textures")
    show_category_button: bool = True
