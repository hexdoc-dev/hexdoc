from __future__ import annotations

import inspect
import typing
from contextvars import ContextVar
from typing import (
    Annotated,
    Any,
    ClassVar,
    Sequence,
    cast,
    dataclass_transform,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    SkipValidation,
    TypeAdapter,
    ValidationInfo,
    model_validator,
)
from pydantic.fields import FieldInfo
from pydantic.functional_validators import ModelBeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

from hexdoc.utils import ValidationContext, set_contextvar
from hexdoc.utils.classproperties import ClassPropertyDescriptor

DEFAULT_CONFIG = ConfigDict(
    extra="forbid",
    validate_default=True,
    ignored_types=(  # pyright: ignore[reportUnknownArgumentType]
        ClassPropertyDescriptor,
        URL,
    ),
)

IGNORE_EXTRA_CONFIG = DEFAULT_CONFIG | ConfigDict(
    extra="ignore",
)

_init_context_var = ContextVar[Any]("_init_context_var", default=None)


def init_context(value: Any):
    """https://docs.pydantic.dev/latest/usage/validators/#using-validation-context-with-basemodel-initialization"""
    return set_contextvar(_init_context_var, value)


@dataclass_transform()
class HexdocModel(BaseModel):
    """Base class for all Pydantic models in hexdoc.

    Sets the default model config, and overrides __init__ to allow using the
    `init_context` context manager to set validation context for constructors.
    """

    model_config = DEFAULT_CONFIG
    """@private"""

    __hexdoc_before_validator__: ClassVar[ModelBeforeValidator | None] = None

    @classmethod
    def __hexdoc_check_model_field__(
        cls,
        model_type: type[HexdocModel],
        field_name: str,
        field_info: FieldInfo,
        origin_stack: Sequence[Any],
        annotation_stack: Sequence[Any],
    ) -> None:
        """Called when initializing a model of type `model_type` for all places where
        `cls` is in a type annotation."""

    # global model field validation (mostly used for HexdocImage)
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        for field_name, field_info in cls.model_fields.items():
            cls._hexdoc_check_model_field(field_name, field_info)

    @classmethod
    def _hexdoc_check_model_field(cls, field_name: str, field_info: FieldInfo):
        if field_type := field_info.rebuild_annotation():
            cls._hexdoc_check_model_field_type(
                field_name, field_info, field_type, [], []
            )

    @classmethod
    def _hexdoc_check_model_field_type(
        cls,
        field_name: str,
        field_info: FieldInfo,
        field_type: Any,
        origin_stack: list[Any],
        annotation_stack: list[Any],
    ):
        # TODO: better way to detect recursive types?
        if len(origin_stack) > 25:
            return

        if inspect.isclass(field_type) and issubclass(field_type, HexdocModel):
            field_type.__hexdoc_check_model_field__(
                cls,
                field_name,
                field_info,
                origin_stack,
                annotation_stack,
            )

        if origin := typing.get_origin(field_type):
            args = typing.get_args(field_type)

            if origin is Annotated:
                arg, *annotations = args
                args = [arg]
            else:
                annotations = []

            if any(isinstance(a, SkipValidation) for a in annotations):
                return

            origin_stack.append(origin)
            annotation_stack += reversed(annotations)
            for arg in args:
                cls._hexdoc_check_model_field_type(
                    field_name,
                    field_info,
                    arg,
                    origin_stack,
                    annotation_stack,
                )
            origin_stack.pop()
            if annotations:
                del annotation_stack[-len(annotations) :]

    def __init__(__pydantic_self__, **data: Any) -> None:  # type: ignore
        __tracebackhide__ = True
        __pydantic_self__.__pydantic_validator__.validate_python(
            data,
            self_instance=__pydantic_self__,
            context=_init_context_var.get(),
        )

    __init__.__pydantic_base_init__ = True  # type: ignore

    @model_validator(mode="before")
    @classmethod
    def _call_hexdoc_before_validator(cls, value: Any, info: ValidationInfo):
        # allow json schema field in all models
        if isinstance(value, dict):
            value = cast(dict[Any, Any], value)
            value.pop("$schema", None)
        if cls.__hexdoc_before_validator__:
            return cls.__hexdoc_before_validator__(cls, value, info)
        return value


class HexdocSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    @classmethod
    def model_getenv(cls, defaults: Any = None):
        return cls.model_validate(defaults or {})


class ValidationContextModel(HexdocModel, ValidationContext):
    pass


HexdocTypeAdapter = TypeAdapter
"""DEPRECATED: Use `pydantic.TypeAdapter` instead."""
