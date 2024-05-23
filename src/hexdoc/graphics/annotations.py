from contextvars import ContextVar
from typing import Annotated, Any, TypeVar

from pydantic import BeforeValidator, ValidationError, ValidationInfo, WrapValidator
from pydantic.functional_validators import ModelWrapValidatorHandler

from hexdoc.utils.contextmanagers import set_contextvar

from .validators import (
    HexdocImage,
    ItemImage as ItemImageType,
    MissingImage,
    TagImage as TagImageType,
    TextureImage as TextureImageType,
)

_T_HexdocImage = TypeVar("_T_HexdocImage", bound=HexdocImage[Any])

_is_annotated_contextvar = ContextVar("_is_annotated_contextvar", default=False)


def _validate_image_field(
    value: Any,
    handler: ModelWrapValidatorHandler[Any],
    info: ValidationInfo,
):
    try:
        with set_contextvar(_is_annotated_contextvar, True):
            return handler(value)
    except ValidationError:
        missing = MissingImage.model_validate(value, context=info.context)
        return missing


def _assert_annotated(model_type: type[_T_HexdocImage]):
    def validator(value: Any, info: ValidationInfo):
        if not _is_annotated_contextvar.get():
            field_name = f" (field: {info.field_name})" if info.field_name else ""
            raise RuntimeError(
                f"{model_type.__name__}{field_name} must be wrapped with ImageField"
            )
        return value

    return BeforeValidator(validator)


ImageField = Annotated[
    _T_HexdocImage | MissingImage,
    WrapValidator(_validate_image_field),
]

ItemImage = Annotated[ItemImageType, _assert_annotated(ItemImageType)]
TagImage = Annotated[TagImageType, _assert_annotated(TagImageType)]
TextureImage = Annotated[TextureImageType, _assert_annotated(TextureImageType)]
