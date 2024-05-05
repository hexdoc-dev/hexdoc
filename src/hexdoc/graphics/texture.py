import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.minecraft.model import Animation, AnimationFrame, AnimationMeta
from hexdoc.utils import listify

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ModelTexture:
    index: int = -1
    image: Image.Image
    animation: Animation | None

    @classmethod
    def load(cls, loader: ModResourceLoader, texture_id: ResourceLocation):
        logger.debug(f"Loading texture: {texture_id}")
        _, path = loader.find_resource("assets", "textures", texture_id + ".png")
        return cls(
            image=Image.open(path).convert("RGBA"),
            animation=cls._load_animation(path.with_suffix(".png.mcmeta")),
        )

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
    def frame_count(self):
        count = self.image.height / self.frame_height
        if not count.is_integer() or count < 1:
            raise ValueError(
                f"Invalid image dimensions (got {count=}):"
                + f"width={self.image.width}, height={self.image.height},"
                + f" frame_height={self.frame_height}"
            )
        return int(count)

    def get_frame(self, tick: int):
        if tick < 0:
            raise ValueError(f"Expected tick >= 0, got {tick}")
        return self.frames[tick % len(self.frames)]

    @cached_property
    @listify
    def frames(self):
        """Returns a list of animation frames, where each frame lasts for one tick.

        If `animation` is None, just returns `[image]`.
        """
        if self.animation is None:
            yield self.image
            return

        # TODO: implement width/height, interpolation

        frames = self.animation.frames or [
            AnimationFrame(index=i, time=self.animation.frametime)
            for i in range(self.frame_count)
        ]

        for frame in frames:
            if frame.index >= self.frame_count:
                raise ValueError(
                    f"Invalid frame index (expected <{self.frame_count}): {frame}"
                )

            start_y = self.frame_height * frame.index
            end_y = start_y + self.frame_height
            frame_image = self.image.crop((0, start_y, self.image.width, end_y))

            for _ in range(frame.time):
                yield frame_image
