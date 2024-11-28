from __future__ import annotations

import logging
import math
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from hexdoc.model import IGNORE_EXTRA_CONFIG, HexdocModel
from hexdoc.utils.types import Vec3, Vec4, clamped

logger = logging.getLogger(__name__)


class Element(HexdocModel):
    """An element of a block/item model. Must be cubic.

    https://minecraft.wiki/w/Tutorials/Models
    """

    model_config = IGNORE_EXTRA_CONFIG

    from_: Vec3[Annotated[float, clamped(-16, 32)]] = Field(alias="from")
    """Start point of a cuboid according to the scheme [x, y, z].

    Values must be between -16 and 32.
    """
    to: Vec3[Annotated[float, clamped(-16, 32)]]
    """Stop point of a cuboid according to the scheme [x, y, z].

    Values must be between -16 and 32.
    """
    rotation: ElementRotation | None = None
    """Defines the rotation of an element."""
    shade: bool = True
    """Defines if shadows are rendered."""
    faces: dict[FaceName, ElementFace]
    """Holds all the faces of the cuboid. If a face is left out, it does not render."""


class ElementRotation(HexdocModel):
    """Defines the rotation of an element.

    https://minecraft.wiki/w/Tutorials/Models
    """

    origin: Vec3
    """Sets the center of the rotation according to the scheme [x, y, z]."""
    axis: Literal["x", "y", "z"]
    """Specifies the direction of rotation."""
    angle: float = Field(ge=-45, le=45, multiple_of=22.5)
    """Specifies the angle of rotation.

    Can be 45 through -45 degrees in 22.5 degree increments.
    """
    rescale: bool = False
    """Specifies whether or not to scale the faces across the whole block.

    (TODO: implement)
    """

    @property
    def eulers(self) -> Vec3:
        """Euler rotation vector, in radians."""
        angle = math.radians(self.angle)
        match self.axis:
            case "x":
                return (angle, 0, 0)
            case "y":
                return (0, angle, 0)
            case "z":
                return (0, 0, angle)


class FaceName(StrEnum):
    down = "down"
    up = "up"
    north = "north"
    south = "south"
    west = "west"
    east = "east"


class ElementFace(HexdocModel):
    """Contains the properties of the specified cuboid face.

    https://minecraft.wiki/w/Tutorials/Models
    """

    raw_uv: Vec4[Annotated[float, Field(ge=0, le=16)]] | None = Field(None, alias="uv")
    """Defines the area of the texture to use according to the scheme [x1, y1, x2, y2].

    The texture behavior is inconsistent if UV extends below 0 or above 16, so these
    values are forbidden by field validation.

    If the numbers of x1 and x2 are swapped (e.g. from 0, 0, 16, 16 to 16, 0, 0, 16),
    the texture flips.

    UV is optional, and if not supplied it automatically generates based on the
    element's position.
    """
    texture: ElementFaceTextureVariable
    """Specifies the texture in form of the texture variable prepended with a #."""
    cullface: FaceName | None = None
    """Specifies whether a face does not need to be rendered when there is a block
    touching it in the specified position.

    It also determines the side of the block to use the light level from for lighting
    the face, and if unset, defaults to the side.

    (TODO: implement; not sure what this means)
    """
    rotation: Literal[0, 90, 180, 270] = 0
    """Rotates the texture clockwise by the specified number of degrees.

    Rotation does not affect which part of the texture is used. Instead, it amounts to
    permutation of the selected texture vertexes (selected implicitly, or explicitly
    though uv).
    """
    tintindex: int = -1
    """Determines whether to tint the texture using a hardcoded tint index.

    The default value, -1, indicates not to use the tint. Any other number is provided
    to BlockColors to get the tint value corresponding to that index. However, most
    blocks do not have a tint value defined (in which case white is used). Furthermore,
    no vanilla block currently uses multiple tint values, and thus the tint index value
    is ignored (as long as it is set to something other than -1); it could be used for
    modded blocks that need multiple distinct tint values in the same block though.

    (TODO: implement)
    """

    @property
    def uv(self):
        if self.raw_uv is None:
            return None
        return ElementFaceUV(uvs=self.raw_uv, rotation=self.rotation)

    @property
    def texture_name(self):
        """Returns `self.texture` without the leading `#`."""
        return self.texture.lstrip("#")


class ElementFaceUV(HexdocModel):
    uvs: Vec4[Annotated[float, Field(ge=0, le=16)]]
    rotation: Literal[0, 90, 180, 270] = 0

    @classmethod
    def default(cls, element: Element, direction: FaceName):
        x1, y1, z1 = element.from_
        x2, y2, z2 = element.to

        uvs: Vec4
        match direction:
            case FaceName.down:
                uvs = (x1, 16 - z2, x2, 16 - z1)
            case FaceName.up:
                uvs = (x1, z1, x2, z2)
            case FaceName.north:
                uvs = (16 - x2, 16 - y2, 16 - x1, 16 - y1)
            case FaceName.south:
                uvs = (x1, 16 - y2, x2, 16 - y1)
            case FaceName.west:
                uvs = (z1, 16 - y2, z2, 16 - y1)
            case FaceName.east:
                uvs = (16 - z2, 16 - y2, 16 - z1, 16 - y1)

        return cls(uvs=uvs)

    def get_uv(self, index: Literal[0, 1, 2, 3]):
        return self.get_u(index), self.get_v(index)

    def get_u(self, index: Literal[0, 1, 2, 3]):
        if self._get_shifted_index(index) in {0, 1}:
            return self.uvs[0]
        return self.uvs[2]

    def get_v(self, index: Literal[0, 1, 2, 3]):
        if self._get_shifted_index(index) in {0, 3}:
            return self.uvs[1]
        return self.uvs[3]

    def _get_shifted_index(self, index: Literal[0, 1, 2, 3]):
        return (index + self.rotation // 90) % 4


def _validate_texture_variable(value: str):
    if not re.fullmatch(r"#\w+", value):
        raise ValueError(
            f"Malformed texture variable, expected `#` followed by at least 1 word character (^#\\w+$): {value}"
        )
    return value


TextureVariable = Annotated[str, AfterValidator(_validate_texture_variable)]


def _validate_element_face_texture_variable(value: str):
    # the minecraft:block/heavy_core model in 1.21.0 doesn't use # for its texture variables ???
    # https://bugs.mojang.com/browse/MC-270059
    # TODO: this is not a very useful error message since it doesn't say what model it's from
    if re.fullmatch(r"\w+", value):
        logger.warning(
            f"Malformed texture variable, expected to start with `#`: {value}"
        )
        value = "#" + value
    return value


ElementFaceTextureVariable = Annotated[
    str,
    AfterValidator(_validate_element_face_texture_variable),
    AfterValidator(_validate_texture_variable),
]
