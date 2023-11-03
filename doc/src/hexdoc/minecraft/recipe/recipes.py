from typing import Any

from hexdoc.utils import HexDocModel

from ..i18n import LocalizedItem
from .abstract_recipes import Recipe
from .ingredients import ItemIngredientOrList


class ItemResult(HexDocModel[Any]):
    item: LocalizedItem
    count: int | None = None


class CraftingShapedRecipe(
    Recipe[Any],
    type="minecraft:crafting_shaped",
):
    pattern: list[str]
    key: dict[str, ItemIngredientOrList[Any]]
    result: ItemResult


class CraftingShapelessRecipe(
    Recipe[Any],
    type="minecraft:crafting_shapeless",
):
    ingredients: list[ItemIngredientOrList[Any]]
    result: ItemResult


CraftingRecipe = CraftingShapedRecipe | CraftingShapelessRecipe
