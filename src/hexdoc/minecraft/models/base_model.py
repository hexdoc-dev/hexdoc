from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, model_validator

from hexdoc.core import ResourceLocation
from hexdoc.model import HexdocModel
from hexdoc.model.base import IGNORE_EXTRA_CONFIG
from hexdoc.utils.types import Vec3, Vec4, clamped


class BaseMinecraftModel(HexdocModel, ABC):
    """Base class for Minecraft block/item models.

    https://minecraft.wiki/w/Tutorials/Models
    """

    model_config = IGNORE_EXTRA_CONFIG

    parent: ResourceLocation | None = None
    """Loads a different model from the given path, in form of a resource location.

    If both "parent" and "elements" are set, the "elements" tag overrides the "elements"
    tag from the previous model.
    """
    display: dict[DisplayPositionName, DisplayPosition] = Field(default_factory=dict)
    """Holds the different places where item models are displayed.

    `fixed` refers to item frames, while the rest are as their name states.
    """
    textures: dict[str, TextureVariable | ResourceLocation] = Field(
        default_factory=dict
    )
    """Holds the textures of the model, in form of a resource location or can be another
    texture variable."""
    elements: list[ModelElement] | None = None
    """Contains all the elements of the model. They can have only cubic forms.

    If both "parent" and "elements" are set, the "elements" tag overrides the "elements"
    tag from the previous model.
    """
    gui_light: Literal["front", "side"] = Field(None, validate_default=False)  # type: ignore
    """If set to `side` (default), the model is rendered like a block.

    If set to `front`, model is shaded like a flat item.

    Note: although the wiki only lists this field for item models, Minecraft sets it in
    the models `minecraft:block/block` and `minecraft:block/calibrated_sculk_sensor`.
    """

    @abstractmethod
    def apply_parent(self, parent: Self):
        """Merge the parent model into this one."""
        self.parent = parent.parent
        # prefer current display/textures over parent
        self.display = parent.display | self.display
        self.textures = parent.textures | self.textures
        # only use parent elements if current model doesn't have elements
        if self.elements is None:
            self.elements = parent.elements
        if not self._was_gui_light_set:
            self.gui_light = parent.gui_light

    @model_validator(mode="after")
    def _set_default_gui_light(self):
        self._was_gui_light_set = self.gui_light is not None  # type: ignore
        if not self._was_gui_light_set:
            self.gui_light = "side"
        return self


def _validate_texture_variable(value: str):
    assert re.fullmatch(r"#\w+", value)
    return value


TextureVariable = Annotated[str, AfterValidator(_validate_texture_variable)]


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


class ModelElement(HexdocModel):
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


FaceName = Literal["down", "up", "north", "south", "west", "east"]


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
    texture: TextureVariable
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
    def default(cls, element: ModelElement, direction: FaceName):
        x1, y1, z1 = element.from_
        x2, y2, z2 = element.to

        uvs: Vec4
        match direction:
            case "down":
                uvs = (x1, 16 - z2, x2, 16 - z1)
            case "up":
                uvs = (x1, z1, x2, z2)
            case "north":
                uvs = (16 - x2, 16 - y2, 16 - x1, 16 - y1)
            case "south":
                uvs = (x1, 16 - y2, x2, 16 - y1)
            case "west":
                uvs = (z1, 16 - y2, z2, 16 - y1)
            case "east":
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


# this is required to ensure BlockModel and ItemModel are fully defined
BaseMinecraftModel.model_rebuild()
