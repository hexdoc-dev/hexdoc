# pyright: reportUnknownMemberType=false

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Flag, auto
from pathlib import Path
from typing import Any, Literal

import importlib_resources as resources
import moderngl as mgl
import moderngl_window as mglw
import numpy as np
from moderngl import Context, Program, Uniform
from moderngl_window import WindowConfig
from moderngl_window.context.headless import Window as HeadlessWindow
from moderngl_window.opengl.vao import VAO
from PIL import Image
from pyrr import Matrix44

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.graphics import glsl
from hexdoc.minecraft.assets import AnimationMeta
from hexdoc.minecraft.assets.animated import AnimationMetaFrame
from hexdoc.minecraft.models import BlockModel
from hexdoc.minecraft.models.base_model import (
    DisplayPosition,
    ElementFace,
    ElementFaceUV,
    FaceName,
    ModelElement,
)
from hexdoc.minecraft.models.load import load_model
from hexdoc.utils.types import Vec3, Vec4

# https://minecraft.wiki/w/Help:Isometric_renders#Preferences
LIGHT_TOP = 0.98
LIGHT_LEFT = 0.8
LIGHT_RIGHT = 0.608

LIGHT_FLAT = 0.98


class DebugType(Flag):
    NONE = 0
    AXES = auto()
    NORMALS = auto()


@dataclass
class BlockRenderer:
    loader: ModResourceLoader
    debug: DebugType = DebugType.NONE

    def __post_init__(self):
        self.window = HeadlessWindow(
            size=(300, 300),
        )
        mglw.activate_context(self.window)

        self.config = BlockRendererConfig(ctx=self.window.ctx, wnd=self.window)

        self.window.config = self.config
        self.window.swap_buffers()
        self.window.set_default_viewport()

    @property
    def ctx(self):
        return self.window.ctx

    def render_block_model(self, model: BlockModel | ResourceLocation):
        if isinstance(model, ResourceLocation):
            _, item_or_block_model = load_model(self.loader, model)
            if not isinstance(item_or_block_model, BlockModel):
                raise ValueError(f"Expected block model, got item: {model}")
            model = item_or_block_model

        model.load_parents_and_apply(self.loader)

        textures = {
            name: self.load_texture(texture_id)
            for name, texture_id in model.resolve_texture_variables().items()
        }

        self.config.render_block(model, textures, self.debug)

    def load_texture(self, texture_id: ResourceLocation):
        _, path = self.loader.find_resource("assets", "textures", texture_id + ".png")

        meta_path = path.with_suffix(".png.mcmeta")
        if meta_path.is_file():
            meta = AnimationMeta.model_validate_json(meta_path.read_bytes())
        else:
            meta = None

        return BlockTextureInfo(path, meta)

    def destroy(self):
        self.window.destroy()

    def __enter__(self):
        return self

    def __exit__(self, *_: Any):
        self.destroy()
        return False


