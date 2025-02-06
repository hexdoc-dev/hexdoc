from __future__ import annotations

import logging
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, Literal, Self, Sequence

from pydantic import Field, PrivateAttr, field_validator, model_validator
from pydantic.json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    SkipJsonSchema,
)
from typing_extensions import override
from yarl import URL

from hexdoc.model.base import HexdocSettings
from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils import (
    TRACE,
    PydanticOrderedSet,
    RelativePath,
    ValidationContext,
    git_root,
    load_toml_with_placeholders,
    relative_path_root,
)
from hexdoc.utils.deserialize.toml import GenerateJsonSchemaTOML
from hexdoc.utils.types import PydanticURL

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


class TemplateProps(StripHiddenModel, validate_assignment=True):
    static_dir: RelativePath | None = None
    icon: RelativePath | None = None
    include: PydanticOrderedSet[str]

    render_from: PydanticOrderedSet[str] = Field(None, validate_default=False)  # type: ignore
    """List of modids to include default rendered templates from.

    If not provided, defaults to `self.include`.
    """
    render: dict[Path, str] = Field(default_factory=dict)
    extend_render: dict[Path, str] = Field(default_factory=dict)

    redirect: tuple[Path, str] | None = (Path("index.html"), "redirect.html.jinja")
    """filename, template"""

    args: dict[str, Any]

    _was_render_set: bool = PrivateAttr(False)

    @property
    def override_default_render(self):
        return self._was_render_set

    @field_validator("include", "render_from", mode="after")
    @classmethod
    def _resolve_aliases(cls, values: PydanticOrderedSet[str] | None):
        if values:
            for alias, replacement in JINJA_NAMESPACE_ALIASES.items():
                if alias in values:
                    values.remove(alias)
                    values.add(replacement)
        return values

    @model_validator(mode="after")
    def _set_default_render_from(self):
        if self.render_from is None:  # pyright: ignore[reportUnnecessaryComparison]
            self.render_from = self.include
        return self


# TODO: support item/block override
class PNGTextureOverride(StripHiddenModel):
    url: PydanticURL
    pixelated: bool


class TextureTextureOverride(StripHiddenModel):
    texture: ResourceLocation
    """The id of an image texture (eg. `minecraft:textures/item/stick.png`)."""


class TexturesProps(StripHiddenModel):
    enabled: bool = True
    """Set to False to disable texture rendering."""
    strict: bool = True
    """Set to False to print some errors instead of throwing them."""
    missing: set[ResourceLocation] | Literal["*"] = Field(default_factory=set)
    override: dict[
        ResourceLocation,
        PNGTextureOverride | TextureTextureOverride,
    ] = Field(default_factory=dict)


class LangProps(StripHiddenModel):
    """Configuration for a specific book language."""

    quiet: bool = False
    """If `True`, do not log warnings for missing translations.

    Using this option for the default language is not recommended.
    """
    ignore_errors: bool = False
    """If `True`, log fatal errors for this language instead of failing entirely.

    Using this option for the default language is not recommended.
    """


class BaseProperties(StripHiddenModel, ValidationContext):
    env: SkipJsonSchema[EnvironmentVariableProps]
    props_dir: SkipJsonSchema[Path]

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.load_data(
            props_dir=path.parent,
            data=load_toml_with_placeholders(path),
        )

    @classmethod
    def load_data(cls, props_dir: Path, data: dict[str, Any]) -> Self:
        props_dir = props_dir.resolve()

        with relative_path_root(props_dir):
            env = EnvironmentVariableProps.model_getenv()
            props = cls.model_validate(
                data
                | {
                    "env": env,
                    "props_dir": props_dir,
                },
            )

        logger.log(TRACE, props)
        return props

    @override
    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchemaTOML,
        mode: Literal["validation", "serialization"] = "validation",
    ) -> dict[str, Any]:
        return super().model_json_schema(by_alias, ref_template, schema_generator, mode)


class Properties(BaseProperties):
    """Pydantic model for `hexdoc.toml` / `properties.toml`."""

    modid: str

    book_type: str = "patchouli"
    """Modid of the `hexdoc.plugin.BookPlugin` to use when loading this book."""

    # TODO: make another properties type without book_id
    book_id: ResourceLocation | None = Field(alias="book", default=None)
    extra_books: list[ResourceLocation] = Field(default_factory=list)

    default_lang: str = "en_us"
    default_branch: str = "main"

    is_0_black: bool = False
    """If true, the style `$(0)` changes the text color to black; otherwise it resets
    the text color to the default."""

    resource_dirs: Sequence[ResourceDir]
    export_dir: RelativePath | None = None

    entry_id_blacklist: set[ResourceLocation] = Field(default_factory=set)

    macros: dict[str, str] = Field(default_factory=dict)
    link_overrides: dict[str, str] = Field(default_factory=dict)

    textures: TexturesProps = Field(default_factory=TexturesProps)

    template: TemplateProps | None = None

    lang: defaultdict[
        str,
        Annotated[LangProps, Field(default_factory=LangProps)],
    ] = Field(default_factory=lambda: defaultdict(LangProps))
    """Per-language configuration. The key should be the language code, eg. `en_us`."""

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
