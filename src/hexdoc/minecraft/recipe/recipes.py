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

from ..assets import ItemWithTexture
from .ingredients import ItemIngredient, ItemIngredientList, ItemResult


class Recipe(TypeTaggedUnion, ResourceModel):
    """Base model for Minecraft recipes.

    https://minecraft.wiki/w/Recipe
    """

    category: str | None = None
    group: str | None = None
    show_notification: AtLeast_1_20[bool] | Before_1_20[None] = Field(
        default_factory=lambda: ValueIfVersion(">=1.20", True, None)()
    )

    @classmethod
    def load_resource(cls, id: ResourceLocation, loader: ModResourceLoader):
        return loader.load_resource("data", "recipes", id)


class CraftingRecipe(Recipe):
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


class CookingRecipe(Recipe):
    ingredient: ItemIngredientList
    result: ItemWithTexture
    experience: float
    cookingtime: int


class BlastingRecipe(CookingRecipe, type="minecraft:blasting"):
    cookingtime: int = 100


class CampfireCookingRecipe(CookingRecipe, type="minecraft:campfire_cooking"):
    cookingtime: int = 100


class SmeltingRecipe(CookingRecipe, type="minecraft:smelting"):
    cookingtime: int = 200


class SmokingRecipe(CookingRecipe, type="minecraft:smoking"):
    cookingtime: int = 100


class SmithingRecipe(Recipe):
    base: ItemIngredient
    addition: ItemIngredient
    template: ItemIngredient


class SmithingTransformRecipe(SmithingRecipe, type="minecraft:smithing_transform"):
    result: ItemWithTexture


class SmithingTrimRecipe(SmithingRecipe, type="minecraft:smithing_trim"):
    pass


class StonecuttingRecipe(Recipe, type="minecraft:stonecutting"):
    ingredient: ItemIngredientList
    result: ItemWithTexture
    count: int
