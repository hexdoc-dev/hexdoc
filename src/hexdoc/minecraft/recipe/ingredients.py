from abc import ABC
from typing import Annotated, Any, Iterator

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    ValidationError,
    ValidationInfo,
)

from hexdoc.core import AssumeTag, ModResourceLoader, ResourceLocation
from hexdoc.graphics.validators import HexdocImage, ImageField, ItemImage, TagImage
from hexdoc.model import HexdocModel, NoValue, TypeTaggedUnion
from hexdoc.utils import listify

from ..tags import Tag


class ItemIngredient(TypeTaggedUnion, ABC):
    @property
    def item(self) -> HexdocImage: ...


class MinecraftItemIdIngredient(ItemIngredient, type=NoValue):
    item_: ImageField[ItemImage] = Field(alias="item")

    @property
    def item(self):
        return self.item_


class MinecraftItemTagIngredient(ItemIngredient, type=NoValue):
    tag: ImageField[AssumeTag[TagImage]]

    @property
    def item(self):
        return self.tag


class ItemResult(HexdocModel):
    item: ImageField[ItemImage]
    count: int = 1


def _validate_single_item_to_list(value: Any):
    match value:
        case [*contents]:
            return contents
        case _:
            return [value]


@listify
def _validate_flatten_nested_tags(
    ingredients: list[ItemIngredient],
    info: ValidationInfo,
) -> Iterator[ItemIngredient]:
    loader = ModResourceLoader.of(info)
    for ingredient in ingredients:
        yield ingredient

        if isinstance(ingredient, MinecraftItemTagIngredient):
            yield from _items_in_tag(ingredient.tag.id.id, info, loader)


def _items_in_tag(
    tag_id: ResourceLocation,
    info: ValidationInfo,
    loader: ModResourceLoader,
) -> Iterator[ItemIngredient]:
    try:
        tag = Tag.load("items", tag_id, loader)
    except FileNotFoundError:
        return

    for id in tag.value_ids:
        try:
            yield MinecraftItemIdIngredient.model_validate(
                {"item": id},
                context=info.context,
            )
        except ValidationError:
            yield from _items_in_tag(id, info, loader)


ItemIngredientList = Annotated[
    list[ItemIngredient],
    BeforeValidator(_validate_single_item_to_list),
    AfterValidator(_validate_flatten_nested_tags),
]
"""A list of ItemIngredients. Accepts a single value or a list."""
