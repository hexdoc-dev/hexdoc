# pyright: reportUnknownMemberType=false

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import importlib_resources as resources
import moderngl as mgl
import moderngl_window as mglw
import numpy as np
from moderngl import Context, Uniform
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
from hexdoc.minecraft.models.base import (
    DisplayPosition,
    ElementFace,
    FaceName,
    ModelElement,
)
from hexdoc.minecraft.models.load import load_model
from hexdoc.utils.types import Vec3, Vec4

# https://minecraft.wiki/w/Help:Isometric_renders#Preferences
LIGHT_UP = 0.98
LIGHT_LEFT = 0.8
LIGHT_RIGHT = 0.608


@dataclass
class BlockRenderer:
    loader: ModResourceLoader
    debug: bool = False

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

        # ensure faces are displayed in the correct order
        self.ctx.enable(mgl.DEPTH_TEST | mgl.BLEND)

        view_size = 16  # TODO: value?
        self.projection = Matrix44.orthogonal_projection(
            left=-view_size / 2,
            right=view_size / 2,
            top=view_size / 2,
            bottom=-view_size / 2,
            near=0.01,
            far=20_000,
            dtype="f4",
        )

        self.camera = orbit_camera(yaw=90, pitch=0)
        # self.camera = orbit_camera(yaw=180, pitch=0)

        # block faces

        self.face_prog = self.ctx.program(
            vertex_shader=read_shader("block_face", "vertex"),
            fragment_shader=read_shader("block_face", "fragment"),
        )

        self.uniform("m_proj").write(self.projection)
        self.uniform("m_camera").write(self.camera)
        self.uniform("layer").value = 0  # TODO: implement animations

        # debugging, eg. axis planes

        self.debug_prog = self.ctx.program(
            vertex_shader=read_shader("debug", "vertex"),
            fragment_shader=read_shader("debug", "fragment"),
        )

        self.uniform("m_proj", "debug").write(self.projection)
        self.uniform("m_camera", "debug").write(self.camera)
        self.uniform("m_model", "debug").write(Matrix44.identity(dtype="f4"))

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
            vao.buffer(np.array(verts, dtype=np.float32), "3f", ["in_position"])
            self.debug_axes.append((vao, color))

    def render_block(
        self,
        model: BlockModel,
        texture_vars: dict[str, BlockTextureInfo],
        debug: bool = False,
    ):
        if not model.elements:
            raise ValueError("Unable to render model, no elements found")

        self.wnd.clear()

        # load textures

        texture_locs = dict[str, int]()
        for i, (name, info) in enumerate(texture_vars.items()):
            texture_locs[name] = i
            texture = self.load_texture_array(
                path=str(info.image_path),
                layers=info.layers,
            )
            texture.filter = (mgl.NEAREST, mgl.NEAREST)
            texture.use(i)

        # transform entire model

        model_transform = Matrix44.identity(dtype="f4")

        gui = model.display.get("gui") or DisplayPosition(
            rotation=(30, 225, 0),
            translation=(0, 0, 0),
            scale=(0.625, 0.625, 0.625),
        )

        model_transform *= (
            Matrix44.from_translation(gui.translation)
            * get_rotation_matrix(gui.eulers)
            * Matrix44.from_scale(gui.scale)
        )

        # render elements

        for element in model.elements:
            element_transform = model_transform.copy()

            # TODO: rescale??
            if rotation := element.rotation:
                center = np.add(element.to, element.from_) / 2
                origin = np.array(rotation.origin)
                element_transform *= (
                    Matrix44.from_translation(center - origin)
                    * get_rotation_matrix(rotation.eulers)
                    * Matrix44.from_translation(origin - center)
                )

            element_transform *= Matrix44.from_translation((-8, -8, -8))

            self.uniform("m_model").write(element_transform)

            # render each face of the element
            for direction, face in element.faces.items():
                rotation = Matrix44.from_y_rotation(math.radians(face.rotation), "f4")
                self.uniform("m_texture").write(rotation)

                self.uniform("light").value = get_face_light(direction)
                self.uniform("texture0").value = texture_locs[face.texture.lstrip("#")]

                vao = get_face_vao(element, direction, face)
                vao.render(self.face_prog)

        if debug:
            for axis, color in self.debug_axes:
                self.uniform("color", "debug").value = color
                axis.render(self.debug_prog)

        self.ctx.finish()

        image = Image.frombytes(
            mode="RGBA",
            size=self.wnd.fbo.size,
            data=self.wnd.fbo.read(components=4),
        )

        image.save("out.png", format="png")

    def uniform(self, name: str, prog_name: Literal["face", "debug"] = "face"):
        match prog_name:
            case "face":
                prog = self.face_prog
            case "debug":
                prog = self.debug_prog

        assert isinstance(uniform := prog[name], Uniform)
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


