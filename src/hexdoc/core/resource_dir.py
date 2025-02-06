# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from contextlib import ExitStack, contextmanager
from fnmatch import fnmatch
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, ContextManager, Iterable, Iterator, Literal, Self
from zipfile import ZipFile

import importlib_resources as resources
from pydantic import Field, model_validator
from typing_extensions import override

from hexdoc.model import HexdocModel
from hexdoc.model.base import DEFAULT_CONFIG
from hexdoc.plugin import PluginManager
from hexdoc.utils import JSONDict, RelativePath
from hexdoc.utils.types import cast_nullable


class BaseResourceDir(HexdocModel, ABC):
    @staticmethod
    def _json_schema_extra(schema: dict[str, Any]):
        properties = schema.pop("properties")
        new_schema = {
            "anyOf": [
                schema | {"properties": properties | {key: value}}
                for key, value in {
                    "external": properties.pop("external"),
                    "internal": {
                        "type": "boolean",
                        "default": True,
                        "title": "Internal",
                    },
                }.items()
            ],
        }
        schema.clear()
        schema.update(new_schema)

    model_config = DEFAULT_CONFIG | {
        "json_schema_extra": _json_schema_extra,
    }

    external: bool
    reexport: bool
    """If not set, the default value will be `not self.external`.

    Must be defined AFTER `external` in the Pydantic model.
    """

    @abstractmethod
    def load(
        self,
        pm: PluginManager,
    ) -> ContextManager[Iterable[PathResourceDir]]: ...

    @property
    def internal(self):
        return not self.external

    @model_validator(mode="before")
    @classmethod
    def _default_reexport(cls, data: JSONDict | Any):
        if not isinstance(data, dict):
            return data

        external = cls._get_external(data)
        if external is None:
            return data

        if "reexport" not in data:
            data["reexport"] = not external

        return data

    @classmethod
    def _get_external(cls, data: JSONDict | Any):
        match data:
            case {"external": bool(), "internal": bool()}:
                raise ValueError(f"Expected internal OR external, got both: {data}")
            case {"external": bool(external)}:
                return external
            case {"internal": bool(internal)}:
                data.pop("internal")
                external = data["external"] = not internal
                return external
            case _:
                return None


class BasePathResourceDir(BaseResourceDir):
    # direct paths are probably internal
    external: bool = False
    reexport: bool = True

    required: bool = True
    """If false, ignore "file not found" errors."""

    @property
    @abstractmethod
    def _paths(self) -> Iterable[Path]: ...

    def _validate_path(self, path: Path) -> bool:
        return path.exists()

    @model_validator(mode="after")
    def _validate_paths(self):
        if self.required:
            for path in self._paths:
                if not self._validate_path(path):
                    raise ValueError(
                        f"{self.__class__.__name__} path does not exist: {path}"
                    )
        return self


class PathResourceDir(BasePathResourceDir):
    """Represents a path to a resources directory or a mod's `.jar` file."""

    @staticmethod
    def _json_schema_extra(schema: dict[str, Any]):
        BaseResourceDir._json_schema_extra(schema)
        new_schema = {
            "anyOf": [
                {
                    "type": "string",
                    "format": "path",
                },
                *schema["anyOf"],
            ]
        }
        schema.clear()
        schema.update(new_schema)

    model_config = DEFAULT_CONFIG | {
        "json_schema_extra": _json_schema_extra,
    }

    path: RelativePath
    """A path relative to `hexdoc.toml`."""

    archive: bool = Field(default=None, validate_default=False)  # type: ignore
    """If true, treat this path as a zip archive (eg. a mod's `.jar` file).

    If `path` ends with `.jar` or `.zip`, defaults to `True`.
    """

    # not a props field
    _modid: str | None = None

    @property
    def modid(self):
        return self._modid

    @property
    @override
    def _paths(self):
        return [self.path]

    def set_modid(self, modid: str) -> Self:
        self._modid = modid
        return self

    @contextmanager
    @override
    def load(self, pm: PluginManager):
        if self.archive:
            with self._extract_archive() as path:
                update = {
                    "path": path,
                    "archive": False,
                }
                yield [self.model_copy(update=update)]
        else:
            yield [self]

    @contextmanager
    def _extract_archive(self) -> Iterator[Path]:
        with (
            ZipFile(self.path, "r") as zf,
            TemporaryDirectory(suffix=self.path.name) as tempdir,
        ):
            # extract root-level files and *useful* sub-directories
            # ie. avoid extracting classes etc
            for info in zf.filelist:
                path = info.filename
                if path.startswith(("assets/", "data/")) or "/" not in path:
                    zf.extract(info, tempdir)

            yield Path(tempdir)

    @model_validator(mode="before")
    def _pre_root(cls: Any, value: Any):
        # treat plain strings as paths
        if isinstance(value, str):
            return {"path": value}
        return value

    @model_validator(mode="after")
    def _post_root(self):
        if cast_nullable(self.archive) is None:
            self.archive = self.path.suffix in {".jar", ".zip"}
        return self


