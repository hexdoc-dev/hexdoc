from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import AfterValidator, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import ResourceDir
from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils.cd import RelativePath, relative_path_root
from hexdoc.utils.deserialize.toml import load_toml_with_placeholders

NoTrailingSlashHttpUrl = Annotated[
    str,
    HttpUrl,
    AfterValidator(lambda u: str(u).rstrip("/")),
]


class EnvironmentVariableProps(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # default Actions environment variables
    github_repository: str
    github_sha: str

    # set by CI
    github_pages_url: NoTrailingSlashHttpUrl

    # optional for debugging
    debug_githubusercontent: str | None = None

    @classmethod
    def model_validate_env(cls):
        return cls.model_validate({})

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


class TemplateProps(StripHiddenModel):
    static_dir: RelativePath | None = None
    include: list[str]

    render: dict[Path, str] = Field(
        default_factory=lambda: {
            "index.html": "index.html.jinja",
            "index.css": "index.css.jinja",
            "textures.css": "textures.jcss.jinja",
            "index.js": "index.js.jinja",
        },
        validate_default=True,
    )
    extend_render: dict[Path, str] | None = None

    args: dict[str, Any]

    @model_validator(mode="after")
    def _merge_extend_render(self):
        if self.extend_render:
            self.render |= self.extend_render
        return self


class MinecraftAssetsProps(StripHiddenModel):
    ref: str
    version: str


class GaslightingProps(StripHiddenModel):
    id: str
    variants: int


class TexturesProps(StripHiddenModel):
    missing: list[ResourceLocation] = Field(default_factory=list)
    override: dict[ResourceLocation, ResourceLocation] = Field(default_factory=dict)
    gaslighting: dict[ResourceLocation, GaslightingProps] = Field(default_factory=dict)


class BaseProperties(StripHiddenModel):
    env: EnvironmentVariableProps
    props_dir: Path

    @classmethod
    def load(cls, path: Path) -> Self:
        props_dir = path.parent

        with relative_path_root(props_dir):
            env = EnvironmentVariableProps.model_validate_env()
            props = cls.model_validate(
                load_toml_with_placeholders(path)
                | {
                    "env": env,
                    "props_dir": props_dir,
                },
            )

        logging.getLogger(__name__).debug(props)
        return props


class Properties(BaseProperties):
    modid: str
    book: ResourceLocation | None
    default_lang: str
    is_0_black: bool = Field(default=False)
    """If true, the style `$(0)` changes the text color to black; otherwise it resets
    the text color to the default."""

    resource_dirs: list[ResourceDir]
    export_dir: RelativePath | None = None

    entry_id_blacklist: set[ResourceLocation] = Field(default_factory=set)

    minecraft_assets: MinecraftAssetsProps

    # FIXME: remove this and get the data from the actual model files
    textures: TexturesProps = Field(default_factory=TexturesProps)

    template: TemplateProps | None

    extra: dict[str, Any] = Field(default_factory=dict)

    def mod_loc(self, path: str) -> ResourceLocation:
        """Returns a ResourceLocation with self.modid as the namespace."""
        return ResourceLocation(self.modid, path)

    @property
    def url(self):
        return self.env.github_pages_url