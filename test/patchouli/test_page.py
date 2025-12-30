from typing import Any

import pytest
from hexdoc.patchouli.book_context import BookContext
from hexdoc.patchouli.page import EmptyPage, Page
from hexdoc.plugin import PluginManager


@pytest.fixture
def context(pm: PluginManager):
    return {
        pm.context_key: pm,
        BookContext.context_key: BookContext.model_construct(flags={}),
    }


def test_empty_page(context: dict[str, Any]):
    data = {
        "type": "patchouli:empty",
    }

    page = Page.model_validate(data, context=context)

    assert isinstance(page, EmptyPage)


def test_use_default_patchouli_namespace(context: dict[str, Any]):
    data = {
        "type": "empty",
    }

    page = Page.model_validate(data, context=context)

    assert isinstance(page, EmptyPage)
