from functools import cached_property
from typing import Iterable, Mapping

from hexdoc.core import ResourceLocation
from hexdoc.minecraft.assets import (
    HexdocAssetLoader,
    HexdocPythonResourceLoader,
    ImageTexture,
    ItemTexture,
    ModelItem,
    PNGTexture,
)
from hexdoc.minecraft.assets.items import SingleItemTexture

from .minecraft_assets import MinecraftAssetsRepo


class MinecraftAssetLoader(HexdocAssetLoader):
    repo: MinecraftAssetsRepo

    @cached_property
    def fallbacks(self) -> Mapping[ResourceLocation, ItemTexture]:
        texture_content = self.repo.texture_content()
        return {
            value.name: SingleItemTexture(
                inner=PNGTexture(url=value.texture, pixelated=True)
            )
            for value in texture_content
            if value.texture
        }

    def find_image_textures(self) -> Iterable[tuple[ResourceLocation, ImageTexture]]:
        yield from self.repo.scrape_image_textures()

    def load_item_models(self) -> Iterable[tuple[ResourceLocation, ModelItem]]:
        for item_id, model in super().load_item_models():
            if model.parent and model.parent.path.startswith("builtin"):
                continue
            yield item_id, model

    def fallback_texture(self, item_id: ResourceLocation) -> ItemTexture | None:
        return self.fallbacks.get(item_id)

    def renderer_loader(self):
        return HexdocPythonResourceLoader(loader=self.loader).wrapped()
