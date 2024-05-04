# pyright: reportUnknownMemberType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import moderngl_window as mglw
from moderngl_window.context.headless import Window as HeadlessWindow
from pydantic import ValidationError

from hexdoc.core import ModResourceLoader, ResourceLocation
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

    def __post_init__(self):
        self.window = HeadlessWindow(
            size=(300, 300),
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
            self._render_item(model, output_path)
        else:
            self._render_block(model, output_path)

    def _render_item(self, model: BlockModel, output_path: Path) -> None:
        raise NotImplementedError()

    def _render_block(self, model: BlockModel, output_path: Path):
        textures = self._load_textures(model.resolved_textures)
        self.block_renderer.render_block(model, textures, output_path, self.debug)

    def _load_textures(self, textures: dict[str, ResourceLocation]):
        return {
            name: self._load_texture(texture_id)
            for name, texture_id in textures.items()
        }

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
