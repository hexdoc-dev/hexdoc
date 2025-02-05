import pytest
from hexdoc.core.resource import AssumeTag, ItemStack, ResLoc, ResourceLocation
from pydantic import TypeAdapter

resource_locations: list[tuple[str, ResourceLocation, str]] = [
    (
        "stone",
        ResLoc("minecraft", "stone"),
        "minecraft:",
    ),
    (
        "hexcasting:patchouli_book",
        ResLoc("hexcasting", "patchouli_book"),
        "",
    ),
]


@pytest.mark.parametrize("s,expected,str_prefix", resource_locations)
def test_resourcelocation(s: str, expected: ResourceLocation, str_prefix: str):
    actual = ResourceLocation.from_str(s)
    assert actual == expected
    assert str(actual) == str_prefix + s


item_stacks: list[tuple[str, ItemStack, str, str | None]] = [
    (
        "stone",
        ItemStack("minecraft", "stone", None, None),
        "minecraft:",
        None,
    ),
    (
        "hexcasting:patchouli_book",
        ItemStack("hexcasting", "patchouli_book", None, None),
        "",
        None,
    ),
    (
        "minecraft:stone#64",
        ItemStack("minecraft", "stone", 64, None),
        "",
        None,
    ),
    (
        "minecraft:diamond_pickaxe{display:{Lore:['A really cool pickaxe']}}",
        ItemStack(
            "minecraft",
            "diamond_pickaxe",
            None,
            "{display:{Lore:['A really cool pickaxe']}}",
        ),
        "",
        None,
    ),
    (
        "minecraft:diamond_pickaxe#64{display:{Lore:['A really cool pickaxe']}}",
        ItemStack(
            "minecraft",
            "diamond_pickaxe",
            64,
            "{display:{Lore:['A really cool pickaxe']}}",
        ),
        "",
        None,
    ),
    (
        """minecraft:diamond_pickaxe{display:{Name:'{"text": "foo"}'}}""",
        ItemStack(
            "minecraft",
            "diamond_pickaxe",
            None,
            """{display:{Name:'{"text": "foo"}'}}""",
        ),
        "",
        "foo",
    ),
    (
        """minecraft:diamond_pickaxe{display:{Name:'{"text": "foo}'}}""",
        ItemStack(
            "minecraft",
            "diamond_pickaxe",
            None,
            """{display:{Name:'{"text": "foo}'}}""",
        ),
        "",
        None,
    ),
    (
        """minecraft:diamond_pickaxe{displayy:{Name:'{"text": "foo"}'}}""",
        ItemStack(
            "minecraft",
            "diamond_pickaxe",
            None,
            """{displayy:{Name:'{"text": "foo"}'}}""",
        ),
        "",
        None,
    ),
    (
        """minecraft:diamond_pickaxe{display:{Namee:'{"text": "foo"}'}}""",
        ItemStack(
            "minecraft",
            "diamond_pickaxe",
            None,
            """{display:{Namee:'{"text": "foo"}'}}""",
        ),
        "",
        None,
    ),
]


@pytest.mark.parametrize("s,expected,str_prefix,name", item_stacks)
def test_itemstack(s: str, expected: ItemStack, str_prefix: str, name: str | None):
    actual = ItemStack.from_str(s)
    assert actual == expected
    assert str(actual) == str_prefix + s
    assert actual.get_name() == name


@pytest.mark.parametrize(
    ["type", "value", "want_is_tag"],
    [
        [ResourceLocation, "namespace:path", False],
        [ResourceLocation, "#namespace:path", True],
        [AssumeTag[ResourceLocation], "namespace:path", True],
        [AssumeTag[ResourceLocation], "#namespace:path", True],
    ],
)
def test_assume_is_tag(type: type[ResourceLocation], value: str, want_is_tag: bool):
    ta = TypeAdapter(type)

    got = ta.validate_python(value)

    assert got.is_tag == want_is_tag
