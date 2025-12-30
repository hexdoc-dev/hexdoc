# pyright: reportUnknownMemberType=false

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import cached_property
from typing import cast

import moderngl as mgl
import numpy as np
from moderngl import Context, Program, Uniform
from moderngl_window import WindowConfig
from moderngl_window.context.headless import Window as HeadlessWindow
from moderngl_window.opengl.vao import VAO
from PIL import Image
from pyrr import Matrix44

from hexdoc.utils.logging import TRACE
from hexdoc.utils.types import Vec3, Vec4

from .camera import direction_camera
from .lookups import get_face_normals, get_face_uv_indices, get_face_verts
from .model import (
    BlockModel,
    DisplayPosition,
    Element,
    ElementFace,
    ElementFaceUV,
    FaceName,
)
from .texture import ModelTexture
from .utils import DebugType, get_rotation_matrix, read_shader

logger = logging.getLogger(__name__)


# https://minecraft.wiki/w/Help:Isometric_renders#Preferences
LIGHT_TOP = 0.98
LIGHT_LEFT = 0.8
LIGHT_RIGHT = 0.608

LIGHT_FLAT = 0.98


class BlockRenderer(WindowConfig):
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

        self.camera, self.eye = direction_camera(pos=FaceName.south)

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
            ((0, neg, neg), (0, pos, pos), (1, 0, 0, 0.75), FaceName.east),
            ((neg, 0, neg), (pos, 0, pos), (0, 1, 0, 0.75), FaceName.up),
            ((neg, neg, 0), (pos, pos, 0), (0, 0, 1, 0.75), FaceName.south),
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
        texture_vars: dict[str, ModelTexture],
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
        transparent_textures = set[str]()

        for i, (name, texture) in enumerate(texture_vars.items()):
            texture_locs[name] = i

            image = texture.image
            frame_height = texture.frame_height
            layers = len(texture.frames)

            extrema = image.getextrema()
            assert len(extrema) >= 4, f"Expected 4 bands but got {len(extrema)}"
            min_alpha, _ = extrema[3]
            if min_alpha < 255:
                logger.log(TRACE, f"Transparent texture: {name} ({min_alpha=})")
                transparent_textures.add(name)

            data = bytes()
            for frame in texture.frames:
                data += frame.tobytes()

            logger.log(
                TRACE, f"Texture array: {image.width=}, {frame_height=}, {layers=}"
            )
            texture_array = self.ctx.texture_array(
                size=(image.width, frame_height, layers),
                components=4,
                data=data,
            )
            texture_array.filter = (mgl.NEAREST, mgl.NEAREST)
            texture_array.use(i)

        # transform entire model

        gui = model.display.get("gui") or DisplayPosition(
            rotation=(30, 225, 0),
            translation=(0, 0, 0),
            scale=(0.625, 0.625, 0.625),
        )

        model_transform = cast(
            Matrix44,
            Matrix44.from_scale(gui.scale, "f4")
            * get_rotation_matrix(gui.eulers)
            * Matrix44.from_translation(gui.translation, "f4")
            * Matrix44.from_translation((-8, -8, -8), "f4"),
        )

        normals_transform = Matrix44.from_y_rotation(-gui.eulers[1], "f4")
        self.uniform("m_normals").write(normals_transform)

        # render elements

        baked_faces = list[BakedFace]()

        for element in model.elements:
            element_transform = model_transform.copy()

            # TODO: rescale??
            if rotation := element.rotation:
                origin = np.array(rotation.origin)
                element_transform *= cast(
                    Matrix44,
                    Matrix44.from_translation(origin, "f4")
                    * get_rotation_matrix(rotation.eulers)
                    * Matrix44.from_translation(-origin, "f4"),
                )

            # prepare each face of the element for rendering
            for direction, face in element.faces.items():
                baked_face = BakedFace(
                    element=element,
                    direction=direction,
                    face=face,
                    m_model=element_transform,
                    texture_loc=texture_locs[face.texture_name],
                    texture=texture_vars[face.texture_name],
                    is_opaque=face.texture_name not in transparent_textures,
                )
                baked_faces.append(baked_face)

        # TODO: use a map if this is actually slow
        baked_faces.sort(key=lambda face: face.sortkey(self.eye))

        animation_length = max(len(face.texture.frames) for face in baked_faces)
        return [
            self._render_frame(baked_faces, debug, animation_tick)
            for animation_tick in range(animation_length)
        ]

    def _render_frame(self, baked_faces: list[BakedFace], debug: DebugType, tick: int):
        self.wnd.clear()

        for face in baked_faces:
            self.uniform("m_model").write(face.m_model)
            self.uniform("texture0").value = face.texture_loc
            self.uniform("layer").value = face.texture.get_frame_index(tick)

            face.vao.render(self.face_prog)

            if DebugType.NORMALS in debug:
                self.uniform("m_model", self.debug_normal_prog).write(face.m_model)
                face.vao.render(self.debug_normal_prog)

        if DebugType.AXES in debug:
            self.ctx.disable(mgl.CULL_FACE)
            for axis, color in self.debug_axes:
                self.uniform("color", self.debug_plane_prog).value = color
                axis.render(self.debug_plane_prog)
            self.ctx.enable(mgl.CULL_FACE)

        self.ctx.finish()

        image = Image.frombytes(
            mode="RGBA",
            size=self.wnd.fbo.size,
            data=self.wnd.fbo.read(components=4),
        ).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        return image

    def uniform(self, name: str, program: Program | None = None):
        program = program or self.face_prog
        assert isinstance(uniform := program[name], Uniform)
        return uniform


@dataclass(kw_only=True)
class BakedFace:
    element: Element
    direction: FaceName
    face: ElementFace
    m_model: Matrix44
    texture_loc: float
    texture: ModelTexture
    is_opaque: bool

    def __post_init__(self):
        self.verts = get_face_verts(self.element.from_, self.element.to, self.direction)

        self.normals = get_face_normals(self.direction)

        face_uv = self.face.uv or ElementFaceUV.default(self.element, self.direction)
        self.uvs = [
            value
            for index in get_face_uv_indices(self.direction)
            for value in face_uv.get_uv(index)
        ]

        self.vao = VAO()
        self.vao.buffer(np.array(self.verts, np.float32), "3f", ["in_position"])
        self.vao.buffer(np.array(self.normals, np.float32), "3f", ["in_normal"])
        self.vao.buffer(np.array(self.uvs, np.float32) / 16, "2f", ["in_texcoord_0"])

    @cached_property
    def position(self):
        x, y, z, n = 0, 0, 0, 0
        for i in range(0, len(self.verts), 3):
            x += self.verts[i]
            y += self.verts[i + 1]
            z += self.verts[i + 2]
            n += 1
        return (x / n, y / n, z / n)

    def sortkey(self, eye: Vec3):
        if self.is_opaque:
            return 0
        return sum((a - b) ** 2 for a, b in zip(eye, self.position))
