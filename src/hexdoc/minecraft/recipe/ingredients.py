from typing import Annotated, Any, Iterator

from pydantic import AfterValidator, BeforeValidator, ValidationError, ValidationInfo

from hexdoc.core import ResourceLocation
from hexdoc.model import HexdocModel, NoValue, TypeTaggedUnion
from hexdoc.utils import cast_or_raise, listify

from ..assets import ItemWithTexture, TagWithTexture, TextureI18nContext
from ..tags import Tag


class ItemIngredient(TypeTaggedUnion, type=None):
    pass


class MinecraftItemIdIngredient(ItemIngredient, type=NoValue):
    item: ItemWithTexture


class MinecraftItemTagIngredient(ItemIngredient, type=NoValue):
    tag: TagWithTexture

    @property
    def item(self):
        return self.tag


class ItemResult(HexdocModel):
    item: ItemWithTexture
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
    context = cast_or_raise(info.context, TextureI18nContext)

    for ingredient in ingredients:
        yield ingredient

        if isinstance(ingredient, MinecraftItemTagIngredient):
            yield from _items_in_tag(ingredient.tag.id, context)


def _items_in_tag(
    tag_id: ResourceLocation,
    context: TextureI18nContext,
) -> Iterator[ItemIngredient]:
    try:
        tag = Tag.load("items", tag_id, context.loader)
    except FileNotFoundError:
        return

    for id in tag.value_ids:
        try:
            yield MinecraftItemIdIngredient.model_validate(
                {"item": id},
                context=context,
            )
        except ValidationError:
            yield from _items_in_tag(id, context)


ItemIngredientList = Annotated[
    list[ItemIngredient],
    BeforeValidator(_validate_single_item_to_list),
    AfterValidator(_validate_flatten_nested_tags),
]
