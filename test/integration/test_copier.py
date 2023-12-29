# pyright: reportUnknownMemberType=false

import subprocess
import sys
from pathlib import Path

import pytest
from hexdoc.cli import ci
from pytest import MonkeyPatch
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory
from ..tree import write_file_tree


def run_pip(*args: str):
    return subprocess.run((sys.executable, "-m", "pip") + args, check=True)


@pytest.fixture(scope="session")
def output_dir(monkeysession: MonkeyPatch, env_overrides: dict[str, str]):
    monkeysession.chdir("submodules/hexdoc-hexcasting-template/.ctt/test_copier")

    write_file_tree(
        ".",
        {
            "src/generated/resources": {},
            "src/main/java/com/package/Patterns.java": (
                """\
                public static final ActionRegistryEntry GET_CASTER = make(
                    "foobar",
                    new ActionRegistryEntry(
                        HexPattern.fromAngles("qaqaqaqaqaq", HexDir.NORTH_EAST),
                        OpGetCaster.INSTANCE
                    )
                );
                """
            ),
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
                    # expect the entry to be spoilered but the category to not be
                    "entries/baz.json": {
                        "name": "hexdoc.welcome.header",
                        "category": "hexcasting:basics",
                        "icon": "minecraft:textures/mob_effect/nausea.png",
                        "sortnum": 0,
                        "advancement": "hexcasting:enlightenment",
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

    run_pip("install", ".", "--force-reinstall", "--no-deps")

    monkeysession.setenv("GITHUB_OUTPUT", "github_output.txt")
    monkeysession.setenv("GITHUB_REF_NAME", "main")
    monkeysession.setenv("MOCK_GITHUB_PAGES_URL", "GITHUB_PAGES_URL")

    ci.build(
        props_file=Path("doc/hexdoc.toml"),
        release=False,
    )

    yield Path("_site/src/docs").resolve()


@pytest.mark.copier
def test_index(output_dir: Path, path_snapshot: SnapshotAssertion):
    path_snapshot._custom_index = "vlatestmainen_usindex.html"  # pyright: ignore[reportPrivateUsage]
    assert output_dir / "v/latest/main/en_us/index.html" == path_snapshot


@pytest.mark.copier
def test_list_directory(output_dir: Path, snapshot: SnapshotAssertion):
    assert list_directory(output_dir) == snapshot
