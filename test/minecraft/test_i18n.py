from typing import Any

import pytest
from hexdoc.core import I18n, LocalizedStr, ResourceLocation
from hexdoc.core.properties import LangProps
from hexdoc.patchouli.page.abstract_pages import PageWithTitle
from hexdoc.plugin import PluginManager


@pytest.mark.parametrize(
    ["namespace", "path", "want"],
    [
        ("forge", "ores", "Ores"),
        ("c", "saplings/almond", "Almond Saplings"),
        ("c", "tea_ingredients/gloopy/weak", "Tea Ingredients, Gloopy, Weak"),
    ],
)
def test_fallback_tag_name(namespace: str, path: str, want: str):
    tag = ResourceLocation(namespace, path)

    i18n = I18n(
        lookup={},
        lang="en_us",
        default_i18n=None,
        enabled=True,
        lang_props=LangProps(),
    )

    got = i18n.localize_item_tag(tag)

    assert got.value == f"Tag: {want}"


@pytest.mark.skip("known issue: #50")
def test_disabled_i18n(pm: PluginManager):
    context = dict[str, Any]()

    pm.add_to_context(context)

    I18n(
        lookup={"key": LocalizedStr(key="key", value="value")},
        lang="en_us",
        default_i18n=None,
        enabled=False,
        lang_props=LangProps(),
    ).add_to_context(context)

    class MockPage(PageWithTitle, type="patchouli:mock"):
        pass

    page = MockPage.model_validate(
        {
            "type": "patchouli:mock",
            "title": "key",
        },
        context=context,
    )

    assert str(page.title) == "key"
