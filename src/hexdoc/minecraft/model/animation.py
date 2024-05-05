from __future__ import annotations

from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator

from hexdoc.model import HexdocModel
from hexdoc.utils.types import cast_nullable


class AnimationMeta(HexdocModel):
    """Animated texture `.mcmeta` file.

    Block, item, particle, painting, item frame, and status effect icon
    (`assets/minecraft/textures/mob_effect`) textures support animation by placing each
    additional frame below the last. The animation is then controlled using a `.mcmeta`
    file in JSON format with the same name and `.png` at the end of the filename, in the
    same directory. For example, the `.mcmeta` file for `stone.png` would be
    `stone.png.mcmeta`.

    https://minecraft.wiki/w/Resource_pack#Animation
    """

    animation: Animation
    """Contains data for the animation."""


class Animation(HexdocModel):
    """https://minecraft.wiki/w/Resource_pack#Animation"""

    interpolate: bool = False
    """If true, generate additional frames between frames with a frame time greater than
    1 between them."""
    width: int | None = Field(None, ge=1)
    """The width of the tile, as a direct ratio rather than in pixels.

    This is unused in vanilla's files but can be used by resource packs to have
    frames that are not perfect squares.
    """
    height: int | None = Field(None, ge=1)
    """The height of the tile as a ratio rather than in pixels.

    This is unused in vanilla's files but can be used by resource packs to have
    frames that are not perfect squares.
    """
    frametime: int = Field(1, ge=1)
    """Sets the default time for each frame in increments of one game tick."""
    frames: list[AnimationFrame] = Field(default_factory=list)
    """Contains a list of frames.

    Integer values are a number corresponding to position of a frame from the top,
    with the top frame being 0.

    Defaults to displaying all the frames from top to bottom.
    """

    @field_validator("width", "height", mode="after")
    @classmethod
    def _raise_not_implemented(cls, value: int | None, info: ValidationInfo):
        if value is not None:
            raise ValueError(
                f"Field {info.field_name} is not currently supported"
                + f" (expected None, got {value})"
            )
        return value

    @model_validator(mode="after")
    def _late_init_frames(self):
        for i, frame in enumerate(self.frames):
            if cast_nullable(frame.index) is None:
                frame.index = i
            if cast_nullable(frame.time) is None:
                frame.time = self.frametime
        return self


class AnimationFrame(HexdocModel):
    index: int = Field(None, ge=0, validate_default=False)
    """A number corresponding to position of a frame from the top, with the top
    frame being 0."""
    time: int = Field(None, ge=1, validate_default=False)
    """The time in ticks to show this frame."""

    @model_validator(mode="before")
    @classmethod
    def _convert_from_int(cls, value: Any):
        match value:
            case int():
                return {"index": value}
            case _:
                return value
