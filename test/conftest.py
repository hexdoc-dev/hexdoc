import json
from fnmatch import fnmatch
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Literal, cast

import pytest
from hexdoc.core.properties import Properties
from hexdoc.plugin import PluginManager
from hexdoc.utils import JSONValue
from pytest import MonkeyPatch
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode
from syrupy.types import SerializableData, SerializedData

collect_ignore = [
    "noxfile.py",
]


class FilePathSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT

    def serialize(self, data: SerializableData, **_: Any) -> SerializedData:
        match data:
            case str() | Path():
                return self._read_file_at_path(Path(data))
            case _:
                raise TypeError(f"Expected StrPath, got {type(data)}: {data}")

    def _read_file_at_path(self, path: Path):
        if self._write_mode is WriteMode.BINARY:
            return path.read_bytes()
        return path.read_text(self._text_encoding)


# fixtures


@pytest.fixture
def path_snapshot(snapshot: SnapshotAssertion):
    return snapshot.use_extension(FilePathSnapshotExtension)


@pytest.fixture
def pm():
    return PluginManager(branch="main", props=cast(Properties, None))


@pytest.fixture
def empty_pm():
    return PluginManager(branch="main", props=cast(Properties, None), load=False)


@pytest.fixture(scope="session")
def monkeysession():
    with MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="session")
def env_overrides():
    return {
        "GITHUB_REPOSITORY": "GITHUB_REPOSITORY",
        "GITHUB_SHA": "GITHUB_SHA",
        "GITHUB_PAGES_URL": "GITHUB_PAGES_URL",
        "DEBUG_GITHUBUSERCONTENT": "DEBUG_GITHUBUSERCONTENT",
    }


@pytest.fixture(scope="session")
def hexcasting_props_file():
    return Path("submodules/HexMod/doc/hexdoc.toml")


@pytest.fixture(autouse=True, scope="session")
def patch_env(monkeysession: MonkeyPatch, env_overrides: dict[str, str]):
    for name, value in env_overrides.items():
        monkeysession.setenv(name, value)


# helpers


def list_directory(
    root: str | Path,
    glob: str = "**/*",
    exclude_glob: str | None = None,
) -> list[str]:
    def _should_include(path: Path):
        if not exclude_glob:
            return True
        return not fnmatch(path.as_posix(), exclude_glob)

    root = Path(root)
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.glob(glob)
        if _should_include(path)
    )


FileValue = JSONValue | tuple[Literal["a"], str] | Callable[[str | None], str]

FileTree = dict[str, "FileTree | FileValue"]


def write_file_tree(root: str | Path, tree: FileTree):
    for path, value in tree.items():
        path = Path(root, path)
        match value:
            case {**children} if path.suffix != ".json":
                # subtree
                path.mkdir(parents=True, exist_ok=True)
                write_file_tree(path, children)
            case {**json_data}:
                # JSON file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(json_data, indent="  "))
            case tuple((mode, text)):
                # append to existing file
                with path.open(mode) as f:
                    f.write(dedent(text))
            case str() as text:
                # anything else - usually just text
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(dedent(text))
            case int() | float() | bool() | None:
                raise TypeError(
                    f"Type {type(value)} is only allowed in JSON data: {value}"
                )
            case fn:
                assert not isinstance(fn, (list, dict))
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    current_value = path.read_text()
                except FileNotFoundError:
                    current_value = None
                path.write_text(dedent(fn(current_value)))
