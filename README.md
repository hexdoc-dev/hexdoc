<p align="center">
  <img alt="hexdoc logo" src="https://github.com/hexdoc-dev/hexdoc/raw/main/media/hexdoc.svg" height="200" />
  <br /><br />
  <a href="https://hexdoc.hexxy.media/"><img alt="Docs - hexdoc.hexxy.media" src="https://img.shields.io/badge/docs-hexdoc.hexxy.media-darkmagenta"></a>
  <a href="https://pypi.org/project/hexdoc/"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/hexdoc"></a>
  <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/hexdoc">
  <a href="https://github.com/hexdoc-dev/hexdoc/actions/workflows/ci.yml"><img alt="GitHub Workflow Status (with event)" src="https://img.shields.io/github/actions/workflow/status/hexdoc-dev/hexdoc/ci.yml?logo=github&label=ci"></a>
  <a href="https://github.com/hexdoc-dev/hexdoc#badges"><img src="https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc" alt="hexdoc" style="max-width:100%;"></a>
</p>

# hexdoc

A [Jinja](https://jinja.palletsprojects.com/en/3.1.x/)-based documentation generator for [Patchouli](https://github.com/VazkiiMods/Patchouli) books.

This is the library that powers [Hex Casting](https://github.com/gamma-delta/HexMod)'s web book.

Check out the docs at [https://hexdoc.hexxy.media](https://hexdoc.hexxy.media)!

## IMPORTANT: Version incompatibilities

There are issues related to installing hexdoc with the following dependency versions:
* Python 3.12+ on Windows: https://github.com/aio-libs/multidict/issues/887

hexdoc is known to work with Python 3.11.

## Plugins

hexdoc has a few Copier templates that you can use to set up a hexdoc plugin for your mod:

* [hexdoc-mod-template](https://github.com/hexdoc-dev/hexdoc-mod-template): generic template
* [hexdoc-hexcasting-template](https://github.com/hexdoc-dev/hexdoc-hexcasting-template): Hex Casting addons (also compatible with [HexDummy](https://github.com/FallingColors/hexdummy)!)

## Support

hexdoc does not currently have a dedicated support server. If you have any questions, please feel free to join the [Hex Casting Discord server](https://discord.gg/4xxHGYteWk) and ask in the [#hexdoc](https://discord.com/channels/936370934292549712/1180655324684894309) channel, or open an [issue](https://github.com/hexdoc-dev/hexdoc/issues)/[discussion](https://github.com/hexdoc-dev/hexdoc/discussions) on GitHub.

## Contributing

### Setup

Automatically set up a development environment with Nox:

```sh
pipx install nox  # pipx (recommended)
python3 -m pip install nox  # pip

nox -s setup
# next, run the venv activation command printed by uv
```

Manual setup:

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
GITHUB_REPOSITORY=hexdoc-dev/hexdoc
GITHUB_PAGES_URL=https://hexdoc.hexxy.media
```

Useful commands:
```sh
# show help
hexdoc -h

# serve hexdoc resources locally
# this is useful if serving other books locally that depend on hexdoc resources
nodemon --exec "hexdoc serve --port 8001 --no-merge"

# render and serve the Hex Casting web book in watch mode
nodemon

# start the Python interpreter with some extra local variables
hexdoc repl

# run tests
pytest  # fast, skips Cookiecutter
nox  # slow, full test suite in an isolated venv
nox --no-install  # after the first Nox run, use this to skip reinstalling everything

# update test snapshots (only running sessions with the tag "test")
nox -t test -- --snapshot-update

# run hexdoc commands in an isolated environment to ensure it works on its own
nox -s hexdoc -- build
nox -s hexdoc -- repl

# set up a dummy book for local testing
nox -s dummy_setup
nox -s dummy_serve

nox -s dummy_hexdoc -- build

nox -s dummy_clean

# generate and run the full docs website locally, or just run Docusaurus
nox -t docs
nox -s docusaurus
```

## Badges

### Shields.io

<a href="https://github.com/hexdoc-dev/hexdoc"><img src="https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc" alt="hexdoc" style="max-width:100%;"></a>
<a href="https://github.com/hexdoc-dev/hexdoc"><img src="https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc?label=1" alt="powered by hexdoc" style="max-width:100%;"></a>

#### Markdown

```md
[![hexdoc](https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc)](https://github.com/hexdoc-dev/hexdoc)

[![powered by hexdoc](https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc?label=1)](https://github.com/hexdoc-dev/hexdoc)
```

#### HTML

```html
<a href="https://github.com/hexdoc-dev/hexdoc"><img src="https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc" alt="hexdoc" style="max-width:100%;"></a>

<a href="https://github.com/hexdoc-dev/hexdoc"><img src="https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc?label=1" alt="powered by hexdoc" style="max-width:100%;"></a>
```

#### reStructuredText

```rst
.. image:: https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc
    :target: https://github.com/hexdoc-dev/hexdoc
    :alt: hexdoc

.. image:: https://img.shields.io/endpoint?url=https://hexxy.media/api/v0/badge/hexdoc?label=1
    :target: https://github.com/hexdoc-dev/hexdoc
    :alt: powered by hexdoc
```

### Devin's Badges

<a target="_blank" href="https://hexcasting.hexxy.media"><img src="https://github.com/SamsTheNerd/HexGloop/blob/73ea39b3becd/externalassets/hexdoc-badgecozy.svg?raw=true" alt="A badge for hexdoc in the style of Devins Badges" width=225></a>
<a target="_blank" href="https://addons.hexxy.media" height=75><img src="https://github.com/SamsTheNerd/HexGloop/blob/73ea39b3becd/externalassets/addon-badge-cozy.svg?raw=true" alt="A badge for addons.hexxy.media in the style of Devins Badges" width=200></a>

Thanks to [Sam](https://github.com/SamsTheNerd) for making these!

#### HTML

```html
<a target="_blank" href="INSERT_YOUR_BOOK_LINK_HERE"><img src="https://github.com/SamsTheNerd/HexGloop/blob/73ea39b3becd/externalassets/hexdoc-badgecozy.svg?raw=true" alt="A badge for hexdoc in the style of Devins Badges" width=225></a>

<a target="_blank" href="https://addons.hexxy.media" height=75><img src="https://github.com/SamsTheNerd/HexGloop/blob/73ea39b3becd/externalassets/addon-badge-cozy.svg?raw=true" alt="A badge for addons.hexxy.media in the style of Devins Badges" width=200></a>
```
