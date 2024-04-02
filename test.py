from pathlib import Path

from hexdoc.cli.utils.load import load_common_data
from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.graphics.render import BlockRenderer
from hexdoc.minecraft.models import load_model
from hexdoc.minecraft.models.item import ItemModel

# MODEL_ID = "minecraft:block/oak_log"
# MODEL_ID = "minecraft:block/lectern"
# MODEL_ID = "minecraft:block/oak_stairs"
MODEL_ID = "minecraft:item/oak_trapdoor"
# MODEL_ID = "minecraft:block/dropper"


def main():
    props_file = Path("hexdoc_textures.toml")
    props, pm, *_ = load_common_data(props_file, branch="")

    with ModResourceLoader.load_all(props, pm, export=False) as loader:
        _, model = load_model(loader, ResourceLocation.from_str(MODEL_ID))
        while isinstance(model, ItemModel) and model.parent:
            _, model = load_model(loader, model.parent)

        if isinstance(model, ItemModel):
            raise ValueError(f"Invalid block id: {MODEL_ID}")

        with BlockRenderer(loader, debug=False) as renderer:
            renderer.render_block_model(model)


if __name__ == "__main__":
    main()
