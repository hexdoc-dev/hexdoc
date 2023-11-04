# pyright: reportUnknownMemberType=false

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch, TempPathFactory
from syrupy.assertion import SnapshotAssertion

from hexdoc.cli.main import render

from ..conftest import longrun

PROPS_FILE = Path("test/_submodules/HexMod/doc/properties.toml")

RENDERED_FILENAMES = [
    "v/latest/index.html",
    "v/latest/index.css",
    "v/latest/textures.css",
    "v/latest/index.js",
    "v/latest/hexcasting.js",
]


@pytest.fixture(autouse=True)
def patch_env(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "GITHUB_REPOSITORY")
    monkeypatch.setenv("GITHUB_SHA", "GITHUB_SHA")
    monkeypatch.setenv("GITHUB_PAGES_URL", "GITHUB_PAGES_URL")
    monkeypatch.setenv("DEBUG_GITHUBUSERCONTENT", "DEBUG_GITHUBUSERCONTENT")


@pytest.fixture(scope="session")
def app_output_dir(tmp_path_factory: TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("app", numbered=False)


@pytest.fixture(scope="session")
def subprocess_output_dir(tmp_path_factory: TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("subprocess", numbered=False)


@longrun
@pytest.mark.dependency()
def test_render_app(app_output_dir: Path):
    render(
        output_dir=app_output_dir,
        props_file=PROPS_FILE,
        lang="en_us",
    )


@longrun
@pytest.mark.dependency()
def test_render_subprocess(subprocess_output_dir: Path):
    cmd = [
        "hexdoc",
        "render",
        subprocess_output_dir.as_posix(),
        f"--props={PROPS_FILE.as_posix()}",
        "--lang=en_us",
    ]
    subprocess.run(cmd, check=True)


@pytest.mark.dependency(depends=["test_render_app", "test_render_subprocess"])
@pytest.mark.parametrize("filename", RENDERED_FILENAMES)
def test_files(
    filename: str,
    app_output_dir: Path,
    subprocess_output_dir: Path,
    path_snapshot: SnapshotAssertion,
):
    app_file = app_output_dir / filename
    subprocess_file = subprocess_output_dir / filename

    assert app_file.read_bytes() == subprocess_file.read_bytes()
    assert app_file == path_snapshot
