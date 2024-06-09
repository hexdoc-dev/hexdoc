# pyright: reportPrivateUsage=false

from __future__ import annotations

import logging
import re
from enum import Enum, auto
from fnmatch import fnmatch
from typing import Literal, Self, final

from jinja2 import pass_context
from jinja2.runtime import Context
from pydantic import ValidationInfo, model_validator
from pydantic.dataclasses import dataclass
from pydantic.functional_validators import ModelWrapValidatorHandler

from hexdoc.core import Properties, ResourceLocation
from hexdoc.minecraft import I18n, LocalizedStr
from hexdoc.model import DEFAULT_CONFIG, HexdocModel, ValidationContextModel
from hexdoc.plugin import PluginManager
from hexdoc.utils import PydanticURL, TryGetEnum, classproperty
from hexdoc.utils.json_schema import inherited, json_schema_extra_config, type_str

logger = logging.getLogger(__name__)


DEFAULT_MACROS = {
    "$(obf)": "$(k)",
    "$(bold)": "$(l)",
    "$(strike)": "$(m)",
    "$(italic)": "$(o)",
    "$(italics)": "$(o)",
    "$(list": "$(li",
    "$(reset)": "$()",
    "$(clear)": "$()",
    "$(2br)": "$(br2)",
    "$(p)": "$(br2)",
    "/$": "$()",
    "<br>": "$(br)",
    "$(nocolor)": "$(0)",
    "$(item)": "$(#b0b)",
    "$(thing)": "$(#490)",
}

_REPLACEMENTS = {
    "br": "\n",
    "playername": "[Playername]",
}

_COLORS = {
    "0": "000",
    "1": "00a",
    "2": "0a0",
    "3": "0aa",
    "4": "a00",
    "5": "a0a",
    "6": "fa0",
    "7": "aaa",
    "8": "555",
    "9": "55f",
    "a": "5f5",
    "b": "5ff",
    "c": "f55",
    "d": "f5f",
    "e": "ff5",
    "f": "fff",
}

BookLinks = dict[str, PydanticURL]


class FormattingContext(ValidationContextModel):
    book_id: ResourceLocation
    macros: dict[str, str]


class BookLink(HexdocModel):
    raw_value: str
    id: ResourceLocation
    anchor: str | None

    @classmethod
    def from_str(cls, raw_value: str, book_id: ResourceLocation) -> Self:
        # anchor
        if "#" in raw_value:
            id_str, anchor = raw_value.split("#", 1)
        else:
            id_str, anchor = raw_value, None

        # case-insensitive id of the category or entry being linked to
        # namespace defaults to the namespace of the book, not minecraft
        id_str = id_str.lower()
        if ":" in id_str:
            id = ResourceLocation.from_str(id_str)
        else:
            id = book_id.with_path(id_str)

        return cls(raw_value=raw_value, id=id, anchor=anchor)

    @property
    def as_tuple(self) -> tuple[ResourceLocation, str | None]:
        return (self.id, self.anchor)

    @property
    def book_links_key(self) -> str:
        key = str(self.id)
        if self.anchor is not None:
            key += f"#{self.anchor}"
        return key

    @property
    def fragment(self) -> str:
        return f"#{self.raw_value.replace('#', '@')}"


# Higgledy piggledy
# Old fuck Alwinfy said,
# "Eschew your typechecks and
# live with a pair,"
#
# Making poor Object do
# Re-re-re-factoring
# Till Winfy took up her
# Classical flair.


class CommandStyleType(TryGetEnum):
    """Command styles, like `$(type)`."""

    obfuscated = "k"
    bold = "l"
    strikethrough = "m"
    underline = "n"
    italic = "o"

    @classproperty
    @classmethod
    def macro_group(cls) -> str:
        return "command"


class FunctionStyleType(TryGetEnum):
    """Function styles, like `$(type:value)`."""

    tooltip = "t"
    cmd_click = "c"

    @classproperty
    @classmethod
    def macro_group(cls) -> str:
        return "function"


class SpecialStyleType(Enum):
    """Styles with no defined name, like `$(#0080ff)`, or styles which must be handled
    differently than the normal styles, like `$()`."""

    base = auto()
    paragraph = auto()
    color = auto()
    link = "l"

    @classproperty
    @classmethod
    def macro_group(cls) -> str:
        return "special"


