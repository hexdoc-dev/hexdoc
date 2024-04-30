import logging
from pathlib import Path
from typing import Annotated

from typer import Argument, Option, Typer

from hexdoc.utils import commands
from hexdoc.utils.types import typed_partial

logger = logging.getLogger(__name__)

DEFAULT_MERGE_SRC = Path("_site/src/docs")
DEFAULT_MERGE_DST = Path("_site/dst/docs")

DEFAULT_PROPS_FILES = [
    "hexdoc.toml",
    "doc/hexdoc.toml",
    "properties.toml",
    "doc/properties.toml",
]


DefaultTyper = typed_partial(Typer)(
    pretty_exceptions_enable=False,
    context_settings={
        "help_option_names": ["--help", "-h"],
    },
    add_completion=False,
)


def get_default_props() -> Path:
    for path in DEFAULT_PROPS_FILES:
        path = Path(path)
        if path.is_file():
            logger.debug(f"Loading props from default path: {path}")
            return path

    raise FileNotFoundError(
        f"Props file not found at any default path: {', '.join(DEFAULT_PROPS_FILES)}"
    )


def get_current_commit() -> str:
    return commands.run(["git", "rev-parse", "--short", "HEAD"])


PathArgument = Annotated[Path, Argument()]

ReleaseOption = Annotated[bool, Option(envvar="HEXDOC_RELEASE")]

VerbosityOption = Annotated[int, Option("--verbose", "-v", count=True)]

PropsOption = Annotated[
    Path,
    Option(
        "--props",
        "-p",
        envvar="HEXDOC_PROPS",
        default_factory=get_default_props,
    ),
]

BranchOption = Annotated[
    str,
    Option(
        "--branch",
        envvar="HEXDOC_BRANCH",
        default_factory=get_current_commit,
    ),
]
