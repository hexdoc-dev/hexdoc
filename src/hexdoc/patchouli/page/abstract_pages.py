from typing import Any, Self, Unpack

from pydantic import ConfigDict, model_validator
from pydantic.functional_validators import ModelWrapValidatorHandler

from hexdoc.core import ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.model import TypeTaggedTemplate
from hexdoc.utils import Inherit, InheritType, NoValue, classproperty

from ..text import FormatTree


class Page(TypeTaggedTemplate, type=None):
    """Base class for Patchouli page types.

    See: https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/page-types
    """

    advancement: ResourceLocation | None = None
    flag: str | None = None
    anchor: str | None = None

    def __init_subclass__(
        cls,
        *,
        type: str | InheritType | None = Inherit,
        template_type: str | None = None,
        **kwargs: Unpack[ConfigDict],
    ) -> None:
        super().__init_subclass__(type=type, template_type=template_type, **kwargs)

    @classproperty
    @classmethod
    def type(cls) -> ResourceLocation | None:
        assert cls._type is not NoValue
        return cls._type

    @model_validator(mode="wrap")
    @classmethod
    def _pre_root(cls, value: str | Any, handler: ModelWrapValidatorHandler[Self]):
        if isinstance(value, str):
            return handler({"type": "patchouli:text", "text": value})
        return handler(value)

    @classproperty
    @classmethod
    def template(cls) -> str:
        return f"pages/{cls.template_id.namespace}/{cls.template_id.path}"


class PageWithText(Page, type=None):
    """Base class for a `Page` with optional text.

    If text is required, do not subclass this type.
    """

    text: FormatTree | None = None


class PageWithTitle(PageWithText, type=None):
    """Base class for a `Page` with optional title and text.

    If title and/or text is required, do not subclass this type.
    """

    title: LocalizedStr | None = None
