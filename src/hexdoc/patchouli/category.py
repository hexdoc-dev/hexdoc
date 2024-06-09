from typing import Any, Self

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from hexdoc.core import ResourceLocation
from hexdoc.core.loader import ModResourceLoader
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.assets import ItemWithTexture, NamedTexture
from hexdoc.model import IDModel
from hexdoc.utils import Sortable, sorted_dict
from hexdoc.utils.graphs import TypedDiGraph

from .entry import Entry
from .text import FormatTree


class Category(IDModel, Sortable):
    """Category with pages and localizations.

    See: https://vazkiimods.github.io/Patchouli/docs/reference/category-json
    """

    entries: SkipJsonSchema[dict[ResourceLocation, Entry]] = Field(default_factory=dict)
    is_spoiler: SkipJsonSchema[bool] = False

    # required
    name: LocalizedStr
    description: FormatTree
    icon: ItemWithTexture | NamedTexture

    # optional
    parent_id: ResourceLocation | None = Field(default=None, alias="parent")
    _parent_cmp_key: tuple[int, ...] | None = None
    flag: str | None = None
    sortnum: int = 0
    secret: bool = False

    @classmethod
    def load_all(
        cls,
        context: dict[str, Any],
        book_id: ResourceLocation,
        use_resource_pack: bool,
    ) -> dict[ResourceLocation, Self]:
        loader = ModResourceLoader.of(context)

        # load
        categories = dict[ResourceLocation, Self]()
        G = TypedDiGraph[ResourceLocation]()

        for resource_dir, id, data in loader.load_book_assets(
            book_id,
            "categories",
            use_resource_pack,
        ):
            category = categories[id] = cls.load(resource_dir, id, data, context)
            if category.parent_id:
                G.add_edge(category.parent_id, category.id)

        # if there's a cycle in the graph, we can't find a valid ordering
        # eg. two categories with each other as parents
        if cycle := G.find_cycle():
            raise ValueError(
                "Found cycle of category parents:\n  "
                + "\n  ".join(f"{u} -> {v}" for u, v in cycle)
            )

        # late-init _parent_cmp_key
        for parent_id in G.topological_sort():
            parent = categories[parent_id]
            for _, child_id in G.iter_out_edges(parent_id):
                categories[child_id]._parent_cmp_key = parent._cmp_key

        # return sorted by sortnum, which requires parent to be initialized
        return sorted_dict(categories)

    @property
    def book_link_key(self):
        """Key to look up this category in `BookContext.book_links`."""
        return str(self.id)

    @property
    def fragment(self):
        """URL fragment for this category in `BookContext.book_links`."""
        return self.id.path

    @property
    def redirect_path(self):
        """Path to this category when generating redirect pages."""
        return self.id.path

    @property
    def _is_cmp_key_ready(self) -> bool:
        return self.parent_id is None or self._parent_cmp_key is not None

    @property
    def _cmp_key(self) -> tuple[int, ...]:
        # implement Sortable
        if parent_cmp_key := self._parent_cmp_key:
            return parent_cmp_key + (self.sortnum,)
        return (self.sortnum,)
