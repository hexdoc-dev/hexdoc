from pathlib import Path
from typing import Iterable

from hexdoc.core import ResourceLocation
from hexdoc.minecraft.assets import HexdocAssetLoader, ImageTexture, ModelItem


class MinecraftAssetLoader(HexdocAssetLoader):
    def find_image_textures(
        self,
    ) -> Iterable[tuple[ResourceLocation, ImageTexture | Path]]:
        return super().find_image_textures()

    def load_item_models(self) -> Iterable[tuple[ResourceLocation, ModelItem]]:
        return super().load_item_models()

    def find_blockstates(self) -> Iterable[ResourceLocation]:
        return super().find_blockstates()
