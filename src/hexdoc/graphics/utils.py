# pyright: reportUnknownMemberType=false

from __future__ import annotations

from enum import Flag, auto
from typing import Literal, cast

import importlib_resources as resources
import numpy as np
from PIL.Image import Image
from pyrr import Matrix44

from hexdoc.graphics import glsl
from hexdoc.minecraft.model import Animation, AnimationMeta
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


# TODO: remove
def get_height_and_layers(image: Image, meta: AnimationMeta | None):
    match meta:
        case AnimationMeta(
            animation=Animation(height=frame_height),
        ) if frame_height:
            # animated with specified size
            layers = image.height // frame_height
        case AnimationMeta():
            # size is unspecified, assume it's square and verify later
            frame_height = image.width
            layers = image.height // frame_height
        case None:
            # non-animated
            frame_height = image.height
            layers = 1
    return frame_height, layers
