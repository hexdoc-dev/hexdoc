"""
Commands designed to run in a GitHub Actions workflow.
"""

# pyright: reportPrivateUsage=false

import os
import shutil
import subprocess
from functools import cached_property
from pathlib import Path
from typing import Literal, TypedDict, TypeVar, Unpack

from github import Auth, Github
from github.Repository import Repository
from typer import Typer

from hexdoc.cli.utils.args import PropsOption, ReleaseOption
from hexdoc.model import HexdocModel, HexdocSettings
from hexdoc.model.base import HexdocTypeAdapter

from . import app as hexdoc_app

app = Typer(name="ci")


@app.command()
def export(
    *,
    props_file: PropsOption,
    release: ReleaseOption,
):
    env = CIEnvironment.model_getenv()

    pages_url = get_pages_url(env.repo)

    os.environ.update(
        GITHUB_PAGES_URL=pages_url,
    )

    props, all_i18n, path = hexdoc_app.export(
        Path("_site"),
        branch=env.branch,
        verbosity=env.verbosity,
        props_file=props_file,
        release=release,
    )

    subprocess.run(["hatch", "build", "--clean"], check=True)
    shutil.copytree("dist", path / "dist")

    matrix = [
        CIMatrixItem(
            value=lang,
            continue_on_error=lang != props.default_lang,
        )
        for lang in all_i18n.keys()
    ]

    env.set_output("pages-url", pages_url)
    env.set_output("matrix", (list[CIMatrixItem], matrix))


@app.command()
def render(
    lang: str,
    *,
    props_file: PropsOption,
    release: ReleaseOption,
):
    env = CIEnvironment.model_getenv()

    def _render(*, allow_missing: bool):
        hexdoc_app.render(
            Path("_site"),
            lang=lang,
            clean=True,
            allow_missing=allow_missing,
            branch=env.branch,
            verbosity=env.verbosity,
            props_file=props_file,
            release=release,
        )

    try:
        _render(allow_missing=False)
    except Exception as e:
        add_warning(f"Render failed. Retrying with --allow-missing. Exception: {e}")
        _render(allow_missing=True)
        add_warning(f"Language {lang} is missing some i18n keys.")


@app.command()
def merge(
    *,
    props_file: PropsOption,
):
    env = CIEnvironment.model_getenv()

    hexdoc_app.merge(
        props_file=props_file,
        verbosity=env.verbosity,
    )


# utils

_T = TypeVar("_T")


class CIEnvironment(HexdocSettings):
    github_output: str
    github_ref_name: str
    github_repository: str
    github_token: str | None = None
    runner_debug: bool = False

    @property
    def branch(self):
        return self.github_ref_name

    @property
    def verbosity(self):
        return 1 if self.runner_debug else 0

    @cached_property
    def repo(self):
        return self.gh.get_repo(self.github_repository)

    @cached_property
    def gh(self):
        return Github(
            auth=self._gh_auth,
        )

    @property
    def _gh_auth(self):
        if self.github_token:
            return Auth.Token(self.github_token)

    def set_output(self, name: str, value: str | tuple[type[_T], _T]):
        match value:
            case str():
                pass
            case (data_type, data):
                ta = HexdocTypeAdapter(data_type)
                value = ta.dump_json(data).decode()

        with open(self.github_output, "a") as f:
            print(f"{name}={value}", file=f)


def get_pages_url(repo: Repository) -> str:
    endpoint = f"{repo.url}/pages"
    try:
        _, data = repo._requester.requestJsonAndCheck("GET", endpoint)
    except Exception as e:
        e.add_note(f"  Endpoint: {endpoint}")
        raise
    return str(data["html_url"])


class CIMatrixItem(HexdocModel):
    value: str
    continue_on_error: bool


class AnnotationKwargs(TypedDict, total=False):
    title: str
    """Custom title"""
    file: str
    """Filename"""
    col: int
    """Column number, starting at 1"""
    endColumn: int
    """End column number"""
    line: int
    """Line number, starting at 1"""
    endLine: int
    """End line number"""


def add_notice(message: str, **kwargs: Unpack[AnnotationKwargs]):
    return add_annotation("notice", message, **kwargs)


def add_warning(message: str, **kwargs: Unpack[AnnotationKwargs]):
    return add_annotation("warning", message, **kwargs)


def add_error(message: str, **kwargs: Unpack[AnnotationKwargs]):
    return add_annotation("error", message, **kwargs)


def add_annotation(
    type: Literal["notice", "warning", "error"],
    message: str,
    **kwargs: Unpack[AnnotationKwargs],
):
    if kwargs:
        kwargs_str = " " + ",".join(f"{k}={v}" for k, v in kwargs.items())
    else:
        kwargs_str = ""

    print(f"::{type}{kwargs_str}::{message}")
