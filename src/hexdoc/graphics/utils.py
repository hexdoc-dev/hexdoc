# pyright: reportUnknownMemberType=false

from __future__ import annotations

from enum import Flag, auto
from typing import Literal, cast

import importlib_resources as resources
import numpy as np
from pyrr import Matrix44

from hexdoc.graphics import glsl
from hexdoc.utils.types import Vec3


class DebugType(Flag):
    NONE = 0
    AXES = auto()
    NORMALS = auto()


def read_shader(path: str, type: Literal["fragment", "vertex", "geometry"]):
    file = resources.files(glsl) / path / f"{type}.glsl"
    return file.read_text("utf-8")


def transform_vec(vec: Vec3, matrix: Matrix44) -> Vec3:
    return np.matmul((*vec, 1), matrix, dtype="f4")[:3]


def get_rotation_matrix(eulers: Vec3) -> Matrix44:
    return cast(
        Matrix44,
        Matrix44.from_x_rotation(-eulers[0], "f4")
        * Matrix44.from_y_rotation(-eulers[1], "f4")
        * Matrix44.from_z_rotation(-eulers[2], "f4"),
    )
