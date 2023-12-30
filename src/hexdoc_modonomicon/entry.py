from hexdoc.core import ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.model import HexdocModel
from pydantic import Field

from .condition import Condition
from .page import Page


class EntryParent(HexdocModel):
    """https://klikli-dev.github.io/modonomicon/docs/basics/structure/entries#parents"""

    entry: ResourceLocation
    draw_arrow: bool = True
    line_enabled: bool = True
    line_reversed: bool = False


class Entry(HexdocModel):
    """https://klikli-dev.github.io/modonomicon/docs/basics/structure/entries"""

    category: ResourceLocation
    name: LocalizedStr
    description: LocalizedStr
    icon: ItemWithTexture | NamedTexture
    x: int
    y: int

    hide_while_locked: bool = False
    background_u_index: int = 0
    background_v_index: int = 0
    condition: Condition | None = None
    parents: list[EntryParent] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)
    category_to_open: ResourceLocation | None = None
    command_to_run_on_first_read: ResourceLocation | None = None
