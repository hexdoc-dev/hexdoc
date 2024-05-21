import importlib
import logging
import os
from pathlib import Path
from typing import Annotated

from click import BadParameter
from typer import Argument, Option, Typer

from hexdoc.utils import commands
from hexdoc.utils.tracebacks import get_message_with_hints
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
    context_settings={
        "help_option_names": ["--help", "-h"],
    },
    add_completion=False,
    pretty_exceptions_show_locals=bool(os.getenv("HEXDOC_TYPER_EXCEPTION_LOCALS")),
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


def parse_import_class(value: str):
    if "." not in value:
        raise BadParameter("import path must contain at least one '.' character.")
    module_name, attr_name = value.rsplit(".", 1)

    try:
        module = importlib.import_module(module_name, package="hexdoc")
    except ModuleNotFoundError as e:
        raise BadParameter(str(e))

    try:
        type_ = getattr(module, attr_name)
    except AttributeError as e:
        raise BadParameter(get_message_with_hints(e))

    if not isinstance(type_, type):
        raise BadParameter(f"{type_} is not a class.")

    return type_
