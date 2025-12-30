from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import Field, PrivateAttr, field_validator, model_validator

from hexdoc.model.strip_hidden import StripHiddenModel
from hexdoc.utils import (
    PydanticOrderedSet,
    RelativePath,
)

logger = logging.getLogger(__name__)


JINJA_NAMESPACE_ALIASES = {
    "patchouli": "hexdoc",
}


class TemplateProps(StripHiddenModel, validate_assignment=True):
    static_dir: RelativePath | None = None
    icon: RelativePath | None = None
    include: PydanticOrderedSet[str]

    render_from: PydanticOrderedSet[str] = Field(None, validate_default=False)  # pyright: ignore[reportAssignmentType]
    """List of modids to include default rendered templates from.

    If not provided, defaults to `self.include`.
    """
    render: dict[Path, str] = Field(default_factory=lambda: {})
    extend_render: dict[Path, str] = Field(default_factory=lambda: {})

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
