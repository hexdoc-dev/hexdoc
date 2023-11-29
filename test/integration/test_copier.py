# pyright: reportUnknownMemberType=false

import subprocess
import sys
from pathlib import Path

import pytest
from hexdoc.cli.app import render
from pytest import MonkeyPatch
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory, write_file_tree


def run_pip(*args: str):
    return subprocess.run((sys.executable, "-m", "pip") + args, check=True)


@pytest.mark.copier
def test_copier(
    monkeypatch: MonkeyPatch,
    snapshot: SnapshotAssertion,
    path_snapshot: SnapshotAssertion,
    env_overrides: dict[str, str],
):
    monkeypatch.chdir("submodules/hexdoc-hexcasting-template/.ctt/test_copier")

    write_file_tree(
        ".",
        {
            "src/generated/resources": {},
            "src/main/java/com/package/Patterns.java": "",
            "src/main/resources/assets": {
                "hexcasting/patchouli_books/thehexbook/en_us": {
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
                                "text": "bar.link.patterns",
                            },
                        ],
                    },
                },
                "mod/lang/en_us.json": {
                    # make sure we're specifically testing internal and external links
                    "bar.link.patterns": "$(l:patterns)patterns$(l:foo)foo/$",
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
