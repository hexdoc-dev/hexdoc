from collections import defaultdict
from typing import Any

import pytest
from hexdoc.core import Properties
from hexdoc.core.properties import LangProps
from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft.assets.textures import TextureContext
from hexdoc.minecraft.assets.with_texture import ItemWithTexture, TagWithTexture
from hexdoc.minecraft.i18n import I18n
from hexdoc.plugin import PluginManager
from hexdoc.utils.context import ContextSource
from pydantic import TypeAdapter


@pytest.fixture
def context():
    props = Properties.model_construct()
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

    texture_ctx = TextureContext(
        textures=defaultdict(dict),
        allowed_missing_textures={
            ResourceLocation("minecraft", "*"),
        },
    )

    context: ContextSource = {}
    for ctx in [props, pm, i18n, texture_ctx]:
        ctx.add_to_context(context)

    return context


@pytest.mark.parametrize(
    "union",
    [
        ItemWithTexture | TagWithTexture,
        TagWithTexture | ItemWithTexture,
    ],
    ids=[
        "item_first",
        "tag_first",
    ],
)
@pytest.mark.parametrize(
    ["data", "want_type"],
    [
        ["minecraft:gold", ItemWithTexture],
        ["#minecraft:gold", TagWithTexture],
    ],
)
def test_item_tag_union(
    union: type[ItemWithTexture | TagWithTexture],
    data: Any,
    want_type: type[ItemWithTexture | TagWithTexture],
    context: Any,
):
    ta = TypeAdapter(union)

    result = ta.validate_python(data, context=context)

    assert isinstance(result, want_type)
