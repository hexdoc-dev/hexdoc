# pyright: reportUnknownMemberType=false

from __future__ import annotations

from hexdoc.utils.types import Vec3

from .model import FaceName


def get_face_verts(from_: Vec3, to: Vec3, direction: FaceName):
    x1, y1, z1 = from_
    x2, y2, z2 = to

    # fmt: off
    match direction:
        case FaceName.south:
            return [
                x2, y1, z2,
                x2, y2, z2,
                x1, y1, z2,
                x2, y2, z2,
                x1, y2, z2,
                x1, y1, z2,
            ]
        case FaceName.east:
            return [
                x2, y1, z1,
                x2, y2, z1,
                x2, y1, z2,
                x2, y2, z1,
                x2, y2, z2,
                x2, y1, z2,
            ]
        case FaceName.down:
            return [
                x2, y1, z1,
                x2, y1, z2,
                x1, y1, z2,
                x2, y1, z1,
                x1, y1, z2,
                x1, y1, z1,
            ]
        case FaceName.west:
            return [
                x1, y1, z2,
                x1, y2, z2,
                x1, y2, z1,
                x1, y1, z2,
                x1, y2, z1,
                x1, y1, z1,
            ]
        case FaceName.north:
            return [
                x2, y2, z1,
                x2, y1, z1,
                x1, y1, z1,
                x2, y2, z1,
                x1, y1, z1,
                x1, y2, z1,
            ]
        case FaceName.up:
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
        case FaceName.south:
            return (2, 3, 1, 3, 0, 1)
        case FaceName.east:
            return (2, 3, 1, 3, 0, 1)
        case FaceName.down:
            return (2, 3, 0, 2, 0, 1)
        case FaceName.west:
            return (2, 3, 0, 2, 0, 1)
        case FaceName.north:
            return (0, 1, 2, 0, 2, 3)
        case FaceName.up:
            return (3, 0, 2, 0, 1, 2)


def get_direction_vec(direction: FaceName, magnitude: float = 1):
    match direction:
        case FaceName.north:
            return (0, 0, -magnitude)
        case FaceName.south:
            return (0, 0, magnitude)
        case FaceName.west:
            return (-magnitude, 0, 0)
        case FaceName.east:
            return (magnitude, 0, 0)
        case FaceName.down:
            return (0, -magnitude, 0)
        case FaceName.up:
            return (0, magnitude, 0)


def get_face_normals(direction: FaceName):
    return 6 * get_direction_vec(direction)
