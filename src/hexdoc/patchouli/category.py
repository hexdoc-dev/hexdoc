from typing import Any, Self

from pydantic import Field

from hexdoc.core import ResourceLocation
from hexdoc.core.loader import ModResourceLoader
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.model import IDModel
from hexdoc.utils import Sortable, sorted_dict

from .entry import Entry
from .flag import FlagExpression
from .text import FormatTree


class Category(IDModel, Sortable):
    """Category with pages and localizations.

    See: https://vazkiimods.github.io/Patchouli/docs/reference/category-json
    """

    entries: dict[ResourceLocation, Entry] = Field(default_factory=dict)
    is_spoiler: bool = False

    # required
    name: LocalizedStr
    description: FormatTree
    icon: ItemWithTexture | NamedTexture

    # optional
    parent_id: ResourceLocation | None = Field(default=None, alias="parent")
    _parent_cmp_key: tuple[int, ...] | None = None
    flag: FlagExpression | None = None
    sortnum: int = 0
    secret: bool = False

    @classmethod
    def load_all(
        cls,
        context: dict[str, Any],
        book_id: ResourceLocation,
        use_resource_pack: bool,
    ) -> dict[ResourceLocation, Self]:
        # load
        loader = ModResourceLoader.of(context)
        categories = {
            id: cls.load(resource_dir, id, data, context)
            for resource_dir, id, data in loader.load_book_assets(
                book_id,
                "categories",
                use_resource_pack,
            )
        }

        # late-init _parent_cmp_key
        # track iterations to avoid an infinite loop if for some reason there's a cycle
        # TODO: array of non-ready categories so we can give a better error message?
        done, iterations = False, 0
        while not done and (iterations := iterations + 1) < 1000:
            done = True
            for category in categories.values():
                # if we still need to init this category, get the parent
                if category._is_cmp_key_ready:
                    continue
                assert category.parent_id
                parent = categories[category.parent_id]

                # only set _parent_cmp_key if the parent has been initialized
                if parent._is_cmp_key_ready:
                    category._parent_cmp_key = parent._cmp_key
                else:
                    done = False

        if not done:
            raise RuntimeError(
                f"Possible circular dependency of category parents: {categories}"
            )

        # return sorted by sortnum, which requires parent to be initialized
        return sorted_dict(categories)

    @property
    def _is_cmp_key_ready(self) -> bool:
        return self.parent_id is None or self._parent_cmp_key is not None

    @property
    def _cmp_key(self) -> tuple[int, ...]:
        # implement Sortable
        if parent_cmp_key := self._parent_cmp_key:
            return parent_cmp_key + (self.sortnum,)
        return (self.sortnum,)
