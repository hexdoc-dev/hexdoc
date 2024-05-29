from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import (
    Field,
    PrivateAttr,
    SkipValidation,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import TypeVar, override
from yarl import URL

from hexdoc.core import I18n, ItemStack, LocalizedStr, Properties, ResourceLocation
from hexdoc.model import (
    InlineItemModel,
    InlineModel,
    TemplateModel,
    UnionModel,
)
from hexdoc.model.types import MustBeAnnotated
from hexdoc.plugin import PluginManager
from hexdoc.utils import (
    ContextSource,
    Inherit,
    InheritType,
    PydanticURL,
    cast_context,
    classproperty,
)

from .loader import MISSING_TEXTURE_ID, TAG_TEXTURE_ID, ImageLoader
from .model import BlockModel

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class _ImageFieldType:
    def __class_getitem__(cls, item: Any) -> Any:
        return Annotated[item | MissingImage, cls]


# scuffed, but Pydantic did it first
# see: pydantic.functional_validators.SkipValidation
if TYPE_CHECKING:
    ImageField = Annotated["_T | MissingImage", _ImageFieldType]
else:

    class ImageField(_ImageFieldType):
        pass


class HexdocImage(TemplateModel, MustBeAnnotated, ABC, annotation=ImageField):
    """An image that can be rendered in a hexdoc web book."""

    id: ResourceLocation

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

    @property
    @abstractmethod
    def first_url(self) -> URL: ...

    @abstractmethod
    def _get_name(self, info: ValidationInfo) -> LocalizedStr: ...

    @model_validator(mode="after")
    def _set_name(self, info: ValidationInfo):
        try:
            self._name = self._get_name(info)
        except ValidationError as e:
            logger.debug(f"Failed to get name for {self.__class__}: {e}")
            self._name = LocalizedStr.with_value(str(self.id))
        return self


class URLImage(HexdocImage, template_id="hexdoc:single"):
    url: PydanticURL
    pixelated: bool = True

    @property
    @override
    def first_url(self):
        return self.url


class TextureImage(URLImage, InlineModel):
    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: dict[str, Any]) -> Any:
        url = ImageLoader.of(context).render_texture(id)
        return cls(id=id, url=url)

    @override
    def _get_name(self, info: ValidationInfo):
        return I18n.of(info).localize_texture(self.id)


class MissingImage(TextureImage, annotation=None):
    @override
    @classmethod
    def load_id(cls, id: ResourceLocation, context: dict[str, Any]) -> Any:
        if cls.should_raise(id, context):
            raise ValueError(f"Failed to load image for id: {id}")
        logger.warning(f"Using missing texture for id: {id}")

        url = ImageLoader.of(context).render_texture(MISSING_TEXTURE_ID)
        return cls(id=id, url=url, pixelated=True)

    @override
    def _get_name(self, info: ValidationInfo):
        return LocalizedStr.with_value(str(self.id))

    @classmethod
    def should_raise(cls, id: ResourceLocation, context: ContextSource):
        props = Properties.of(context).textures
        return props.strict and not props.can_be_missing(id)


class ItemImage(HexdocImage, InlineItemModel, UnionModel, ABC):
    item: ItemStack

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


class SingleItemImage(URLImage, ItemImage):
    model: BlockModel | None

    @override
    @classmethod
    def load_id(cls, item: ItemStack, context: dict[str, Any]) -> Any:
        result = ImageLoader.of(context).render_item(item)
        return cls(
            id=item.id,
            item=item,
            url=result.url,
            model=result.model,
            pixelated=result.image_type.pixelated,
        )

    @override
    def _get_name(self, info: ValidationInfo):
        return I18n.of(info).localize_item(self.id)


class CyclingImage(HexdocImage, template_id="hexdoc:cycling"):
    images: SkipValidation[list[HexdocImage]] = Field(min_length=1)

    @property
    @override
    def first_url(self):
        return self.images[0].first_url

    @override
    def _get_name(self, info: ValidationInfo):
        return self.images[0].name


class TagImage(URLImage, InlineModel):
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


def validate_image(
    model_type: type[_T] | Any,
    value: Any,
    context: ContextSource,
) -> _T | MissingImage:
    ta = TypeAdapter(ImageField[model_type])
    return ta.validate_python(value, context=cast_context(context))
