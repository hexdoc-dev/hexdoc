from __future__ import annotations

import os
import shutil
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Mapping

import nox

MOCK_ENV = {
    "GITHUB_REPOSITORY": "GITHUB_REPOSITORY",
    "GITHUB_SHA": "GITHUB_SHA",
    "GITHUB_PAGES_URL": "GITHUB_PAGES_URL",
    "DEBUG_GITHUBUSERCONTENT": "DEBUG_GITHUBUSERCONTENT",
    "MOCK_PLATFORM": "Windows",
}

DUMMY_PATH = Path(".hexdoc/dummy_book")

STATIC_GENERATED = "web/docusaurus/static-generated"

nox.options.default_venv_backend = "uv|virtualenv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = [
    "pyright",
    "test",
    "test_build",
    "test_hexcasting",
    "test_copier",
]


# tests


@nox.session
def pyright(session: nox.Session):
    session.install("-e", ".[test]")

    args = ["--warnings", *session.posargs]
    if os.getenv("RUNNER_DEBUG") == "1" and "--verbose" not in args:
        args.append("--verbose")

    session.run("pyright", *args)


@nox.session(tags=["test"])
def test(session: nox.Session):
    session.install("-e", ".[test]")

    session.run("pytest", *session.posargs)


@nox.session(tags=["test"])
def test_build(session: nox.Session):
    session.install("-e", ".[test]")

    session.run("hexdoc", "build", "--branch=main", env=MOCK_ENV)


@nox.session(tags=["test", "post_build"])
@nox.parametrize(["branch"], ["1.19_old", "main_old"])
def test_hexcasting(session: nox.Session, branch: str):
    with session.cd("submodules/HexMod"):
        original_branch = run_silent_external(
            session, "git", "rev-parse", "--abbrev-ref", "HEAD"
        )
        if original_branch == "HEAD":  # properly handle detached HEAD
            original_branch = run_silent_external(session, "git", "rev-parse", "HEAD")

        session.run("git", "checkout", branch, external=True)

    try:
        session.install("-e", ".[test]", "-e", "./submodules/HexMod")

        session.run(
            "hexdoc",
            "--quiet-lang=ru_ru",
            "--quiet-lang=zh_cn",
            "build",
            "--branch=main",
            "--props=submodules/HexMod/doc/hexdoc.toml",
            env=MOCK_ENV,
        )

        session.run(
            "pytest",
            "-m",
            "hexcasting",
            *session.posargs,
            env={"MOCK_PLATFORM": "Windows"},
        )
    finally:
        with session.cd("submodules/HexMod"):
            session.run("git", "checkout", original_branch, external=True)


@nox.session(tags=["test", "post_build"])
def test_copier(session: nox.Session):
    session.install("pip", "-e", ".[test]", "-e", "./submodules/HexMod")

    template_repo = Path("submodules/hexdoc-hexcasting-template")
    rendered_template = template_repo / ".ctt" / "test_copier"

    rmtree(session, rendered_template, ignore_errors=True)
    session.run("ctt", "--base-dir", str(template_repo))
    session.run("git", "init", str(rendered_template), external=True)

    session.run(
        "pytest",
        "-m",
        "copier",
        *session.posargs,
        env={"MOCK_PLATFORM": "Windows"},
    )


# CI/CD


@nox.session(tags=["docs"], python=False)
def clean_docs(session: nox.Session):
    rmtree(session, STATIC_GENERATED)


@nox.session(tags=["docs"])
def json_schemas(session: nox.Session):
    session.install("-e", ".")

    for model_type in [
        "core.Properties",
        "patchouli.Book",
        "patchouli.Category",
        "patchouli.Entry",
    ]:
        session.run(
            "python",
            "-m",
            "_scripts.json_schema",
            f"hexdoc.{model_type}",
            "--output",
            f"{STATIC_GENERATED}/schema/{model_type.replace('.', '/')}.json",
        )

    # backwards compatibility with old naming scheme
    Path(f"{STATIC_GENERATED}/schema/hexdoc/core").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        f"{STATIC_GENERATED}/schema/core/Properties.json",
        f"{STATIC_GENERATED}/schema/hexdoc/core/Properties.json",
    )


