__all__ = [
    "hookimpl",
    "ModVersionImpl",
    "LoadResourceDirsImpl",
    "LoadTaggedUnionsImpl",
    "LoadJinjaTemplatesImpl",
    "UpdateJinjaEnvImpl",
    "UpdateTemplateArgsImpl",
    "ValidateFormatTreeImpl",
    "MinecraftVersionImpl",
    "UpdateContextImpl",
    "PluginManager",
    "HookReturn",
]

import pluggy

from .manager import PluginManager
from .specs import (
    HEXDOC_PROJECT_NAME,
    HookReturn,
    LoadJinjaTemplatesImpl,
    LoadResourceDirsImpl,
    LoadTaggedUnionsImpl,
    MinecraftVersionImpl,
    ModVersionImpl,
    UpdateContextImpl,
    UpdateJinjaEnvImpl,
    UpdateTemplateArgsImpl,
    ValidateFormatTreeImpl,
)

hookimpl = pluggy.HookimplMarker(HEXDOC_PROJECT_NAME)
