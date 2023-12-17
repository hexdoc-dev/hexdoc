from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, ClassVar, Generic, Protocol, TypeVar

from packaging.specifiers import SpecifierSet
from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema
from typing_extensions import override

from hexdoc.model.base import HexdocModel

_T = TypeVar("_T")

_T_ModelType = TypeVar("_T_ModelType", bound=type[HexdocModel])

_If = TypeVar("_If")
_Else = TypeVar("_Else")


class VersionSource(Protocol):
    @classmethod
    def get(cls) -> str | None:
        """Returns the current version."""
        ...

    @classmethod
    def matches(cls, specifier: str | SpecifierSet) -> bool:
        """Returns True if the current version matches the version_spec."""
        ...


class MinecraftVersion(VersionSource):
    MINECRAFT_VERSION: ClassVar[str | None] = None

    @override
    @classmethod
    def get(cls) -> str | None:
        return cls.MINECRAFT_VERSION

    @override
    @classmethod
    def matches(cls, specifier: str | SpecifierSet) -> bool:
        if isinstance(specifier, str):
            specifier = SpecifierSet(specifier)
        if (version := cls.get()) is None:
            return True
        return version in specifier


@dataclass(frozen=True)
class Versioned:
    """Base class for types which can behave differently based on a version source,
    which defaults to MinecraftVersion."""

    version_spec: str
    version_source: VersionSource = field(default=MinecraftVersion, kw_only=True)

    @property
    def is_current(self):
        return self.version_source.matches(self.version_spec)


@dataclass(frozen=True)
class IsVersion(Versioned):
    """Instances of this class are truthy if version_spec matches version_source, which
    defaults to MinecraftVersion.

    Can be used as a Pydantic validator annotation, which raises ValueError if
    version_spec doesn't match the current version. Use it like this:

    `Annotated[str, IsVersion(">=1.20")] | Annotated[None, IsVersion("<1.20")]`

    Can also be used as a class decorator for Pydantic models, which raises ValueError
    when validating the model if version_spec doesn't match the current version.
    Decorated classes must subclass HexdocModel (or HexdocBaseModel).
    """

    def __bool__(self):
        return self.is_current

    def __call__(self, cls: _T_ModelType) -> _T_ModelType:
        cls.__hexdoc_before_validator__ = self._model_validator
        return cls

    def __get_pydantic_core_schema__(
        self,
        source_type: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(
            self._schema_validator,
            schema=handler(source_type),
        )

    def _schema_validator(self, value: Any):
        if self.is_current:
            return value
        raise ValueError(
            f"Expected version {self.version_spec}, got {self.version_source.get()}"
        )

    def _model_validator(self, cls: Any, value: Any, info: ValidationInfo):
        return self._schema_validator(value)


Before_1_19 = Annotated[_T, IsVersion("<1.19")]
"""Alias for `Annotated[_T, IsVersion("<1.19")]`."""
AtLeast_1_19 = Annotated[_T, IsVersion(">=1.19")]
"""Alias for `Annotated[_T, IsVersion(">=1.19")]`."""
After_1_19 = Annotated[_T, IsVersion(">1.19")]
"""Alias for `Annotated[_T, IsVersion("<1.19")]`."""

Before_1_20 = Annotated[_T, IsVersion("<1.20")]
"""Alias for `Annotated[_T, IsVersion("<1.20")]`."""
AtLeast_1_20 = Annotated[_T, IsVersion(">=1.20")]
"""Alias for `Annotated[_T, IsVersion(">=1.20")]`."""
After_1_20 = Annotated[_T, IsVersion(">1.20")]
"""Alias for `Annotated[_T, IsVersion("<1.20")]`."""


@dataclass(frozen=True)
class ValueIfVersion(Versioned, Generic[_If, _Else]):
    value_if: _If
    value_else: _Else

    def __call__(self) -> _If | _Else:
        if self.is_current:
            return self.value_if
        return self.value_else
