import nox


@nox.session(reuse_venv=True)
def tests(session: nox.Session):
    session.install("-e", ".[test]", "-e", "./test/_submodules/HexMod")

    session.run("pre-commit")

    # test cookiecutter last so the extra package install doesn't interfere
    session.run("pytest", *session.posargs)
    session.run("pytest", "-k", "test_cookiecutter", "--nox", *session.posargs)
