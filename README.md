<p align="center">
  <img alt="hexdoc logo" src="https://github.com/object-Object/hexdoc/raw/main/media/hexdoc.svg" height="200" />
  <br /><br />
  <a href="https://hexdoc.hexxy.media/"><img alt="Docs - hexdoc.hexxy.media" src="https://img.shields.io/badge/docs-hexdoc.hexxy.media-darkmagenta"></a>
  <a href="https://pypi.org/project/hexdoc/"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/hexdoc"></a>
  <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/hexdoc">
  <a href="https://github.com/object-Object/hexdoc/actions/workflows/ci.yml"><img alt="GitHub Workflow Status (with event)" src="https://img.shields.io/github/actions/workflow/status/object-Object/hexdoc/ci.yml?logo=github&label=ci"></a>
</p>

# hexdoc

A [Jinja](https://jinja.palletsprojects.com/en/3.1.x/)-based documentation generator for [Patchouli](https://github.com/VazkiiMods/Patchouli) books.

This is the library that powers [Hex Casting](https://github.com/gamma-delta/HexMod)'s web book.

## Plugins

### Creating a plugin / addon

WIP.

- Run these commands, then follow the prompts:
  ```sh
  pip3 install cruft
  cruft create https://github.com/object-Object/hexdoc
  ```
  - `--directory doc` tells Cookiecutter to look for a template in the `doc` directory of hexdoc, and cannot be omitted.
  - If you run this from within an existing mod repo, add the flag `-f`, and leave the `output_directory` option blank when prompted by Cookiecutter.
    - Note: this currently overwrites any conflicting files, including your .gitignore, so you may need to use your Git history to re-add anything not covered by the new file.
- Fill in the TODOs in `doc/hexdoc.toml` (mostly paths to files/folders in your mod so hexdoc can find the data it needs).
- Try running the docgen locally by following the instructions in `doc/README.md`.
- If it doesn't already exist, create an empty `gh-pages` branch and push it.
- On GitHub, under `Settings > Pages`, set the source to `Deploy from a branch`, the branch to `gh-pages`, and the folder to `docs/`.
- Commit and push the docgen, and see if the CI works.
- On GitHub, under `Settings > Environments`, create two new environments called `pypi` and `testpypi`.
- Follow these instructions for PyPI and TestPyPI: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
  - TestPyPI is a duplicate of PyPI which can be used for testing package publishing without affecting the real index. The CI workflow includes a manual execution option to publish to TestPyPI.
  - If you like to live dangerously, this step is optional - you can remove the `publish-testpypi` job and the `TestPyPI` release choice from your workflow without impacting the rest of the CI.

### Updating to the latest Cookiecutter template

Run this command: `cruft update`

See also: https://cruft.github.io/cruft/#updating-a-project

## Contributing

### Setup

```sh
git submodule update --init

python3.11 -m venv venv

.\venv\Scripts\activate   # Windows
. venv/bin/activate.fish  # fish
source venv/bin/activate  # everything else

pip install -e .[dev]
pre-commit install
```

### Usage

For local testing, create a file called `.env` in the repo root following this template:
```sh
GITHUB_SHA=main
GITHUB_REPOSITORY=object-Object/hexdoc
GITHUB_PAGES_URL=https://hexdoc.hexxy.media
```

Useful commands:
```sh
# show help
hexdoc -h

# render and serve the web book in watch mode
nodemon

# render and serve the web book
hexdoc serve

# export, render, and merge the web book
hexdoc export
hexdoc render
hexdoc merge

# start the Python interpreter with some extra local variables
hexdoc repl

# run tests
pytest  # fast, skips Cookiecutter
nox  # slow, full test suite in an isolated venv
nox --no-install  # after the first Nox run, use this to skip reinstalling everything

# update test snapshots
nox -- --snapshot-update

# run hexdoc commands in an isolated environment to ensure it works on its own
nox -s hexdoc -- export
nox -s hexdoc -- repl
```
