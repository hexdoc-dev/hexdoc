from typing import Self

from pydantic import Field, model_validator

from hexdoc.core.metadata import MetadataContext
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir
from hexdoc.minecraft import Tag
from hexdoc.model.base_model import ValidationContext

from .text import FormattingContext


class BookContext(FormattingContext, MetadataContext):
    spoilered_advancements: set[ResourceLocation] = Field(default_factory=set)
    extra: dict[str, ValidationContext] = Field(default_factory=dict)
    """Addons can add their own context here by implementing hexdoc_update_context."""

    def get_link_base(self, resource_dir: PathResourceDir) -> str:
        modid = resource_dir.modid
        if modid is None or modid == self.props.modid:
            return ""
        return self.all_metadata[modid].book_url

    @model_validator(mode="after")
    def _post_root_load_tags(self) -> Self:
        tag = Tag.load(
            registry="hexdoc",
            id=ResourceLocation("*", "spoilered_advancements"),
            context=self,
        )
        self.spoilered_advancements.update(tag.value_ids)

        return self
