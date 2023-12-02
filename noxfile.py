from __future__ import annotations

import shutil
import tomllib
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
    "test_submodules",
]


# tests


@nox.session
def test(session: nox.Session):
    session.install("-e", ".[test]")

    # this apparently CANNOT run from pre-commit in GitHub Actions (venv issues)
    session.run("pyright", "--warnings")

    session.run("pytest", *session.posargs)


@nox.session
def test_submodules(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./submodules/HexMod")

    # Hex Casting

    for props_file in [
        "hexdoc.toml",
        "submodules/HexMod/doc/hexdoc.toml",
    ]:
        env = {
            "GITHUB_REPOSITORY": "GITHUB_REPOSITORY",
            "GITHUB_SHA": "GITHUB_SHA",
            "GITHUB_PAGES_URL": "GITHUB_PAGES_URL",
            "DEBUG_GITHUBUSERCONTENT": "DEBUG_GITHUBUSERCONTENT",
        }
        session.run(
            "hexdoc", "export", "--branch", "main", "--props", props_file, env=env
        )

    session.run("pytest", "-m", "hexcasting", *session.posargs)

    # hexdoc-hexcasting-template

    ctt_root = "submodules/hexdoc-hexcasting-template"
    shutil.rmtree(f"{ctt_root}/.ctt", ignore_errors=True)
    session.run("ctt", "--base-dir", ctt_root)  # run copier-template-tester

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
def version(session: nox.Session):
    """Usage: `nox -s version -- <hatch version arguments>`"""

    session.install("hatch", "packaging")

    from packaging.version import Version

    if not session.posargs:
        session.run("hatch", "--quiet", "version")
        return

    # bump version

    old_version = Version(run_silent(session, "hatch", "--quiet", "version"))
    print(f"Old version: {old_version}")

    session.run("hatch", "version", *session.posargs)

    new_version = Version(run_silent(session, "hatch", "--quiet", "version"))

    if old_version.epoch and not new_version.epoch:
        session.warn("Adding epoch to updated version")
        new_version = Version(f"{old_version.epoch}!{new_version}")
        session.run("hatch", "version", str(new_version))

    print(f"New version: {new_version}")

    # commit new version and add tag

    session.log("Loading pyproject.toml")
    with open("pyproject.toml", "rb") as f:
        pyproject_toml = tomllib.load(f)
        version_path = pyproject_toml["tool"]["hatch"]["version"]["path"]

    message = f"Bump version to `{new_version}`"

    session.run("git", "add", version_path, external=True)
    session.run("git", "commit", "-m", message, external=True)
    session.run("git", "tag", f"v{new_version}", "-m", message, external=True)


@nox.session
def tag(session: nox.Session):
    session.install("hatch", "packaging")

    from packaging.version import Version

    message = "Automatic PEP 440 release tag"

    # validate some assumptions to make this simpler
    version = Version(run_silent(session, "hatch", "--quiet", "version"))
    assert version.epoch != 0
    assert len(version.release) == 3

    major, minor, _ = version.release
    tag = f"v{version.epoch}!{major}"

    # always update the prerelease tag, and also update the release tag if needed
    update_git_tag(session, tag=tag + ".dev", message=message)
    if version.dev is None:
        update_git_tag(session, tag=tag, message=message)

    tag += f".{minor}"

    update_git_tag(session, tag=tag + ".dev", message=message)
    if version.dev is None:
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

    session.run("hexdoc", "ci", "export")

    session.run("hexdoc", "ci", "render", "en_us")
    session.run("hexdoc", "ci", "render", "zh_cn")

    shutil.move("_site", "_site_tmp")
    shutil.move("_site_tmp", "_site/src/docs")

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
