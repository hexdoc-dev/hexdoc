import nox

nox.options.sessions = ["tests"]


@nox.session(reuse_venv=True)
def hexdoc(session: nox.Session):
    session.install(".")
    session.run("hexdoc", *session.posargs)


@nox.session(reuse_venv=True)
def tests(session: nox.Session):
    session.run("pip", "uninstall", "hexdoc-mod", "-y")
    session.install("-e", ".[test]", "-e", "./test/_submodules/HexMod")

    # this apparently CANNOT run from pre-commit in GitHub Actions (venv issues)
    session.run("pyright", "src", "--warnings")

    # test cookiecutter last so the extra package install doesn't interfere
    session.run("pytest", "--nox", *session.posargs)
