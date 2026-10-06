import inspect
import string
import textwrap
from typing import Any, ClassVar, Sequence

from pydantic import ConfigDict, field_validator, model_validator
from pydantic.dataclasses import dataclass
from pydantic.fields import FieldInfo
from typing_extensions import Unpack

from hexdoc.utils import Inherit, InheritType
from hexdoc.utils.json_schema import inherited, json_schema_extra_config, type_str

from .base import DEFAULT_CONFIG, HexdocModel


@dataclass(
    frozen=True,
    config=DEFAULT_CONFIG
    | json_schema_extra_config(
        type_str,
        inherited,
        pattern=r"(#|0x)?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})",
    ),
)
class Color:
    """Represents a hexadecimal color.

    Inputs are coerced to lowercase `rrggbb`. Raises ValueError on invalid input.

    Valid formats, all of which would be converted to `0099ff`:
    - `"#0099FF"`
    - `"#0099ff"`
    - `"#09F"`
    - `"#09f"`
    - `"0099FF"`
    - `"0099ff"`
    - `"09F"`
    - `"09f"`
    - `0x0099ff`
    """

    value: str

    @model_validator(mode="before")
    def _pre_root(cls, value: Any):
        if isinstance(value, (str, int)):
            return {"value": value}
        return value

    @field_validator("value", mode="before")
    def _check_value(cls, value: Any) -> str:
        # type check
        match value:
            case str():
                value = value.removeprefix("#").lower()
            case int():
                # int to hex string
                value = f"{value:0>6x}"
            case _:
                raise TypeError(f"Expected str or int, got {type(value)}")

        # 012 -> 001122
        if len(value) == 3:
            value = "".join(c + c for c in value)

        # length and character check
        if len(value) != 6 or any(c not in string.hexdigits for c in value):
            raise ValueError(f"invalid color code: {value}")

        return value


class MustBeAnnotated(HexdocModel):
    _annotation_type: ClassVar[type[Any] | None]

    def __init_subclass__(
        cls,
        annotation: type[Any] | InheritType | None = Inherit,
        **kwargs: Unpack[ConfigDict],
    ):
        super().__init_subclass__(**kwargs)
        if annotation != Inherit:
            if annotation and not inspect.isclass(annotation):
                raise TypeError(
                    f"Expected annotation to be a type or None, got {type(annotation)}: {annotation}"
                )
            cls._annotation_type = annotation

    @classmethod
    def __hexdoc_check_model_field__(
        cls,
        model_type: type[HexdocModel],
        field_name: str,
        field_info: FieldInfo,
        origin_stack: Sequence[Any],
        annotation_stack: Sequence[Any],
    ) -> None:
        if cls._annotation_type is None:
            return
        if cls._annotation_type not in annotation_stack:
            annotation = cls._annotation_type.__name__
            raise TypeError(
                textwrap.dedent(
                    f"""\
                    {cls.__name__} must be annotated with {annotation} (eg. {annotation}[{cls.__name__}]) when used as a validation type hint.
                      Model: {model_type}
                      Field: {field_name}
                      Type:  {field_info.rebuild_annotation()}
                    """.rstrip()
                )
            )
