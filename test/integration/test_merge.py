import json
from importlib.resources import Package
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from hexdoc.cli import app
from hexdoc.plugin import hookimpl
from hexdoc.plugin.manager import PluginManager
from hexdoc.plugin.mod_plugin import ModPluginWithBook
from hexdoc.plugin.specs import ModPluginImpl

from ..tree import write_file_tree

init_entrypoints = PluginManager.init_entrypoints


class MockPlugin(ModPluginImpl):
    @staticmethod
    @hookimpl
    def hexdoc_mod_plugin(branch: str) -> ModPluginWithBook:
        return MockModPlugin(branch=branch)


class MockModPlugin(ModPluginWithBook):
    @property
    def modid(self):
        return "test"

    @property
    def full_version(self):
        return "1.2.3.4"

    @property
    def mod_version(self):
        return "1.2"

    @property
    def plugin_version(self):
        return "3.4"

    def resource_dirs(self) -> list[Package]:
        return []


@pytest.fixture(autouse=True)
def register_plugin(monkeypatch: MonkeyPatch):
    def mock_init_entrypoints(self: PluginManager):
        init_entrypoints(self)
        self.register(MockPlugin)

    monkeypatch.setattr(
        PluginManager,
        "init_entrypoints",
        mock_init_entrypoints,
    )


@pytest.fixture
def hexdoc_toml() -> str:
    return """\
    modid = "test"
    default_lang = "en_us"
    default_branch = "main"

    resource_dirs = []

    [template]
    include = []

    [template.args]
    """


@pytest.fixture
def sitemap_marker() -> dict[str, Any]:
    return {
        "version": "1.2",
        "lang": "en_us",
        "lang_name": "English (United States)",
        "path": "/v/1.2/3.4/en_us",
        "is_default_lang": True,
        "full_version": "1.2.3.4",
        "minecraft_version": "1.20.1",
        "redirect_contents": "",
        "mod_version": "1.2",
        "plugin_version": "3.4",
    }


# TODO: this could be parametric


def test_merge(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hexdoc_toml: str,
    sitemap_marker: dict[str, Any],
):
    write_file_tree(
        tmp_path,
        {
            "hexdoc.toml": hexdoc_toml,
            "_site/src/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
        },
    )

    monkeypatch.chdir(tmp_path)

    app.merge(props_file=Path("hexdoc.toml"))

    with open("_site/dst/docs/v/1.2/3.4/en_us/.sitemap-marker.json") as f:
        assert json.load(f) == sitemap_marker


def test_allow_overwrite_identical_non_release(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hexdoc_toml: str,
    sitemap_marker: dict[str, Any],
):
    write_file_tree(
        tmp_path,
        {
            "hexdoc.toml": hexdoc_toml,
            "_site/src/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
            "_site/dst/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
        },
    )

    monkeypatch.chdir(tmp_path)

    app.merge(props_file=Path("hexdoc.toml"), release=False)

    with open("_site/dst/docs/v/1.2/3.4/en_us/.sitemap-marker.json") as f:
        assert json.load(f) == sitemap_marker


def test_prevent_overwrite_identical_release(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hexdoc_toml: str,
    sitemap_marker: dict[str, Any],
):
    write_file_tree(
        tmp_path,
        {
            "hexdoc.toml": hexdoc_toml,
            "_site/src/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
            "_site/dst/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
        },
    )

    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        app.merge(props_file=Path("hexdoc.toml"), release=True)


def test_prevent_overwrite_different_lang_release(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hexdoc_toml: str,
    sitemap_marker: dict[str, Any],
):
    write_file_tree(
        tmp_path,
        {
            "hexdoc.toml": hexdoc_toml,
            "_site/src/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
            "_site/dst/docs/v/1.2/3.4/zh_cn/.sitemap-marker.json": sitemap_marker,
        },
    )

    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        app.merge(props_file=Path("hexdoc.toml"), release=True)


def test_merge_different_existing_plugin_version_release(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hexdoc_toml: str,
    sitemap_marker: dict[str, Any],
):
    write_file_tree(
        tmp_path,
        {
            "hexdoc.toml": hexdoc_toml,
            "_site/src/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
            "_site/dst/docs/v/1.2/3.3/en_us/.sitemap-marker.json": sitemap_marker,
        },
    )

    monkeypatch.chdir(tmp_path)

    app.merge(props_file=Path("hexdoc.toml"), release=True)


def test_merge_different_existing_mod_version_release(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hexdoc_toml: str,
    sitemap_marker: dict[str, Any],
):
    write_file_tree(
        tmp_path,
        {
            "hexdoc.toml": hexdoc_toml,
            "_site/src/docs/v/1.2/3.4/en_us/.sitemap-marker.json": sitemap_marker,
            "_site/dst/docs/v/1.1/3.4/en_us/.sitemap-marker.json": sitemap_marker,
        },
    )

    monkeypatch.chdir(tmp_path)

    app.merge(props_file=Path("hexdoc.toml"), release=True)
