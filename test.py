from pathlib import Path

from hexdoc.cli.utils.load import load_common_data
from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.graphics.render import BlockRenderer
from hexdoc.minecraft.models import load_model
from hexdoc.minecraft.models.item import ItemModel

BLOCK_ID = "minecraft:oak_log"


def main():
    props_file = Path("submodules/HexMod/doc/hexdoc.toml")
    props, pm, *_ = load_common_data(props_file, branch="")

    with ModResourceLoader.load_all(props, pm, export=False) as loader:
        _, model = load_model(loader, "item" / ResourceLocation.from_str(BLOCK_ID))
        while isinstance(model, ItemModel) and model.parent:
            _, model = load_model(loader, model.parent)

        if isinstance(model, ItemModel):
            raise ValueError(f"Invalid block id: {BLOCK_ID}")

        with BlockRenderer(loader) as renderer:
            renderer.render_block_model(model)


if __name__ == "__main__":
    main()
