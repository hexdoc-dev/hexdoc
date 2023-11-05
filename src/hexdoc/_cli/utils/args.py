from pathlib import Path
from typing import Annotated

import typer

DEFAULT_PROPS_FILE = Path("doc/properties.toml")
DEFAULT_MERGE_SRC = Path("_site/src/docs")
DEFAULT_MERGE_DST = Path("_site/dst/docs")

PathArgument = Annotated[Path, typer.Argument()]
PropsOption = Annotated[Path, typer.Option("--props", "-p", envvar="HEXDOC_PROPS")]
VerbosityOption = Annotated[int, typer.Option("--verbose", "-v", count=True)]
UpdateLatestOption = Annotated[bool, typer.Option(envvar="UPDATE_LATEST")]
ReleaseOption = Annotated[bool, typer.Option(envvar="RELEASE")]