@nox.session(tags=["docs"])
def pdoc(session: nox.Session):
    session.install("-e", ".[pdoc]")

    hexdoc_version = get_hexdoc_version()
    commit = run_silent_external(session, "git", "rev-parse", "--short", "HEAD")

    session.run(
        "pdoc",
        "hexdoc",
        "--template-directory=web/pdoc",
        "--favicon=https://github.com/hexdoc-dev/hexdoc/raw/main/media/hexdoc.png",
        "--logo-link=https://hexdoc.hexxy.media",
        "--logo=https://github.com/hexdoc-dev/hexdoc/raw/main/media/hexdoc.svg",
        "--edit-url=hexdoc=https://github.com/hexdoc-dev/hexdoc/blob/main/src/hexdoc/",
        f"--footer-text=Version: {hexdoc_version} ({commit})",
        f"--output-directory={STATIC_GENERATED}/docs/api",
    )


# docs for the docs!
@nox.session(tags=["docs"], python=False)
def docusaurus(session: nox.Session):
    shutil.copytree("media", f"{STATIC_GENERATED}/img", dirs_exist_ok=True)

    with session.cd("web/docusaurus"):
        session.run_install("npm", ("ci" if is_ci() else "install"), external=True)

        match session.posargs:
            case ["build", *args]:
                command = "build"
            case args:
                command = "start"
                args = ["--no-open", *args]

        session.run("npm", "run", command, "--", *args, external=True)


# IMPORTANT: must install packaging alongside Nox to use this session!
# FIXME: this should be in src/_scripts instead
@nox.session
def tag(session: nox.Session):
    from packaging.version import Version

    message = "Automatic PEP 440 release tag"

    # validate some assumptions to make this simpler
    raw_version = get_hexdoc_version()
    version = Version(raw_version)
    assert version.epoch != 0
    assert len(version.release) == 3

    major, minor, _ = version.release
    tag = f"v{version.epoch}!{major}"

    # always update the prerelease tag, and also update the release tag if needed
    update_git_tag(session, tag=tag + ".dev", message=message)
    if not version.is_prerelease:
        update_git_tag(session, tag=tag, message=message)

    tag += f".{minor}"

    update_git_tag(session, tag=tag + ".dev", message=message)
    if not version.is_prerelease:
        update_git_tag(session, tag=tag, message=message)


# development helpers


@nox.session
def setup(session: nox.Session):
    session.install("uv", "pre-commit")

    if not Path("submodules/HexMod/pyproject.toml").exists():
        session.run("git", "submodule", "update", "--init")

    rmtree(session, "venv", onerror=on_rm_error)
    session.run("uv", "venv", "venv", "--seed")

    session.run(
        *("uv", "pip", "install"),
        "--quiet",
        "-e=.[dev]",
        "-e=./submodules/HexMod",
        env={
            "VIRTUAL_ENV": str(Path.cwd() / "venv"),
        },
    )

    session.run("pre-commit", "install")


@nox.session
def hexdoc(session: nox.Session):
    session.install("-e", ".")
    session.run("hexdoc", *session.posargs)


