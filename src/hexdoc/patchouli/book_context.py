from typing import Self

from pydantic import Field, model_validator

from hexdoc.core import PathResourceDir, ResourceLocation
from hexdoc.data import MetadataContext
from hexdoc.minecraft import Tag
from hexdoc.model import ValidationContext

from .text import FormattingContext


class BookContext(FormattingContext, MetadataContext):
    spoilered_advancements: set[ResourceLocation] = Field(default_factory=set)
    extra: dict[str, ValidationContext] = Field(default_factory=dict)
    """Addons can add their own context here by implementing hexdoc_update_context."""

    def get_link_base(self, resource_dir: PathResourceDir) -> str:
        modid = resource_dir.modid
        if modid is None or modid == self.props.modid:
            return ""

        book_url = self.all_metadata[modid].book_url
        if book_url is None:
            raise ValueError(f"Mod {modid} does not export a book url")

        return book_url

    @model_validator(mode="after")
    def _post_root_load_tags(self) -> Self:
        self.spoilered_advancements |= Tag.SPOILERED_ADVANCEMENTS.load(
            self.loader
        ).value_ids_set

        return self
