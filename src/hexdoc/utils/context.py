from typing import Any, Self, cast, overload

from jinja2.runtime import Context
from pydantic import ValidationInfo

from .classproperties import classproperty
from .deserialize import cast_or_raise

ContextSource = dict[str, Any] | ValidationInfo | Context
"""Valid argument types for `ValidationContext.of`."""


class ValidationContext:
    @classproperty
    @classmethod
    def context_key(cls) -> str:
        return str(cls)

    @overload
    @classmethod
    def of(cls, info: ValidationInfo, /) -> Self: ...

    @overload
    @classmethod
    def of(cls, context: dict[str, Any] | Context, /) -> Self: ...

    @overload
    @classmethod
    def of(cls, source: ContextSource, /) -> Self: ...

    @classmethod
    def of(cls, source: ContextSource, /) -> Self:
        match source:
            case dict() | Context():
                pass
            case _:
                source = cast_or_raise(source.context, dict)
        return cast_or_raise(source[cls.context_key], cls)

    def add_to_context(self, context: dict[str, Any], overwrite: bool = False):
        return add_to_context(context, self.context_key, self, overwrite)


def add_to_context(
    context: dict[str, Any],
    key: str,
    value: Any,
    overwrite: bool = False,
):
    if not overwrite and key in context:
        raise KeyError(f"Key {key} for {value} already exists in context")
    context[key] = value


def cast_context(source: ContextSource) -> dict[str, Any]:
    """Wrapper for `typing.cast` to simplify passing `ContextSource` to validation
    methods. This is a lie to keep the type checker happy."""
    return cast(dict[str, Any], source)
