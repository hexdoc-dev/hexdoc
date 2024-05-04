import logging
import os
import re
import sys
from bisect import bisect
from logging import (
    Filter,
    Formatter,
    LogRecord,
    StreamHandler,
)
from typing import Any, Iterable, Literal, Mapping

from .tracebacks import create_filtered_excepthook

TRACE = 5
"""For even more verbose logs than `logging.DEBUG`."""

TRACEBACK_HIDDEN_MODULES = {
    "click.core",
    "typer.core",
    "typer.main",
}


logger = logging.getLogger(__name__)

filtered_excepthook = create_filtered_excepthook(TRACEBACK_HIDDEN_MODULES)


class RegexFilter(Filter):
    def __init__(self, pattern: str | re.Pattern[str]):
        super().__init__()
        self.regex: re.Pattern[str]
        match pattern:
            case str():
                self.regex = re.compile(pattern)
            case re.Pattern():
                self.regex = pattern

    def filter(self, record: LogRecord) -> bool:
        if not super().filter(record):
            return False
        return self.regex.search(record.msg) is None


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


# separate class so we can isinstance below
class HexdocLevelFormatter(LevelFormatter):
    pass


def setup_logging(
    verbosity: int,
    ci: bool,
    *,
    filters: Iterable[Filter] | None = None,
    quiet_langs: Iterable[str] | None = None,
):
    logging.addLevelName(TRACE, "TRACE")

    root_logger = logging.getLogger()

    if root_logger.handlers:
        for handler in root_logger.handlers:
            if isinstance(handler.formatter, HexdocLevelFormatter):
                logger.debug(f"Removing existing handler from root logger: {handler}")
                root_logger.removeHandler(handler)

    level = verbosity_log_level(verbosity)
    root_logger.setLevel(level)

    formats = {
        logging.DEBUG: log_format("relativeCreated", "levelname", "name"),
    }

    if level >= logging.INFO:
        # set this here so we don't clobber exceptions in verbose mode
        # but don't set it if Typer's pretty tracebacks are enabled
        # see also: https://typer.tiangolo.com/tutorial/exceptions/#disable-pretty-exceptions
        if os.getenv("_TYPER_STANDARD_TRACEBACK"):
            sys.excepthook = filtered_excepthook

        formats |= {
            logging.INFO: log_format("levelname"),
            logging.WARNING: log_format("levelname", "name"),
        }

    if ci:
        formats |= {
            logging.WARNING: "::warning file={name},line={lineno},title={levelname}::{message}",
            logging.ERROR: "::error file={name},line={lineno},title={levelname}::{message}",
        }

    handler = StreamHandler()

    handler.setLevel(level)
    handler.setFormatter(HexdocLevelFormatter(formats, style="{"))

    if filters:
        for filter in filters:
            handler.addFilter(filter)

    if quiet_langs:
        for lang in quiet_langs:
            handler.addFilter(RegexFilter(f"^No translation in {lang}"))

    root_logger.addHandler(handler)

    logging.getLogger("PIL").setLevel(logging.INFO)

    logger.debug("Initialized logger.")


def log_format(*names: Literal["relativeCreated", "levelname", "name"]):
    components = {
        "relativeCreated": "{relativeCreated:.02f}",
        "levelname": "{levelname}",
        "name": "{name}",
    }

    joined_components = " | ".join(components[name] for name in names)
    return "\033[1m[" + joined_components + "]\033[0m {message}"


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
