from typing import Any, cast

import pytest
from pydantic import TypeAdapter

from hexdoc.core.properties import Properties
from hexdoc.model import HexdocModel, TypeTaggedUnion
from hexdoc.plugin import PluginManager
from hexdoc.utils.singletons import NoValue


class _TaggedUnion(TypeTaggedUnion, type=NoValue):
    tagged_union: str


class _OtherType(HexdocModel):
    other_type: str


@pytest.fixture
def context():
    pm = PluginManager("", props=cast(Properties, None))
    return {pm.context_key: pm}


@pytest.mark.parametrize(
    "union",
    [
        _TaggedUnion | _OtherType,
        _OtherType | _TaggedUnion,
    ],
    ids=[
        "tagged_first",
        "other_first",
    ],
)
@pytest.mark.parametrize(
    ["data", "want_type"],
    [
        [{"tagged_union": ""}, _TaggedUnion],
        [{"other_type": ""}, _OtherType],
    ],
)
def test_union_with_other_type(
    union: type[_TaggedUnion | _OtherType],
    data: Any,
    want_type: type[_TaggedUnion | _OtherType],
    context: Any,
):
    ta = TypeAdapter(union)

    result = ta.validate_python(data, context=context)

    assert isinstance(result, want_type)
