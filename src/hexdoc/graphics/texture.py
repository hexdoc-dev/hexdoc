from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
from PIL import Image
from pydantic import ValidationError

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.core.properties import AnimatedTexturesProps
from hexdoc.utils import listify

from .model import Animation, AnimationFrame, AnimationMeta

logger = logging.getLogger(__name__)


# TODO: maybe put this in some system in ModResourceLoader? (see weakref.finalize)
# then we could clear the cache and free up memory when the loader is closed
_TEXTURE_CACHE: dict[ResourceLocation | Path, ModelTexture] = {}


@dataclass(kw_only=True)
class ModelTexture:
    texture_id: ResourceLocation | Path
    image: Image.Image
    animation: Animation | None
    layer_index: int = -1
    props: AnimatedTexturesProps

    @classmethod
    def load(cls, loader: ModResourceLoader, texture_id: ResourceLocation | Path):
        if cached := _TEXTURE_CACHE.get(texture_id):
            logger.debug(f"Cache hit: {texture_id}")
            return cached

        match texture_id:
            case ResourceLocation():
                _, path = loader.find_resource(
                    "assets",
                    "textures",
                    texture_id + ".png",
                )
                logger.debug(f"Loading texture {texture_id}: {path}")
            case Path() as path:
                logger.debug(f"Loading texture: {texture_id}")

        texture = cls(
            texture_id=texture_id,
            image=Image.open(path).convert("RGBA"),
            animation=cls._load_animation(path.with_suffix(".png.mcmeta")),
            props=loader.props.textures.animated,
        )
        _TEXTURE_CACHE[texture_id] = texture
        return texture

    @classmethod
    def _load_animation(cls, path: Path):
        if not path.is_file():
            return None

        logger.debug(f"Loading animation mcmeta: {path}")
        try:
            meta = AnimationMeta.model_validate_json(path.read_bytes())
            return meta.animation
        except ValidationError as e:
            # FIXME: hack
            logger.warning(f"Failed to parse animation meta ({path}):\n{e}")
            return None

    @cached_property
    def frame_height(self):
        match self.animation:
            case Animation(height=int()):
                raise NotImplementedError()
            case Animation() | None:
                return self.image.width

    @cached_property
    def _frame_count(self):
        """Number of sub-images within `self.image`.

        Not necessarily equal to `len(self.frames)`!
        """
        count = self.image.height / self.frame_height
        if not count.is_integer() or count < 1:
            raise ValueError(
                f"Invalid image dimensions (got {count=}):"
                + f"width={self.image.width}, height={self.image.height},"
                + f" frame_height={self.frame_height}"
            )
        return int(count)

    def get_frame_index(self, tick: int):
        if tick < 0:
            raise ValueError(f"Expected tick >= 0, got {tick}")
        return tick % len(self.frames)

    def get_frame(self, tick: int):
        return self.frames[self.get_frame_index(tick)]

    @cached_property
    @listify
    def frames(self):
        """Returns a list of animation frames, where each frame lasts for one tick.

        If `animation` is None, just returns `[image]`.
        """
        if self.animation is None:
            yield self.image
            return

        # TODO: implement width/height

        frames = self.animation.frames or [
            AnimationFrame(index=i, time=self.animation.frametime)
            for i in range(self._frame_count)
        ]

        if not self.props.enabled:
            yield self._get_frame_image(frames[0])
            return

        images = [self._get_frame_image(frame) for frame in frames]

        frame_time_multiplier = 1
        total_frames = sum(frame.time for frame in frames)
        if self.props.max_frames > 0 and total_frames > self.props.max_frames:
            logger.warning(
                f"Animation for texture {self.texture_id} is too long, dropping about"
                + f" {total_frames - self.props.max_frames} frames"
                + f" ({total_frames} > {self.props.max_frames})"
            )
            frame_time_multiplier = self.props.max_frames / total_frames

        frame_lerps: list[tuple[int, float]] = [
            (frame_idx, time / frame.time if self.animation.interpolate else 0)
            for frame_idx, frame in enumerate(frames)
            for time in np.linspace(
                0,
                frame.time - 1,
                max(1, math.floor(frame.time * frame_time_multiplier)),
            )
        ]

        for i, lerp in frame_lerps:
            j = (i + 1) % len(images)
            yield Image.blend(images[i], images[j], lerp)

    def _get_frame_image(self, frame: AnimationFrame):
        if frame.index >= self._frame_count:
            raise ValueError(
                f"Invalid frame index (expected <{self._frame_count}): {frame}"
            )
        start_y = self.frame_height * frame.index
        end_y = start_y + self.frame_height
        return self.image.crop((0, start_y, self.image.width, end_y))
