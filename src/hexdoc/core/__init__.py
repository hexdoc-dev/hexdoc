__all__ = [
    "METADATA_SUFFIX",
    "AssumeTag",
    "BaseProperties",
    "BaseResourceDir",
    "BaseResourceLocation",
    "BookFolder",
    "Entity",
    "ExportFn",
    "I18n",
    "IsVersion",
    "ItemStack",
    "LocalizedItem",
    "LocalizedStr",
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
    "properties",
]

from .compat import (
    IsVersion,
    MinecraftVersion,
    ValueIfVersion,
    Versioned,
    VersionSource,
)
from .i18n import I18n, LocalizedItem, LocalizedStr
from .loader import (
    METADATA_SUFFIX,
    BookFolder,
    ExportFn,
    ModResourceLoader,
)
from .properties import BaseProperties, Properties
from .resource import (
    AssumeTag,
    BaseResourceLocation,
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
