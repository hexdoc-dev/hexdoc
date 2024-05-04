from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.model import IGNORE_EXTRA_CONFIG, HexdocModel

from .display import DisplayPosition, DisplayPositionName
from .element import Element
from .variable import TextureVariable


class BlockModel(HexdocModel):
    """Represents a Minecraft block (or item!!) model.

    https://minecraft.wiki/w/Tutorials/Models
    """

    model_config = IGNORE_EXTRA_CONFIG

    # common fields

    parent: ResourceLocation | None = None
    """Loads a different model from the given path, in form of a resource location.

    If both "parent" and "elements" are set, the "elements" tag overrides the "elements"
    tag from the previous model.
    """
    display: dict[DisplayPositionName, DisplayPosition] = Field(default_factory=dict)
    """Holds the different places where item models are displayed.

    `fixed` refers to item frames, while the rest are as their name states.
    """
    textures: dict[str, TextureVariable | ResourceLocation] = Field(
        default_factory=dict
    )
    """Holds the textures of the model, in form of a resource location or can be another
    texture variable."""
    elements: list[Element] | None = None
    """Contains all the elements of the model. They can have only cubic forms.

    If both "parent" and "elements" are set, the "elements" tag overrides the "elements"
    tag from the previous model.
    """
    gui_light: Literal["front", "side"] = Field(None, validate_default=False)
    """If set to `side` (default), the model is rendered like a block.

    If set to `front`, model is shaded like a flat item.

    Note: although the wiki only lists this field for item models, Minecraft sets it in
    the models `minecraft:block/block` and `minecraft:block/calibrated_sculk_sensor`.
    """

    # blocks only

    ambientocclusion: bool = True
    """Whether to use ambient occlusion or not.

    Note: only works on parent file.
    """
    render_type: ResourceLocation | None = None
    """Sets the rendering type for this model.

    https://docs.minecraftforge.net/en/latest/rendering/modelextensions/rendertypes/
    """

    # items only

    overrides: list[ItemOverride] | None = None
    """Determines cases in which a different model should be used based on item tags.

    All cases are evaluated in order from top to bottom and last predicate that matches
    overrides. However, overrides are ignored if it has been already overridden once,
    for example this avoids recursion on overriding to the same model.
    """

    @classmethod
    def load(cls, loader: ModResourceLoader, model_id: ResourceLocation):
        try:
            return loader.load_resource(
                type="assets",
                folder="models",
                id=model_id,
                decode=cls.model_validate_json,
            )
        except Exception as e:
            e.add_note(f"  note: {model_id=}")
            raise

    def apply_parent(self, parent: Self):
        self.parent = parent.parent

        # prefer current display/textures over parent
        self.display = parent.display | self.display
        self.textures = parent.textures | self.textures

        # only use parent elements if current model doesn't have elements
        if self.elements is None:
            self.elements = parent.elements
        if not self._was_gui_light_set:
            self.gui_light = parent.gui_light

        self.ambientocclusion = parent.ambientocclusion
        self.render_type = self.render_type or parent.render_type

    def load_parents_and_apply(self, loader: ModResourceLoader):
        while self.parent:
            _, parent = loader.load_resource(
                "assets",
                "models",
                self.parent,
                decode=self.model_validate_json,
            )
            self.apply_parent(parent)

    def resolve_texture_variables(self):
        textures = dict[str, ResourceLocation]()
        for name, value in self.textures.items():
            # TODO: is it possible for this to loop forever?
            while not isinstance(value, ResourceLocation):
                value = value.lstrip("#")
                if value == name:
                    raise ValueError(f"Cyclic texture variable detected: {name}")
                value = self.textures[value]
            textures[name] = value
        return textures

    @model_validator(mode="after")
    def _set_default_gui_light(self):
        self._was_gui_light_set = self.gui_light is not None  # type: ignore
        if not self._was_gui_light_set:
            self.gui_light = "side"
        return self


class ItemOverride(HexdocModel):
    """An item model override case.

    https://minecraft.wiki/w/Tutorials/Models#Item_models
    """

    model: ResourceLocation
    """The path to the model to use if the case is met."""
    predicate: dict[ResourceLocation, float]
    """Item predicates that must be true for this model to be used."""
