__all__ = [
    "FaviconColorError",
    "FaviconNotFoundError",
    "FaviconNotSupportedError",
    "Favicons",
    "FaviconsError",
]

from ._exceptions import (
    FaviconColorError,
    FaviconNotFoundError,
    FaviconNotSupportedError,
    FaviconsError,
)
from ._generate import Favicons
