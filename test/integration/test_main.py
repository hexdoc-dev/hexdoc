# pyright: reportUnknownMemberType=false

import subprocess
from pathlib import Path

import pytest
from hexdoc.cli.app import render
from hexdoc_hexcasting import _hooks
from pytest import MonkeyPatch, TempPathFactory
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory, longrun

CHECK_RENDERED_FILENAMES = [
    "v/latest/main/en_us/index.html",
    "v/latest/main/en_us/index.css",
    "v/latest/main/en_us/textures.css",
    "v/latest/main/en_us/index.js",
    "v/latest/main/en_us/hexcasting.js",
]


@pytest.fixture(scope="session")
def app_output_dir(tmp_path_factory: TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("app")


@pytest.fixture(scope="session")
def subprocess_output_dir(tmp_path_factory: TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("subprocess")


@longrun
@pytest.mark.dependency()
def test_render_app_release(
    monkeypatch: MonkeyPatch,
    tmp_path_factory: TempPathFactory,
    snapshot: SnapshotAssertion,
    hexcasting_props_file: Path,
):
    monkeypatch.setattr(_hooks, "GRADLE_VERSION", "MOD_VERSION")
    monkeypatch.setattr(_hooks, "PY_VERSION", "PLUGIN_VERSION")
    app_output_dir = tmp_path_factory.mktemp("app")

    render(
        output_dir=app_output_dir,
        props_file=hexcasting_props_file,
        lang="en_us",
        release=True,
        branch="main",
    )

    assert list_directory(app_output_dir) == snapshot


@longrun
@pytest.mark.dependency()
def test_render_app(app_output_dir: Path, hexcasting_props_file: Path):
    render(
        output_dir=app_output_dir,
        props_file=hexcasting_props_file,
        lang="en_us",
        branch="main",
    )


@longrun
@pytest.mark.dependency()
def test_render_subprocess(subprocess_output_dir: Path, hexcasting_props_file: Path):
    cmd = [
        "hexdoc",
        "render",
        subprocess_output_dir.as_posix(),
        f"--props={hexcasting_props_file.as_posix()}",
        "--lang=en_us",
        "--branch=main",
    ]
    subprocess.run(cmd, check=True)


@pytest.mark.dependency(depends=["test_render_app", "test_render_subprocess"])
def test_file_structure(
    app_output_dir: Path,
    subprocess_output_dir: Path,
    snapshot: SnapshotAssertion,
):
    app_list = list_directory(app_output_dir)
    subprocess_list = list_directory(subprocess_output_dir)

    assert app_list == subprocess_list
    assert app_list == snapshot


@pytest.mark.dependency(depends=["test_render_app", "test_render_subprocess"])
@pytest.mark.parametrize("filename", CHECK_RENDERED_FILENAMES)
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