def get_face_vao(element: ModelElement, direction: FaceName, face: ElementFace):
    verts = get_face_verts(element.from_, element.to, direction)

    if face.uv:
        u1, v1, u2, v2 = face.uv
    else:
        u1, v1, u2, v2 = get_default_uv(element, direction)

    # fmt: off
    match direction:
        case "south":
            uvs = [
                u2, v1,
                u2, v2,
                u1, v1,
                u2, v2,
                u1, v2,
                u1, v1,
            ]
        case "east":
            uvs = [
                u2, v1,
                u2, v2,
                u1, v1,
                u2, v2,
                u1, v2,
                u1, v1,
            ]
        case "down":
            uvs = [
                u2, v2,
                u1, v2,
                u1, v1,
                u2, v2,
                u1, v1,
                u2, v1,
            ]
        case "west":
            uvs = [
                u1, v2,
                u1, v1,
                u2, v1,
                u1, v2,
                u2, v1,
                u2, v2,
            ]
        case "north":
            uvs = [
                u2, v1,
                u2, v2,
                u1, v2,
                u2, v1,
                u1, v2,
                u1, v1,
            ]
        case "up":
            uvs = [
                u2, v2,
                u1, v2,
                u2, v1,
                u1, v2,
                u1, v1,
                u2, v1,
            ]
    # fmt: on

    vao = VAO()
    vao.buffer(np.array(verts, dtype=np.float32), "3f", ["in_position"])
    vao.buffer(np.array(uvs, dtype=np.float32) / 16, "2f", ["in_texcoord_0"])
    return vao


def get_face_light(direction: FaceName):
    match direction:
        case "up":
            return LIGHT_UP
        case "down":
            return LIGHT_UP / 4
        case "south":
            return LIGHT_LEFT
        case "north":
            return LIGHT_LEFT / 4
        case "east":
            return LIGHT_RIGHT
        case "west":
            return LIGHT_RIGHT / 4


def get_default_uv(element: ModelElement, direction: FaceName):
    match direction:
        case "up" | "down":
            ui = 0
            vi = 2
        case "north" | "south":
            ui = 0
            vi = 1
        case "east" | "west":
            ui = 2
            vi = 1

    u_from = element.from_[ui]
    u_to = element.to[ui]
    v_from = element.from_[vi]
    v_to = element.to[vi]

    return (
        min(u_from, u_to),
        min(v_from, v_to),
        max(u_from, u_to),
        max(v_from, v_to),
    )


def orbit_camera(pitch: float, yaw: float):
    """Both values are in degrees."""

    eye = np.matmul(
        (-64, 0, 0, 1),
        (
            Matrix44.identity(dtype="f4")
            * Matrix44.from_y_rotation(math.radians(yaw))
            * Matrix44.from_z_rotation(math.radians(pitch))
        ),
    )[:3]

    up = np.matmul(
        (-1, 0, 0, 1),
        (
            Matrix44.identity(dtype="f4")
            * Matrix44.from_y_rotation(math.radians(yaw))
            * Matrix44.from_z_rotation(math.radians(90 - pitch))
        ),
    )[:3]

    return Matrix44.look_at(
        eye=eye,
        target=(0, 0, 0),
        up=up,
        dtype="f4",
    )


def read_shader(path: str, type: Literal["fragment", "vertex", "geometry"]):
    file = resources.files(glsl) / path / f"{type}.glsl"
    return file.read_text("utf-8")


def get_rotation_matrix(eulers: Vec3):
    return (
        Matrix44.from_x_rotation(eulers[0])
        * Matrix44.from_y_rotation(eulers[1])
        * Matrix44.from_z_rotation(eulers[2])
    )
