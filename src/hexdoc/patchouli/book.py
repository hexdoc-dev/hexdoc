from collections import defaultdict
from typing import Any, Literal

from pydantic import Field, PrivateAttr, ValidationInfo, model_validator

from hexdoc.core import (
    ItemStack,
    ModResourceLoader,
    ResLoc,
    ResourceLocation,
)
from hexdoc.core.compat import AtLeast_1_20, Before_1_20
from hexdoc.minecraft import LocalizedStr
from hexdoc.model import Color, HexdocModel
from hexdoc.utils import ContextSource, cast_context, sorted_dict

from .book_context import BookContext
from .category import Category
from .entry import Entry
from .text import FormattingContext, FormatTree


class Book(HexdocModel):
    """Main Patchouli book class.

    Includes all data from book.json, categories/entries/pages, and i18n.

    You should probably not use this (or any other Patchouli types, eg. Category, Entry)
    to edit and re-serialize book.json, because this class sets all the default values
    as defined by the docs.

    See: https://vazkiimods.github.io/Patchouli/docs/reference/book-json
    """

    # not in book.json
    _categories: dict[ResourceLocation, Category] = PrivateAttr(default_factory=dict)

    # required
    name: LocalizedStr
    landing_text: FormatTree

    # required in 1.20 but optional in 1.19
    # so we'll make it optional and validate later
    use_resource_pack: AtLeast_1_20[Literal[True]] | Before_1_20[bool] = False

    # optional
    book_texture: ResourceLocation = ResLoc("patchouli", "textures/gui/book_brown.png")
    filler_texture: ResourceLocation | None = None
    crafting_texture: ResourceLocation | None = None
    model: ResourceLocation = ResLoc("patchouli", "book_brown")
    text_color: Color = Color("000000")
    header_color: Color = Color("333333")
    nameplate_color: Color = Color("FFDD00")
    link_color: Color = Color("0000EE")
    link_hover_color: Color = Color("8800EE")
    progress_bar_color: Color = Color("FFFF55")
    progress_bar_background: Color = Color("DDDDDD")
    open_sound: ResourceLocation | None = None
    flip_sound: ResourceLocation | None = None
    index_icon: ResourceLocation | None = None
    pamphlet: bool = False
    show_progress: bool = True
    version: str | int = 0
    subtitle: LocalizedStr | None = None
    creative_tab: str | None = None
    advancements_tab: str | None = None
    dont_generate_book: bool = False
    custom_book_item: ItemStack | None = None
    show_toasts: bool = True
    use_blocky_font: bool = False
    i18n: bool = False
    macros: dict[str, str] = Field(default_factory=dict)
    pause_game: bool = False
    text_overflow_mode: Literal["overflow", "resize", "truncate"] | None = None

    @property
    def categories(self):
        return self._categories

    def _load_categories(self, context: ContextSource, book_ctx: BookContext):
        categories = Category.load_all(
            cast_context(context),
            book_ctx.book_id,
            self.use_resource_pack,
        )

        if not categories:
            raise ValueError(
                "No categories found, are the paths in your properties file correct?"
            )

        for id, category in categories.items():
            self._categories[id] = category

            link_base = book_ctx.get_link_base(category.resource_dir)
            book_ctx.book_links[category.book_link_key] = link_base.with_fragment(
                category.fragment
            )

    def _load_entries(
        self,
        context: ContextSource,
        book_ctx: BookContext,
        loader: ModResourceLoader,
    ):
        internal_entries = defaultdict[ResLoc, dict[ResLoc, Entry]](dict)
        spoilered_categories = dict[ResLoc, bool]()

        for resource_dir, id, data in loader.load_book_assets(
            parent_book_id=book_ctx.book_id,
            folder="entries",
            use_resource_pack=self.use_resource_pack,
        ):
            entry = Entry.load(resource_dir, id, data, cast_context(context))

            spoilered_categories[entry.category_id] = (
                entry.is_spoiler and spoilered_categories.get(entry.category_id, True)
            )

            # i used the entry to insert the entry (pretty sure thanos said that)
            if resource_dir.internal:
                internal_entries[entry.category_id][entry.id] = entry

            link_base = book_ctx.get_link_base(resource_dir)
            book_ctx.book_links[entry.book_link_key] = link_base.with_fragment(
                entry.fragment
            )

            for page in entry.pages:
                page_key = page.book_link_key(entry.book_link_key)
                page_fragment = page.fragment(entry.fragment)
                if page_key is not None and page_fragment is not None:
                    book_ctx.book_links[page_key] = link_base.with_fragment(
                        page_fragment
                    )

        if not internal_entries:
            raise ValueError(
                f"No internal entries found for book {book_ctx.book_id}, is this the correct id?"
            )

        for category_id, new_entries in internal_entries.items():
            category = self._categories[category_id]
            category.entries = sorted_dict(category.entries | new_entries)
            if is_spoiler := spoilered_categories.get(category.id):
                category.is_spoiler = is_spoiler

    @model_validator(mode="before")
    @classmethod
    def _pre_root(cls, data: dict[Any, Any] | Any):
        if isinstance(data, dict) and "index_icon" not in data:
            data["index_icon"] = data.get("model")
        return data

    @model_validator(mode="after")
    def _post_root(self, info: ValidationInfo):
        if not info.context:
            return self

        # make the macros accessible when rendering the template
        self.macros |= FormattingContext.of(info).macros

        return self
