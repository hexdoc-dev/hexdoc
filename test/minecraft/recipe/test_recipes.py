from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter
from yarl import URL

from hexdoc.core.i18n import I18n
from hexdoc.core.loader import ModResourceLoader
from hexdoc.core.properties import LangProps, Properties
from hexdoc.core.properties.textures import TexturesProps
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir, PluginResourceDir
from hexdoc.graphics.loader import ImageLoader
from hexdoc.graphics.renderer import ModelRenderer
from hexdoc.minecraft.recipe.recipes import CraftingShapelessRecipe, Recipe
from hexdoc.model.base import init_context
from hexdoc.plugin.manager import PluginManager
from hexdoc.utils.cd import relative_path_root
from hexdoc.utils.context import ContextSource


@pytest.fixture
def context(tmp_path: Path):
    props = Properties.model_construct(
        textures=TexturesProps.model_construct(
            missing="*",
        ),
    )

    pm = PluginManager("branch", props=props)

    with (
        relative_path_root(Path()),
        PluginResourceDir(modid="hexdoc").load(pm) as resource_dirs,
    ):
        loader = ModResourceLoader(
            props=props,
            export_dir=None,
            resource_dirs=resource_dirs,
            _stack=ExitStack(),
        )

        renderer = ModelRenderer(loader=loader)

        image_loader = ImageLoader(
            loader=loader,
            renderer=renderer,
            site_dir=tmp_path,
            site_url=URL(),
        )

        i18n = I18n(
            lookup=I18n.parse_lookup(
                {
                    "item.minecraft.stick": "Stick",
                    "item.minecraft.diamond": "Diamond",
                }
            ),
            lang="en_us",
            default_i18n=None,
            enabled=True,
            lang_props=LangProps(),
        )

        context: ContextSource = {}
        for ctx in [
            props,
            pm,
            loader,
            image_loader,
            i18n,
        ]:
            ctx.add_to_context(context)

        with init_context(context):
            yield context


def test_shapeless(context: dict[str, Any]):
    data = {
        "type": "minecraft:crafting_shapeless",
        "ingredients": [{"item": "minecraft:stick"}],
        "result": {"item": "minecraft:diamond"},
        # for hexdoc
        "id": ResourceLocation("a", "b"),
        "resource_dir": PathResourceDir.model_construct(path=Path()),
    }

    recipe = TypeAdapter(Recipe).validate_python(data, context=context)

    assert isinstance(recipe, CraftingShapelessRecipe)


def test_fabric_load_conditions(context: dict[str, Any]):
    data = {
        "type": "minecraft:crafting_shapeless",
        "ingredients": [{"item": "minecraft:stick"}],
        "result": {"item": "minecraft:diamond"},
        "fabric:load_conditions": [
            {
                "condition": "fabric:all_mods_loaded",
                "values": ["fabric-resource-conditions-api-v1"],
            }
        ],
        # for hexdoc
        "id": ResourceLocation("a", "b"),
        "resource_dir": PathResourceDir.model_construct(path=Path()),
    }

    recipe = TypeAdapter(Recipe).validate_python(data, context=context)

    assert isinstance(recipe, CraftingShapelessRecipe)
