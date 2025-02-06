from hexdoc.core import ResourceLocation
from hexdoc.minecraft import LocalizedStr
from hexdoc.model import HexdocModel
from pydantic import Field, model_validator


def _gui_texture(name: str):
    return ResourceLocation("modonomicon", f"textures/gui/{name}.png")


class Modonomicon(HexdocModel):
    """https://klikli-dev.github.io/modonomicon/docs/basics/structure/book"""

    name: LocalizedStr

    tooltip: LocalizedStr | None = None
    generate_book_item: bool = True
    model: ResourceLocation | None = Field("modonomicon:modonomicon_purple")  # type: ignore
    custom_book_item: ResourceLocation | None = None
    creative_tab: str = "misc"
    default_title_color: int = 0
    auto_add_read_conditions: bool = False
    book_overview_texture: ResourceLocation = _gui_texture("book_overview")
    frame_texture: ResourceLocation = _gui_texture("book_frame")
    left_frame_overlay: ResourceLocation = _gui_texture("book_frame_left_overlay")
    right_frame_overlay: ResourceLocation = _gui_texture("book_frame_right_overlay")
    top_frame_overlay: ResourceLocation = _gui_texture("book_frame_top_overlay")
    bottom_frame_overlay: ResourceLocation = _gui_texture("book_frame_bottom_overlay")
    book_content_texture: ResourceLocation = _gui_texture("book_content")
    crafting_texture: ResourceLocation = _gui_texture("crafting_textures")
    category_button_icon_scale: float = 1
    category_button_x_offset: int = 0
    category_button_y_offset: int = 0
    search_button_x_offset: int = 0
    search_button_y_offset: int = 0
    read_all_button_y_offset: int = 0
    turn_page_sound: ResourceLocation = Field("minecraft:turn_page")  # type: ignore

    @model_validator(mode="after")
    def _validate_constraints(self):
        if self.generate_book_item:
            assert self.model, "model is required if generate_book_item is True"
        else:
            assert (
                self.custom_book_item
            ), "custom_book_item is required if generate_book_item is False"

        return self
