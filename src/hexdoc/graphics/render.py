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

# https://minecraft.wiki/w/Help:Isometric_renders#Preferences
LIGHT_UP = 0.98
LIGHT_LEFT = 0.8
LIGHT_RIGHT = 0.608


@dataclass
class BlockRenderer:
    loader: ModResourceLoader

    def __post_init__(self):
        self.window = HeadlessWindow(
            size=(300, 300),
        )

        self.config = BlockRendererConfig(ctx=self.window.ctx, wnd=self.window)
        self.window.config = self.config

        self.window.swap_buffers()
        self.window.set_default_viewport()

        mglw.activate_context(self.window)

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

        self.config.render_block(model, textures)

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
        self.ctx.enable(mgl.DEPTH_TEST)

        self.face_prog = self.ctx.program(
            vertex_shader=read_shader("block_face", "vertex"),
            fragment_shader=read_shader("block_face", "fragment"),
        )

        # self.debug_prog = self.ctx.program(
        #     vertex_shader=read_shader("debug", "vertex"),
        #     fragment_shader=read_shader("debug", "fragment"),
        # )

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

        self.uniform("m_proj").write(self.projection)
        self.uniform("m_camera").write(self.camera)
        self.uniform("layer").value = 0  # TODO: implement animations

    def render_block(
        self,
        model: BlockModel,
        texture_vars: dict[str, BlockTextureInfo],
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
            * Matrix44.from_x_rotation(gui.eulers[0])
            * Matrix44.from_y_rotation(gui.eulers[1])
            * Matrix44.from_z_rotation(gui.eulers[2])
            * Matrix44.from_scale(gui.scale)
        )

        model_transform *= Matrix44.from_translation((-8, -8, -8))

        for element in model.elements:
            # transform element

            element_transform = model_transform.copy()
            # if rotation := element.rotation:
            #     # TODO: rescale??
            #     origin = np.array(rotation.origin)
            #     element_transform *= Matrix44.from_translation(-origin)
            #     element_transform *= Matrix44.from_eulers(rotation.eulers)
            #     element_transform *= Matrix44.from_translation(origin)

            self.uniform("m_model").write(element_transform)

            # render each face of the element
            for direction, face in element.faces.items():
                self.uniform("light").value = get_face_light(direction)
                self.uniform("texture0").value = texture_locs[face.texture.lstrip("#")]
                get_face_vao(element, direction, face).render(self.face_prog)

        self.ctx.finish()

        image = Image.frombytes(
            mode="RGBA",
            size=self.wnd.fbo.size,
            data=self.wnd.fbo.read(components=4),
        )

        image.save("out.png", format="png")

    def uniform(self, name: str):
        uniform = self.face_prog[name]
        assert isinstance(uniform, Uniform)
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


def get_face_vao(element: ModelElement, direction: FaceName, face: ElementFace):
    x1, y1, z1 = element.from_
    x2, y2, z2 = element.to

    if face.uv:
        u1, v1, u2, v2 = face.uv
    else:
        u1, v1, u2, v2 = get_default_uv(element, direction)

    # fmt: off
    match direction:
        case "south":
            verts = [
                x2, y1, z2,
                x2, y2, z2,
                x1, y1, z2,
                x2, y2, z2,
                x1, y2, z2,
                x1, y1, z2,
            ]
            uvs = [
                u2, v1,
                u2, v2,
                u1, v1,
                u2, v2,
                u1, v2,
                u1, v1,
            ]
        case "east":
            verts = [
                x2, y1, z1,
                x2, y2, z1,
                x2, y1, z2,
                x2, y2, z1,
                x2, y2, z2,
                x2, y1, z2,
            ]
            uvs = [
                u2, v1,
                u2, v2,
                u1, v1,
                u2, v2,
                u1, v2,
                u1, v1,
            ]
        case "down":
            verts = [
                x2, y1, z1,
                x2, y1, z2,
                x1, y1, z2,
                x2, y1, z1,
                x1, y1, z2,
                x1, y1, z1,
            ]
            uvs = [
                u2, v2,
                u1, v2,
                u1, v1,
                u2, v2,
                u1, v1,
                u2, v1,
            ]
        case "west":
            verts = [
                x1, y1, z2,
                x1, y2, z2,
                x1, y2, z1,
                x1, y1, z2,
                x1, y2, z1,
                x1, y1, z1,
            ]
            uvs = [
                u1, v2,
                u1, v1,
                u2, v1,
                u1, v2,
                u2, v1,
                u2, v2,
            ]
        case "north":
            verts = [
                x2, y2, z1,
                x2, y1, z1,
                x1, y1, z1,
                x2, y2, z1,
                x1, y1, z1,
                x1, y2, z1,
            ]
            uvs = [
                u2, v1,
                u2, v2,
                u1, v2,
                u2, v1,
                u1, v2,
                u1, v1,
            ]
        case "up":
            verts = [
                x2, y2, z1,
                x1, y2, z1,
                x2, y2, z2,
                x1, y2, z1,
                x1, y2, z2,
                x2, y2, z2,
            ]
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
            return LIGHT_UP / 2
        case "south":
            return LIGHT_LEFT
        case "north":
            return LIGHT_LEFT / 2
        case "east":
            return LIGHT_RIGHT
        case "west":
            return LIGHT_RIGHT / 2


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


def read_shader(path: str, type: Literal["fragment", "vertex"]):
    file = resources.files(glsl) / path / f"{type}.glsl"
    return file.read_text("utf-8")
