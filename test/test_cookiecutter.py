# pyright: reportUnknownMemberType=false

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from pytest import MonkeyPatch
from pytest_cookies.plugin import Cookies

from hexdoc._cli.app import render

from .conftest import longrun


@longrun
def test_cookiecutter(cookies: Cookies, monkeypatch: MonkeyPatch):
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

    Path("gradle.properties").write_text(
        dedent(
            f"""\
            modVersion=1.0.0
            hexcastingVersion=0.11.1-7
            minecraftVersion=1.20.1
            """
        )
    )

    java_root = Path("src/main/java/com/package")
    java_root.mkdir(parents=True)
    (java_root / "Patterns.java").touch()

    Path("src/generated/resources").mkdir(parents=True)

    book_root = Path(
        "src/main/resources/assets/hexcasting/patchouli_books/thehexbook/en_us"
    )
    book_root.mkdir(parents=True)

    category_root = book_root / "categories"
    category_root.mkdir(parents=True)
    with open(category_root / "foo.json", "w") as f:
        json.dump(
            {
                "name": "hexdoc.mod.title",
                "icon": "minecraft:amethyst_shard",
                "description": "hexcasting.category.basics.desc",
                "sortnum": 0,
            },
            f,
        )

    entry_root = book_root / "entries"
    (entry_root / "foo").mkdir(parents=True)
    with open(entry_root / "foo" / "bar.json", "w") as f:
        json.dump(
            {
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
            f,
        )

    (result.project_path / ".env").write_text(
        dedent(
            f"""\
            GITHUB_REPOSITORY=GITHUB/REPOSITORY
            GITHUB_SHA=GITHUB_SHA
            GITHUB_PAGES_URL=GITHUB_PAGES_URL"""
        )
    )

    # TODO: remove when textures stop being broken
    with open(result.project_path / "doc" / "properties.toml", "a") as f:
        f.write(
            dedent(
                """
                [textures]
                missing = [
                    "minecraft:*",
                    "hexcasting:*",
                ]
                """
            )
        )

    monkeypatch.syspath_prepend(result.project_path / "doc" / "src")

    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."])

    render()