class Style(HexdocModel, frozen=True):
    type: CommandStyleType | FunctionStyleType | SpecialStyleType

    @staticmethod
    def parse(
        style_str: str,
        book_id: ResourceLocation,
        i18n: I18n,
        is_0_black: bool,
        link_overrides: dict[str, str],
    ) -> Style | _CloseTag | str:
        # direct text replacements
        if style_str in _REPLACEMENTS:
            return _REPLACEMENTS[style_str]

        # paragraph
        if style := ParagraphStyle.try_parse(style_str):
            return style

        # commands
        if style_type := CommandStyleType.get(style_str):
            return CommandStyle(type=style_type)

        # reset color, but only if 0 is considered reset instead of black
        if style_str == "0" and not is_0_black:
            return _CloseTag(type=SpecialStyleType.color)

        # preset colors
        if style_str in _COLORS:
            return FunctionStyle(type=SpecialStyleType.color, value=_COLORS[style_str])

        # hex colors (#rgb and #rrggbb)
        if style_str.startswith("#") and len(style_str) in [4, 7]:
            return FunctionStyle(type=SpecialStyleType.color, value=style_str[1:])

        # functions
        if ":" in style_str:
            name, value = style_str.split(":", 1)

            # keys
            if name == "k":
                return str(i18n.localize_key(value))

            # links
            if name == SpecialStyleType.link.value:
                return LinkStyle.from_str(value, book_id, link_overrides)

            # all the other functions
            if style_type := FunctionStyleType.get(name):
                return FunctionStyle(type=style_type, value=value)

        # reset
        if style_str == "":
            return _CloseTag(type=SpecialStyleType.base)

        # close functions
        if style_str.startswith("/"):
            # links
            if style_str[1:] == SpecialStyleType.link.value:
                return _CloseTag(type=SpecialStyleType.link)

            # all the other functions
            if style_type := FunctionStyleType.get(style_str[1:]):
                return _CloseTag(type=style_type)

        # oopsies
        raise ValueError(f"Unhandled style: {style_str}")

    @property
    def macro(self) -> str:
        return f"{self.type.macro_group}_{self.type.name}"


def is_external_link(value: str) -> bool:
    return value.startswith(("https:", "http:"))


class CommandStyle(Style, frozen=True):
    type: CommandStyleType | Literal[SpecialStyleType.base]


class ParagraphStyleSubtype(Enum):
    paragraph = auto()
    list_item = auto()


class ParagraphStyle(Style, frozen=True):
    type: Literal[SpecialStyleType.paragraph] = SpecialStyleType.paragraph
    subtype: ParagraphStyleSubtype

    @classmethod
    def try_parse(cls, style_str: str) -> ParagraphStyle | None:
        if style_str == "br2":
            return cls.paragraph()

        # https://github.com/VazkiiMods/Patchouli/blob/4522fbb3e4/Xplat/src/main/java/vazkii/patchouli/client/book/text/BookTextParser.java#L346-L355
        if re.fullmatch(r"li\d?", style_str):
            level_str = style_str.removeprefix("li")
            level = int(level_str) if level_str.isnumeric() else 1
            return ListItemStyle(level=level)

    @classmethod
    def paragraph(cls):
        return ParagraphStyle(subtype=ParagraphStyleSubtype.paragraph)

    @property
    def macro(self) -> str:
        return f"paragraph_{self.subtype.name}"


class ListItemStyle(ParagraphStyle, frozen=True):
    subtype: Literal[ParagraphStyleSubtype.list_item] = ParagraphStyleSubtype.list_item
    level: int


class FunctionStyle(Style, frozen=True):
    type: FunctionStyleType | Literal[SpecialStyleType.color]
    value: str


class LinkStyle(Style, frozen=True):
    type: Literal[SpecialStyleType.link] = SpecialStyleType.link
    value: str | BookLink
    external: bool

    @classmethod
    def from_str(
        cls,
        raw_value: str,
        book_id: ResourceLocation,
        link_overrides: dict[str, str],
    ) -> Self:
        value = raw_value
        external = False

        for link, override in link_overrides.items():
            if fnmatch(value, link):
                value = override
                break

        if is_external_link(value):
            external = True
        elif not value.startswith("?"):  # TODO: support query params in BookLink
            value = BookLink.from_str(value, book_id)

        return cls(value=value, external=external)

    @pass_context
    def href(self, context: Context | dict[{"book_links": BookLinks}]):  # noqa
        match self.value:
            case str(href):
                return href
            case BookLink(book_links_key=key) as book_link:
                book_links: BookLinks = context["book_links"]
                if key not in book_links:
                    logger.debug(f"{key=}\n{book_link=}\n{book_links=}")
                    raise ValueError(f"broken link: {book_link}")
                return str(book_links[key])


