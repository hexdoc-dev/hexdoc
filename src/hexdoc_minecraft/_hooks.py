from importlib.resources import Package

from hexdoc.plugin import (
    HookReturn,
    LoadResourceDirsImpl,
    hookimpl,
)


class MinecraftPlugin(LoadResourceDirsImpl):
    @staticmethod
    @hookimpl
    def hexdoc_load_resource_dirs() -> HookReturn[Package]:
        from hexdoc_minecraft._export import generated

        return generated
