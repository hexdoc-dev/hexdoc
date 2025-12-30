from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, Self, TypeVar, Unpack

from pydantic import ConfigDict, Field, model_validator
from pydantic.functional_validators import ModelWrapValidatorHandler
from typing_extensions import override

from hexdoc.core import LocalizedStr, ResourceLocation
from hexdoc.minecraft.recipe import Recipe
from hexdoc.model import TypeTaggedTemplate
from hexdoc.utils import Inherit, InheritType, NoValue, classproperty

from ..text import FormatTree
from ..utils import AdvancementSpoilered, Flagged

_T_Recipe = TypeVar("_T_Recipe", bound=Recipe)

_T_PageWithAccumulator = TypeVar(
    "_T_PageWithAccumulator",
    bound="PageWithAccumulator[Any]",
    contravariant=True,
)

_T_PageWithRecipeAccumulator = TypeVar(
    "_T_PageWithRecipeAccumulator",
    bound="PageWithRecipeAccumulator[Any]",
    contravariant=True,
)


class Page(TypeTaggedTemplate, AdvancementSpoilered, Flagged, type=None):
    """Base class for Patchouli page types.

    See: https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/page-types
    """

    advancement: ResourceLocation | None = None
    anchor: str | None = None

    def __init_subclass__(
        cls,
        *,
        type: str | InheritType | None = Inherit,
        template_type: str | None = None,
        **kwargs: Unpack[ConfigDict],
    ) -> None:
        super().__init_subclass__(type=type, template_type=template_type, **kwargs)

    @classproperty
    @classmethod
    def type(cls) -> ResourceLocation | None:
        assert cls._type is not NoValue
        return cls._type

    @model_validator(mode="wrap")
    @classmethod
    def _pre_root(cls, value: str | Any, handler: ModelWrapValidatorHandler[Self]):
        match value:
            case str(text):
                # treat a plain string as a text page
                value = {"type": "patchouli:text", "text": text}
            case {"type": str(raw_type)} if ":" not in raw_type:
                # default to the patchouli namespace if not specified
                # see: https://github.com/VazkiiMods/Patchouli/blob/b87e91a5a08d/Xplat/src/main/java/vazkii/patchouli/client/book/ClientBookRegistry.java#L110
                value["type"] = f"patchouli:{raw_type}"
            case _:
                pass
        return handler(value)

    @classproperty
    @classmethod
    def template(cls) -> str:
        return cls.template_id.template_path("pages")

    def book_link_key(self, entry_key: str):
        """Key to look up this page in `BookContext.book_links`, or `None` if this page
        has no anchor."""
        if self.anchor is not None:
            return f"{entry_key}#{self.anchor}"

    def fragment(self, entry_fragment: str):
        """URL fragment for this page in `BookContext.book_links`, or `None` if this
        page has no anchor."""
        if self.anchor is not None:
            return f"{entry_fragment}@{self.anchor}"

    def redirect_path(self, entry_path: str):
        """Path to this page when generating redirect pages, or `None` if this page has
        no anchor."""
        if self.anchor is not None:
            return f"{entry_path}/{self.anchor}"

    def _get_advancement(self):
        # implements AdvancementSpoilered
        return self.advancement


class PageWithText(Page, type=None):
    """Base class for a `Page` with optional text.

    If text is required, do not subclass this type.
    """

    text: FormatTree | None = None


class PageWithTitle(PageWithText, type=None):
    """Base class for a `Page` with optional title and text.

    If title and/or text is required, do not subclass this type.
    """

    title: LocalizedStr | None = None


class PageWithDoubleRecipe(PageWithTitle, Generic[_T_Recipe], type=None):
    recipe: _T_Recipe
    recipe2: _T_Recipe | None = None

    @property
    def recipes(self) -> list[_T_Recipe]:
        return [r for r in [self.recipe, self.recipe2] if r is not None]


