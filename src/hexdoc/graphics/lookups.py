# pyright: reportUnknownMemberType=false

from __future__ import annotations

from hexdoc.minecraft.model import FaceName
from hexdoc.utils.types import Vec3


def get_face_verts(from_: Vec3, to: Vec3, direction: FaceName):
    x1, y1, z1 = from_
    x2, y2, z2 = to

    # fmt: off
    match direction:
        case "south":
            return [
                x2, y1, z2,
                x2, y2, z2,
                x1, y1, z2,
                x2, y2, z2,
                x1, y2, z2,
                x1, y1, z2,
            ]
        case "east":
            return [
                x2, y1, z1,
                x2, y2, z1,
                x2, y1, z2,
                x2, y2, z1,
                x2, y2, z2,
                x2, y1, z2,
            ]
        case "down":
            return [
                x2, y1, z1,
                x2, y1, z2,
                x1, y1, z2,
                x2, y1, z1,
                x1, y1, z2,
                x1, y1, z1,
            ]
        case "west":
            return [
                x1, y1, z2,
                x1, y2, z2,
                x1, y2, z1,
                x1, y1, z2,
                x1, y2, z1,
                x1, y1, z1,
            ]
        case "north":
            return [
                x2, y2, z1,
                x2, y1, z1,
                x1, y1, z1,
                x2, y2, z1,
                x1, y1, z1,
                x1, y2, z1,
            ]
        case "up":
            return [
                x2, y2, z1,
                x1, y2, z1,
                x2, y2, z2,
                x1, y2, z1,
                x1, y2, z2,
                x2, y2, z2,
            ]
    # fmt: on


def get_face_uv_indices(direction: FaceName):
    match direction:
        case "south":
            return (2, 3, 1, 3, 0, 1)
        case "east":
            return (2, 3, 1, 3, 0, 1)
        case "down":
            return (2, 3, 0, 2, 0, 1)
        case "west":
            return (2, 3, 0, 2, 0, 1)
        case "north":
            return (0, 1, 2, 0, 2, 3)
        case "up":
            return (3, 0, 2, 0, 1, 2)


def get_direction_vec(direction: FaceName, magnitude: float = 1):
    match direction:
        case "north":
            return (0, 0, -magnitude)
        case "south":
            return (0, 0, magnitude)
        case "west":
            return (-magnitude, 0, 0)
        case "east":
            return (magnitude, 0, 0)
        case "down":
            return (0, -magnitude, 0)
        case "up":
            return (0, magnitude, 0)


def get_face_normals(direction: FaceName):
    return 6 * get_direction_vec(direction)
