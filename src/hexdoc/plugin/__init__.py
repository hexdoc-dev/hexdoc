__all__ = [
    "HEXDOC_PROJECT_NAME",
    "HookReturn",
    "LoadTaggedUnionsImpl",
    "ModPlugin",
    "ModPluginImpl",
    "ModPluginWithBook",
    "PluginManager",
    "PluginNotFoundError",
    "UpdateContextImpl",
    "UpdateJinjaEnvImpl",
    "UpdateTemplateArgsImpl",
    "ValidateFormatTreeImpl",
    "VersionedModPlugin",
    "hookimpl",
]

import pluggy

from .manager import (
    PluginManager,
    PluginNotFoundError,
)
from .mod_plugin import (
    ModPlugin,
    ModPluginWithBook,
    VersionedModPlugin,
)
from .specs import (
    HEXDOC_PROJECT_NAME,
    LoadTaggedUnionsImpl,
    ModPluginImpl,
    UpdateContextImpl,
    UpdateJinjaEnvImpl,
    UpdateTemplateArgsImpl,
    ValidateFormatTreeImpl,
)
from .types import HookReturn

hookimpl = pluggy.HookimplMarker(HEXDOC_PROJECT_NAME)
"""Decorator for marking functions as hook implementations."""
