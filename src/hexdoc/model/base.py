from __future__ import annotations

from contextvars import ContextVar
from typing import (
    Any,
    ClassVar,
    cast,
    dataclass_transform,
)

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationInfo, model_validator
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
