import nox


@nox.session
def lint(session: nox.Session):
    session.install("favicons")  # TODO: remove
    session.install(".[test]", "nox", "pyright")

    session.run("pyright", "--warnings")


@nox.session
def tests(session: nox.Session):
    session.install("favicons")  # TODO: remove
    session.install(".[test]", "./test/_submodules/HexMod")

    # test cookiecutter last so the extra package install doesn't interfere
    session.run("pytest", "-k", "not test_cookiecutter")
    session.run("pytest", "-k", "test_cookiecutter")
