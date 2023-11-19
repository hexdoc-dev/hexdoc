from pathlib import Path
from typing import Self

from pydantic import model_validator

from hexdoc.minecraft.assets import Texture, TextureI18nContext, TextureLookups
from hexdoc.model import HexdocModel
from hexdoc.utils import NoTrailingSlashHttpUrl


class HexdocMetadata(HexdocModel):
    """Automatically generated at `export_dir/modid.hexdoc.json`."""

    book_url: NoTrailingSlashHttpUrl | None
    """Github Pages base url."""
    asset_url: NoTrailingSlashHttpUrl
    """raw.githubusercontent.com base url."""
    textures: TextureLookups[Texture]

    @classmethod
    def path(cls, modid: str) -> Path:
        return Path(f"{modid}.hexdoc.json")


class MetadataContext(TextureI18nContext):
    all_metadata: dict[str, HexdocMetadata]

    @model_validator(mode="after")
    def _add_metadata_textures(self) -> Self:
        self.textures |= load_metadata_textures(self.all_metadata)
        return self


def load_metadata_textures(all_metadata: dict[str, HexdocMetadata]):
    lookups = TextureLookups[Texture](dict)

    for metadata in all_metadata.values():
        for classname, lookup in metadata.textures.items():
            lookups[classname] |= lookup

    return lookups
