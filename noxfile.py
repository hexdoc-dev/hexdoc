from typing import Mapping

import nox

PDOC_FAVICON = "https://github.com/object-Object/hexdoc/raw/main/media/hexdoc.png"
PDOC_LOGO_LINK = "https://pypi.org/project/hexdoc/"
PDOC_LOGO = "https://github.com/object-Object/hexdoc/raw/main/media/hexdoc.svg"
PDOC_EDIT_URL = "https://github.com/object-Object/hexdoc/blob/main/src/hexdoc/"

nox.options.reuse_existing_virtualenvs = True

nox.options.sessions = ["tests"]


@nox.session
def tests(session: nox.Session):
    session.run("pip", "uninstall", "hexdoc-mod", "-y")
    session.install("-e", ".[test]", "-e", "./test/_submodules/HexMod")

    # this apparently CANNOT run from pre-commit in GitHub Actions (venv issues)
    session.run("pyright", "src", "--warnings")

    # test cookiecutter last so the extra package install doesn't interfere
    session.run("pytest", "--nox", *session.posargs)


@nox.session
def hexdoc(session: nox.Session):
    session.install(".")
    session.run("hexdoc", *session.posargs)


@nox.session
def pdoc(session: nox.Session):
    session.install(".[pdoc]")

    version = run_silent(session, "hatch", "version")
    commit = run_silent(session, "git", "rev-parse", "--short", "HEAD", external=True)

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
