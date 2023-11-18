from importlib.resources import Package
from pathlib import Path

import hexdoc
from hexdoc import HEXDOC_MODID
from hexdoc.__version__ import VERSION
from hexdoc.minecraft.recipe import (
    ingredients as minecraft_ingredients,
    recipes as minecraft_recipes,
)
from hexdoc.patchouli.page import pages as patchouli_pages
from hexdoc.plugin import (
    HookReturn,
    LoadTaggedUnionsImpl,
    ModPlugin,
    ModPluginImpl,
    hookimpl,
)


class HexdocPlugin(LoadTaggedUnionsImpl, ModPluginImpl):
    @staticmethod
    @hookimpl
    def hexdoc_mod_plugin(branch: str) -> ModPlugin:
        return HexdocModPlugin(branch=branch)

    @staticmethod
    @hookimpl
    def hexdoc_load_tagged_unions() -> HookReturn[Package]:
        return [
            patchouli_pages,
            minecraft_recipes,
            minecraft_ingredients,
        ]


class HexdocModPlugin(ModPlugin):
    @property
    def modid(self) -> str:
        return HEXDOC_MODID

    @property
    def full_version(self) -> str:
        return VERSION

    @property
    def plugin_version(self) -> str:
        return VERSION

    def resource_dirs(self) -> HookReturn[Package]:
        from hexdoc._export import generated, resources

        return [generated, resources]

    def jinja_template_root(self) -> tuple[Package, str] | None:
        return hexdoc, "_templates"

    def default_rendered_templates(self) -> dict[str | Path, str]:
        return {
            "index.html": "index.html.jinja",
            "index.css": "index.css.jinja",
            "textures.css": "textures.jcss.jinja",
            "index.js": "index.js.jinja",
        }
