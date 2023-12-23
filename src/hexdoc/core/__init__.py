__all__ = [
    "AssumeTag",
    "BaseProperties",
    "BaseResourceDir",
    "BookFolder",
    "Entity",
    "ExportFn",
    "IsVersion",
    "ItemStack",
    "METADATA_SUFFIX",
    "MinecraftVersion",
    "ModResourceLoader",
    "PathResourceDir",
    "PluginResourceDir",
    "Properties",
    "ResLoc",
    "ResourceDir",
    "ResourceLocation",
    "ResourceType",
    "ValueIfVersion",
    "VersionSource",
    "Versioned",
    "compat",
]

from . import compat
from .compat import (
    IsVersion,
    MinecraftVersion,
    ValueIfVersion,
    Versioned,
    VersionSource,
)
from .loader import (
    METADATA_SUFFIX,
    BookFolder,
    ExportFn,
    ModResourceLoader,
)
from .properties import BaseProperties, Properties
from .resource import (
    AssumeTag,
    Entity,
    ItemStack,
    ResLoc,
    ResourceLocation,
    ResourceType,
)
from .resource_dir import (
    BaseResourceDir,
    PathResourceDir,
    PluginResourceDir,
    ResourceDir,
)
