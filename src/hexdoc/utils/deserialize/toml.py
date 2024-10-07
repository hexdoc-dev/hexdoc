import datetime
import re
import tomllib
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import CoreSchema
from pydantic_core.core_schema import NoneSchema, NullableSchema, StringSchema
from typing_extensions import TypedDict, override

from .assertions import cast_or_raise

# TODO: there's (figuratively) literally no comments in this file

TOMLValue = (
    str
    | int
    | float
    | bool
    | datetime.datetime
    | datetime.date
    | datetime.time
    | list["TOMLValue"]
    | dict[str, "TOMLValue"]
    | None
)

TOMLDict = dict[str, "TOMLValue"]


def fill_placeholders(data: TOMLDict):
    """Replaces hexdoc-style string placeholders in-place in a parsed TOML file."""
    _fill_placeholders(data, [data], set())


def _expand_placeholder(
    data: TOMLDict,
    stack: list[TOMLDict],
    expanded: set[tuple[int, str | int]],
    placeholder: str,
) -> str:
    tmp_stack: list[TOMLDict] = stack[:]

    # leading $ references the root table
    if placeholder[0] == "$":  # the regex *should* ensure placeholder is never empty
        placeholder = placeholder.lstrip("$.")
        tmp_stack = [tmp_stack[0]]

    key = "UNBOUND"
    keys = placeholder.split(".")
    for i, key in enumerate(keys):
        if n := key.count("^"):
            tmp_stack = tmp_stack[:-n]
            key = key.replace("^", "")
        if key and i < len(keys) - 1:
            # TODO: does this work?
            new = cast_or_raise(tmp_stack[-1][key], TOMLDict)
            tmp_stack.append(new)

    table = tmp_stack[-1]
    if (id(table), key) not in expanded:
        _handle_child(data, tmp_stack, expanded, key, table[key], table.__setitem__)

    value = cast_or_raise(table[key], str)
    return value


_T_key = TypeVar("_T_key", str, int)

_PLACEHOLDER_RE = re.compile(r"\{(.+?)\}")


def _handle_child(
    data: TOMLDict,
    stack: list[TOMLDict],
    expanded: set[tuple[int, str | int]],
    key: _T_key,
    value: TOMLValue,
    update: Callable[[_T_key, TOMLValue], None],
):
    # wait no that sounds wrong-
    match value:
        case str():
            # fill the string's placeholders
            for match in reversed(list(_PLACEHOLDER_RE.finditer(value))):
                try:
                    v = _expand_placeholder(
                        data,
                        stack,
                        expanded,
                        match[1],
                    )
                    value = value[: match.start()] + v + value[match.end() :]
                except Exception as e:
                    e.add_note(f"{match[0]} @ {value} @ {stack[-1]}")
                    raise
            expanded.add((id(stack[-1]), key))
            update(key, value)

        case {"!Raw": raw} if len(value) == 1:
            # interpolaten't
            expanded.add((id(stack[-1]), key))
            update(key, raw)

        case {"!None": _}:
            update(key, None)

        case list():
            # handle each item in the list without adding the list to the stack
            for i, item in enumerate(value):
                _handle_child(data, stack, expanded, i, item, value.__setitem__)

        case dict():
            # recursion!
            _fill_placeholders(data, stack + [value], expanded)

        case _:
            pass


def _fill_placeholders(
    data: TOMLDict,
    stack: list[TOMLDict],
    expanded: set[tuple[int, str | int]],
):
    table = stack[-1]
    for key, child in table.items():
        _handle_child(data, stack, expanded, key, child, table.__setitem__)


def load_toml_with_placeholders(path: Path) -> TOMLDict:
    data = tomllib.loads(path.read_text("utf-8"))
    fill_placeholders(data)
    return data


IntrinsicRaw = TypedDict("IntrinsicRaw", {"!Raw": Any})
raw_core_schema = TypeAdapter(IntrinsicRaw).core_schema

IntrinsicNone = TypedDict("IntrinsicNone", {"!None": Any})
none_core_schema = TypeAdapter(IntrinsicNone).core_schema


class GenerateJsonSchemaTOML(GenerateJsonSchema):
    _is_recursing = False

    @override
    def str_schema(self, schema: StringSchema) -> JsonSchemaValue:
        string_schema = super().str_schema(schema)
        if self._is_recursing:
            return string_schema

        return self.get_flattened_anyof(
            [
                string_schema,
                self._generate_inner_recursive(raw_core_schema),
            ]
        )

    @override
    def none_schema(self, schema: NoneSchema) -> JsonSchemaValue:
        return self.get_flattened_anyof(
            [
                super().none_schema(schema),
                self.generate_inner(none_core_schema),
            ]
        )

    @override
    def nullable_schema(self, schema: NullableSchema) -> JsonSchemaValue:
        null_schema = self.none_schema(NoneSchema(type="none"))
        inner_json_schema = self.generate_inner(schema["schema"])
        if inner_json_schema == null_schema:
            return null_schema
        return self.get_flattened_anyof([inner_json_schema, null_schema])

    def _generate_inner_recursive(self, core_schema: CoreSchema):
        # FIXME: hack
        self._is_recursing = True
        result = self.generate_inner(core_schema)
        self._is_recursing = False
        return result