@nox.session
def dummy_setup(session: nox.Session):
    session.install("copier", "hatch")

    with prepend_sys_path("."):
        from test.tree import write_file_tree

    session.run(
        "copier",
        "copy",
        "gh:hexdoc-dev/hexdoc-mod-template",
        str(DUMMY_PATH),
        "--no-cleanup",
        "--force",
        "--data=modid=dummy",
        "--data=author=author",
        "--data=multiloader=false",
    )

    # Example image:
    # PNG image, 16x16, 1-bit indexed color
    # Palette: 0 = #202020 1 = #50ff50 (green)
    # No compression, filter 0 on all scanlines (none)
    image = (
        b"\x89PNG\r\n\x1a\n"
        b"\0\0\0\x0dIHDR\0\0\0\x10\0\0\0\x10\x01\x03\0\0\0\x25\x3d\x6d\x22"
        b"\0\0\0\x06PLTE\x22\x22\x22\x50\xff\x50\xca\xca\x84\x15"
        b"\0\0\0\x3bIDAT\x78\x01\x01\x30\0\xcf\xff\0\0\0\0\x7f\xfe\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x40\x02\0\x7f\xfe\0\0\0\x92\xd5\x06\x13\xec\x45\xbf\x6a"
        b"\0\0\0\0IEND\xae\x42\x60\x82"
    )

    session.log(f"write_file_tree({DUMMY_PATH}, ...)")
    write_file_tree(
        DUMMY_PATH,
        {
            "doc": {
                "resources": {
                    "assets/minecraft/textures/entities": {
                        "chicken.png": ("wb", image)
                    },
                    "assets/dummy/patchouli_books/dummybook": {
                        "en_us": {
                            "categories/foo.json": {
                                "name": "Dummy Category",
                                "icon": "minecraft:amethyst_shard",
                                "description": "Foo bar baz qux$(br)$(li)quux$(br)$(li2)corge$(br)$(li3)grault$(br)$(li4)garply$(li)waldo$(br)fred plugh xyzzy thud",
                                "sortnum": 0,
                            },
                            "entries/bar.json": {
                                "name": "Dummy Entry",
                                "category": "dummy:foo",
                                "icon": "minecraft:textures/mob_effect/nausea.png",
                                "sortnum": 0,
                                "pages": [
                                    {
                                        "type": "patchouli:text",
                                        "text": "Dummy Page",
                                    },
                                    {
                                        "type": "dummy:example",
                                        "example_value": "insert funny message here",
                                    },
                                    {
                                        "type": "patchouli:spotlight",
                                        "text": "spotlight!",
                                        "item": "minecraft:stone",
                                    },
                                    {
                                        "type": "patchouli:spotlight",
                                        "title": "title!",
                                        "text": "spotlight with title!",
                                        "item": "minecraft:stone",
                                    },
                                    {
                                        "type": "patchouli:spotlight",
                                        "text": "spotlight with anchor!",
                                        "item": "minecraft:stone",
                                        "anchor": "spotlight",
                                    },
                                    {
                                        "type": "patchouli:spotlight",
                                        "text": "spotlight with named item!",
                                        "item": """minecraft:stone{display:{Name:'{"text":"dirt?","color":"white"}'}}""",
                                    },
                                ],
                            },
                            "entries/patchistuff.json": {
                                "name": "Patchouli Stuff",
                                "category": "dummy:foo",
                                "icon": "minecraft:book",
                                "sortnum": 0,
                                "pages": [
                                    {
                                        "type": "patchouli:multiblock",
                                        "name": "MultiBlock Test",
                                        "multiblock": {
                                            "pattern": [
                                                [
                                                    " GRG ",
                                                    "GGRGG",
                                                    "RRRRR",
                                                    "GGRGG",
                                                    " GRG ",
                                                ],
                                                [
                                                    "GG GG",
                                                    "G   G",
                                                    "     ",
                                                    "G   G",
                                                    "GG GG",
                                                ],
                                                [
                                                    "G   G",
                                                    "     ",
                                                    "     ",
                                                    "     ",
                                                    "G   G",
                                                ],
                                                [
                                                    "G   G",
                                                    "     ",
                                                    "  0  ",
                                                    "     ",
                                                    "G   G",
                                                ],
                                                [
                                                    "_WWW_",
                                                    "WWWWW",
                                                    "WWWWW",
                                                    "WWWWW",
                                                    "_WWW_",
                                                ],
                                            ],
                                            "mapping": {
                                                "G": "minecraft:gold_block",
                                                "W": "#minecraft:wool",
                                                "R": "minecraft:terracotta",
                                            },
                                        },
                                        "text": "Multi Block Test !",
                                    },
                                    {
                                        "type": "patchouli:quest",
                                        "trigger": "story/smelt_iron",
                                        "text": "Wow, what a wonderful quest this is here",
                                    },
                                    {
                                        "type": "patchouli:relations",
                                        "entries": [
                                            "dummy:otherrecipes",
                                            "dummy:bar",
                                        ],
                                        "text": "have a look at these related entries!!",
                                    },
                                    {
                                        "type": "patchouli:entity",
                                        "entity": "minecraft:chicken",
                                        "text": "ah yes, the chicken. it lays eggs and stuff",
                                    },
                                    {
                                        "type": "patchouli:link",
                                        "url": "https://github.com/hexdoc-dev/hexdoc",
                                        "link_text": "hexdoc GitHub",
                                        "text": "Link page",
                                    },
                                    {"type": "patchouli:empty"},
                                ],
                            },
                            "entries/otherrecipes.json": {
                                "name": "More Recipe Types",
                                "category": "dummy:foo",
                                "icon": "minecraft:stonecutter",
                                "sortnum": 0,
                                "pages": [
                                    {
                                        "type": "patchouli:stonecutting",
                                        "recipe": "dummy:test_stonecutting",
                                        "text": "Very true and valid stonecutting recipe",
                                    },
                                    {
                                        "type": "patchouli:smithing",
                                        "recipe": "dummy:test_smithing_trim",
                                        "text": "Pretty armor!",
                                        "advancement": "dummy:spoiler",
                                    },
                                    {
                                        "type": "patchouli:crafting",
                                        "recipe": "dummy:test_crafting",
                                    },
                                ],
                            },
                            "entries/smelting.json": {
                                "name": "Smelting",
                                "category": "dummy:foo",
                                "icon": "minecraft:furnace",
                                "sortnum": 0,
                                "pages": [
                                    {
                                        "type": "patchouli:smelting",
                                        "recipe": "dummy:test_smelting",
                                        "text": "Smelting Time !",
                                    },
                                    {
                                        "type": "patchouli:smoking",
                                        "recipe": "dummy:test_smoking",
                                        "text": "Smoking Time !",
                                    },
                                    {
                                        "type": "patchouli:campfire_cooking",
                                        "recipe": "dummy:test_campfire",
                                        "text": "Campfire Time !",
                                    },
                                    {
                                        "type": "patchouli:blasting",
                                        "recipe": "dummy:test_blasting",
                                        "text": "Blasting Time !",
                                    },
                                ],
                            },
                        },
                    },
                    "data/dummy": {
                        "patchouli_books/dummybook/book.json": {
                            "name": "Dummy Book",
                            "landing_text": "Lorem ipsum dolor sit amet",
                            "use_resource_pack": True,
                            "i18n": False,
                        },
                        "recipes": {
                            "test_blasting.json": {
                                "type": "minecraft:blasting",
                                "experience": 0.1,
                                "ingredient": {"item": "minecraft:raw_iron"},
                                "result": "minecraft:iron_ingot",
                            },
                            "test_campfire.json": {
                                "type": "minecraft:campfire_cooking",
                                "experience": 0.1,
                                "ingredient": {"item": "minecraft:potato"},
                                "result": "minecraft:baked_potato",
                            },
                            "test_crafting.json": {
                                "type": "minecraft:crafting_shaped",
                                "pattern": [" DD", " SD", "S  "],
                                "key": {
                                    "S": {"item": "minecraft:stick"},
                                    "D": {"item": "minecraft:diamond"},
                                },
                                "result": {
                                    "item": "minecraft:diamond_pickaxe",
                                    "count": 3,
                                },
                            },
                            "test_smelting.json": {
                                "type": "minecraft:smelting",
                                "cookingtime": 200,
                                "experience": 0.1,
                                "ingredient": {"item": "minecraft:sand"},
                                "result": "minecraft:glass",
                            },
                            "test_smithing_trim.json": {
                                "type": "minecraft:smithing_trim",
                                "base": {"item": "minecraft:netherite_chestplate"},
                                "template": {
                                    "item": "minecraft:wayfinder_armor_trim_smithing_template"
                                },
                                "addition": {"item": "minecraft:gold_ingot"},
                            },
                            "test_smoking.json": {
                                "type": "minecraft:smoking",
                                "experience": 0.1,
                                "ingredient": {"item": "minecraft:potato"},
                                "result": "minecraft:baked_potato",
                            },
                            "test_stonecutting.json": {
                                "type": "minecraft:stonecutting",
                                "ingredient": {"item": "minecraft:stone"},
                                "result": "minecraft:stone_bricks",
                                "count": 9,
                            },
                        },
                    },
                    "data/hexdoc/tags/advancements/spoilered.json": {
                        "replace": False,
                        "values": ["dummy:spoiler"],
                    },
                },
                "hexdoc.toml": (
                    """\
                    modid = "dummy"
                    book = "dummy:dummybook"
                    default_lang = "en_us"
                    default_branch = "main"

                    resource_dirs = [
                        "resources",
                        { modid="minecraft" },
                        { modid="hexdoc" },
                    ]
                    export_dir = "src/hexdoc_dummy/_export/generated"

                    [template]
                    icon = "icon.png"
                    include = [
                        "dummy",
                        "hexdoc",
                    ]

                    [template.args]
                    mod_name = "Dummy"
                    author = "author"
                    show_landing_text = true

                    [template.args.navbar]
                    left = [
                        { text="<strong>Left</strong>", href="https://google.ca" },
                    ]
                    center = [
                        { text="Center 1", href="https://google.ca", external=false },
                        { text="Center 2", href="https://google.ca", external=false, icon="box-arrow-down-right" },
                    ]
                    right = [
                        { text="Right", href="https://google.ca", icon="box-arrow-up-left" },
                        { text="GitHub", href.variable="source_url" },
                    ]
                    """
                ),
                "nodemon.json": {
                    "watch": [
                        "doc/src",
                        "doc/resources",
                        "doc/hexdoc.toml",
                        "src/main/resources/assets/*/lang",
                        "src/main/resources/assets/dummy/patchouli_books",
                        "../../src",
                    ],
                    "ignore": ["**/generated/**"],
                    "ext": "jinja,html,css,js,ts,toml,json,json5,py",
                    "exec": "hexdoc serve",
                },
            },
            "gradle.properties": (
                """\
                modVersion=1.0.0
                minecraftVersion=1.20.1
                """
            ),
        },
    )

    with session.cd(DUMMY_PATH):
        session.run("hatch", "version", silent=True)

        session.run("git", "init", ".", external=True)
        session.run("git", "add", ".", external=True)
        session.run(
            "git",
            "commit",
            "-m",
            "Initial commit",
            external=True,
            success_codes=[0, 1],
        )


