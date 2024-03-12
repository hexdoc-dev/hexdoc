# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from contextlib import ExitStack, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, ContextManager, Iterable, Literal, Self

import importlib_resources as resources
from pydantic import model_validator
from typing_extensions import override

from hexdoc.model import HexdocModel
from hexdoc.plugin import PluginManager
from hexdoc.utils import JSONDict, RelativePath, relative_path_root


class BaseResourceDir(HexdocModel, ABC):
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

    @model_validator(mode="after")
    def _assert_path_exists(self):
        if self.required:
            for path in self._paths:
                assert (
                    path.exists()
                ), f"{self.__class__.__name__} path does not exist: {path}"

        return self


class PathResourceDir(BasePathResourceDir):
    # input is relative to the props file
    path: RelativePath

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
    def load(self, pm: PluginManager):
        yield [self]

    @model_validator(mode="before")
    def _pre_root(cls: Any, value: Any):
        # treat plain strings as paths
        if isinstance(value, str):
            return {"path": value}
        return value


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
    def load(self, pm: PluginManager):
        with relative_path_root(Path()), TemporaryDirectory() as tmpdir:
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
    def load(self, pm: PluginManager):
        with ExitStack() as stack, relative_path_root(Path()):
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


ResourceDir = PathResourceDir | PatchouliBooksResourceDir | PluginResourceDir
