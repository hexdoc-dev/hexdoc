import nox


@nox.session(reuse_venv=True)
def tests(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./test/_submodules/HexMod")

    # this apparently CANNOT run from pre-commit in GitHub Actions (venv issues)
    session.run("pyright", "src", "--warnings")

    # test cookiecutter last so the extra package install doesn't interfere
    session.run("pytest", *session.posargs)
    session.run("pytest", "-k", "test_cookiecutter", "--nox", *session.posargs)
