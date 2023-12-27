from typing import Unpack

from hexdoc.core import ResourceLocation
from hexdoc.model import TypeTaggedTemplate
from hexdoc.utils import Inherit, InheritType, NoValue, classproperty
from pydantic import ConfigDict


class Page(TypeTaggedTemplate, type=None):
    """Base class for Patchouli page types.

    See: https://vazkiimods.github.io/Patchouli/docs/patchouli-basics/page-types
    """

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

    @classproperty
    @classmethod
    def template(cls) -> str:
        return f"pages/{cls.template_id.namespace}/{cls.template_id.path}"
