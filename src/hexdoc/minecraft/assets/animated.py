from functools import cached_property
from typing import Any, Literal, Self

from hexdoc.model import HexdocModel

from .textures import BaseTexture


class AnimationMetaFrame(HexdocModel):
    index: int | None = None
    time: int | None = None


class AnimationMetaTag(HexdocModel):
    interpolate: Literal[False]  # TODO: handle interpolation
    width: None = None  # TODO: handle non-square textures
    height: None = None
    frametime: int = 1
    frames: list[int | AnimationMetaFrame]


class AnimationMeta(HexdocModel):
    animation: AnimationMetaTag


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
    url: str
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
        return sum(time for _, time in self._normalized_frames)

    @property
    def frames(self):
        start = 0
        for index, time in self._normalized_frames:
            yield AnimatedTextureFrame(
                index=index,
                start=start,
                time=time,
                animation_time=self.time,
            )
            start += time

    @property
    def _normalized_frames(self):
        """index, time"""
        animation = self.meta.animation

        for i, frame in enumerate(animation.frames):
            match frame:
                case int(index):
                    time = None
                case AnimationMetaFrame(index=index, time=time):
                    pass

            if index is None:
                index = i
            if time is None:
                time = animation.frametime

            yield index, time
