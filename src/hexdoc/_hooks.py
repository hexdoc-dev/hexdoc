from importlib.resources import Package
from pathlib import Path

import hexdoc
from hexdoc.minecraft.recipe import (
    ingredients as minecraft_ingredients,
    recipes as minecraft_recipes,
)
from hexdoc.patchouli.page import pages as patchouli_pages
from hexdoc.plugin import (
    DefaultRenderedTemplatesImpl,
    HookReturn,
    LoadJinjaTemplatesImpl,
    LoadResourceDirsImpl,
    LoadTaggedUnionsImpl,
    hookimpl,
)


class HexdocPlugin(
    LoadTaggedUnionsImpl,
    LoadResourceDirsImpl,
    LoadJinjaTemplatesImpl,
    DefaultRenderedTemplatesImpl,
):
    @staticmethod
    @hookimpl
    def hexdoc_load_resource_dirs() -> HookReturn[Package]:
        from hexdoc._export import generated, resources

        return [generated, resources]

    @staticmethod
    @hookimpl
    def hexdoc_load_tagged_unions() -> HookReturn[Package]:
        return [
            patchouli_pages,
            minecraft_recipes,
            minecraft_ingredients,
        ]

    @staticmethod
    @hookimpl
    def hexdoc_load_jinja_templates() -> tuple[Package, str]:
        return hexdoc, "_templates"

    @staticmethod
    @hookimpl
    def hexdoc_default_rendered_templates(templates: dict[str | Path, str]) -> None:
        templates.update(
            {
                "index.html": "index.html.jinja",
                "index.css": "index.css.jinja",
                "textures.css": "textures.jcss.jinja",
                "index.js": "index.js.jinja",
            }
        )
