# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from pathlib import Path
from typing import Any, Callable

import pytest
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup
from pytest import FixtureRequest, Mark

from hexdoc.jinja.render import create_jinja_env
from hexdoc.plugin import (
    ModPlugin,
    ModPluginImpl,
    PluginManager,
    UpdateTemplateArgsImpl,
    hookimpl,
)

RenderTemplate = Callable[[list[str]], str]


@pytest.fixture
def render_template(request: FixtureRequest, pm: PluginManager) -> RenderTemplate:
    match request.node.get_closest_marker("template"):
        case Mark(args=[str(template_str)], kwargs=template_args):
            pass
        case marker:
            raise TypeError(f"Expected marker `template` with 1 string, got {marker}")

    def callback(include: list[str]):
        env = create_jinja_env(pm, include, Path())
        template = env.from_string(template_str)
        return template.render(pm.update_template_args(dict(template_args)))

    return callback


@pytest.mark.template("{{ '<br />' }}")
def test_update_jinja_env(pm: PluginManager, render_template: RenderTemplate):
    class _ModPlugin(ModPlugin):
        @property
        def modid(self):
            return "modplugin"

        @property
        def full_version(self):
            return ""

        @property
        def plugin_version(self):
            return ""

        def update_jinja_env(self, env: SandboxedEnvironment) -> None:
            env.autoescape = False

    class _Plugin(ModPluginImpl):
        @staticmethod
        @hookimpl
        def hexdoc_mod_plugin(branch: str) -> ModPlugin:
            return _ModPlugin(branch="")

    # TODO: split this into 3 separate tests
    assert render_template([]) == Markup.escape("<br />")
    pm.register(_Plugin)
    assert render_template([]) == Markup.escape("<br />")
    assert render_template(["modplugin"]) == "<br />"


@pytest.mark.template(
    "{{ key }}",
    key="old_value",
)
def test_update_template_args(pm: PluginManager, render_template: RenderTemplate):
    class Hooks(UpdateTemplateArgsImpl):
        @staticmethod
        @hookimpl
        def hexdoc_update_template_args(template_args: dict[str, Any]) -> None:
            template_args["key"] = "new_value"

    assert render_template([]) == "old_value"
    pm.inner.register(Hooks)
    assert render_template([]) == "new_value"