class PageWithAccumulator(Page, ABC, type=None):
    """Base class for pages that can merge together when adjacent."""

    @classmethod
    @abstractmethod
    def accumulator_type(cls) -> type[AccumulatorPage[Any]]:
        """Returns the RecipeAccumulator class for this page type.

        The template type of the returned class must match that of this class.
        """

    @property
    @abstractmethod
    def accumulator_title(self) -> LocalizedStr | None:
        """Returns the page's title, if any, for use in the accumulator."""

    @property
    @abstractmethod
    def accumulator_text(self) -> FormatTree | None:
        """Returns the page's text, if any, for use in the accumulator."""


class PageWithRecipeAccumulator(
    PageWithAccumulator, ABC, Generic[_T_Recipe], type=None
):
    @property
    @abstractmethod
    def accumulator_recipes(self) -> list[_T_Recipe]:
        """Returns the page's recipes for use in the accumulator."""


class PageWithDoubleRecipeAccumulator(
    PageWithDoubleRecipe[_T_Recipe],
    PageWithRecipeAccumulator[_T_Recipe],
    ABC,
    Generic[_T_Recipe],
    type=None,
):
    @property
    @override
    def accumulator_title(self) -> LocalizedStr | None:
        return self.title

    @property
    @override
    def accumulator_text(self) -> FormatTree | None:
        return self.text

    @property
    @override
    def accumulator_recipes(self) -> list[_T_Recipe]:
        return self.recipes


class AccumulatorPage(PageWithTitle, ABC, Generic[_T_PageWithAccumulator], type=None):
    """Base class for virtual pages generated to merge adjacent instances of a
    PageWithAccumulator page type together."""

    _page_type: ClassVar[ResourceLocation | None]

    def __init_subclass__(
        cls,
        *,
        page_type: type[PageWithAccumulator[_T_PageWithAccumulator]] | None = None,
        **kwargs: Unpack[ConfigDict],
    ) -> None:
        if page_type:
            super().__init_subclass__(
                type=None,
                template_type=str(page_type.template_id),
                **kwargs,
            )
            cls._page_type = page_type.type
        else:
            super().__init_subclass__(type=None, template_type=None, **kwargs)
            cls._page_type = None

    @classmethod
    def from_page(cls, page: _T_PageWithAccumulator) -> Self:
        """Constructs a new accumulator from the given page.

        Note: `append(page)` is always called immediately after this.
        """
        if cls._page_type is None:
            raise RuntimeError(f"Cannot instantiate {cls} because page_type is None")
        if page.type != cls._page_type:
            raise ValueError(f"Mismatched page type: {cls}, {page}")

        self = cls.model_construct()
        self.title = page.accumulator_title
        self.anchor = page.anchor
        self.advancement = page.advancement
        return self

    @property
    def has_content(self) -> bool:
        """Returns True if this accumulator contains any user-visible content."""
        return bool(self.title or self.text)

    def can_append(self, page: _T_PageWithAccumulator) -> bool:
        """Returns True if this accumulator can append the given page."""
        return (
            self._page_type == page.type
            and self.title == page.accumulator_title
            and self.anchor == page.anchor
            and self.advancement == page.advancement
        )

    @abstractmethod
    def append(self, page: _T_PageWithAccumulator):
        """Appends the given page to this accumulator."""
        self.text = page.accumulator_text

    @property
    def can_append_more(self) -> bool:
        """Returns True if this accumulator can append more pages."""
        return self.text is None


class RecipeAccumulatorPage(
    AccumulatorPage[_T_PageWithRecipeAccumulator],
    Generic[_T_PageWithRecipeAccumulator, _T_Recipe],
):
    recipes: list[_T_Recipe] = Field(default_factory=lambda: [])

    @property
    @override
    def has_content(self) -> bool:
        return super().has_content or bool(self.recipes)

    @override
    def append(self, page: _T_PageWithRecipeAccumulator):
        super().append(page)
        self.recipes += page.accumulator_recipes
