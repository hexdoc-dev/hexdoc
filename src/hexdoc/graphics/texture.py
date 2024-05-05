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
    image: Image.Image
    animation: Animation | None
    layer_index: int = -1

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

        frame_images = [(frame, self._get_frame_image(frame)) for frame in frames]

        for i, (frame, image) in enumerate(frame_images):
            # wrap around so it interpolates back to the start of the loop
            _, next_image = frame_images[(i + 1) % len(frame_images)]

            for i in range(frame.time):
                if self.animation.interpolate:
                    yield Image.blend(image, next_image, i / frame.time)
                else:
                    yield image

    def _get_frame_image(self, frame: AnimationFrame):
        if frame.index >= self._frame_count:
            raise ValueError(
                f"Invalid frame index (expected <{self._frame_count}): {frame}"
            )
        start_y = self.frame_height * frame.index
        end_y = start_y + self.frame_height
        return self.image.crop((0, start_y, self.image.width, end_y))
