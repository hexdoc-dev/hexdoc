from __future__ import annotations

import logging
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator
from typing_extensions import deprecated

from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils.types import PydanticURL

from ..resource import ResourceLocation

logger = logging.getLogger(__name__)


class URLOverride(StripHiddenModel):
    url: PydanticURL
    pixelated: bool = True


class TextureOverride(StripHiddenModel):
    texture: ResourceLocation
    """The id of an image texture (eg. `minecraft:textures/item/stick.png`)."""


class ItemOverride(StripHiddenModel):
    item: ResourceLocation
    """The id of an item (eg. `minecraft:stick`)."""


class ModelOverride(StripHiddenModel):
    model: ResourceLocation
    """The id of a model (eg. `minecraft:item/stick`)."""


Override = URLOverride | TextureOverride | ItemOverride | ModelOverride


class AnimationFormat(StrEnum):
    APNG = "apng"
    GIF = "gif"

    @property
    def suffix(self):
        match self:
            case AnimationFormat.APNG:
                return ".png"
            case AnimationFormat.GIF:
                return ".gif"


class AnimatedTexturesProps(StripHiddenModel):
    enabled: bool = True
    """If set to `False`, animated textures will be rendered as a PNG with the first
    frame of the animation."""
    format: AnimationFormat = AnimationFormat.GIF
    """Animated image output format.

    `gif` (the default) produces smaller but lower quality files, and interpolated
    textures may have issues with flickering.

    `apng` is higher quality, but the file size is a bit larger, and some
    platforms (eg. Discord) don't fully support it.
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


class TextureOverrides(StripHiddenModel):
    models: dict[ResourceLocation, Override] = Field(default_factory=dict)
    """Model overrides.

    Key: model id (eg. `minecraft:item/stick`).

    Value: override.
    """


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

    overrides: TextureOverrides = Field(default_factory=TextureOverrides)

    override: dict[ResourceLocation, URLOverride | TextureOverride] = Field(
        default_factory=dict,
        deprecated=deprecated("Use textures.overrides.models instead"),
    )
    """DEPRECATED - Use `textures.overrides.models` instead."""

    def can_be_missing(self, id: ResourceLocation):
        if not self.strict or self.missing == "*":
            return True
        return any(id.match(pat) for pat in self.missing)

    @model_validator(mode="after")
    def _copy_deprecated_overrides(self):
        self.overrides.models = self.override | self.overrides.models
        return self
