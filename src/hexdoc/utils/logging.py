import logging
import sys
from bisect import bisect
from logging import (
    Formatter,
    LogRecord,
    StreamHandler,
)
from typing import Any, Literal, Mapping

TRACE = 5
"""For even more verbose logs than `logging.DEBUG`."""

logger = logging.getLogger(__name__)


# https://stackoverflow.com/a/68154386
class LevelFormatter(Formatter):
    def __init__(
        self,
        formats: dict[int, str],
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
    ):
        super().__init__()

        self.formats = sorted(
            (
                level,
                Formatter(fmt, datefmt, style, validate, defaults=defaults),
            )
            for level, fmt in formats.items()
        )

    def format(self, record: LogRecord) -> str:
        idx = bisect(self.formats, (record.levelno,), hi=len(self.formats) - 1)
        _, formatter = self.formats[idx]
        return formatter.format(record)


_is_initialized = False


def setup_logging(verbosity: int, ci: bool):
    global _is_initialized

    if _is_initialized:
        logger.debug("Root logger already initialized, skipping setup.")
        return

    logging.addLevelName(TRACE, "TRACE")

    formats = {
        logging.INFO: "\033[1m[{relativeCreated:.02f} | {levelname} | {name}]\033[0m {message}",
    }
    if ci:
        formats |= {
            logging.WARNING: "::warning file={name},line={lineno},title={levelname}::{message}",
            logging.ERROR: "::error file={name},line={lineno},title={levelname}::{message}",
        }

    handler = StreamHandler()
    handler.setLevel(TRACE)
    handler.setFormatter(LevelFormatter(formats, style="{"))

    root_logger = logging.getLogger()
    root_logger.setLevel(verbosity_log_level(verbosity))
    root_logger.addHandler(handler)

    logger.debug("Initialized logger.")
    _is_initialized = True


def verbosity_log_level(verbosity: int) -> int:
    match verbosity:
        case 0:
            return logging.INFO
        case 1:
            return logging.DEBUG
        case _:
            return TRACE


def repl_readfunc():
    exit_next = False

    def inner(prompt: str) -> str:
        nonlocal exit_next
        try:
            response = input(prompt)
            exit_next = False
            return response
        except KeyboardInterrupt:
            if exit_next:
                print("\nExiting.")
                sys.exit()

            print("\nPress ctrl+c again to exit.", end="")
            exit_next = True
            raise

    return inner
