from __future__ import annotations

import logging
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils.types import PydanticURL

from ..resource import ResourceLocation

logger = logging.getLogger(__name__)


# TODO: support item/block override
class PNGTextureOverride(StripHiddenModel):
    url: PydanticURL
    pixelated: bool


class TextureTextureOverride(StripHiddenModel):
    texture: ResourceLocation
    """The id of an image texture (eg. `minecraft:textures/item/stick.png`)."""


class AnimationFormat(StrEnum):
    APNG = "apng"
    GIF = "gif"


class AnimatedTexturesProps(StripHiddenModel):
    enabled: bool = True
    """If set to `False`, animated textures will be rendered as a PNG with the first
    frame of the animation."""
    format: AnimationFormat = AnimationFormat.APNG
    """Animated image output format.

    `apng` (the default) is higher quality, but the file size is a bit larger.

    `gif` produces smaller but lower quality files, and interpolated textures may have
    issues with flickering.
    """
    max_frames: Annotated[int, Field(ge=0)] = 15 * 20  # 15 seconds * 20 tps
    """Maximum number of frames for animated textures (1 frame = 1 tick = 1/20 seconds).
    If a texture would have more frames than this, some frames will be dropped.

    This is mostly necessary because of prismarine, which is an interpolated texture
    with a total length of 6600 frames or 5.5 minutes.

    The default value is 300 frames or 15 seconds, producing about a 3 MB animation for
    prismarine.

    To disable the frame limit entirely, set this value to 0.
    """


class OverridesProps(StripHiddenModel):
    pass


class TexturesProps(StripHiddenModel):
    enabled: bool = True
    """Set to False to disable model rendering."""
    strict: bool = True
    """Set to False to print some errors instead of throwing them."""
    large_items: bool = True
    """Controls whether flat item renders should be enlarged after rendering, or left at
    the default size (usually 16x16). Defaults to `True`."""

    missing: set[ResourceLocation] | Literal["*"] = Field(default_factory=set)

    animated: AnimatedTexturesProps = Field(default_factory=AnimatedTexturesProps)

    override: dict[
        ResourceLocation,
        PNGTextureOverride | TextureTextureOverride,
    ] = Field(default_factory=dict)
