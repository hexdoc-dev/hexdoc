# pyright: reportUnknownMemberType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

import moderngl_window as mglw
from moderngl_window.context.headless import Window as HeadlessWindow
from PIL import Image
from PIL.Image import Resampling
from PIL.PngImagePlugin import Disposal as APNGDisposal

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.core.properties import AnimationFormat
from hexdoc.graphics.model.block import BuiltInModelType

from .block import BlockRenderer
from .model import BlockModel
from .texture import ModelTexture
from .utils import DebugType

logger = logging.getLogger(__name__)


# FIXME: I don't really like this - ideally we should check the image size and pixelate if it's small
class ImageType(Enum):
    BLOCK = auto()
    ITEM = auto()
    UNKNOWN = auto()

    @property
    def pixelated(self):
        match self:
            case ImageType.BLOCK:
                return False
            case ImageType.ITEM | ImageType.UNKNOWN:
                return True


@dataclass(kw_only=True)
class ModelRenderer:
    """Avoid creating multiple instances of this class - it seems to cause issues with
    the OpenGL/ModernGL context."""

    loader: ModResourceLoader
    debug: DebugType = DebugType.NONE
    block_size: int | None = None
    item_size: int | None = None

    def __post_init__(self):
        self.window = HeadlessWindow(
            size=(self.block_size or 300,) * 2,
        )
        mglw.activate_context(self.window)

        self.block_renderer = BlockRenderer(ctx=self.window.ctx, wnd=self.window)

        self.window.config = self.block_renderer
        self.window.swap_buffers()
        self.window.set_default_viewport()

        if self.texture_props.large_items:
            self.item_size = self.item_size or 256

    @property
    def texture_props(self):
        return self.loader.props.textures

    @property
    def ctx(self):
        return self.window.ctx

    def render_model(
        self,
        model: BlockModel | ResourceLocation,
        output_path: str | Path,
    ):
        if isinstance(model, ResourceLocation):
            _, model = BlockModel.load_only(self.loader, model)

        model.resolve(self.loader)

        match model.builtin_parent:
            case BuiltInModelType.GENERATED:
                frames = self._render_item(model)
                image_type = ImageType.ITEM
            case None:
                frames = self._render_block(model)
                image_type = ImageType.BLOCK
            case builtin_type:
                raise ValueError(f"Unsupported model parent id: {builtin_type.value}")

        return self.save_image(output_path, frames), image_type

    def save_image(self, output_path: str | Path, frames: list[Image.Image]):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        match frames:
            case []:
                # TODO: awful error message.
                raise ValueError("No frames rendered!")
            case [image]:
                image.save(output_path)
                return output_path.suffix
            case _:
                return self._save_animation(output_path, frames)

    def _render_block(self, model: BlockModel):
        textures = {
            name: ModelTexture.load(self.loader, texture_id)
            for name, texture_id in model.resolved_textures.items()
        }
        return self.block_renderer.render_block(model, textures, self.debug)

    def _render_item(self, model: BlockModel):
        layers = sorted(
            self._load_layers(model),
            key=lambda tex: tex.layer_index,
        )
        animation_length = max(len(layer.frames) for layer in layers)
        return [
            self._render_item_frame(layers, animation_tick)
            for animation_tick in range(animation_length)
        ]

    def _render_item_frame(self, layers: list[ModelTexture], tick: int):
        image = layers[0].get_frame(tick)

        for texture in layers[1:]:
            layer = texture.get_frame(tick)
            if layer.size != image.size:
                raise ValueError(
                    f"Mismatched size for layer {texture.layer_index} at frame 0 "
                    + f"(expected {image.size}, got {layer.size})"
                )
            image = Image.alpha_composite(image, layer)

        if self.item_size:
            image = image.resize((self.item_size, self.item_size), Resampling.NEAREST)

        return image

    def _load_layers(self, model: BlockModel):
        for name, texture_id in model.resolved_textures.items():
            if not name.startswith("layer"):
                continue

            index = name.removeprefix("layer")
            if not index.isnumeric():
                continue

            texture = ModelTexture.load(self.loader, texture_id)
            texture.layer_index = int(index)
            yield texture

    def _save_animation(self, output_path: Path, frames: list[Image.Image]):
        kwargs: dict[str, Any]
        match output_format := self.texture_props.animated.format:
            case AnimationFormat.APNG:
                kwargs = dict(
                    disposal=APNGDisposal.OP_BACKGROUND,
                )
            case AnimationFormat.GIF:
                kwargs = dict(
                    loop=0,  # loop forever
                    disposal=2,  # restore to background color
                )

        frames[0].save(
            output_path.with_suffix(output_format.suffix),
            save_all=True,
            append_images=frames[1:],
            duration=1000 / 20,
            **kwargs,
        )
        return output_format.suffix

    def destroy(self):
        self.window.destroy()

    def __enter__(self):
        return self

    def __exit__(self, *_: Any):
        self.destroy()
        return False
