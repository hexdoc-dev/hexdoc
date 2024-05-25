from typing import Any

import pytest
from hexdoc.core import I18n, Properties
from hexdoc.core.properties import LangProps
from hexdoc.graphics import ItemImage, TagImage
from hexdoc.plugin import PluginManager
from hexdoc.utils.context import ContextSource
from pydantic import TypeAdapter


@pytest.fixture
def context():
    props = Properties.model_construct()
    props.textures.strict = False
    pm = PluginManager("branch", props=props)

    i18n = I18n(
        lookup=I18n.parse_lookup(
            {
                "item.minecraft.stone": "Stone",
                "block.minecraft.stone": "Stone",
                "tag.minecraft.stone": "Stone",
            }
        ),
        lang="en_us",
        default_i18n=None,
        enabled=True,
        lang_props=LangProps(),
    )

    context: ContextSource = {}
    for ctx in [props, pm, i18n]:
        ctx.add_to_context(context)

    return context


@pytest.mark.skip("Needs some effort to make it work with the new image loader")
@pytest.mark.parametrize(
    "union",
    [
        ItemImage | TagImage,
        TagImage | ItemImage,
    ],
    ids=[
        "item_first",
        "tag_first",
    ],
)
@pytest.mark.parametrize(
    ["data", "want_type"],
    [
        ["minecraft:gold", ItemImage],
        ["#minecraft:gold", TagImage],
    ],
)
def test_item_tag_union(
    union: type[ItemImage | TagImage],
    data: Any,
    want_type: type[ItemImage | TagImage],
    context: Any,
):
    ta = TypeAdapter(union)

    result = ta.validate_python(data, context=context)

    assert isinstance(result, want_type)
