# pyright: reportUnknownMemberType=false

import subprocess
import sys
from pathlib import Path

import pytest
from hexdoc.cli.app import export, render
from pytest import MonkeyPatch
from pytest_copie.plugin import Copie
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory, nox_only, write_file_tree


def run_pip(*args: str):
    return subprocess.run((sys.executable, "-m", "pip") + args, check=True)


@pytest.fixture(autouse=True, scope="session")
def export_hexdoc_data(patch_env: None, hexcasting_props_file: Path):
    export(props_file=Path("hexdoc.toml"), branch="main")
    export(props_file=hexcasting_props_file, branch="main")


@nox_only
def test_copier(
    copie: Copie,
    monkeypatch: MonkeyPatch,
    snapshot: SnapshotAssertion,
    path_snapshot: SnapshotAssertion,
    env_overrides: dict[str, str],
):
    git_tag = "v9999!9999"
    subprocess.run(["git", "tag", git_tag])
    try:
        result = copie.copy(
            {
                "modid": "mod",
                "multiloader": False,
                "java_package": "com/package",
                "pattern_registry": "Patterns.java",
            }
        )
    finally:
        subprocess.run(["git", "tag", "-d", git_tag])

    assert result.exception is None
    assert result.project_dir is not None

    monkeypatch.chdir(result.project_dir)

    subprocess.run(["git", "init"], check=True)

    write_file_tree(
        result.project_dir,
        {
            "src/generated/resources": {},
            "src/main/java/com/package/Patterns.java": "",
            "src/main/resources/assets/hexcasting/patchouli_books/thehexbook/en_us": {
                "categories/foo.json": {
                    "name": "hexdoc.mod.title",
                    "icon": "minecraft:amethyst_shard",
                    "description": "hexcasting.category.basics.desc",
                    "sortnum": 0,
                },
                "entries/bar.json": {
                    "name": "hexdoc.welcome.header",
                    "category": "hexcasting:foo",
                    "icon": "minecraft:textures/mob_effect/nausea.png",
                    "sortnum": 0,
                    "advancement": "hexcasting:y_u_no_cast_angy",
                    "pages": [
                        {
                            "type": "patchouli:text",
                            "text": "hexcasting.page.couldnt_cast.1",
                        },
                    ],
                },
            },
            ".env": "\n".join(
                f"{name}={value}" for name, value in env_overrides.items()
            ),
            "gradle.properties": (
                """\
                modVersion=1.0.0
                hexcastingVersion=0.11.1-7
                minecraftVersion=1.20.1
                """
            ),
        },
    )

    output_dir = Path("_site")

    try:
        run_pip("install", ".", "--force-reinstall", "--no-deps")
        render(
            output_dir=output_dir,
            props_file=Path("doc/hexdoc.toml"),
            branch="main",
        )
    finally:
        run_pip("uninstall", "hexdoc-mod", "-y")

    path_snapshot._custom_index = "vlatestmainen_usindex.html"  # pyright: ignore[reportPrivateUsage]
    assert output_dir / "v/latest/main/en_us/index.html" == path_snapshot

    assert list_directory(output_dir) == snapshot
