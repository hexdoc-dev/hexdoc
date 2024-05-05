from __future__ import annotations

from functools import cached_property
from typing import Any, Self

from hexdoc.model import HexdocModel
from hexdoc.utils.types import PydanticURL

from ..model.animation import AnimationMeta
from .textures import BaseTexture


class AnimatedTextureFrame(HexdocModel):
    index: int
    start: int
    time: int
    animation_time: int

    @property
    def start_percent(self):
        return self._format_time(self.start)

    @property
    def end_percent(self):
        return self._format_time(self.start + self.time, backoff=True)

    def _format_time(self, time: int, *, backoff: bool = False) -> str:
        percent = 100 * time / self.animation_time
        if backoff and percent < 100:
            percent -= 0.01
        return f"{percent:.2f}".rstrip("0").rstrip(".")


class AnimatedTexture(BaseTexture):
    url: PydanticURL | None
    pixelated: bool
    css_class: str
    meta: AnimationMeta

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        raise NotImplementedError("AnimatedTexture does not support from_url()")

    @property
    def time_seconds(self):
        return self.time / 20

    @cached_property
    def time(self):
        return sum(frame.time for frame in self.meta.animation.frames)

    @property
    def frames(self):
        start = 0
        for frame in self.meta.animation.frames:
            yield AnimatedTextureFrame(
                index=frame.index,
                start=start,
                time=frame.time,
                animation_time=self.time,
            )
            start += frame.time
