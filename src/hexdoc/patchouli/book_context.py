from pydantic import Field
from yarl import URL

from hexdoc.core import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir
from hexdoc.data import HexdocMetadata
from hexdoc.model import ValidationContextModel
from hexdoc.patchouli.text import BookLinks


class BookContext(ValidationContextModel):
    modid: str
    book_id: ResourceLocation
    book_links: BookLinks = Field(default_factory=dict)
    spoilered_advancements: set[ResourceLocation]
    all_metadata: dict[str, HexdocMetadata]

    def get_link_base(self, resource_dir: PathResourceDir) -> URL:
        modid = resource_dir.modid
        if resource_dir.internal or modid is None or modid == self.modid:
            return URL()

        book_url = self.all_metadata[modid].book_url
        if book_url is None:
            raise ValueError(f"Mod {modid} does not export a book url")

        return book_url