@nox.session
def dummy_hexdoc(session: nox.Session):
    session.install("-e", ".", "-e", f"./{DUMMY_PATH.as_posix()}")

    with session.cd(DUMMY_PATH):
        session.run("hexdoc", *session.posargs)


@nox.session
def dummy_serve(session: nox.Session):
    session.install("-e", ".", "-e", f"./{DUMMY_PATH.as_posix()}")

    with session.cd(DUMMY_PATH):
        session.run("nodemon", "--config", "./doc/nodemon.json", external=True)


@nox.session(python=False)
def dummy_clean(session: nox.Session):
    rmtree(session, DUMMY_PATH)


# utils (not sessions)


def is_ci():
    return os.getenv("CI") == "true"


def run_silent_external(
    session: nox.Session,
    *args: str,
    env: Mapping[str, str] | None = None,
):
    return run_silent(session, *args, env=env, external=True)


def run_silent(
    session: nox.Session,
    *args: str,
    env: Mapping[str, str] | None = None,
    external: bool = False,
):
    output: str | None = session.run(
        *args,
        env=env,
        silent=True,
        external=external,
    )
    assert output
    return output.strip()


def update_git_tag(session: nox.Session, *, tag: str, message: str):
    return session.run(
        "git",
        "tag",
        "-fam",
        message,
        tag,
        external=True,
        env=dict(
            GIT_COMMITTER_NAME="GitHub Actions",
            GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com",
        ),
    )


def on_rm_error(func: Callable[..., Any], path: str, exc_info: Any):
    # from: https://stackoverflow.com/questions/4829043/how-to-remove-read-only-attrib-directory-with-python-in-windows
    path_ = Path(path)
    path_.chmod(stat.S_IWRITE)
    path_.unlink()


def rmtree(
    session: nox.Session,
    path: str | Path,
    ignore_errors: bool = False,
    onerror: Callable[[Callable[..., Any], str, Any], object] | None = on_rm_error,
):
    if Path(path).is_dir():
        session.log(f"Removing directory: {path}")
        shutil.rmtree(path, ignore_errors, onerror)


def get_hexdoc_version():
    with prepend_sys_path("src"):
        from hexdoc.__version__ import VERSION

    return VERSION


@contextmanager
def prepend_sys_path(value: str):
    sys.path.insert(0, value)
    yield
    sys.path.pop(0)


# @contextmanager
# def activate_venv(session: nox.Session):
#     venv_dir = session.virtualenv.location
#     site_packages =
#     with prepend_sys_path()
