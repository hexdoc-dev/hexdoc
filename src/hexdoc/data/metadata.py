from pathlib import Path
from typing import Self

from pydantic import model_validator

from hexdoc.minecraft.assets.textures import TextureI18nContext, TextureLookups
from hexdoc.model import HexdocModel
from hexdoc.utils import NoTrailingSlashHttpUrl


class HexdocMetadata(HexdocModel):
    """Automatically generated at `export_dir/modid.hexdoc.json`."""

    book_url: NoTrailingSlashHttpUrl | None
    """Github Pages base url."""
    asset_url: NoTrailingSlashHttpUrl
    """raw.githubusercontent.com base url."""
    textures: TextureLookups

    @classmethod
    def path(cls, modid: str) -> Path:
        return Path(f"{modid}.hexdoc.json")


class MetadataContext(TextureI18nContext):
    all_metadata: dict[str, HexdocMetadata]

    @model_validator(mode="after")
    def _add_metadata_textures(self) -> Self:
        for metadata in self.all_metadata.values():
            for classname, lookup in metadata.textures.items():
                self.textures[classname] |= lookup
        return self
