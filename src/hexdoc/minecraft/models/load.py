from hexdoc.core import ModResourceLoader, ResourceLocation

from .block import BlockModel
from .item import ItemModel


def load_model(loader: ModResourceLoader, model_id: ResourceLocation):
    match model_id.path.split("/")[0]:
        case "block":
            model_type = BlockModel
        case "item":
            model_type = ItemModel
        case type_name:
            raise ValueError(f"Unsupported type {type_name} for model {model_id}")

    try:
        return loader.load_resource(
            type="assets",
            folder="models",
            id=model_id,
            decode=model_type.model_validate_json,
        )
    except Exception as e:
        e.add_note(f"  note: {model_id=}")
        raise
