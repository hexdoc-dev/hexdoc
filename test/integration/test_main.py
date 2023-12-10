# pyright: reportUnknownMemberType=false

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hexdoc.cli.app import build, callback
from pytest import MonkeyPatch, TempPathFactory
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory

# include: v/latest/main/assets
# include: v/latest/main/assets/hexcasting
# exclude: v/latest/main/assets/hexcasting/textures/block/akashic_ligature.png
EXCLUDE_GLOB = "**/assets/**/**"

CHECK_RENDERED_FILENAMES = [
    "v/latest/main/en_us/index.html",
    "v/latest/main/en_us/index.css",
    "v/latest/main/en_us/textures.css",
    "v/latest/main/en_us/index.js",
    "v/latest/main/en_us/hexcasting.js",
    "v/latest/main/en_us/.sitemap-marker.json",
]


@pytest.fixture(scope="session", autouse=True)
def call_callback():
    callback(quiet_lang=["ru_ru", "zh_cn"])


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

    build(
        output_dir=app_output_dir,
        props_file=hexcasting_props_file,
        release=True,
        branch="main",
    )

    assert list_directory(app_output_dir, exclude_glob=EXCLUDE_GLOB) == snapshot


@pytest.mark.hexcasting
@pytest.mark.dependency
def test_render_app(app_output_dir: Path, hexcasting_props_file: Path):
    build(
        output_dir=app_output_dir,
        props_file=hexcasting_props_file,
        branch="main",
    )


@pytest.mark.hexcasting
@pytest.mark.dependency
def test_render_subprocess(subprocess_output_dir: Path, hexcasting_props_file: Path):
    cmd = [
        "hexdoc",
        "--quiet-lang=ru_ru",
        "--quiet-lang=zh_cn",
        "build",
        subprocess_output_dir.as_posix(),
        f"--props={hexcasting_props_file.as_posix()}",
        "--branch=main",
    ]
    subprocess.run(cmd, check=True)


@pytest.mark.hexcasting
@pytest.mark.dependency(depends=["test_render_app", "test_render_subprocess"])
def test_file_structure(
    app_output_dir: Path,
    subprocess_output_dir: Path,
    snapshot: SnapshotAssertion,
):
    app_list = list_directory(app_output_dir, exclude_glob=EXCLUDE_GLOB)
    subprocess_list = list_directory(subprocess_output_dir, exclude_glob=EXCLUDE_GLOB)

    assert app_list == subprocess_list
    assert app_list == snapshot


@pytest.mark.hexcasting
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
