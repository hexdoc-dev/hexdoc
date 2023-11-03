# hexdoc

This is the library that powers [Hex Casting](https://github.com/gamma-delta/HexMod)'s web book docgen.

## Creating a plugin / addon

WIP.

- Run these commands, then follow the prompts:
  ```sh
  pip3 install cruft
  cruft create gh:object-Object/hexdoc --directory doc
  ```
  - `--directory doc` tells Cookiecutter to look for a template in the `doc` directory of hexdoc, and cannot be omitted.
  - If you run this from within an existing mod repo, add the flag `-f`, and leave the `output_directory` option blank when prompted by Cookiecutter.
    - Note: this currently overwrites any conflicting files, including your .gitignore, so you may need to use your Git history to re-add anything not covered by the new file.
- Fill in the TODOs in `doc/properties.toml` (mostly paths to files/folders in your mod so hexdoc can find the data it needs).
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

## Setup

```sh
python3.11 -m venv venv

.\venv\Scripts\activate   # Windows
. venv/bin/activate.fish  # fish
source venv/bin/activate  # everything else

pip install -e .[dev]
```

## Usage

For local testing, create a file called `.env` in the repo root following this template:
```sh
GITHUB_SHA=main
GITHUB_REPOSITORY=object-Object/hexdoc
GITHUB_PAGES_URL=https://object-object.github.io/hexdoc
```

Then run these commands to generate the book:
```sh
hexdoc render
hexdoc merge
```

Or, run this command to render the book and start a local web server:
```sh
hexdoc serve --lang en_us
```

Nodemon is also configured.
