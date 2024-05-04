from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self, dataclass_transform

from pydantic import GetJsonSchemaHandler, TypeAdapter, ValidationInfo, model_validator
from pydantic.functional_validators import ModelWrapValidatorHandler
from pydantic_core import core_schema as cs

from hexdoc.core.resource import (
    BaseResourceLocation,
    ItemStack,
    ResourceLocation,
)

from .base import HexdocModel


class BaseInlineModel(HexdocModel):
    @classmethod
    @abstractmethod
    def _id_type(cls) -> type[BaseResourceLocation]: ...

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: cs.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        return handler(TypeAdapter(cls._id_type()).core_schema)


@dataclass_transform()
class InlineModel(BaseInlineModel, ABC):
    @classmethod
    def _id_type(cls):
        return ResourceLocation

    @classmethod
    @abstractmethod
    def load_id(cls, id: ResourceLocation, context: dict[str, Any]) -> Any: ...

    @model_validator(mode="wrap")
    @classmethod
    def _wrap_root_load_from_id(
        cls,
        value: Any,
        handler: ModelWrapValidatorHandler[Self],
        info: ValidationInfo,
    ) -> Self:
        """Loads the recipe from json if the actual value is a resource location str.

        Uses a wrap validator so we load the file *before* resolving the tagged union.
        """
        # if necessary, convert the id to a ResourceLocation
        match value:
            case str():
                id = ResourceLocation.from_str(value)
            case ResourceLocation() as id:
                pass
            case _:
                return handler(value)

        # load the data
        assert info.context is not None
        return handler(cls.load_id(id, info.context))


@dataclass_transform()
class InlineItemModel(BaseInlineModel, ABC):
    @classmethod
    def _id_type(cls):
        return ItemStack

    @classmethod
    @abstractmethod
    def load_id(cls, item: ItemStack, context: dict[str, Any]) -> Any: ...

    @model_validator(mode="wrap")
    @classmethod
    def _wrap_root_load_from_id(
        cls,
        value: Any,
        handler: ModelWrapValidatorHandler[Self],
        info: ValidationInfo,
    ) -> Self:
        """Loads the recipe from json if the actual value is a resource location str.

        Uses a wrap validator so we load the file *before* resolving the tagged union.
        """
        # if necessary, convert the id to a ItemStack
        match value:
            case str():
                item = ItemStack.from_str(value)
            case ItemStack() as item:
                pass
            case ResourceLocation() as id:
                item = ItemStack(namespace=id.namespace, path=id.path)
            case _:
                return handler(value)

        # load the data
        assert info.context is not None
        return handler(cls.load_id(item, info.context))
