from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.model import InlineIDModel, TypeTaggedUnion

from .ingredients import ItemResult


class Recipe(TypeTaggedUnion, InlineIDModel, type=None):
    group: str | None = None
    category: str | None = None

    @classmethod
    def load_resource(cls, id: ResourceLocation, loader: ModResourceLoader):
        return loader.load_resource("data", "recipes", id)


class CraftingRecipe(Recipe, type=None):
    result: ItemResult
