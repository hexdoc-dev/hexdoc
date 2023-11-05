# pyright: reportUnknownMemberType=false

import subprocess
from pathlib import Path

import pytest
from hexdoc._cli.app import export, render
from hexdoc_hexcasting import _hooks
from pytest import MonkeyPatch, TempPathFactory
from syrupy.assertion import SnapshotAssertion

from ..conftest import longrun

HEXCASTING_PROPS_FILE = Path("test/_submodules/HexMod/doc/properties.toml")

RENDERED_FILENAMES = [
    "v/latest/index.html",
    "v/latest/index.css",
    "v/latest/textures.css",
    "v/latest/index.js",
    "v/latest/hexcasting.js",
]


def list_directory(root: str | Path, glob: str = "**/*") -> list[str]:
    root = Path(root)
    return sorted(path.relative_to(root).as_posix() for path in root.glob(glob))


@pytest.fixture(autouse=True, scope="session")
def patch_env(monkeysession: MonkeyPatch):
    monkeysession.setenv("GITHUB_REPOSITORY", "GITHUB_REPOSITORY")
    monkeysession.setenv("GITHUB_SHA", "GITHUB_SHA")
    monkeysession.setenv("GITHUB_PAGES_URL", "GITHUB_PAGES_URL")
    monkeysession.setenv("DEBUG_GITHUBUSERCONTENT", "DEBUG_GITHUBUSERCONTENT")


@pytest.fixture(autouse=True, scope="session")
def export_hexdoc_data(patch_env: None):
    export(props_file=Path("properties.toml"))
    export(props_file=HEXCASTING_PROPS_FILE)


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
):
    monkeypatch.setattr(_hooks, "GRADLE_VERSION", "VERSION")
    app_output_dir = tmp_path_factory.mktemp("app")

    render(
        output_dir=app_output_dir,
        props_file=HEXCASTING_PROPS_FILE,
        lang="en_us",
        release=True,
    )

    assert list_directory(app_output_dir) == snapshot


@longrun
@pytest.mark.dependency()
def test_render_app(app_output_dir: Path):
    render(
        output_dir=app_output_dir,
        props_file=HEXCASTING_PROPS_FILE,
        lang="en_us",
    )


@longrun
@pytest.mark.dependency()
def test_render_subprocess(subprocess_output_dir: Path):
    cmd = [
        "hexdoc",
        "render",
        subprocess_output_dir.as_posix(),
        f"--props={HEXCASTING_PROPS_FILE.as_posix()}",
        "--lang=en_us",
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
