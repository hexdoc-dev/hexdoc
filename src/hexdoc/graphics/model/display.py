from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import Field

from hexdoc.model import HexdocModel
from hexdoc.utils.types import Vec3, clamped

DisplayPositionName = Literal[
    "thirdperson_righthand",
    "thirdperson_lefthand",
    "firstperson_righthand",
    "firstperson_lefthand",
    "gui",
    "head",
    "ground",
    "fixed",
]
"""`fixed` refers to item frames, while the rest are as their name states."""


class DisplayPosition(HexdocModel):
    """Place where an item model is displayed. Holds its rotation, translation and scale
    for the specified situation.

    Note that translations are applied to the model before rotations.

    If this is specified but not all of translation, rotation and scale are in it, the
    others aren't inherited from the parent. (TODO: is this only for items? see wiki)

    https://minecraft.wiki/w/Tutorials/Models
    """

    rotation: Vec3 = (0, 0, 0)
    """Specifies the rotation of the model according to the scheme [x, y, z]."""
    translation: Vec3[Annotated[float, clamped(-80, 80)]] = (0, 0, 0)
    """Specifies the position of the model according to the scheme [x, y, z].

    The values are clamped between -80 and 80.
    """
    scale: Vec3[Annotated[float, clamped(None, 4), Field(ge=0)]] = Field((0, 0, 0))
    """Specifies the scale of the model according to the scheme [x, y, z].

    If the value is greater than 4, it is displayed as 4.
    """

    @property
    def eulers(self) -> Vec3:
        """Euler rotation vector, in radians."""
        rotation = tuple(math.radians(v) for v in self.rotation)
        assert len(rotation) == 3
        return rotation
