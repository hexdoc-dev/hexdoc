from typing import Any, Self, overload

from pydantic import ValidationInfo

from .classproperties import classproperty
from .deserialize import cast_or_raise


class ValidationContext:
    @classproperty
    @classmethod
    def context_key(cls) -> str:
        return str(cls)

    @overload
    @classmethod
    def of(cls, info: ValidationInfo, /) -> Self:
        ...

    @overload
    @classmethod
    def of(cls, context: dict[str, Any], /) -> Self:
        ...

    @classmethod
    def of(cls, source: ValidationInfo | dict[str, Any], /) -> Self:
        if not isinstance(source, dict):
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
