from typing import Iterable, Iterator

from pydantic import Field

from hexdoc.core import ItemStack, ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.minecraft.recipe import CraftingRecipe
from hexdoc.model import Color, IDModel
from hexdoc.utils import Sortable

from .page import CraftingPage, Page, PageWithTitle
from .text import FormatTree
from .utils import AdvancementSpoilered


class Entry(IDModel, Sortable, AdvancementSpoilered):
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
    flag: str | None = None
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
        """Combines adjacent CraftingPage recipes as much as possible."""
        accumulator = _CraftingPageAccumulator.blank()

        for page in self.pages:
            match page:
                case CraftingPage(
                    recipes=list(recipes),
                    text=None,
                    title=None,
                    anchor=None,
                ):
                    accumulator.recipes += recipes
                case CraftingPage(
                    recipes=list(recipes),
                    title=LocalizedStr() as title,
                    text=None,
                    anchor=None,
                ):
                    if accumulator.recipes:
                        yield accumulator
                    accumulator = _CraftingPageAccumulator.blank()
                    accumulator.recipes += recipes
                    accumulator.title = title
                case CraftingPage(
                    recipes=list(recipes),
                    title=None,
                    text=FormatTree() as text,
                    anchor=None,
                ):
                    accumulator.title = None
                    accumulator.text = text
                    accumulator.recipes += recipes
                    yield accumulator
                    accumulator = _CraftingPageAccumulator.blank()
                case _:
                    if accumulator.recipes:
                        yield accumulator
                        accumulator = _CraftingPageAccumulator.blank()
                    yield page

        if accumulator.recipes:
            yield accumulator

    def _get_advancement(self):
        # implements AdvancementSpoilered
        return self.advancement


class _CraftingPageAccumulator(PageWithTitle, template_type="patchouli:crafting"):
    recipes: list[CraftingRecipe] = Field(default_factory=list)

    @classmethod
    def blank(cls):
        return cls.model_construct()