class BlockRendererConfig(WindowConfig):
    def __init__(self, ctx: Context, wnd: HeadlessWindow):
        super().__init__(ctx, wnd)

        # depth test: ensure faces are displayed in the correct order
        # blend: handle translucency
        # cull face: remove back faces, eg. for trapdoors
        self.ctx.enable(mgl.DEPTH_TEST | mgl.BLEND | mgl.CULL_FACE)

        view_size = 16
        self.projection = Matrix44.orthogonal_projection(
            left=-view_size / 2,
            right=view_size / 2,
            top=view_size / 2,
            bottom=-view_size / 2,
            near=0.01,
            far=20_000,
            dtype="f4",
        ) * Matrix44.from_scale((1, -1, 1), "f4")

        self.camera = direction_camera(pos="south")

        self.lights = [
            ((0, -1, 0), LIGHT_TOP),
            ((1, 0, -1), LIGHT_LEFT),
            ((-1, 0, -1), LIGHT_RIGHT),
        ]

        # block faces

        self.face_prog = self.ctx.program(
            vertex_shader=read_shader("block_face", "vertex"),
            fragment_shader=read_shader("block_face", "fragment"),
        )

        self.uniform("m_proj").write(self.projection)
        self.uniform("m_camera").write(self.camera)
        self.uniform("layer").value = 0  # TODO: implement animations

        for i, (direction, diffuse) in enumerate(self.lights):
            self.uniform(f"lights[{i}].direction").value = direction
            self.uniform(f"lights[{i}].diffuse").value = diffuse

        # axis planes

        self.debug_plane_prog = self.ctx.program(
            vertex_shader=read_shader("debug/plane", "vertex"),
            fragment_shader=read_shader("debug/plane", "fragment"),
        )

        self.uniform("m_proj", self.debug_plane_prog).write(self.projection)
        self.uniform("m_camera", self.debug_plane_prog).write(self.camera)
        self.uniform("m_model", self.debug_plane_prog).write(Matrix44.identity("f4"))

        self.debug_axes = list[tuple[VAO, Vec4]]()

        pos = 8
        neg = 0
        for from_, to, color, direction in [
            ((0, neg, neg), (0, pos, pos), (1, 0, 0, 0.75), "east"),
            ((neg, 0, neg), (pos, 0, pos), (0, 1, 0, 0.75), "up"),
            ((neg, neg, 0), (pos, pos, 0), (0, 0, 1, 0.75), "south"),
        ]:
            vao = VAO()
            verts = get_face_verts(from_, to, direction)
            vao.buffer(np.array(verts, np.float32), "3f", ["in_position"])
            self.debug_axes.append((vao, color))

        # vertex normal vectors

        self.debug_normal_prog = self.ctx.program(
            vertex_shader=read_shader("debug/normal", "vertex"),
            geometry_shader=read_shader("debug/normal", "geometry"),
            fragment_shader=read_shader("debug/normal", "fragment"),
        )

        self.uniform("m_proj", self.debug_normal_prog).write(self.projection)
        self.uniform("m_camera", self.debug_normal_prog).write(self.camera)
        self.uniform("lineSize", self.debug_normal_prog).value = 4

        self.ctx.line_width = 3

    def render_block(
        self,
        model: BlockModel,
        texture_vars: dict[str, BlockTextureInfo],
        debug: DebugType = DebugType.NONE,
    ):
        if not model.elements:
            raise ValueError("Unable to render model, no elements found")

        self.wnd.clear()

        # enable/disable flat item lighting
        match model.gui_light:
            case "front":
                flatLighting = LIGHT_FLAT
            case "side":
                flatLighting = 0
        self.uniform("flatLighting").value = flatLighting

        # load textures
        texture_locs = dict[str, int]()
        for i, (name, info) in enumerate(texture_vars.items()):
            texture_locs[name] = i
            image = Image.open(info.image_path).convert("RGBA")
            texture = self.ctx.texture_array(
                size=(image.width, image.width, info.layers),
                components=4,
                data=image.tobytes(),
            )
            texture.filter = (mgl.NEAREST, mgl.NEAREST)
            texture.use(i)

        # transform entire model

        gui = model.display.get("gui") or DisplayPosition(
            rotation=(30, 225, 0),
            translation=(0, 0, 0),
            scale=(0.625, 0.625, 0.625),
        )

        model_transform = (
            Matrix44.from_scale(gui.scale, "f4")
            * get_rotation_matrix(gui.eulers)
            * Matrix44.from_translation(gui.translation, "f4")
            * Matrix44.from_translation((-8, -8, -8), "f4")
        )

        normals_transform = Matrix44.from_y_rotation(-gui.eulers[1], "f4")
        self.uniform("m_normals").write(normals_transform)

        # render elements

        for element in model.elements:
            element_transform = model_transform.copy()

            # TODO: rescale??
            if rotation := element.rotation:
                origin = np.array(rotation.origin)
                element_transform *= (
                    Matrix44.from_translation(origin, "f4")
                    * get_rotation_matrix(rotation.eulers)
                    * Matrix44.from_translation(-origin, "f4")
                )

            self.uniform("m_model").write(element_transform)

            if DebugType.NORMALS in debug:
                self.uniform("m_model", self.debug_normal_prog).write(element_transform)

            # render each face of the element
            for direction, face in element.faces.items():
                self.uniform("texture0").value = texture_locs[face.texture.lstrip("#")]
                vao = get_face_vao(element, direction, face)
                vao.render(self.face_prog)
                if DebugType.NORMALS in debug:
                    vao.render(self.debug_normal_prog)

        if DebugType.AXES in debug:
            self.ctx.disable(mgl.CULL_FACE)
            for axis, color in self.debug_axes:
                self.uniform("color", self.debug_plane_prog).value = color
                axis.render(self.debug_plane_prog)
            self.ctx.enable(mgl.CULL_FACE)

        self.ctx.finish()

        # save to file

        image = Image.frombytes(
            mode="RGBA",
            size=self.wnd.fbo.size,
            data=self.wnd.fbo.read(components=4),
        ).transpose(Image.FLIP_TOP_BOTTOM)

        image.save("out.png", format="png")

    def uniform(self, name: str, program: Program | None = None):
        program = program or self.face_prog
        assert isinstance(uniform := program[name], Uniform)
        return uniform


