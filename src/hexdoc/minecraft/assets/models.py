from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Set
from typing import Annotated, Any, Literal

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.model import HexdocModel
from hexdoc.utils import JSONDict, clamping_validator

logger = logging.getLogger(__name__)

FoundNormalTexture = tuple[Literal["texture", "block_model"], ResourceLocation]
FoundGaslightingTexture = tuple[Literal["gaslighting"], list[FoundNormalTexture]]
FoundTexture = FoundNormalTexture | FoundGaslightingTexture

ItemDisplayPosition = Literal[
    "thirdperson_righthand",
    "thirdperson_lefthand",
    "firstperson_righthand",
    "firstperson_lefthand",
    "gui",
    "head",
    "ground",
    "fixed",
]

_Translation = Annotated[float, clamping_validator(-80, 80)]
_Scale = Annotated[float, clamping_validator(-4, 4)]


class ItemDisplay(HexdocModel):
    rotation: tuple[float, float, float] | None = None
    translation: tuple[_Translation, _Translation, _Translation] | None = None
    scale: tuple[_Scale, _Scale, _Scale] | None = None


class ModelOverride(HexdocModel):
    model: ResourceLocation
    """The id of the model to use if the case is met."""
    predicate: dict[ResourceLocation, float]


class ModelItem(HexdocModel):
    """https://minecraft.wiki/w/Tutorials/Models#Item_models

    This is called BaseModelItem instead of BaseItemModel because SomethingModel is our
    naming convention for abstract Pydantic models.
    """

    id: ResourceLocation
    """Not in the actual file."""

    parent: ResourceLocation | None = None
    """Loads a different model with the given id."""
    display: dict[ItemDisplayPosition, ItemDisplay] | None = None
    gui_light: Literal["front", "side"] = "side"
    overrides: list[ModelOverride] | None = None
    # TODO: minecraft_render would need to support this
    elements: Any | None = None
    # TODO: support texture variables etc?
    textures: dict[str, ResourceLocation] | None = None
    """Texture ids. For example, `{"layer0": "item/red_bed"}` refers to the resource
    `assets/minecraft/textures/item/red_bed.png`.

    Technically this is only allowed for `minecraft:item/generated`, but we're currently
    not loading Minecraft's item models, so there's lots of other parent ids that this
    field can show up for.
    """

    @classmethod
    def load_resource(cls, id: ResourceLocation, loader: ModResourceLoader):
        _, data = loader.load_resource("assets", "models", id, export=False)
        return cls.load_data(id, data)

    @classmethod
    def load_data(cls, id: ResourceLocation, data: JSONDict):
        return cls.model_validate(data | {"id": id})

    @property
    def item_id(self):
        if "/" not in self.id.path:
            return self.id
        path_without_prefix = "/".join(self.id.path.split("/")[1:])
        return self.id.with_path(path_without_prefix)

    @property
    def layer0(self):
        if self.textures:
            return self.textures.get("layer0")

    def find_texture(
        self,
        loader: ModResourceLoader,
        gaslighting_items: Set[ResourceLocation],
        checked_overrides: defaultdict[ResourceLocation, set[int]] | None = None,
    ) -> FoundTexture | None:
        """May return a texture **or** a model. Texture ids will start with `textures/`."""
        if checked_overrides is None:
            checked_overrides = defaultdict(set)

        # gaslighting
        # as of 0.11.1-7, all gaslighting item models are implemented with overrides
        if self.item_id in gaslighting_items:
            if not self.overrides:
                raise ValueError(
                    f"Model {self.id} for item {self.item_id} marked as gaslighting but"
                    " does not have overrides"
                )

            gaslighting_textures = list[FoundNormalTexture]()
            for i, override in enumerate(self.overrides):
                match self._find_override_texture(
                    i, override, loader, gaslighting_items, checked_overrides
                ):
                    case "gaslighting", _:
                        raise ValueError(
                            f"Model {self.id} for item {self.item_id} marked as"
                            f" gaslighting but override {i} resolves to another gaslighting texture"
                        )
                    case None:
                        break
                    case result:
                        gaslighting_textures.append(result)
            else:
                return "gaslighting", gaslighting_textures

        # if it exists, the layer0 texture is *probably* representative
        # TODO: impl multi-layer textures for Sam
        if self.layer0:
            texture_id = "textures" / self.layer0 + ".png"
            return "texture", texture_id

        # first resolvable override, if any
        for i, override in enumerate(self.overrides or []):
            if result := self._find_override_texture(
                i, override, loader, gaslighting_items, checked_overrides
            ):
                return result

        # try the parent id
        # we only do this for blocks in the same namespace because most other parents
        # are generic "base class"-type models which won't actually represent the item
        if (
            self.parent
            and self.parent.namespace == self.id.namespace
            and self.parent.path.startswith("block/")
        ):
            return "block_model", self.parent

        return None

    def _find_override_texture(
        self,
        index: int,
        override: ModelOverride,
        loader: ModResourceLoader,
        gaslighting_items: Set[ResourceLocation],
        checked_overrides: defaultdict[ResourceLocation, set[int]],
    ) -> FoundTexture | None:
        if override.model.path.startswith("block/"):
            return "block_model", override.model

        if index in checked_overrides[self.id]:
            logger.info(f"Ignoring recursive override: {override.model}")
            return None

        checked_overrides[self.id].add(index)
        return (
            (ModelItem)
            .load_resource(override.model, loader)
            .find_texture(loader, gaslighting_items, checked_overrides)
        )
