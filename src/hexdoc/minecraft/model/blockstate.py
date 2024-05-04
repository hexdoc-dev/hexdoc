from __future__ import annotations

from typing import Annotated, Any, Literal

from frozendict import frozendict
from pydantic import AfterValidator, BeforeValidator, ConfigDict, model_validator

from hexdoc.core import ResourceLocation
from hexdoc.model import HexdocModel
from hexdoc.model.base import DEFAULT_CONFIG


class Blockstate(HexdocModel):
    """Represents a Minecraft blockstate file.

    There are several different variants of some blocks (like doors, which can be open
    or closed), hence each block has its own block state file, which lists all its
    existing variants and links them to their corresponding models. Blocks can also be
    composed of several different models at the same time, called "multipart". The
    models are then used depending on the block states of the block.

    These files are stored in the following folder: `assets/<namespace>/blockstates`.
    The files are used directly based on their filename, thus a block state file with
    another name than the existing ones does not affect any block.

    https://minecraft.wiki/w/Tutorials/Models#Block_states
    """

    model_config = DEFAULT_CONFIG | ConfigDict(
        arbitrary_types_allowed=True,
    )

    variants: dict[_BlockstateVariantKey, _BlockstateModels] | None = None
    """Holds the names of all the variants of the block.

    Name of a variant, which consists of the relevant block states separated by commas.
    A block with just one variant uses "" as a name for its variant. Each variant can
    have one model or an array of models and contains their properties. If set to an
    array, the model is chosen randomly from the options given.
    """
    multipart: list[BlockstateMultipart] | None = None
    """Used instead of variants to combine models based on block state attributes."""

    @model_validator(mode="after")
    def _validate_variant_or_multipart(self):
        match bool(self.variants), bool(self.multipart):
            case True, True:
                reason = "both"
            case False, False:
                reason = "neither"
            case _:
                return self
        raise ValueError(f"Expected exactly one of variants or multipart, got {reason}")


class BlockstateModel(HexdocModel):
    """Contains the properties of a model.

    https://minecraft.wiki/w/Tutorials/Models#Block_states
    """

    model: ResourceLocation
    """Specifies the path to the model file of the block."""
    x: Literal[0, 90, 180, 270] = 0
    """Rotation of the model on the x-axis in increments of 90 degrees."""
    y: Literal[0, 90, 180, 270] = 0
    """Rotation of the model on the y-axis in increments of 90 degrees."""
    uvlock: bool = False
    """Locks the rotation of the texture of a block, if set to true. This way the
    texture does not rotate with the block when using the x and y-tags above."""
    weight: int = 1
    """Sets the probability of the model for being used in the game, defaults to 100%.

    If more than one model is used for the same variant, the probability is calculated
    by dividing the individual model's weight by the sum of the weights of all models.
    """


class BlockstateMultipart(HexdocModel):
    """Determines a case and the model that should apply in that case.

    https://minecraft.wiki/w/Tutorials/Models#Block_states
    """

    apply: _BlockstateModels
    """Determines the model(s) to apply and its properties.

    If set to an array, the model is chosen randomly from the options given.
    """
    when: _MultipartCondition | None = None
    """A list of cases that have to be met for the model to be applied.

    If unset, the model always applies.
    """


def _validate_variant_key(value: Any):
    if isinstance(value, str):
        value = dict(item.split("=") for item in value.split(","))
    return frozendict[Any, Any](value)


_BlockstateVariantKey = Annotated[
    frozendict[str, str],
    BeforeValidator(_validate_variant_key),
]
"""Name of a variant, which consists of the relevant block states separated by commas.

A block with just one variant uses "" as a name for its variant.

Item frames are treated as blocks and use "map=false" for a map-less item frame, and
"map=true" for item frames with maps.
"""


_BlockstateModels = BlockstateModel | list[BlockstateModel]
"""There can be one model or an array of models.

If set to an array, the model is chosen randomly from the options given.
"""


def _validate_states_key(value: str):
    assert value not in {"AND", "OR"}, "State name cannot be AND/OR"
    return value


def _validate_states_value(value: Any):
    if isinstance(value, str):
        return set(value.split("|"))
    return value


_MultipartStates = dict[
    Annotated[str, AfterValidator(_validate_states_key)],
    Annotated[set[str], BeforeValidator(_validate_states_value)],
]
"""A list of cases that all have to match the block to return true.

Name of a block state. A single case that has to match one of the block states. It can
be set to a list separated by | to allow multiple values to match.
"""

_MultipartCondition = (
    dict[Literal["AND"], list[_MultipartStates]]
    | dict[Literal["OR"], list[_MultipartStates]]
    | _MultipartStates
)
"""A list of cases that have to be met for the model to be applied.

OR: Matches if any of the contained cases return true. Cannot be set alongside other
cases.

AND: Matches if all of the contained cases return true. Cannot be set alongside other
cases.
"""
