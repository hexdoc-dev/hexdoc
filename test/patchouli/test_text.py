# pyright: reportPrivateUsage=false
from argparse import Namespace
from typing import Any, cast

import pytest
from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft import I18n
from hexdoc.patchouli.text import (
    DEFAULT_MACROS,
    BookLink,
    CommandStyle,
    FormatTree,
    FunctionStyle,
    LinkStyle,
    ParagraphStyle,
    SpecialStyleType,
)
from hexdoc.plugin import PluginManager
from jinja2 import Environment, PackageLoader


class MockPluginManager:
    def validate_format_tree(self, tree: FormatTree, *_: Any, **__: Any):
        return tree


def format_with_mocks(
    test_str: str,
    macros: dict[str, str] = {},
    link_overrides: dict[str, str] = {},
):
    return FormatTree.format(
        test_str,
        book_id=ResourceLocation("hexcasting", "thehexbook"),
        i18n=cast(I18n, Namespace(keys={})),
        macros=DEFAULT_MACROS | macros,
        is_0_black=False,
        pm=cast(PluginManager, MockPluginManager()),
        link_overrides=link_overrides,
    )


def flatten_html(html: str):
    return "".join(line.lstrip() for line in html.splitlines())


def hexdoc_block(value: FormatTree):
    loader = PackageLoader("hexdoc", "_templates")
    env = Environment(loader=loader)
    template = env.from_string(
        """\
        {%- import "macros/formatting.html.jinja" as fmt with context -%}
        {{- fmt.styled(value) -}}
        """
    )
    return template.render(value=value)


def test_link():
    tree = format_with_mocks("$(l:http://google.com)A$(/l)")
    assert (
        hexdoc_block(tree) == '<p><a href="http://google.com" target="_blank">A</a></p>'
    )


def test_link_in_color():
    tree = format_with_mocks(
        "$(1)A$(l:http://google.com)B$(/l)C/$",
        {"$(1)": "$(#111)"},
    )
    html = hexdoc_block(tree)

    assert html == flatten_html(
        """<p>
            <span style="color: #111">
                A
                <a href="http://google.com" target="_blank">
                    B
                </a>
                C
            </span>
        </p>"""
    )


@pytest.mark.skip("Currently failing, the parser needs a fix")
def test_colors_across_link():
    tree = format_with_mocks(
        "$(1)A$(l:http://google.com)B$(2)C$(1)D$(/l)E/$",
        {"$(1)": "$(#111)", "$(2)": "$(#222)"},
    )
    html = hexdoc_block(tree)

    assert html == flatten_html(
        """<p>
            <span style="color: #111">
                A
            </span>
            <a href="http://google.com" target="_blank">
                <span style="color: #222">
                    C
                </span>
                <span style="color: #111">
                    D
                </span>
            </a>
            <span style="color: #111">
                E
            </span>
        </p>"""
    )


def test_format_string():
    tree = format_with_mocks(
        "Write the given iota to my $(l:patterns/readwrite#hexcasting:write/local)$(#490)local$().$(br)The $(l:patterns/readwrite#hexcasting:write/local)$(#490)local$() is a lot like a $(l:items/focus)$(#b0b)Focus$(). It's cleared when I stop casting a Hex, starts with $(l:casting/influences)$(#490)Null$() in it, and is preserved between casts of $(l:patterns/meta#hexcasting:for_each)$(#fc77be)Thoth's Gambit$(). ",
        link_overrides={"casting/*": "https://example.com"},
    )

    assert tree == FormatTree(
        style=CommandStyle(type=SpecialStyleType.base),
        children=[
            FormatTree(
                style=ParagraphStyle.paragraph(),
                children=[
                    "Write the given iota to my ",
                    FormatTree(
                        style=LinkStyle(
                            value=BookLink.from_str(
                                "patterns/readwrite#hexcasting:write/local",
                                ResourceLocation("hexcasting", "thehexbook"),
                            ),
                            external=False,
                        ),
                        children=[
                            FormatTree(
                                style=FunctionStyle(
                                    type=SpecialStyleType.color,
                                    value="490",
                                ),
                                children=["local"],
                            )
                        ],
                    ),
                    ".\nThe ",
                    FormatTree(
                        style=LinkStyle(
                            value=BookLink.from_str(
                                "patterns/readwrite#hexcasting:write/local",
                                ResourceLocation("hexcasting", "thehexbook"),
                            ),
                            external=False,
                        ),
                        children=[
                            FormatTree(
                                style=FunctionStyle(
                                    type=SpecialStyleType.color,
                                    value="490",
                                ),
                                children=["local"],
                            )
                        ],
                    ),
                    " is a lot like a ",
                    FormatTree(
                        style=LinkStyle(
                            value=BookLink.from_str(
                                "items/focus",
                                ResourceLocation("hexcasting", "thehexbook"),
                            ),
                            external=False,
                        ),
                        children=[
                            FormatTree(
                                style=FunctionStyle(
                                    type=SpecialStyleType.color,
                                    value="b0b",
                                ),
                                children=["Focus"],
                            )
                        ],
                    ),
                    ". It's cleared when I stop casting a Hex, starts with ",
                    FormatTree(
                        style=LinkStyle(
                            value="https://example.com",
                            external=True,
                        ),
                        children=[
                            FormatTree(
                                style=FunctionStyle(
                                    type=SpecialStyleType.color,
                                    value="490",
                                ),
                                children=["Null"],
                            )
                        ],
                    ),
                    " in it, and is preserved between casts of ",
                    FormatTree(
                        style=LinkStyle(
                            value=BookLink.from_str(
                                "patterns/meta#hexcasting:for_each",
                                ResourceLocation("hexcasting", "thehexbook"),
                            ),
                            external=False,
                        ),
                        children=[
                            FormatTree(
                                style=FunctionStyle(
                                    type=SpecialStyleType.color,
                                    value="fc77be",
                                ),
                                children=["Thoth's Gambit"],
                            )
                        ],
                    ),
                    ". ",
                ],
            )
        ],
    )


def test_broken_link_fails_without_override():
    style = LinkStyle.from_str(
        "link",
        book_id=ResourceLocation("namespace", "path"),
        link_overrides={},
    )

    with pytest.raises(ValueError):
        style.href({"link_bases": {}})


def test_broken_link_uses_override():
    style = LinkStyle.from_str(
        "link",
        book_id=ResourceLocation("namespace", "path"),
        link_overrides={"link": "https://example.com"},
    )

    href = style.href({"link_bases": {}})

    assert href == "https://example.com"


def test_wildcard_link_override():
    style = LinkStyle.from_str(
        "foo/bar",
        book_id=ResourceLocation("namespace", "path"),
        link_overrides={"foo*": "https://example.com"},
    )

    href = style.href({"link_bases": {}})

    assert href == "https://example.com"


def test_wildcard_link_override_not_matching():
    style = LinkStyle.from_str(
        "https://example.ca",
        book_id=ResourceLocation("namespace", "path"),
        link_overrides={"foo*": "https://example.com"},
    )

    href = style.href({"link_bases": {}})

    assert href == "https://example.ca"
