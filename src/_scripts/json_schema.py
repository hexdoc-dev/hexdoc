import json
from pathlib import Path
from typing import Annotated, Any, Optional

import rich
import typer
from pydantic import BaseModel, TypeAdapter
from typer import Argument, Option

from hexdoc.cli.utils import DefaultTyper
from hexdoc.cli.utils.args import parse_import_class
from hexdoc.core.compat import MinecraftVersion

app = DefaultTyper()


@app.command()
def main(
    model_type: Annotated[type[Any], Argument(parser=parse_import_class)],
    *,
    output_path: Annotated[Optional[Path], Option("--output", "-o")] = None,
    minecraft_version: Annotated[Optional[str], Option("--minecraft")] = None,
):
    # FIXME: doesn't seem to actually be used
    MinecraftVersion.MINECRAFT_VERSION = minecraft_version

    if issubclass(model_type, BaseModel):
        schema = model_type.model_json_schema()
    else:
        schema = TypeAdapter(model_type).json_schema()

    schema.setdefault("properties", {}).setdefault(
        "$schema",
        {
            "type": "string",
            "format": "uri",
        },
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        typer.echo(f"Successfully wrote schema for {model_type} to {output_path}.")
    else:
        typer.echo(f"Schema for {model_type}:")
        rich.print(schema)


if __name__ == "__main__":
    app()
