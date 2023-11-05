from typing import Iterator

from hexdoc.core import AtLeast_1_20, Before_1_20

from .abstract_recipes import CraftingRecipe
from .ingredients import ItemIngredientList


class CraftingShapelessRecipe(CraftingRecipe, type="minecraft:crafting_shapeless"):
    ingredients: list[ItemIngredientList]


class CraftingShapedRecipe(CraftingRecipe, type="minecraft:crafting_shaped"):
    key: dict[str, ItemIngredientList]
    pattern: list[str]
    show_notification: AtLeast_1_20[bool] | Before_1_20[None] = None

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
