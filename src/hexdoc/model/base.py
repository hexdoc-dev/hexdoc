from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeVar, dataclass_transform

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationInfo, model_validator
from pydantic.functional_validators import ModelBeforeValidator
from pydantic_core import Some
from pydantic_settings import BaseSettings, SettingsConfigDict

from hexdoc.plugin import PluginManager
from hexdoc.utils import set_contextvar
from hexdoc.utils.classproperties import ClassPropertyDescriptor

DEFAULT_CONFIG = ConfigDict(
    extra="forbid",
    validate_default=True,
    ignored_types=(  # pyright: ignore[reportUnknownArgumentType]
        ClassPropertyDescriptor,
    ),
)

_init_context_var = ContextVar[Any]("_init_context_var", default=None)


def init_context(value: Any):
    """https://docs.pydantic.dev/latest/usage/validators/#using-validation-context-with-basemodel-initialization"""
    return set_contextvar(_init_context_var, value)


@dataclass_transform()
class HexdocBaseModel(BaseModel):
    """Base class for all Pydantic models in hexdoc. You should probably use
    `HexdocModel` or `ValidationContext` instead.

    Sets the default model config, and overrides __init__ to allow using the
    `init_context` context manager to set validation context for constructors.
    """

    model_config = DEFAULT_CONFIG

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
        if cls.__hexdoc_before_validator__:
            return cls.__hexdoc_before_validator__(cls, value, info)
        return value


@dataclass_transform()
class ValidationContext(HexdocBaseModel):
    """Base class for Pydantic validation context for `HexdocModel`."""


class PluginManagerContext(ValidationContext, arbitrary_types_allowed=True):
    pm: PluginManager


@dataclass_transform()
class HexdocModel(HexdocBaseModel):
    """Base class for most Pydantic models in hexdoc.

    Includes type overrides to require using subclasses of `ValidationContext` for
    validation context.
    """

    model_config = DEFAULT_CONFIG

    # pydantic core actually allows PyAny for context, so I'm pretty sure this is fine
    if TYPE_CHECKING:

        @classmethod
        def model_validate(  # pyright: ignore[reportIncompatibleMethodOverride]
            cls,
            obj: Any,
            *,
            strict: bool | None = None,
            from_attributes: bool | None = None,
            context: ValidationContext | None = None,
        ) -> Self:
            ...

        @classmethod
        def model_validate_json(  # pyright: ignore[reportIncompatibleMethodOverride]
            cls,
            json_data: str | bytes | bytearray,
            *,
            strict: bool | None = None,
            context: ValidationContext | None = None,
        ) -> Self:
            ...


class HexdocSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    @classmethod
    def model_getenv(cls, defaults: Any = None):
        return cls.model_validate(defaults or {})


_T = TypeVar("_T")


class HexdocTypeAdapter(TypeAdapter[_T]):
    def __init__(self, type: _T, *, config: ConfigDict | None = None):
        if config is None and not isinstance(type, BaseModel):
            config = DEFAULT_CONFIG
        return super().__init__(type, config=config)

    if TYPE_CHECKING:

        def validate_python(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            __object: Any,
            *,
            strict: bool | None = None,
            from_attributes: bool | None = None,
            context: ValidationContext | None = None,
        ) -> _T:
            ...

        def validate_json(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            __data: str | bytes,
            *,
            strict: bool | None = None,
            context: ValidationContext | None = None,
        ) -> _T:
            ...

        def validate_strings(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            __obj: Any,
            *,
            strict: bool | None = None,
            context: ValidationContext | None = None,
        ) -> _T:
            ...

        def get_default_value(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            *,
            strict: bool | None = None,
            context: ValidationContext | None = None,
        ) -> Some[_T] | None:
            ...
