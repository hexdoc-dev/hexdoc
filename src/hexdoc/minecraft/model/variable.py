import re
from typing import Annotated

from pydantic import AfterValidator


def _validate_texture_variable(value: str):
    assert re.fullmatch(r"#\w+", value)
    return value


TextureVariable = Annotated[str, AfterValidator(_validate_texture_variable)]
