from importlib.resources import Package

import hexdoc
from hexdoc.plugin import (
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
    def hexdoc_load_jinja_templates() -> HookReturn[tuple[Package, str]]:
        return hexdoc, "_templates"
