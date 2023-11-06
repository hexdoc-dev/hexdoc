import base64
import time
from dataclasses import dataclass
from pathlib import Path

import typer
from minecraft_render import ResourcePath, require

from hexdoc.core import ModResourceLoader, ResLoc, ResourceLocation

from .utils.args import PropsOption, VerbosityOption
from .utils.load import load_common_data


# TODO: actually implement this
@dataclass
class HexdocPythonResourceLoader:
    loader: ModResourceLoader

    def loadJSON(self, resource_path: ResourcePath) -> str:
        path = "assets" / Path(require().resourcePathAsString(resource_path))
        return self.loader.load_resource(path, decode=lambda v: v)[1]

    def loadTexture(self, resource_path: ResourcePath) -> str:
        path = "assets" / Path(require().resourcePathAsString(resource_path))
        _, resolved_path = self.loader.find_resource(path)
        with open(resolved_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def close(self):
        pass


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
    with ModResourceLoader.load_all(props, pm, export=False) as loader:
        render_loader = require().createMultiloader(
            require().PythonLoaderWrapper(HexdocPythonResourceLoader(loader)),
            require().MinecraftAssetsLoader.fetchAll(
                props.minecraft_assets.ref,
                props.minecraft_assets.version,
            ),
        )
        renderer = require().RenderClass(render_loader, {"outDir": "out"})

        output_path = renderer.renderToFile(require().ResourceLocation.parse(block))
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
    with ModResourceLoader.load_all(props, pm, export=False) as loader:
        render_loader = require().createMultiloader(
            require().PythonLoaderWrapper(HexdocPythonResourceLoader(loader)),
            require().MinecraftAssetsLoader.fetchAll(
                props.minecraft_assets.ref,
                props.minecraft_assets.version,
            ),
        )
        renderer = require().RenderClass(render_loader, {"outDir": "out"})

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
                output_path = renderer.renderToFile(
                    require().ResourceLocation(block.namespace, block.path)
                )
                print(f"Rendered: {output_path}")
            except Exception as e:
                print(f"Failed to render {block}: {e}")
        end = time.perf_counter()

        print(f"Total render time: {end - start:.2f} s")
