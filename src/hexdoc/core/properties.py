from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import Any, Self, Sequence

from pydantic import Field, PrivateAttr, field_validator

from hexdoc.model.base import HexdocSettings
from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils import (
    NoTrailingSlashHttpUrl,
    PydanticOrderedSet,
    RelativePath,
    git_root,
    load_toml_with_placeholders,
    relative_path_root,
)

from .resource import ResourceLocation
from .resource_dir import ResourceDir

logger = logging.getLogger(__name__)

JINJA_NAMESPACE_ALIASES = {
    "patchouli": "hexdoc",
}


class EnvironmentVariableProps(HexdocSettings):
    # default Actions environment variables
    github_repository: str
    github_sha: str

    # set by CI
    github_pages_url: NoTrailingSlashHttpUrl

    # optional for debugging
    debug_githubusercontent: str | None = None

    @property
    def asset_url(self):
        if self.debug_githubusercontent is not None:
            return self.debug_githubusercontent

        return (
            f"https://raw.githubusercontent.com"
            f"/{self.repo_owner}/{self.repo_name}/{self.github_sha}"
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


class TemplateProps(StripHiddenModel, validate_assignment=True):
    static_dir: RelativePath | None = None
    icon: RelativePath
    include: PydanticOrderedSet[str]

    render: dict[Path, str] = Field(default_factory=dict)
    extend_render: dict[Path, str] = Field(default_factory=dict)

    redirect: tuple[Path, str] = (Path("index.html"), "redirect.html.jinja")
    """filename, template"""

    args: dict[str, Any]

    _was_render_set: bool = PrivateAttr(False)

    @property
    def override_default_render(self):
        return self._was_render_set

    @field_validator("include", mode="after")
    @classmethod
    def _resolve_aliases(cls, values: PydanticOrderedSet[str]):
        for alias, replacement in JINJA_NAMESPACE_ALIASES.items():
            if alias in values:
                values.remove(alias)
                values.add(replacement)
        return values


class TexturesProps(StripHiddenModel):
    missing: set[ResourceLocation] = Field(default_factory=set)
    override: dict[ResourceLocation, ResourceLocation] = Field(default_factory=dict)


class BaseProperties(StripHiddenModel):
    env: EnvironmentVariableProps
    props_dir: Path

    @classmethod
    def load(cls, path: Path) -> Self:
        path = path.resolve()
        props_dir = path.parent

        with relative_path_root(props_dir):
            env = EnvironmentVariableProps.model_getenv()
            props = cls.model_validate(
                load_toml_with_placeholders(path)
                | {
                    "env": env,
                    "props_dir": props_dir,
                },
            )

        logger.debug(props)
        return props


class Properties(BaseProperties):
    """Pydantic model for `hexdoc.toml` / `properties.toml`."""

    modid: str
    # TODO: make another properties type without book_id
    book_id: ResourceLocation | None = Field(alias="book", default=None)
    extra_books: list[ResourceLocation] = Field(default_factory=list)
    default_lang: str
    default_branch: str

    is_0_black: bool = False
    """If true, the style `$(0)` changes the text color to black; otherwise it resets
    the text color to the default."""

    resource_dirs: Sequence[ResourceDir]
    export_dir: RelativePath | None = None

    entry_id_blacklist: set[ResourceLocation] = Field(default_factory=set)

    textures: TexturesProps = Field(default_factory=TexturesProps)

    template: TemplateProps | None = None

    extra: dict[str, Any] = Field(default_factory=dict)

    def mod_loc(self, path: str) -> ResourceLocation:
        """Returns a ResourceLocation with self.modid as the namespace."""
        return ResourceLocation(self.modid, path)

    @property
    def prerender_dir(self):
        return self.cache_dir / "prerender"

    @property
    def cache_dir(self):
        return self.repo_root / ".hexdoc"

    @cached_property
    def repo_root(self):
        return git_root(self.props_dir)
