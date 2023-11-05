__all__ = [
    "HEXDOC_PROJECT_NAME",
    "HookReturn",
    "LoadJinjaTemplatesImpl",
    "LoadResourceDirsImpl",
    "LoadTaggedUnionsImpl",
    "MinecraftVersionImpl",
    "ModVersionImpl",
    "PluginManager",
    "PluginNotFoundError",
    "UpdateContextImpl",
    "UpdateJinjaEnvImpl",
    "UpdateTemplateArgsImpl",
    "ValidateFormatTreeImpl",
    "hookimpl",
]

import pluggy

from .manager import PluginManager, PluginNotFoundError
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
"""Decorator for marking functions as hook implementations."""
