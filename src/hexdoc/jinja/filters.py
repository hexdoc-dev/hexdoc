import functools
from typing import Any, Callable, ParamSpec, TypeVar

from jinja2 import pass_context
from jinja2.runtime import Context
from markupsafe import Markup

from hexdoc.core import I18n, Properties, ResourceLocation
from hexdoc.core.resource import ItemStack
from hexdoc.graphics.validators import ItemImage, TextureImage, validate_image
from hexdoc.model.base import init_context
from hexdoc.patchouli import FormatTree
from hexdoc.plugin import PluginManager

_P = ParamSpec("_P")
_R = TypeVar("_R")


def hexdoc_pass_context(f: Callable[_P, _R]) -> Callable[_P, _R]:
    @functools.wraps(f)
    @pass_context
    def wrapper(*args: _P.args, **kwargs: _P.kwargs):
        with init_context(args[0]):
            return f(*args, **kwargs)

    return wrapper


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


@hexdoc_pass_context
@make_jinja_exceptions_suck_a_bit_less
def hexdoc_texture_image(context: Context, id: str | ResourceLocation):
    return validate_image(TextureImage, id, context)


@hexdoc_pass_context
@make_jinja_exceptions_suck_a_bit_less
def hexdoc_item_image(context: Context, id: str | ResourceLocation | ItemStack):
    return validate_image(ItemImage, id, context)


@pass_context
@make_jinja_exceptions_suck_a_bit_less
def hexdoc_smart_var(context: Context, value: Any):
    """Smart template argument filter.

    If `value` is of the form `{"variable": str(ref)}`, returns the value of the
    template variable called `ref`.

    Otherwise, returns `value` unchanged.
    """

    match value:
        case {**items} if len(items) != 1:
            return value
        case {"variable": str(ref)}:
            return context.resolve(ref)
        case _:
            return value
