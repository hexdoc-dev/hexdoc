# pyright: reportUnknownMemberType=false

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Callable, Literal

from hexdoc.cli.app import render
from hexdoc.utils import JSONValue
from pytest import MonkeyPatch
from pytest_cookies.plugin import Cookies
from syrupy.assertion import SnapshotAssertion

from ..conftest import list_directory, nox_only

FileValue = JSONValue | tuple[Literal["a"], str] | Callable[[str | None], str]

FileTree = dict[str, "FileTree | FileValue"]


def write_file_tree(root: Path, tree: FileTree):
    for path, value in tree.items():
        path = root / path
        match value:
            case {**children} if path.suffix != ".json":
                # subtree
                path.mkdir(parents=True, exist_ok=True)
                write_file_tree(path, children)
            case {**json_data}:
                # JSON file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(json_data, indent="  "))
            case tuple((mode, text)):
                # append to existing file
                with path.open(mode) as f:
                    f.write(dedent(text))
            case str() as text:
                # anything else - usually just text
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(dedent(text))
            case int() | float() | bool() | None:
                raise TypeError(
                    f"Type {type(value)} is only allowed in JSON data: {value}"
                )
            case fn:
                assert not isinstance(fn, (list, dict))
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    current_value = path.read_text()
                except FileNotFoundError:
                    current_value = None
                path.write_text(dedent(fn(current_value)))


def run_pip(*args: str):
    return subprocess.run((sys.executable, "-m", "pip") + args, check=True)


@nox_only
def test_cookiecutter(
    cookies: Cookies,
    monkeypatch: MonkeyPatch,
    snapshot: SnapshotAssertion,
    path_snapshot: SnapshotAssertion,
    env_overrides: dict[str, str],
):
    result = cookies.bake(
        {
            "output_directory": "output",
            "modid": "mod",
            "pattern_regex": "hex_latest",
            "multiloader": False,
            "java_package": "com/package",
            "pattern_registry": "Patterns.java",
        }
    )

    assert result.exception is None
    assert result.project_path is not None

    monkeypatch.chdir(result.project_path)

    subprocess.run(["git", "init"], check=True)

    write_file_tree(
        result.project_path,
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
            # TODO: remove when textures are fully implemented
            "doc/hexdoc.toml": (
                "a",
                """
                [textures]
                missing = [
                    "minecraft:*",
                    "hexcasting:*",
                ]
                """,
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

    path_snapshot._custom_index = "vlatestindex.html"  # pyright: ignore[reportPrivateUsage]
    assert output_dir / "v" / "latest" / "index.html" == path_snapshot

    assert list_directory(output_dir) == snapshot
