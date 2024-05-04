# pyright: reportUnknownMemberType=false

from __future__ import annotations

import math
from typing import cast

from pyrr import Matrix44

from hexdoc.minecraft.model import FaceName

from .lookups import get_direction_vec
from .utils import transform_vec


def orbit_camera(pitch: float, yaw: float):
    """Both values are in degrees."""

    eye = transform_vec(
        (-64, 0, 0),
        cast(
            Matrix44,
            Matrix44.identity(dtype="f4")
            * Matrix44.from_y_rotation(math.radians(yaw))
            * Matrix44.from_z_rotation(math.radians(pitch)),
        ),
    )

    up = transform_vec(
        (-1, 0, 0),
        cast(
            Matrix44,
            Matrix44.identity(dtype="f4")
            * Matrix44.from_y_rotation(math.radians(yaw))
            * Matrix44.from_z_rotation(math.radians(90 - pitch)),
        ),
    )

    return Matrix44.look_at(
        eye=eye,
        target=(0, 0, 0),
        up=up,
        dtype="f4",
    ), eye


def direction_camera(pos: FaceName, up: FaceName = "up"):
    """eg. north -> camera is placed to the north of the model, looking south"""
    eye = get_direction_vec(pos, 64)
    return Matrix44.look_at(
        eye=eye,
        target=(0, 0, 0),
        up=get_direction_vec(up),
        dtype="f4",
    ), eye
