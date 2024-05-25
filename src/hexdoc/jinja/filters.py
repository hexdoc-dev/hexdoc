import functools
from typing import Callable, ParamSpec, TypeVar

from jinja2 import pass_context
from jinja2.runtime import Context
from markupsafe import Markup

from hexdoc.core import I18n, Properties, ResourceLocation
from hexdoc.core.resource import ItemStack
from hexdoc.graphics.validators import (
    ItemImage,
    MissingImage,
    TextureImage,
    validate_image,
)
from hexdoc.patchouli import FormatTree
from hexdoc.plugin import PluginManager

_P = ParamSpec("_P")
_R = TypeVar("_R")


def make_jinja_exceptions_suck_a_bit_less(f: Callable[_P, _R]) -> Callable[_P, _R]:
    @functools.wraps(f)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            args_ = list(args)
            if args_ and isinstance(args_[0], Context):
                args_ = args_[1:]

            e.add_note(f"args:   {args_}")
            e.add_note(f"kwargs: {kwargs}")
            raise

    return wrapper


# filters


@make_jinja_exceptions_suck_a_bit_less
def hexdoc_wrap(value: str, *args: str):
    tag, *attributes = args
    if attributes:
        attributes = " " + " ".join(attributes)
    else:
        attributes = ""
    return Markup(f"<{tag}{attributes}>{Markup.escape(value)}</{tag}>")


# aliased as _() and _f() at render time
@make_jinja_exceptions_suck_a_bit_less
def hexdoc_localize(
    key: str,
    *,
    do_format: bool,
    props: Properties,
    book_id: ResourceLocation,
    i18n: I18n,
    macros: dict[str, str],
    pm: PluginManager,
):
    # get the localized value from i18n
    localized = i18n.localize(key)

    if not do_format:
        return Markup(localized.value)

    # construct a FormatTree from the localized value (to allow using patchi styles)
    formatted = FormatTree.format(
        localized.value,
        book_id=book_id,
        i18n=i18n,
        macros=macros,
        is_0_black=props.is_0_black,
        pm=pm,
        link_overrides=props.link_overrides,
    )
    return formatted


# TODO: rename to hexdoc_texture_url
@pass_context
@make_jinja_exceptions_suck_a_bit_less
def hexdoc_texture(context: Context, id: str | ResourceLocation) -> str:
    image = validate_image(TextureImage, id, context)
    return str(image.url)


@pass_context
@make_jinja_exceptions_suck_a_bit_less
def hexdoc_item(
    context: Context,
    id: str | ResourceLocation | ItemStack,
) -> ItemImage | MissingImage:
    return validate_image(ItemImage, id, context)
