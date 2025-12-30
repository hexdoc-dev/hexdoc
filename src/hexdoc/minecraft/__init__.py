__all__ = [
    "I18n",
    "LocalizedItem",
    "LocalizedStr",
    "Tag",
    "TagValue",
    "recipe",
]

# for backwards compatibility
from hexdoc.core.i18n import I18n, LocalizedItem, LocalizedStr

from . import recipe
from .tags import Tag, TagValue