@dataclass
class BlockTextureInfo:
    image_path: Path
    meta: AnimationMeta | None

    @property
    def layers(self):
        if not self.meta:
            return 1

        max_index = 0
        for i, frame in enumerate(self.meta.animation.frames):
            match frame:
                case int():
                    index = frame
                case AnimationMetaFrame(index=int(index)):
                    pass
                case _:
                    index = i
            max_index = max(max_index, index)

        return max_index + 1


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


def get_face_normals(direction: FaceName):
    return 6 * get_direction_vec(direction)


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


def get_face_vao(element: ModelElement, direction: FaceName, face: ElementFace):
    verts = get_face_verts(element.from_, element.to, direction)

    normals = get_face_normals(direction)

    face_uv = face.uv or ElementFaceUV.default(element, direction)
    uvs = [
        value
        for index in get_face_uv_indices(direction)
        for value in face_uv.get_uv(index)
    ]

    vao = VAO()
    vao.buffer(np.array(verts, np.float32), "3f", ["in_position"])
    vao.buffer(np.array(normals, np.float32), "3f", ["in_normal"])
    vao.buffer(np.array(uvs, np.float32) / 16, "2f", ["in_texcoord_0"])
    return vao


def orbit_camera(pitch: float, yaw: float):
    """Both values are in degrees."""

    eye = transform_vec(
        (-64, 0, 0),
        (
            Matrix44.identity(dtype="f4")
            * Matrix44.from_y_rotation(math.radians(yaw))
            * Matrix44.from_z_rotation(math.radians(pitch))
        ),
    )

    up = transform_vec(
        (-1, 0, 0),
        (
            Matrix44.identity(dtype="f4")
            * Matrix44.from_y_rotation(math.radians(yaw))
            * Matrix44.from_z_rotation(math.radians(90 - pitch))
        ),
    )

    return Matrix44.look_at(
        eye=eye,
        target=(0, 0, 0),
        up=up,
        dtype="f4",
    )


def transform_vec(vec: Vec3, matrix: Matrix44) -> Vec3:
    return np.matmul((*vec, 1), matrix, dtype="f4")[:3]


def direction_camera(pos: FaceName, up: FaceName = "up"):
    """eg. north -> camera is placed to the north of the model, looking south"""
    return Matrix44.look_at(
        eye=get_direction_vec(pos, 64),
        target=(0, 0, 0),
        up=get_direction_vec(up),
        dtype="f4",
    )


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


def read_shader(path: str, type: Literal["fragment", "vertex", "geometry"]):
    file = resources.files(glsl) / path / f"{type}.glsl"
    return file.read_text("utf-8")


def get_rotation_matrix(eulers: Vec3):
    return (
        Matrix44.from_x_rotation(-eulers[0], "f4")
        * Matrix44.from_y_rotation(-eulers[1], "f4")
        * Matrix44.from_z_rotation(-eulers[2], "f4")
    )
