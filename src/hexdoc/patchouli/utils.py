from abc import ABC, abstractmethod

from pydantic import PrivateAttr, ValidationInfo, model_validator

from hexdoc.core import ResourceLocation
from hexdoc.model import HexdocModel

from .book_context import BookContext


class AdvancementSpoilered(HexdocModel, ABC):
    _is_spoiler: bool = PrivateAttr(False)

    @property
    def is_spoiler(self):
        return self._is_spoiler

    @abstractmethod
    def _get_advancement(self) -> ResourceLocation | None: ...

    @model_validator(mode="after")
    def _check_is_spoiler(self, info: ValidationInfo):
        # consider this object a spoiler if its advancement is in the spoilers tag
        advancement = self._get_advancement()
        if info.context and advancement:
            book_ctx = BookContext.of(info)
            self._is_spoiler = any(
                advancement.match(pattern)
                for pattern in book_ctx.spoilered_advancements
            )

        return self
