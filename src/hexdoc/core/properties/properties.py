from __future__ import annotations

import logging
from collections import defaultdict
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, Literal, Self, Sequence

from pydantic import Field
from pydantic.json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    SkipJsonSchema,
)
from typing_extensions import override

from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils import (
    TRACE,
    RelativePath,
    ValidationContext,
    git_root,
    load_toml_with_placeholders,
    relative_path_root,
)
from hexdoc.utils.deserialize.toml import GenerateJsonSchemaTOML

from ..resource import ResourceLocation
from ..resource_dir import ResourceDir
from .env import EnvironmentVariableProps
from .lang import LangProps
from .template import TemplateProps
from .textures import TexturesProps

logger = logging.getLogger(__name__)


# TODO: why is this a separate class?
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

    textures: TexturesProps = Field(default_factory=lambda: TexturesProps())

    template: TemplateProps | None = None

    lang: defaultdict[
        str,
        Annotated[LangProps, Field(default_factory=lambda: LangProps())],
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
