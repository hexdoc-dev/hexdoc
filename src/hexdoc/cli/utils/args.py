import logging
import subprocess
from pathlib import Path
from typing import Annotated

from typer import Argument, Option

logger = logging.getLogger(__name__)

DEFAULT_MERGE_SRC = Path("_site/src/docs")
DEFAULT_MERGE_DST = Path("_site/dst/docs")

DEFAULT_PROPS_FILES = [
    "hexdoc.toml",
    "doc/hexdoc.toml",
    "properties.toml",
    "doc/properties.toml",
]


def get_default_props() -> Path:
    for path in DEFAULT_PROPS_FILES:
        path = Path(path)
        if path.is_file():
            logger.info(f"Loading props from default path: {path}")
            return path

    raise FileNotFoundError(
        f"Props file not found at any default path: {', '.join(DEFAULT_PROPS_FILES)}"
    )


def get_current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout.strip()


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
