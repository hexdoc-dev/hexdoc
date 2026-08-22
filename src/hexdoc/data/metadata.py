from pathlib import Path

from hexdoc.model import IGNORE_EXTRA_CONFIG, HexdocModel
from hexdoc.utils import PydanticURL


class HexdocMetadata(HexdocModel):
    """Automatically generated at `export_dir/modid.hexdoc.json`."""

    # fields have been removed from the metadata; this makes it not a breaking change
    model_config = IGNORE_EXTRA_CONFIG

    book_url: PydanticURL | None
    """Github Pages base url."""
    asset_url: PydanticURL
    """raw.githubusercontent.com base url."""

    @classmethod
    def path(cls, modid: str) -> Path:
        return Path(f"{modid}.hexdoc.json")
