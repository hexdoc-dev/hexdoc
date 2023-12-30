from hexdoc.patchouli.page import EmptyPage, Page
from hexdoc.plugin import PluginManager


def test_empty_page(pm: PluginManager):
    data = {
        "type": "patchouli:empty",
    }
    context = {pm.context_key: pm}

    page = Page.model_validate(data, context=context)

    assert isinstance(page, EmptyPage)


def test_use_default_patchouli_namespace(pm: PluginManager):
    data = {
        "type": "empty",
    }
    context = {pm.context_key: pm}

    page = Page.model_validate(data, context=context)

    assert isinstance(page, EmptyPage)
