# pyright: reportUnknownMemberType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import moderngl_window as mglw
from moderngl_window.context.headless import Window as HeadlessWindow
from PIL import Image
from PIL.Image import Resampling
from pydantic import ValidationError

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.graphics.texture import ModelTexture
from hexdoc.minecraft.assets import AnimationMeta
from hexdoc.minecraft.model import BlockModel

from .block import BlockRenderer, BlockTextureInfo
from .utils import DebugType

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ModelRenderer:
    loader: ModResourceLoader
    output_dir: Path | None = None
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

        output_path = Path(output_path)
        if self.output_dir and not output_path.is_absolute():
            output_path = self.output_dir / output_path

        if model.is_generated_item:
            return self._render_item(model, output_path)
        else:
            return self._render_block(model, output_path)

    def _render_block(self, model: BlockModel, output_path: Path):
        textures = {
            name: self._load_texture(texture_id)
            for name, texture_id in model.resolved_textures.items()
        }
        self.block_renderer.render_block(model, textures, output_path, self.debug)
        return output_path.suffix

    def _render_item(self, model: BlockModel, output_path: Path):
        layers = sorted(self._load_layers(model), key=lambda tex: tex.layer_index)

        animation_length = max(len(layer.frames) for layer in layers)

        frames = [
            self._render_item_frame(layers, tick) for tick in range(animation_length)
        ]

        match frames:
            case [image]:
                image.save(output_path)
            case [first, *rest]:
                output_path = output_path.with_suffix(".gif")
                first.save(
                    output_path,
                    save_all=True,
                    append_images=rest,
                    loop=0,  # loop forever
                    duration=1000 / 20,
                    disposal=2,  # restore to background color
                    interlace=False,
                )
            case _:
                # TODO: awful error message.
                raise ValueError("No frames rendered!")

        return output_path.suffix

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

    def _load_texture(self, texture_id: ResourceLocation):
        logger.debug(f"Loading texture: {texture_id}")
        _, path = self.loader.find_resource("assets", "textures", texture_id + ".png")

        meta_path = path.with_suffix(".png.mcmeta")
        if meta_path.is_file():
            logger.debug(f"Loading animation mcmeta: {meta_path}")
            # FIXME: hack
            try:
                meta = AnimationMeta.model_validate_json(meta_path.read_bytes())
            except ValidationError as e:
                logger.warning(f"Failed to parse animation meta for {texture_id}:\n{e}")
                meta = None
        else:
            meta = None

        return BlockTextureInfo(path, meta)

    def destroy(self):
        self.window.destroy()

    def __enter__(self):
        return self

    def __exit__(self, *_: Any):
        self.destroy()
        return False
