from __future__ import annotations

from typing import Self

from pydantic import model_validator
from yarl import URL

from hexdoc.model.base import HexdocSettings
from hexdoc.utils.types import PydanticURL


class EnvironmentVariableProps(HexdocSettings):
    # default Actions environment variables
    github_repository: str
    github_sha: str

    # set by CI
    github_pages_url: PydanticURL

    # for putting books somewhere other than the site root
    hexdoc_subdirectory: str | None = None

    # optional for debugging
    debug_githubusercontent: PydanticURL | None = None

    @property
    def asset_url(self) -> URL:
        if self.debug_githubusercontent is not None:
            return URL(str(self.debug_githubusercontent))

        return (
            URL("https://raw.githubusercontent.com")
            / self.github_repository
            / self.github_sha
        )

    @property
    def source_url(self) -> URL:
        return (
            URL("https://github.com")
            / self.github_repository
            / "tree"
            / self.github_sha
        )

    @property
    def repo_owner(self):
        return self._github_repository_parts[0]

    @property
    def repo_name(self):
        return self._github_repository_parts[1]

    @property
    def _github_repository_parts(self):
        owner, repo_name = self.github_repository.split("/", maxsplit=1)
        return owner, repo_name

    @model_validator(mode="after")
    def _append_subdirectory(self) -> Self:
        if self.hexdoc_subdirectory:
            self.github_pages_url /= self.hexdoc_subdirectory
        return self
