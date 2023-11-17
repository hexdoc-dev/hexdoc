"""
Mappings/utils for Mojang's API.
"""

import logging
import shutil
from pathlib import Path
from typing import Literal, TypeVar, overload

import requests
from hexdoc.model import HexdocModel
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


# specific version


class VersionPackageDownload(HexdocModel, extra="allow"):
    sha1: str
    size: int
    url: str

    def fetch_file(self, out_file: str | Path):
        logger.info(f"Fetching {self.url}")
        out_file = Path(out_file)

        with requests.get(self.url, stream=True) as response:
            response.raise_for_status()

            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "wb") as f:
                shutil.copyfileobj(response.raw, f)


class VersionPackageDownloads(HexdocModel, extra="allow"):
    client: VersionPackageDownload
    server: VersionPackageDownload


class VersionPackage(HexdocModel, extra="allow"):
    id: str
    downloads: VersionPackageDownloads


# base manifest


class VersionManifestV2Version(HexdocModel, extra="allow"):
    id: str
    type: Literal[
        "release",
        "snapshot",
        "old_alpha",
        "old_beta",
    ]
    url: str

    def fetch_package(self):
        logger.info(f"Fetching package for {self.id}")
        return fetch_model(VersionPackage, self.url)


class VersionManifestV2(HexdocModel, extra="allow"):
    latest: dict[Literal["release", "snapshot"], str]
    versions: list[VersionManifestV2Version]

    @classmethod
    def fetch(cls):
        logger.info(f"Fetching version manifest from {MANIFEST_URL}")
        return fetch_model(cls, MANIFEST_URL)

    def fetch_package(self, version_id: str):
        """Somewhat expensive - scans through `self.versions` as a list.

        If you need to call this frequently, consider refactoring VersionManifestV2 to
        construct a lookup dict.
        """
        for version in self.versions:
            if version.id == version_id:
                return version.fetch_package()
        raise FileNotFoundError(f"Version id not found: {version_id}")


_T = TypeVar("_T")
_T_HexdocModel = TypeVar("_T_HexdocModel", bound=HexdocModel)


@overload
def fetch_model(
    model_type: type[_T_HexdocModel],
    url: str,
) -> _T_HexdocModel:
    ...


@overload
def fetch_model(
    model_type: TypeAdapter[_T],
    url: str,
) -> _T:
    ...


def fetch_model(
    model_type: TypeAdapter[_T] | type[_T_HexdocModel],
    url: str,
) -> _T | _T_HexdocModel:
    response = requests.get(url)
    response.raise_for_status()

    if isinstance(model_type, TypeAdapter):
        return model_type.validate_json(response.content)

    return model_type.model_validate_json(response.content)
