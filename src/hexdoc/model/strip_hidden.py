from typing import Any, dataclass_transform

from pydantic import ConfigDict, model_validator
from pydantic.config import JsonDict

from hexdoc.utils.deserialize.assertions import cast_or_raise

from .base import DEFAULT_CONFIG, HexdocModel


def _json_schema_extra(schema: JsonDict):
    cast_or_raise(schema.setdefault("patternProperties", {}), JsonDict).update(
        {
            r"^\_": {},
        },
    )


@dataclass_transform()
class StripHiddenModel(HexdocModel):
    """Base model which removes all keys starting with _ before validation."""

    model_config = DEFAULT_CONFIG | ConfigDict(
        json_schema_extra=_json_schema_extra,
    )

    @model_validator(mode="before")
    def _pre_root_strip_hidden(cls, values: dict[Any, Any] | Any) -> Any:
        if not isinstance(values, dict):
            return values

        return {
            key: value
            for key, value in values.items()
            if not (isinstance(key, str) and (key.startswith("_") or key == "$schema"))
        }
