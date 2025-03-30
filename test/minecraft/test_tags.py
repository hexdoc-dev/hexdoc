# pyright: reportPrivateUsage=none

import textwrap

import pytest
from hexdoc.core.resource import ResourceLocation
from hexdoc.minecraft.tags import OptionalTagValue, Tag, TagValue
from hexdoc.utils.types import PydanticOrderedSet


@pytest.mark.parametrize(
    ["raw_data", "want_values"],
    [
        (
            """\
            {
                "values": []
            }
            """,
            [],
        ),
        (
            """\
            {
                "values": [
                    "minecraft:stone"
                ]
            }
            """,
            [
                ResourceLocation("minecraft", "stone"),
            ],
        ),
        (
            """\
            {
                "values": [
                    {"id": "minecraft:stone", "required": false}
                ]
            }
            """,
            [
                OptionalTagValue(
                    id=ResourceLocation("minecraft", "stone"),
                    required=False,
                ),
            ],
        ),
        (
            """\
            {
                "values": [
                    "hextweaks:infusion",
                    "hextweaks:nuke_chunk_nowill",
                    {"id": "hextweaks:you_like_drinking_potions","required": false}
                ]
            }
            """,
            [
                ResourceLocation("hextweaks", "infusion"),
                ResourceLocation("hextweaks", "nuke_chunk_nowill"),
                OptionalTagValue(
                    id=ResourceLocation("hextweaks", "you_like_drinking_potions"),
                    required=False,
                ),
            ],
        ),
    ],
)
def test_load_tag_file(raw_data: str, want_values: list[TagValue]):
    tag = Tag._convert(
        registry="",
        raw_data=textwrap.dedent(raw_data),
    )
    assert list(tag.values) == want_values


@pytest.mark.parametrize(
    ["values", "replace", "current_values", "want_data"],
    [
        (
            [],
            False,
            None,
            """{"values":[],"replace":false}""",
        ),
        (
            [],
            False,
            [],
            """{"values":[],"replace":false}""",
        ),
        (
            [ResourceLocation("minecraft", "stone")],
            False,
            None,
            """{"values":["minecraft:stone"],"replace":false}""",
        ),
        (
            [],
            False,
            [ResourceLocation("minecraft", "stone")],
            """{"values":["minecraft:stone"],"replace":false}""",
        ),
        (
            [ResourceLocation("minecraft", "dirt")],
            False,
            [ResourceLocation("minecraft", "stone")],
            """{"values":["minecraft:stone","minecraft:dirt"],"replace":false}""",
        ),
        (
            [],
            True,
            [ResourceLocation("minecraft", "stone")],
            """{"values":[],"replace":true}""",
        ),
        (
            [ResourceLocation("minecraft", "dirt")],
            True,
            [ResourceLocation("minecraft", "stone")],
            """{"values":["minecraft:dirt"],"replace":true}""",
        ),
        (
            [
                OptionalTagValue(
                    id=ResourceLocation("minecraft", "stone"),
                    required=True,
                ),
            ],
            False,
            None,
            """{"values":[{"id":"minecraft:stone","required":true}],"replace":false}""",
        ),
        (
            [
                OptionalTagValue(
                    id=ResourceLocation("minecraft", "stone"),
                    required=False,
                ),
            ],
            False,
            None,
            """{"values":[{"id":"minecraft:stone","required":false}],"replace":false}""",
        ),
        (
            [],
            False,
            [
                OptionalTagValue(
                    id=ResourceLocation("minecraft", "stone"),
                    required=True,
                ),
            ],
            """{"values":[{"id":"minecraft:stone","required":true}],"replace":false}""",
        ),
        (
            [],
            False,
            [
                OptionalTagValue(
                    id=ResourceLocation("minecraft", "stone"),
                    required=False,
                ),
            ],
            """{"values":[{"id":"minecraft:stone","required":false}],"replace":false}""",
        ),
        # (
        #     """\
        #     {
        #         "values": [
        #             "minecraft:stone"
        #         ]
        #     }
        #     """,
        #     [
        #         ResourceLocation("minecraft", "stone"),
        #     ],
        # ),
        # (
        #     """\
        #     {
        #         "values": [
        #             {"id": "minecraft:stone", "required": false}
        #         ]
        #     }
        #     """,
        #     [
        #         OptionalTagValue(
        #             id=ResourceLocation("minecraft", "stone"),
        #             required=False,
        #         ),
        #     ],
        # ),
        # (
        #     """\
        #     {
        #         "values": [
        #             "hextweaks:infusion",
        #             "hextweaks:nuke_chunk_nowill",
        #             {"id": "hextweaks:you_like_drinking_potions","required": false}
        #         ]
        #     }
        #     """,
        #     [
        #         ResourceLocation("hextweaks", "infusion"),
        #         ResourceLocation("hextweaks", "nuke_chunk_nowill"),
        #         OptionalTagValue(
        #             id=ResourceLocation("hextweaks", "you_like_drinking_potions"),
        #             required=False,
        #         ),
        #     ],
        # ),
    ],
)
def test_export_tag(
    values: list[TagValue],
    replace: bool,
    current_values: list[TagValue] | None,
    want_data: str,
):
    tag = Tag(
        registry="",
        values=PydanticOrderedSet(values),
        replace=replace,
    )

    if current_values is not None:
        current = Tag(registry="", values=PydanticOrderedSet(current_values))
    else:
        current = None

    assert tag._export(current) == want_data
