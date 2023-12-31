from typing import Any, Generic, Self, TypeVar, Unpack

from pydantic import ConfigDict, model_validator
from pydantic.functional_validators import ModelWrapValidatorHandler

from hexdoc.core import ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.minecraft.recipe import Recipe
from hexdoc.model import TypeTaggedTemplate
from hexdoc.utils import Inherit, InheritType, NoValue, classproperty

from ..flag import FlagExpression
from ..text import FormatTree

_T_Recipe = TypeVar("_T_Recipe", bound=Recipe)


class Page(TypeTaggedTemplate, type=None):
    """Base class for Patchouli page types.

    See: https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/page-types
    """

    advancement: ResourceLocation | None = None
    flag: FlagExpression | None = None
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
        match value:
            case str(text):
                # treat a plain string as a text page
                value = {"type": "patchouli:text", "text": text}
            case {"type": str(raw_type)} if ":" not in raw_type:
                # default to the patchouli namespace if not specified
                # see: https://github.com/VazkiiMods/Patchouli/blob/b87e91a5a08d/Xplat/src/main/java/vazkii/patchouli/client/book/ClientBookRegistry.java#L110
                value["type"] = f"patchouli:{raw_type}"
            case _:
                pass
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


class PageWithDoubleRecipe(PageWithTitle, Generic[_T_Recipe], type=None):
    recipe: _T_Recipe
    recipe2: _T_Recipe | None = None

    @property
    def recipes(self) -> list[_T_Recipe]:
        return [r for r in [self.recipe, self.recipe2] if r is not None]
