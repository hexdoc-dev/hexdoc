from __future__ import annotations

from functools import cached_property
from typing import Literal, Self

from pydantic import Field, PrivateAttr, model_validator

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.model import IGNORE_EXTRA_CONFIG, HexdocModel
from hexdoc.utils.types import PydanticOrderedSet, cast_nullable

from .display import DisplayPosition, DisplayPositionName
from .element import Element
from .variable import TextureVariable


class BlockModel(HexdocModel):
    """Represents a Minecraft block (or item!!) model.

    https://minecraft.wiki/w/Tutorials/Models
    """

    model_config = IGNORE_EXTRA_CONFIG

    # common fields

    parent_id: ResourceLocation | None = Field(None, alias="parent")
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

    # internal fields
    _is_generated_item: bool = PrivateAttr(False)

    @classmethod
    def load_and_resolve(cls, loader: ModResourceLoader, model_id: ResourceLocation):
        resource_dir, model = cls.load_unresolved(loader, model_id)
        return resource_dir, model.resolve(loader)

    @classmethod
    def load_unresolved(cls, loader: ModResourceLoader, model_id: ResourceLocation):
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

    def resolve(self, loader: ModResourceLoader):
        """Loads this model's parents and applies them in-place.

        Returns this model for convenience.
        """
        loaded_parents = PydanticOrderedSet[ResourceLocation]()
        while parent_id := self.parent_id:
            if parent_id in loaded_parents:
                raise ValueError(
                    "Recursive model parent chain: "
                    + " -> ".join(str(v) for v in [*loaded_parents, parent_id])
                )
            loaded_parents.add(parent_id)

            match parent_id:
                case ResourceLocation("minecraft", "builtin/generated"):
                    self._is_generated_item = True
                    self.parent_id = None
                case ResourceLocation("minecraft", "builtin/entity"):
                    raise ValueError(f"Unsupported model parent id: {parent_id}")
                case _:
                    _, parent = self.load_unresolved(loader, parent_id)
                    self._apply_parent(parent)

        return self

    def _apply_parent(self, parent: Self):
        self.parent_id = parent.parent_id

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

    @property
    def is_resolved(self):
        return self.parent_id is None

    @property
    def is_generated_item(self):
        return self._is_generated_item

    @cached_property
    def resolved_textures(self):
        assert self.is_resolved, "Cannot resolve textures for unresolved model"

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
        self._was_gui_light_set = cast_nullable(self.gui_light) is not None
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
