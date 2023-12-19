from typing import Iterator

from pydantic import Field

from hexdoc.core import (
    AtLeast_1_20,
    Before_1_20,
    ModResourceLoader,
    ResourceLocation,
    ValueIfVersion,
)
from hexdoc.model import ResourceModel, TypeTaggedUnion

from .ingredients import ItemIngredientList, ItemResult


class Recipe(TypeTaggedUnion, ResourceModel, type=None):
    group: str | None = None
    category: str | None = None
    show_notification: AtLeast_1_20[bool] | Before_1_20[None] = Field(
        default_factory=lambda: ValueIfVersion(">=1.20", True, None)()
    )

    @classmethod
    def load_resource(cls, id: ResourceLocation, loader: ModResourceLoader):
        return loader.load_resource("data", "recipes", id)


class CraftingRecipe(Recipe, type=None):
    result: ItemResult


class CraftingShapelessRecipe(CraftingRecipe, type="minecraft:crafting_shapeless"):
    ingredients: list[ItemIngredientList]


class CraftingShapedRecipe(CraftingRecipe, type="minecraft:crafting_shaped"):
    key: dict[str, ItemIngredientList]
    pattern: list[str]

    @property
    def ingredients(self) -> Iterator[ItemIngredientList | None]:
        for row in self.pattern:
            if len(row) > 3:
                raise ValueError(f"Expected len(row) <= 3, got {len(row)}: `{row}`")
            for item_key in row.ljust(3):
                match item_key:
                    case " ":
                        yield None
                    case _:
                        yield self.key[item_key]