# intentionally not inheriting from Style, because this is basically an implementation
# detail of the parser and should not be returned or exposed anywhere
class _CloseTag(HexdocModel, frozen=True):
    type: (
        FunctionStyleType
        | Literal[
            SpecialStyleType.link,
            SpecialStyleType.base,
            SpecialStyleType.color,
        ]
    )


STYLE_REGEX = re.compile(r"\$\(([^)]*)\)")


@final
@dataclass(config=DEFAULT_CONFIG | json_schema_extra_config(type_str, inherited))
class FormatTree:
    style: Style
    children: list[FormatTree | str]  # this can't be Self, it breaks Pydantic
    raw: str | None = None

    @classmethod
    def format(
        cls,
        string: str,
        *,
        book_id: ResourceLocation,
        i18n: I18n,
        macros: dict[str, str],
        is_0_black: bool,
        pm: PluginManager,
        link_overrides: dict[str, str],
    ) -> Self:
        for macro, replace in macros.items():
            if macro in replace:
                raise RuntimeError(
                    f"Recursive macro: replacement `{replace}` is matched by key `{macro}`"
                )

        working_string = resolve_macros(string, macros)

        # lex out parsed styles
        text_nodes: list[str] = []
        styles: list[Style | _CloseTag] = []
        text_since_prev_style: list[str] = []
        last_end = 0

        for match in re.finditer(STYLE_REGEX, working_string):
            # get the text between the previous match and here
            leading_text = working_string[last_end : match.start()]
            text_since_prev_style.append(leading_text)
            last_end = match.end()

            match Style.parse(match[1], book_id, i18n, is_0_black, link_overrides):
                case str(replacement):
                    # str means "use this instead of the original value"
                    text_since_prev_style.append(replacement)
                case Style() | _CloseTag() as style:
                    # add this style and collect the text since the previous one
                    styles.append(style)
                    text_nodes.append("".join(text_since_prev_style))
                    text_since_prev_style.clear()

        text_nodes.append("".join(text_since_prev_style) + working_string[last_end:])
        first_node = text_nodes.pop(0)

        # parse
        style_stack = [
            FormatTree(CommandStyle(type=SpecialStyleType.base), []),
            FormatTree(ParagraphStyle.paragraph(), [first_node]),
        ]
        for style, text in zip(styles, text_nodes):
            tmp_stylestack: list[Style] = []
            if style.type == SpecialStyleType.base:
                while style_stack[-1].style.type != SpecialStyleType.paragraph:
                    last_node = style_stack.pop()
                    style_stack[-1].children.append(last_node)
            elif any(tree.style.type == style.type for tree in style_stack):
                while len(style_stack) >= 2:
                    last_node = style_stack.pop()
                    style_stack[-1].children.append(last_node)
                    if last_node.style.type == style.type:
                        break
                    tmp_stylestack.append(last_node.style)

            for sty in tmp_stylestack:
                style_stack.append(FormatTree(sty, []))

            if isinstance(style, _CloseTag):
                if text:
                    style_stack[-1].children.append(text)
            else:
                style_stack.append(FormatTree(style, [text] if text else []))

        while len(style_stack) >= 2:
            last_node = style_stack.pop()
            style_stack[-1].children.append(last_node)

        unvalidated_tree = style_stack[0]
        unvalidated_tree.raw = string

        validated_tree = pm.validate_format_tree(
            tree=unvalidated_tree,
            macros=macros,
            book_id=book_id,
            i18n=i18n,
            is_0_black=is_0_black,
            link_overrides=link_overrides,
        )
        assert isinstance(validated_tree, cls)

        return validated_tree

    @model_validator(mode="wrap")
    @classmethod
    def _wrap_root(
        cls,
        value: str | LocalizedStr | Self,
        handler: ModelWrapValidatorHandler[Self],
        info: ValidationInfo,
    ):
        if not info.context or isinstance(value, FormatTree):
            return handler(value)

        context = FormattingContext.of(info)
        i18n = I18n.of(info)
        pm = PluginManager.of(info)
        props = Properties.of(info)

        if isinstance(value, str):
            value = i18n.localize(value)

        return cls.format(
            value.value,
            book_id=context.book_id,
            i18n=i18n,
            macros=context.macros,
            is_0_black=props.is_0_black,
            pm=pm,
            link_overrides=props.link_overrides,
        )


def resolve_macros(string: str, macros: dict[str, str]) -> str:
    # this could use ahocorasick, but it works fine for now
    old_string = None
    while old_string != string:
        old_string = string
        for macro, replace in macros.items():
            string = string.replace(macro, replace)
    return string