class GlobResourceDir(BasePathResourceDir):
    glob: RelativePath
    exclude: list[str] = Field(default_factory=list)

    _resolved_paths: list[Path] | None = None

    @property
    @override
    def _paths(self):
        if self._resolved_paths:
            return self._resolved_paths

        base = Path()
        for i, part in enumerate(self.glob.parts):
            if "*" in part:
                glob = str(Path(*self.glob.parts[i:]))
                break
            base /= part
        else:
            raise ValueError(f"Glob does not contain any wildcards: {self.glob}")

        self._resolved_paths = [
            path
            for path in base.glob(glob)
            if not any(fnmatch(path.as_posix(), pat) for pat in self.exclude)
        ]
        if not self._resolved_paths:
            raise ValueError(f"Glob failed to find any matches: {self.glob}")

        return self._resolved_paths

    @contextmanager
    @override
    def load(self, pm: PluginManager):
        with ExitStack() as stack:
            yield [
                resource_dir
                for path in self._paths
                for resource_dir in stack.enter_context(
                    PathResourceDir(
                        path=path,
                        external=self.external,
                        reexport=self.reexport,
                    ).load(pm)
                )
            ]


class PatchouliBooksResourceDir(BasePathResourceDir):
    """For modpack books, eg. `.minecraft/patchouli_books`.

    Unlike other resource dirs, this points directly at `patchouli_books`, *not* at the
    `resources` directory. The namespace is always `patchouli`.

    https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/getting-started#1-locate-patchouli_books
    """

    patchouli_books: RelativePath

    @property
    def modid(self) -> Literal["patchouli"]:
        return "patchouli"

    @property
    @override
    def _paths(self):
        return [self.patchouli_books]

    @contextmanager
    @override
    def load(self, pm: PluginManager):
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # TODO: hack
            # at this point, we don't know if it's a resource pack book or not
            # we would need to load book.json to figure that out
            # so just put it in both possible locations to cover all the bases
            for folder in ["assets", "data"]:
                dst = tmpdir / folder / self.modid / "patchouli_books"
                dst.parent.mkdir(parents=True)
                shutil.copytree(self.patchouli_books, dst)

            yield [
                PathResourceDir(
                    path=tmpdir,
                    external=self.external,
                    reexport=self.reexport,
                ).set_modid(self.modid)
            ]


class PluginResourceDir(BaseResourceDir):
    modid: str

    # if we're specifying a modid, it's probably from some other mod/package
    external: bool = True
    reexport: bool = False

    @contextmanager
    @override
    def load(self, pm: PluginManager):
        with ExitStack() as stack:
            yield list(self._load_all(pm, stack))  # NOT "yield from"

    def _load_all(self, pm: PluginManager, stack: ExitStack):
        for module in pm.load_resources(self.modid):
            traversable = resources.files(module)
            path = stack.enter_context(resources.as_file(traversable))

            yield PathResourceDir(
                path=path,
                external=self.external,
                reexport=self.reexport,
            ).set_modid(self.modid)  # setting _modid directly causes a validation error


ResourceDir = (
    PathResourceDir | PatchouliBooksResourceDir | PluginResourceDir | GlobResourceDir
)
