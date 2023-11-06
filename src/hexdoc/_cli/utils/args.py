from pathlib import Path
from typing import Annotated

from typer import Argument, Option

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
            print(f"Loading props from default path: {path}")
            return path

    raise FileNotFoundError(
        f"Props file not found at any default path: {', '.join(DEFAULT_PROPS_FILES)}"
    )


PathArgument = Annotated[Path, Argument()]

PropsOption = Annotated[
    Path,
    Option("--props", "-p", envvar="HEXDOC_PROPS", default_factory=get_default_props),
]

ReleaseOption = Annotated[bool, Option(envvar="HEXDOC_RELEASE")]

UpdateLatestOption = Annotated[bool, Option(envvar="HEXDOC_UPDATE_LATEST")]

VerbosityOption = Annotated[int, Option("--verbose", "-v", count=True)]
