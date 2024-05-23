from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic

from pydantic import (
    Field,
    PrivateAttr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import TypeVar, override

from hexdoc.core import ItemStack, ResourceLocation
from hexdoc.minecraft.i18n import I18n, LocalizedStr
from hexdoc.minecraft.model import BlockModel
from hexdoc.model import (
    InlineItemModel,
    InlineModel,
    TemplateModel,
    UnionModel,
)
from hexdoc.plugin import PluginManager
from hexdoc.utils import Inherit, InheritType, PydanticURL, classproperty

from .loader import TAG_TEXTURE_ID, ImageLoader

_T_ResourceLocation = TypeVar("_T_ResourceLocation", default=ResourceLocation)


class HexdocImage(TemplateModel, Generic[_T_ResourceLocation], ABC):
    """An image that can be rendered in a hexdoc web book."""

    id: _T_ResourceLocation

    _name: LocalizedStr = PrivateAttr()

    # change default from None to Inherit
    def __init_subclass__(
        cls,
        *,
        template_id: str | ResourceLocation | InheritType | None = Inherit,
        **kwargs: Any,
    ):
        super().__init_subclass__(template_id=template_id, **kwargs)

    @classproperty
    @classmethod
    @override
    def template(cls):
        return cls.template_id.template_path("images")

    @property
    def name(self):
        return self._name

    @abstractmethod
    def _get_name(self, info: ValidationInfo) -> LocalizedStr: ...

    @model_validator(mode="after")
    def _set_name(self, info: ValidationInfo):
        self._name = self._get_name(info)
        return self


class URLImage(HexdocImage[_T_ResourceLocation], template_id="hexdoc:single"):
    url: PydanticURL
    pixelated: bool = True


class TextureImage(URLImage[ResourceLocation], InlineModel):
    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: dict[str, Any]) -> Any:
        url = ImageLoader.of(context).render_texture(id)
        return cls(id=id, url=url)

    @override
    def _get_name(self, info: ValidationInfo):
        return I18n.of(info).localize_texture(self.id)


class ItemImage(HexdocImage[ItemStack], InlineItemModel, UnionModel, ABC):
    @override
    @classmethod
    @abstractmethod
    def load_id(cls, item: ItemStack, context: dict[str, Any]) -> Any:
        pm = PluginManager.of(context)
        return cls._resolve_union(
            item,
            context,
            model_types=pm.item_image_types,
            allow_ambiguous=True,
        )


class SingleItemImage(URLImage[ItemStack], ItemImage):
    model: BlockModel | None

    @override
    @classmethod
    def load_id(cls, item: ItemStack, context: dict[str, Any]) -> Any:
        url, model = ImageLoader.of(context).render_item(item)
        return cls(id=item, url=url, model=model)

    @override
    def _get_name(self, info: ValidationInfo):
        return I18n.of(info).localize_item(self.id)


class CyclingImage(HexdocImage[_T_ResourceLocation], template_id="hexdoc:cycling"):
    images: list[HexdocImage] = Field(min_length=1)

    @override
    def _get_name(self, info: ValidationInfo):
        return self.images[0].name


class TagImage(URLImage[ResourceLocation], InlineModel):
    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: dict[str, Any]) -> Any:
        # TODO: load images for all the items in the tag?
        url = ImageLoader.of(context).render_texture(TAG_TEXTURE_ID)
        return cls(id=id, url=url)

    @override
    def _get_name(self, info: ValidationInfo):
        return I18n.of(info).localize_item_tag(self.id)

    @field_validator("id", mode="after")
    @classmethod
    def _validate_id(cls, id: ResourceLocation):
        assert id.is_tag, f"Expected tag id, got {id}"
        return id
