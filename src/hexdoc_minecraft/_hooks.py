from importlib.resources import Package

from hexdoc.plugin import (
    HookReturn,
    ModPlugin,
    ModPluginImpl,
    VersionedModPlugin,
    hookimpl,
)


class MinecraftPlugin(ModPluginImpl):
    @staticmethod
    @hookimpl
    def hexdoc_mod_plugin(branch: str) -> ModPlugin:
        return MinecraftModPlugin(branch=branch)


class MinecraftModPlugin(VersionedModPlugin):
    @property
    def modid(self) -> str:
        return "minecraft"

    @property
    def full_version(self) -> str:
        return "1.20.1.1.0.dev0"  # TODO: replace

    @property
    def plugin_version(self) -> str:
        return "1.0.dev0"  # TODO: replace

    @property
    def mod_version(self) -> str:
        return "1.20.1"  # TODO: replace

    def resource_dirs(self) -> HookReturn[Package]:
        from hexdoc_minecraft._export import generated

        return generated
