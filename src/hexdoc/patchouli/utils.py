import logging
from abc import ABC, abstractmethod
from typing import Iterator

from pydantic import PrivateAttr, ValidationInfo, model_validator

from hexdoc.core import ResourceLocation
from hexdoc.model import HexdocModel

from .book_context import BookContext

logger = logging.getLogger(__name__)


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


class Flagged(HexdocModel):
    """Mixin model for categories, entries, and pages to implement flags."""

    flag: str | None = None

    _is_flag_enabled: bool = PrivateAttr(True)

    @property
    def is_flag_enabled(self) -> bool:
        return self._is_flag_enabled

    @model_validator(mode="after")
    def _evaluate_flag(self, info: ValidationInfo):
        ctx = BookContext.of(info)
        self._is_flag_enabled = (
            _evaluate_flag(self.flag, ctx.flags) if self.flag else True
        )
        return self


# https://github.com/VazkiiMods/Patchouli/blob/abd6d03a08c37bcf116730021fda9f477412b31f/Xplat/src/main/java/vazkii/patchouli/common/base/PatchouliConfig.java#L42
def _evaluate_flag(flag: str, flags: dict[str, bool]) -> bool:
    # this SHOULD never be called with an empty string
    match flag[0]:
        case "&":
            return all(_split_and_evaluate_flag(flag, flags))
        case "|":
            return any(_split_and_evaluate_flag(flag, flags))
        case "!":
            flag = flag[1:]
            target = False
        case _:
            target = True

    flag = flag.strip().lower()

    b = flags.get(flag)
    if b is None:
        if flag.startswith("advancements_disabled_"):
            b = False
        else:
            if not flag.startswith("mod:"):
                logger.warning(f"Unknown config flag defaulting to True: {flag}")
            b = True
        # speed up subsequent checks a bit and avoid logging unnecessary warnings
        flags[flag] = b

    return b == target


def _split_and_evaluate_flag(flag: str, flags: dict[str, bool]) -> Iterator[bool]:
    for inner in flag.replace("&", "").replace("|", "").split(","):
        yield _evaluate_flag(inner, flags)
