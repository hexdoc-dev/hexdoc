from typing import Any, Callable, Iterable

from pydantic import ConfigDict, JsonValue


def inherited(
    schema: dict[str, Any],
    inherit: Iterable[str] = ("title", "description"),
):
    return {key: schema[key] for key in inherit if key in schema}


def type_str(schema: dict[str, Any]):
    return {
        "type": "string",
    }


def json_schema_extra(
    *fns: Callable[[dict[str, Any]], dict[str, Any]],
    replace: bool = False,
    **extra: JsonValue,
):
    def inner(schema: dict[str, Any]):
        new_schema = dict[str, Any]()
        for fn in fns:
            new_schema |= fn(schema)
        new_schema |= extra

        if replace:
            schema.clear()

        schema.update(new_schema)

    return inner


def json_schema_extra_config(
    *fns: Callable[[dict[str, Any]], dict[str, Any]],
    replace: bool = True,
    **extra: JsonValue,
) -> ConfigDict:
    return {"json_schema_extra": json_schema_extra(*fns, replace=replace, **extra)}
