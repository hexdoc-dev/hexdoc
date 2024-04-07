__all__ = [
    "AnimatedTexture",
    "AnimationMeta",
    "HexdocAssetLoader",
    "ImageTexture",
    "ItemTexture",
    "ItemWithTexture",
    "ModelItem",
    "MultiItemTexture",
    "NamedTexture",
    "PNGTexture",
    "SingleItemTexture",
    "TagWithTexture",
    "Texture",
    "TextureContext",
    "TextureLookup",
    "TextureLookups",
    "validate_texture",
]

from .animated import (
    AnimatedTexture,
    AnimationMeta,
)
from .items import (
    ImageTexture,
    ItemTexture,
    MultiItemTexture,
    SingleItemTexture,
)
from .load_assets import (
    HexdocAssetLoader,
    Texture,
    validate_texture,
)
from .models import ModelItem
from .textures import (
    PNGTexture,
    TextureContext,
    TextureLookup,
    TextureLookups,
)
from .with_texture import (
    ItemWithTexture,
    NamedTexture,
    TagWithTexture,
)

HexdocPythonResourceLoader = None
"""PLACEHOLDER - DO NOT USE

This class has been removed from hexdoc, but this variable is required to fix an import
error with old versions of `hexdoc_minecraft`.
"""
