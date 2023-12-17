from pathlib import Path

from hexdoc.minecraft.assets import Texture, TextureLookups
from hexdoc.model import HexdocModel
from hexdoc.utils.types import PydanticURL


class HexdocMetadata(HexdocModel):
    """Automatically generated at `export_dir/modid.hexdoc.json`."""

    book_url: PydanticURL | None
    """Github Pages base url."""
    asset_url: PydanticURL
    """raw.githubusercontent.com base url."""
    textures: TextureLookups[Texture]

    @classmethod
    def path(cls, modid: str) -> Path:
        return Path(f"{modid}.hexdoc.json")


def load_metadata_textures(all_metadata: dict[str, HexdocMetadata]):
    lookups = TextureLookups[Texture](dict)

    for metadata in all_metadata.values():
        for classname, lookup in metadata.textures.items():
            lookups[classname] |= lookup

    return lookups
