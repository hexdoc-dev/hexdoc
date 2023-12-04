from typing import Any

import pytest
from hexdoc.model.base import HexdocModel, HexdocTypeAdapter, PluginManagerContext
from hexdoc.model.tagged_union import TypeTaggedUnion
from hexdoc.plugin.manager import PluginManager
from hexdoc.utils.singletons import NoValue


class _TaggedUnion(TypeTaggedUnion, type=NoValue):
    tagged_union: str


class _OtherType(HexdocModel):
    other_type: str


@pytest.fixture
def context():
    return PluginManagerContext(
        pm=PluginManager(""),
    )


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
    ta = HexdocTypeAdapter(union)

    result = ta.validate_python(data, context=context)

    assert isinstance(result, want_type)
