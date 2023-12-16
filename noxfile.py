from __future__ import annotations

import shutil
from pathlib import Path
from typing import Mapping

import nox

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


@nox.session
def test_hexcasting(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./submodules/HexMod")

    session.run("pytest", "-m", "hexcasting", *session.posargs)


@nox.session
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
def mock_ci(session: nox.Session):
    session.install(".", "./submodules/HexMod", "hatch")

    github_path = Path("out/github")

    shutil.rmtree("_site", ignore_errors=True)
    shutil.rmtree(github_path, ignore_errors=True)

    github_path.mkdir(parents=True)

    with session.cd("submodules/HexMod"):
        github_sha = run_silent_external(session, "git", "rev-parse", "HEAD")

    session.env.update(
        GITHUB_ENV=str(github_path / "env.txt"),
        GITHUB_OUTPUT=str(github_path / "output.txt"),
        GITHUB_REF_NAME="main",
        GITHUB_REPOSITORY="object-Object/HexMod",
        GITHUB_SHA=github_sha,
        GITHUB_STEP_SUMMARY=str(github_path / "step_summary.md"),
        GITHUB_TOKEN=run_silent_external(session, "gh", "auth", "token"),
        HEXDOC_PROPS="submodules/HexMod/doc/hexdoc.toml",
        HEXDOC_RELEASE="true",
    )
    if "-v" in session.posargs or "--verbose" in session.posargs:
        session.env.update(RUNNER_DEBUG="1")

    session.run("hexdoc", "ci", "build")
    session.run("hexdoc", "ci", "merge")


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
