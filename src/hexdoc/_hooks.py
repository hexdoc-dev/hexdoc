from importlib.resources import Package
from pathlib import Path

import hexdoc
from hexdoc.plugin import (
    DefaultRenderedTemplatesImpl,
    HookReturn,
    LoadJinjaTemplatesImpl,
    LoadResourceDirsImpl,
    MinecraftVersionImpl,
    ModVersionImpl,
    hookimpl,
)


class HexdocPlugin(
    MinecraftVersionImpl,
    ModVersionImpl,
    LoadResourceDirsImpl,
    LoadJinjaTemplatesImpl,
    DefaultRenderedTemplatesImpl,
):
    @staticmethod
    @hookimpl
    def hexdoc_mod_version():
        return "(TODO: remove)"

    @staticmethod
    @hookimpl
    def hexdoc_minecraft_version() -> str:
        return "1.20.1"  # TODO: remove

    @staticmethod
    @hookimpl
    def hexdoc_load_resource_dirs() -> HookReturn[Package]:
        from hexdoc._export import generated, resources

        return [generated, resources]

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
