# pyright: reportUnknownMemberType=false

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hexdoc.cli.app import render
from pytest import MonkeyPatch, TempPathFactory
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory

CHECK_RENDERED_FILENAMES = [
    "v/latest/main/en_us/index.html",
    "v/latest/main/en_us/index.css",
    "v/latest/main/en_us/textures.css",
    "v/latest/main/en_us/index.js",
    "v/latest/main/en_us/hexcasting.js",
    "v/latest/main/en_us/.sitemap-marker.json",
]


@pytest.fixture(scope="session", autouse=True)
def patch_versions(monkeysession: MonkeyPatch):
    # because pyright complains when we do this in the CI
    if TYPE_CHECKING:
        _hooks = None
    else:
        from hexdoc_hexcasting import _hooks

    monkeysession.setattr(_hooks, "GRADLE_VERSION", "MOD_VERSION")
    monkeysession.setattr(_hooks, "PY_VERSION", "PLUGIN_VERSION")
    monkeysession.setattr(_hooks, "FULL_VERSION", "FULL_VERSION")


@pytest.fixture(scope="session")
def app_output_dir(tmp_path_factory: TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("app")


@pytest.fixture(scope="session")
def subprocess_output_dir(tmp_path_factory: TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("subprocess")


@pytest.mark.hexcasting
@pytest.mark.dependency
def test_render_app_release(
    tmp_path_factory: TempPathFactory,
    snapshot: SnapshotAssertion,
    hexcasting_props_file: Path,
):
    app_output_dir = tmp_path_factory.mktemp("app")

    render(
        output_dir=app_output_dir,
        props_file=hexcasting_props_file,
        lang="en_us",
        release=True,
        branch="main",
    )

    assert list_directory(app_output_dir) == snapshot


@pytest.mark.hexcasting
@pytest.mark.dependency
def test_render_app(app_output_dir: Path, hexcasting_props_file: Path):
    render(
        output_dir=app_output_dir,
        props_file=hexcasting_props_file,
        lang="en_us",
        branch="main",
    )


@pytest.mark.hexcasting
@pytest.mark.dependency
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

    assert app_file == path_snapshot

    # difficult to monkeypatch versions for subprocess, so this file will be different
    if not filename.endswith(".sitemap-marker.json"):
        assert app_file.read_bytes() == subprocess_file.read_bytes()
