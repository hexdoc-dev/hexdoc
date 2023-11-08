import time
from pathlib import Path

import typer
from minecraft_render import require

from hexdoc.core import ModResourceLoader, ResLoc, ResourceLocation

from .utils.args import PropsOption, VerbosityOption
from .utils.load import load_common_data

app = typer.Typer(name="render-block")


@app.command(name="id")
def id_(
    block: str,
    *,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
):
    """Render a 3D image of a block."""

    props, pm, _ = load_common_data(props_file, verbosity)

    with ModResourceLoader.load_all(
        props,
        pm,
        export=False,
        book_output_dir=Path("out/tmp/textures"),
    ) as loader:
        output_path = loader.renderer.renderToFile(
            require().ResourceLocation.parse(block)
        )
        print(f"Rendered: {output_path}")


@app.command()
def model(
    model_path: Path,
    *,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
):
    """Render a 3D image of a block."""
    props, pm, _ = load_common_data(props_file, verbosity)
    with ModResourceLoader.load_all(
        props,
        pm,
        export=False,
        book_output_dir=Path("out/tmp/textures"),
    ) as loader:
        if model_path.suffix == ".json":
            blocks = [ResourceLocation.from_model_path(model_path)]
        else:
            blocks = [
                ResourceLocation.from_model_path(subpath)
                for subpath in model_path.rglob("*.json")
            ]

        if not blocks:
            raise ValueError(f"No models found: {model_path}")

        start = time.perf_counter()
        for block in blocks:
            if block in {
                ResLoc("hexcasting", "conjured_block"),
                ResLoc("hexcasting", "conjured_light"),
            }:
                print(f"Skipped: {block}")
                continue
            try:
                output_path = loader.renderer.renderToFile(
                    require().ResourceLocation(block.namespace, block.path)
                )
                print(f"Rendered: {output_path}")
            except Exception as e:
                print(f"Failed to render {block}: {e}")
        end = time.perf_counter()

        print(f"Total render time: {end - start:.2f} s")
