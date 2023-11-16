import logging
from pathlib import Path
from zipfile import ZipFile

from github import Github
from hexdoc._cli.utils.args import PropsOption, VerbosityOption
from hexdoc._cli.utils.logging import setup_logging
from typer import Typer

from .minecraft_assets import MinecraftAssetsRepo
from .piston_meta import VersionManifestV2

logger = logging.getLogger(__name__)

CACHE_ROOT = Path(".hexdoc_minecraft")

app = Typer(
    pretty_exceptions_enable=False,
    context_settings={
        "help_option_names": ["--help", "-h"],
    },
)


@app.command()
def fetch(
    version_id: str,
    *,
    verbosity: VerbosityOption = 1,
):
    """Download the Minecraft client jar."""
    setup_logging(verbosity)

    jar_path = CACHE_ROOT / version_id / "client.jar"

    manifest = VersionManifestV2.fetch()
    package = manifest.fetch_package(version_id)
    package.downloads.client.fetch_file(jar_path)

    logger.info("Done.")


@app.command()
def extract(
    version_id: str,
    *,
    verbosity: VerbosityOption = 1,
):
    """Partially extract the Minecraft client jar."""
    setup_logging(verbosity)

    version_dir = CACHE_ROOT / version_id
    jar_path = version_dir / "client.jar"

    with ZipFile(jar_path) as jar:
        for name in jar.namelist():
            if name.startswith(
                (
                    "assets/minecraft/blockstates/",
                    "assets/minecraft/models/",
                    "assets/minecraft/textures/",
                )
            ):
                jar.extract(name, version_dir / "resources")

    logger.info("Done.")


@app.command()
def repo(
    version: str,
    *,
    ref: str = "master",
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
):
    # props, pm, _ = load_common_data(props_file, verbosity)

    # with ModResourceLoader.load_all(props, pm, render_dir=output_dir) as loader:
    #     pass

    repo = MinecraftAssetsRepo(
        github=Github(),
        ref=ref,
        version=version,
    )

    for texture_id, texture in repo.scrape_image_textures():
        print(f"{texture_id},{texture}")


if __name__ == "__main__":
    app()
