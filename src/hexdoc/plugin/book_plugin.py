from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Mapping, TypeVar

if TYPE_CHECKING:
    from hexdoc.core import ModResourceLoader, ResourceLocation
    from hexdoc.utils import ContextSource, JSONDict


_Book = TypeVar("_Book")


class BookPlugin(ABC, Generic[_Book]):
    @property
    @abstractmethod
    def modid(self) -> str:
        """The modid of the mod whose book system this plugin implements."""

    @abstractmethod
    def load_book_data(
        self,
        book_id: ResourceLocation,
        loader: ModResourceLoader,
    ) -> tuple[ResourceLocation, JSONDict]:
        """"""

    @abstractmethod
    def is_i18n_enabled(self, book_data: Mapping[str, Any]) -> bool:
        """Given the raw book data, returns `True` if i18n is enabled for that book."""

    @abstractmethod
    def validate_book(
        self,
        book_data: Mapping[str, Any],
        *,
        context: ContextSource,
    ) -> _Book:
        """"""
