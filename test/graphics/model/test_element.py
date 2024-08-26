from typing import Any

import pytest
from hexdoc.graphics.model.element import ElementFaceTextureVariable, TextureVariable
from pydantic import TypeAdapter


@pytest.mark.parametrize(
    ["type_", "value", "want"],
    [
        [TextureVariable, "#a", "#a"],
        [TextureVariable, "#all", "#all"],
        [TextureVariable, "#ALL", "#ALL"],
        [TextureVariable, "#_", "#_"],
        [ElementFaceTextureVariable, "#a", "#a"],
        [ElementFaceTextureVariable, "#all", "#all"],
        [ElementFaceTextureVariable, "#ALL", "#ALL"],
        [ElementFaceTextureVariable, "#_", "#_"],
        [ElementFaceTextureVariable, "a", "#a"],
        [ElementFaceTextureVariable, "all", "#all"],
        [ElementFaceTextureVariable, "ALL", "#ALL"],
        [ElementFaceTextureVariable, "_", "#_"],
    ],
)
def test_texture_variable_validator_accepts_valid(type_: Any, value: str, want: str):
    ta = TypeAdapter(type_)
    got = ta.validate_python(value)
    assert got == want


@pytest.mark.parametrize(
    ["type_", "value"],
    [
        [TextureVariable, ""],
        [TextureVariable, "#"],
        [TextureVariable, "##"],
        [TextureVariable, "##all"],
        [TextureVariable, "a"],
        [TextureVariable, "all"],
        [ElementFaceTextureVariable, ""],
        [ElementFaceTextureVariable, "#"],
        [ElementFaceTextureVariable, "##"],
        [ElementFaceTextureVariable, "##all"],
    ],
)
def test_texture_variable_validator_throws_invalid(type_: Any, value: str):
    ta = TypeAdapter(type_)
    with pytest.raises(ValueError, match="Malformed texture variable"):
        ta.validate_python(value)
