from collections import defaultdict
from typing import Self

from jinja2 import pass_context
from jinja2.runtime import Context
from pydantic import (
    Field,
    PrivateAttr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import override

from hexdoc.core import Entity, LocalizedStr, ResourceLocation
from hexdoc.graphics import ImageField, ItemImage, TextureImage
from hexdoc.graphics.validators import TagImage
from hexdoc.minecraft.recipe import (
    BlastingRecipe,
    CampfireCookingRecipe,
    CraftingRecipe,
    SmeltingRecipe,
    SmithingRecipe,
    SmokingRecipe,
    StonecuttingRecipe,
)
from hexdoc.model import HexdocModel

from ..text import FormatTree
from .abstract_pages import (
    Page,
    PageWithDoubleRecipe,
    PageWithDoubleRecipeAccumulator,
    PageWithText,
    PageWithTitle,
    RecipeAccumulatorPage,
)


class TextPage(Page, type="patchouli:text"):
    title: LocalizedStr | None = None
    text: FormatTree


class BlastingPage(PageWithDoubleRecipe[BlastingRecipe], type="patchouli:blasting"):
    pass


class CampfireCookingPage(
    PageWithDoubleRecipe[CampfireCookingRecipe], type="patchouli:campfire_cooking"
):
    pass


class CraftingPage(
    PageWithDoubleRecipeAccumulator[CraftingRecipe], type="patchouli:crafting"
):
    @classmethod
    @override
    def accumulator_type(cls):
        return CraftingAccumulatorPage


class CraftingAccumulatorPage(
    RecipeAccumulatorPage[CraftingPage, CraftingRecipe], page_type=CraftingPage
):
    pass


class EmptyPage(Page, type="patchouli:empty", template_type="patchouli:page"):
    draw_filler: bool = True


class EntityPage(PageWithText, type="patchouli:entity"):
    _entity_name: LocalizedStr = PrivateAttr()
    _texture: PNGTexture = PrivateAttr()

    entity: Entity
    scale: float = 1
    offset: float = 0
    rotate: bool = True
    default_rotation: float = -45
    name_field: LocalizedStr | None = Field(default=None, serialization_alias="name")

    @property
    def entity_name(self):
        return self._entity_name

    @property
    def name(self):
        if self.name_field is None or not self.name_field.value:
            return self._entity_name
        return self.name_field

    @property
    def texture(self):
        return self._texture

    @model_validator(mode="after")
    def _get_texture(self, info: ValidationInfo) -> Self:
        # can't be on Entity's validator because it's frozen and
        # causes circular references with the PNGTexture
        assert info.context is not None
        i18n = I18n.of(info)
        self._entity_name = i18n.localize_entity(self.entity.id)
        self._texture = PNGTexture.load_id(
            id="textures/entities" / self.entity.id + ".png", context=info.context
        )
        return self


class ImagePage(PageWithTitle, type="patchouli:image"):
    images: list[ImageField[TextureImage]]
    border: bool = False

    @property
    def images_with_alt(self):
        for image in self.images:
            if self.title:
                yield image, self.title
            else:
                yield image, str(image)


class LinkPage(TextPage, type="patchouli:link"):
    url: str
    link_text: LocalizedStr


class Multiblock(HexdocModel):
    """https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/multiblocks/"""

    mapping: dict[str, ImageField[ItemImage | TextureImage]]
    pattern: list[list[str]]
    symmetrical: bool = False
    offset: tuple[int, int, int] | None = None

    def bill_of_materials(self):
        character_counts = defaultdict[str, int](int)

        for layer in self.pattern:
            for row in layer:
                for character in row:
                    match character:
                        case str() if character in self.mapping:
                            character_counts[character] += 1
                        case " " | "0":  # air
                            pass
                        case _:
                            raise ValueError(
                                f"Character not found in multiblock mapping: `{character}`"
                            )

        materials = [
            (self.mapping[character], count)
            for character, count in character_counts.items()
        ]

        # sort by descending count, break ties by ascending name
        materials.sort(key=lambda v: v[0].name.value)
        materials.sort(key=lambda v: v[1], reverse=True)

        return materials

    @field_validator("mapping", mode="after")
    @classmethod
    def _add_default_mapping(
        cls,
        mapping: dict[str, ImageField[ItemImage | TagImage]],
        info: ValidationInfo,
    ):
        return {
            # FIXME: this needs to be ItemImage somehow
            "_": TextureImage.load_id(
                id=ResourceLocation("hexdoc", "textures/gui/any_block.png"),
                context=info.context or {},
            ),
        } | mapping


class MultiblockPage(PageWithText, type="patchouli:multiblock"):
    name: LocalizedStr
    multiblock_id: ResourceLocation | None = None
    multiblock: Multiblock | None = None
    enable_visualize: bool = True

    @model_validator(mode="after")
    def _check_multiblock(self) -> Self:
        if self.multiblock_id is None and self.multiblock is None:
            raise ValueError(f"One of multiblock_id or multiblock must be set\n{self}")
        return self


class QuestPage(PageWithText, type="patchouli:quest"):
    trigger: ResourceLocation | None = None
    title: LocalizedStr = LocalizedStr.with_value("Objective")


class RelationsPage(PageWithText, type="patchouli:relations"):
    entries: list[ResourceLocation]
    title: LocalizedStr = LocalizedStr.with_value("Related Chapters")

    @pass_context
    def get_entries(self, context: Context) -> list[ResourceLocation]:
        for entry in self.entries:
            if entry not in context["book"].all_entries:
                raise ValueError(f"Broken entry reference in relations: {entry}")
        return self.entries


class SmeltingPage(PageWithDoubleRecipe[SmeltingRecipe], type="patchouli:smelting"):
    pass


class SmithingPage(PageWithDoubleRecipe[SmithingRecipe], type="patchouli:smithing"):
    pass


class SmokingPage(PageWithDoubleRecipe[SmokingRecipe], type="patchouli:smoking"):
    pass


class StonecuttingPage(
    PageWithDoubleRecipe[StonecuttingRecipe], type="patchouli:stonecutting"
):
    pass


class SpotlightPage(PageWithText, type="patchouli:spotlight"):
    title_field: LocalizedStr | None = Field(default=None, alias="title")
    item: ImageField[ItemImage]
    link_recipe: bool = False

    @property
    def title(self) -> LocalizedStr | None:
        return self.title_field or self.item.name
