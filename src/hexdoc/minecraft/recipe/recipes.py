from typing import ClassVar, Iterator, Unpack

from pydantic import ConfigDict, Field, PrivateAttr, ValidationInfo, model_validator
from typing_extensions import override

from hexdoc.core import (
    ModResourceLoader,
    ResourceLocation,
    ValueIfVersion,
)
from hexdoc.core.compat import AtLeast_1_20, Before_1_20
from hexdoc.model import ResourceModel, TypeTaggedTemplate
from hexdoc.utils import Inherit, InheritType, classproperty

from ..assets import ImageTexture, ItemWithTexture, validate_texture
from ..i18n import I18n, LocalizedStr
from .ingredients import ItemIngredient, ItemIngredientList, ItemResult


class Recipe(TypeTaggedTemplate, ResourceModel):
    """Base model for Minecraft recipes.

    https://minecraft.wiki/w/Recipe
    """

    category: str | None = None
    group: str | None = None
    show_notification: AtLeast_1_20[bool] | Before_1_20[None] = Field(
        default_factory=ValueIfVersion(">=1.20", True, None)
    )

    # not in the actual model

    _workstation: ClassVar[ResourceLocation | None] = None

    _gui_name: LocalizedStr | None = PrivateAttr(None)
    _gui_texture: ImageTexture | None = PrivateAttr(None)

    def __init_subclass__(
        cls,
        *,
        type: str | InheritType | None = Inherit,
        workstation: str | InheritType | None = Inherit,
        **kwargs: Unpack[ConfigDict],
    ):
        super().__init_subclass__(type=type, **kwargs)

        match workstation:
            case str():
                cls._workstation = ResourceLocation.from_str(workstation)
            case None:
                cls._workstation = None
            case _:
                pass

    @classmethod
    def load_resource(cls, id: ResourceLocation, loader: ModResourceLoader):
        return loader.load_resource("data", "recipes", id)

    @classproperty
    @classmethod
    @override
    def template(cls):
        return cls.template_id.template_path("recipes")

    @classproperty
    @classmethod
    @override
    def template_id(cls):
        assert cls._workstation is not None
        return cls._workstation

    @property
    def gui_name(self):
        return self._gui_name

    @property
    def gui_texture(self):
        return self._gui_texture

    @classproperty
    @classmethod
    def _gui_texture_id(cls) -> ResourceLocation | None:
        """ResourceLocation of the background image for this recipe type."""
        if cls._workstation is None:
            return None
        return ResourceLocation(
            cls._workstation.namespace,
            f"textures/gui/hexdoc/{cls._workstation.path}.png",
        )

    def _localize_workstation(self, i18n: I18n):
        if self._workstation is not None:
            return i18n.localize_item(self._workstation)

    @model_validator(mode="after")
    def _load_gui_texture(self, info: ValidationInfo):
        self._gui_name = self._localize_workstation(I18n.of(info))

        if self._gui_texture_id is not None:
            self._gui_texture = validate_texture(
                self._gui_texture_id,
                context=info,
                model_type=ImageTexture,
            )

        return self


class CraftingRecipe(Recipe, workstation="minecraft:crafting_table"):
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


class BlastingRecipe(
    CookingRecipe,
    type="minecraft:blasting",
    workstation="minecraft:blast_furnace",
):
    cookingtime: int = 100


class CampfireCookingRecipe(
    CookingRecipe,
    type="minecraft:campfire_cooking",
    workstation="minecraft:campfire",
):
    cookingtime: int = 100


class SmeltingRecipe(
    CookingRecipe,
    type="minecraft:smelting",
    workstation="minecraft:furnace",
):
    cookingtime: int = 200


class SmokingRecipe(
    CookingRecipe,
    type="minecraft:smoking",
    workstation="minecraft:smoker",
):
    cookingtime: int = 100


class SmithingRecipe(Recipe, workstation="minecraft:smithing_table"):
    base: ItemIngredient
    addition: ItemIngredient
    template_ingredient: ItemIngredient = Field(alias="template")

    @property
    def result_item(self):
        return self.base.item


class SmithingTransformRecipe(SmithingRecipe, type="minecraft:smithing_transform"):
    result: ItemWithTexture

    @property
    def result_item(self):
        return self.result


class SmithingTrimRecipe(SmithingRecipe, type="minecraft:smithing_trim"):
    pass


class StonecuttingRecipe(
    Recipe,
    type="minecraft:stonecutting",
    workstation="minecraft:stonecutter",
):
    ingredient: ItemIngredientList
    result: ItemWithTexture
    count: int
