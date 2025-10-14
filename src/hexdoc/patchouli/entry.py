import logging
from typing import Any, Iterable, Iterator

from pydantic import Field, model_validator

from hexdoc.core import ItemStack, ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.model import Color, IDModel
from hexdoc.patchouli.page.abstract_pages import AccumulatorPage, PageWithAccumulator
from hexdoc.utils import Sortable

from .page import Page
from .utils import AdvancementSpoilered, Flagged

logger = logging.getLogger(__name__)


class Entry(IDModel, Sortable, AdvancementSpoilered, Flagged):
    """Entry json file, with pages and localizations.

    See: https://vazkiimods.github.io/Patchouli/docs/reference/entry-json
    """

    # required (entry.json)
    name: LocalizedStr
    category_id: ResourceLocation = Field(alias="category")
    icon: ItemWithTexture | NamedTexture
    pages: list[Page]

    # optional (entry.json)
    advancement: ResourceLocation | None = None
    priority: bool = False
    secret: bool = False
    read_by_default: bool = False
    sortnum: int = 0
    turnin: ResourceLocation | None = None
    extra_recipe_mappings: dict[ItemStack, int] | None = None
    entry_color: Color | None = None  # this is undocumented lmao

    @property
    def _cmp_key(self) -> tuple[bool, int, LocalizedStr]:
        # implement Sortable
        # note: python sorts false before true, so we invert priority
        return (not self.priority, self.sortnum, self.name)

    @property
    def anchors(self) -> Iterable[str]:
        for page in self.pages:
            if page.anchor is not None:
                yield page.anchor

    @property
    def book_link_key(self):
        """Key to look up this entry in `BookContext.book_links`."""
        return str(self.id)

    @property
    def fragment(self):
        """URL fragment for this entry in `BookContext.book_links`."""
        return self.id.path

    @property
    def redirect_path(self):
        """Path to this entry when generating redirect pages."""
        return self.id.path

    @property
    def first_text_page(self):
        for page in self.pages:
            if getattr(page, "text", None):
                return page

    def preprocess_pages(self) -> Iterator[Page]:
        """Combines adjacent PageWithAccumulator recipes as much as possible."""
        acc: AccumulatorPage[Any] | None = None

        for page in self.pages:
            if isinstance(page, PageWithAccumulator):
                if not (acc and acc.can_append(page)):
                    if acc and acc.has_content:
                        yield acc
                    acc = page.accumulator_type().from_page(page)

                acc.append(page)

                if not acc.can_append_more:
                    yield acc
                    acc = None
            else:
                if acc and acc.has_content:
                    yield acc
                acc = None
                yield page

        if acc and acc.has_content:
            yield acc

    def _get_advancement(self):
        # implements AdvancementSpoilered
        return self.advancement

    @model_validator(mode="after")
    def _skip_disabled_pages(self):
        new_pages = list[Page]()
        for i, page in enumerate(self.pages):
            if not page.is_flag_enabled:
                logger.info(
                    f"Skipping page {i} of entry {self.id} due to disabled flag {page.flag}"
                )
                continue
            new_pages.append(page)
        if not new_pages:
            logger.warning(
                f"Entry has no pages{' after applying flags' if self.pages else ''}: {self.id}"
            )
        self.pages = new_pages
        return self
