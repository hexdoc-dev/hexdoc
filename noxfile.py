import nox


@nox.session
def tests(session: nox.Session):
    session.install("favicons")  # TODO: remove
    session.install("pyright", "nox")
    session.install("-e", ".[test]", "-e", "./test/_submodules/HexMod")

    session.run("pyright", "--warnings")

    session.run("hexdoc", "export", "--props", "properties.toml")
    session.run(
        "hexdoc", "export", "--props", "test/_submodules/HexMod/doc/properties.toml"
    )

    # test cookiecutter last so the extra package install doesn't interfere
    session.run("pytest", *session.posargs)
    session.run("pytest", "-k", "test_cookiecutter", "--nox", *session.posargs)
