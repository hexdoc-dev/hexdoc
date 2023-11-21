from typing import Iterable, Iterator

from pydantic import Field, ValidationInfo, model_validator

from hexdoc.core import ItemStack, ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.minecraft.recipe import CraftingRecipe
from hexdoc.model import Color, IDModel
from hexdoc.utils import Sortable, cast_or_raise

from .book_context import BookContext
from .page import CraftingPage, Page, PageWithTitle
from .text import FormatTree


class Entry(IDModel, Sortable):
    """Entry json file, with pages and localizations.

    See: https://vazkiimods.github.io/Patchouli/docs/reference/entry-json
    """

    is_spoiler: bool = False

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

    @model_validator(mode="after")
    def _check_is_spoiler(self, info: ValidationInfo):
        if not info.context or self.advancement is None:
            return self
        context = cast_or_raise(info.context, BookContext)

        self.is_spoiler = any(
            self.advancement.match(spoiler)
            for spoiler in context.spoilered_advancements
        )
        return self


class _CraftingPageAccumulator(PageWithTitle, template_type="patchouli:crafting"):
    recipes: list[CraftingRecipe] = Field(default_factory=list)

    @classmethod
    def blank(cls):
        return cls.model_construct()
