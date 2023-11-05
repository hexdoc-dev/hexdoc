import string
from typing import Any

from pydantic import field_validator, model_validator
from pydantic.dataclasses import dataclass

from .base import DEFAULT_CONFIG


@dataclass(config=DEFAULT_CONFIG, frozen=True)
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
