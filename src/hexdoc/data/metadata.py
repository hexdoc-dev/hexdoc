from pathlib import Path
from typing import Self

from pydantic import model_validator

from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft.assets import Texture, TextureContext
from hexdoc.minecraft.assets.textures import TextureLocation
from hexdoc.model import HexdocModel
from hexdoc.utils import NoTrailingSlashHttpUrl


class HexdocMetadata(HexdocModel):
    """Automatically generated at `export_dir/modid.hexdoc.json`."""

    book_url: NoTrailingSlashHttpUrl
    """Github Pages base url."""
    asset_url: NoTrailingSlashHttpUrl
    """raw.githubusercontent.com base url."""
    png_textures: list[Texture]
    item_textures: dict[ResourceLocation, TextureLocation]

    @classmethod
    def path(cls, modid: str) -> Path:
        return Path(f"{modid}.hexdoc.json")


class MetadataContext(TextureContext):
    all_metadata: dict[str, HexdocMetadata]

    @model_validator(mode="after")
    def _add_metadata_textures(self) -> Self:
        # first pass: find all the actual image paths
        for metadata in self.all_metadata.values():
            for texture in metadata.png_textures:
                self.png_textures[texture.file_id] = texture

        # second pass: resolve the mapping from item id to texture
        # separate because otherwise png_textures[texture_id] might not be set yet
        for metadata in self.all_metadata.values():
            for item_id, texture_id in metadata.item_textures.items():
                self.item_textures[item_id] = self.png_textures[texture_id]

        return self
