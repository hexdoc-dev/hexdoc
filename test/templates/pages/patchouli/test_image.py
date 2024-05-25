from types import SimpleNamespace

from hexdoc.core.resource import ResourceLocation
from hexdoc.jinja.render import create_jinja_env_with_loader
from hexdoc.patchouli.page.pages import ImagePage
from jinja2 import PackageLoader


def test_no_title():
    loader = PackageLoader("hexdoc", "_templates")
    env = create_jinja_env_with_loader(loader)
    template = env.from_string("{% include page.template~'.html.jinja' %}")

    template.render(
        entry=SimpleNamespace(
            id=ResourceLocation("entry_ns", "entry_path"),
        ),
        page=ImagePage.model_construct(
            images=[],
        ),
    )
