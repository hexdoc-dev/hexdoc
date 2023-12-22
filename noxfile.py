from __future__ import annotations

import logging
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Mapping

import nox

DUMMY_PATH = Path(".hexdoc/dummy_book")

PDOC_FAVICON = "https://github.com/hexdoc-dev/hexdoc/raw/main/media/hexdoc.png"
PDOC_LOGO_LINK = "https://pypi.org/project/hexdoc/"
PDOC_LOGO = "https://github.com/hexdoc-dev/hexdoc/raw/main/media/hexdoc.svg"
PDOC_EDIT_URL = "https://github.com/hexdoc-dev/hexdoc/blob/main/src/hexdoc/"

nox.options.reuse_existing_virtualenvs = True

nox.options.sessions = [
    "test",
    "test_build",
    "test_hexcasting",
    "test_copier",
]


# tests


@nox.session
def test(session: nox.Session):
    session.install("-e", ".[test]")

    # this apparently CANNOT run from pre-commit in GitHub Actions (venv issues)
    session.run("pyright", "--warnings")

    session.run("pytest", *session.posargs)


@nox.session
def test_build(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./submodules/HexMod")

    env = {
        "GITHUB_REPOSITORY": "GITHUB_REPOSITORY",
        "GITHUB_SHA": "GITHUB_SHA",
        "GITHUB_PAGES_URL": "GITHUB_PAGES_URL",
        "DEBUG_GITHUBUSERCONTENT": "DEBUG_GITHUBUSERCONTENT",
    }

    session.run("hexdoc", "build", "--branch=main", env=env)

    session.run(
        "hexdoc",
        "--quiet-lang=ru_ru",
        "--quiet-lang=zh_cn",
        "build",
        "--branch=main",
        "--props=submodules/HexMod/doc/hexdoc.toml",
        env=env,
    )


@nox.session(tags=["post_build"])
def test_hexcasting(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./submodules/HexMod")

    session.run("pytest", "-m", "hexcasting", *session.posargs)


@nox.session(tags=["post_build"])
def test_copier(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./submodules/HexMod")

    template_repo = Path("submodules/hexdoc-hexcasting-template")
    rendered_template = template_repo / ".ctt" / "test_copier"

    shutil.rmtree(rendered_template, ignore_errors=True)
    session.run("ctt", "--base-dir", str(template_repo))
    session.run("git", "init", str(rendered_template), external=True)

    session.run("pytest", "-m", "copier", *session.posargs)


# CI/CD


@nox.session
def pdoc(session: nox.Session):
    # docs for the docs!
    session.install(".[pdoc]")

    version = run_silent(session, "hatch", "--quiet", "version")
    commit = run_silent_external(session, "git", "rev-parse", "--short", "HEAD")

    session.run(
        "pdoc",
        "hexdoc",
        "--favicon",
        PDOC_FAVICON,
        "--logo-link",
        PDOC_LOGO_LINK,
        "--logo",
        PDOC_LOGO,
        "--edit-url",
        f"hexdoc={PDOC_EDIT_URL}",
        "--footer-text",
        f"Version: {version} ({commit})",
        *session.posargs,
    )


@nox.session
def tag(session: nox.Session):
    session.install("hatch", "packaging")

    from packaging.version import Version

    message = "Automatic PEP 440 release tag"

    # because hatch is dumb and thinks it's ok to log on stdout i guess?
    # or maybe nox is capturing it
    # i have no idea
    run_silent(session, "hatch", "--quiet", "version")

    # validate some assumptions to make this simpler
    version = Version(run_silent(session, "hatch", "--quiet", "version"))
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
def hexdoc(session: nox.Session):
    session.install(".")
    session.run("hexdoc", *session.posargs)


@nox.session
def dummy_setup(session: nox.Session):
    session.install("copier")

    from copier import run_copy  # type: ignore

    sys.path.insert(0, ".")

    from test.tree import write_file_tree

    sys.path.pop(0)

    logging.getLogger("plumbum.local").setLevel(logging.WARNING)
    run_copy(
        "gh:hexdoc-dev/hexdoc-mod-template",
        DUMMY_PATH,
        cleanup_on_error=False,
        defaults=True,
        overwrite=True,
        data=dict(
            modid="dummy",
            author="author",
            multiloader=False,
        ),
    )

    session.log(f"write_file_tree({DUMMY_PATH}, ...)")
    write_file_tree(
        DUMMY_PATH,
        {
            "doc": {
                "resources": {
                    "assets/dummy/patchouli_books/dummybook": {
                        "en_us": {
                            "categories/foo.json": {
                                "name": "Dummy Category",
                                "icon": "minecraft:amethyst_shard",
                                "description": "Foo bar baz qux quux corge grault garply waldo fred plugh xyzzy thud",
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
                                ],
                            },
                        },
                    },
                    "data/dummy/patchouli_books/dummybook/book.json": {
                        "name": "Dummy Book",
                        "landing_text": "Lorem ipsum dolor sit amet",
                        "use_resource_pack": True,
                        "i18n": False,
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
                    """
                ),
            },
            "gradle.properties": (
                """\
                modVersion=1.0.0
                minecraftVersion=1.20.1
                """
            ),
        },
    )

    with session.chdir(DUMMY_PATH):
        session.run("git", "init", ".", external=True)
        session.run("git", "add", ".", external=True)
        session.run("git", "commit", "-m", "Initial commit", external=True)


@nox.session
def dummy_hexdoc(session: nox.Session):
    session.install("-e", ".", "-e", f"./{DUMMY_PATH.as_posix()}")

    with session.chdir(DUMMY_PATH):
        session.run("hexdoc", *session.posargs)


@nox.session
def dummy_serve(session: nox.Session):
    session.install("-e", ".", "-e", f"./{DUMMY_PATH.as_posix()}")

    with session.chdir(DUMMY_PATH):
        session.run("nodemon", "--config", "./doc/nodemon.json", external=True)


@nox.session(python=False)
def dummy_clean(session: nox.Session):
    if DUMMY_PATH.is_dir():
        session.log(f"Removing directory: {DUMMY_PATH}")
        shutil.rmtree(DUMMY_PATH, onerror=on_rm_error)


# utils (not sessions)


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


def on_rm_error(func: Any, path: str, exc_info: Any):
    # from: https://stackoverflow.com/questions/4829043/how-to-remove-read-only-attrib-directory-with-python-in-windows
    path_ = Path(path)
    path_.chmod(stat.S_IWRITE)
    path_.unlink()
