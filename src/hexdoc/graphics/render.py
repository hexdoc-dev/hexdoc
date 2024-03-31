# pyright: reportUnknownMemberType=false

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import importlib_resources as resources
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
from hexdoc.minecraft.models.base import FaceName, ModelElement
from hexdoc.minecraft.models.load import load_model

# https://minecraft.wiki/w/Help:Isometric_renders#Preferences
LIGHT_UP = 0.98
LIGHT_LEFT = 0.8
LIGHT_RIGHT = 0.608

FACE_ORDER = list[FaceName](["south", "east", "down", "west", "north", "up"])


@dataclass
class BlockRenderer:
    loader: ModResourceLoader

    def __post_init__(self):
        self.window = HeadlessWindow()
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

        files = resources.files(glsl)
        self.prog = self.ctx.program(
            vertex_shader=(files / "block_vertex.glsl").read_text("utf-8"),
            fragment_shader=(files / "block_fragment.glsl").read_text("utf-8"),
        )

        camera_size = 32  # TODO: value?
        self.projection = Matrix44.orthogonal_projection(
            left=-camera_size / 2,
            right=camera_size / 2,
            top=camera_size / 2,
            bottom=-camera_size / 2,
            near=0.01,
            far=20_000,
            dtype="f4",
        )
        self.uniform("m_proj").write(self.projection)

        self.camera = Matrix44.look_at(
            eye=(256, 64, 16),
            target=(0, 0, 16),
            up=(0, 1, 0),
            dtype="f4",
        )
        self.uniform("m_camera").write(self.camera)

        # TODO: implement animations
        self.uniform("layer").value = 0

    def render_block(
        self,
        model: BlockModel,
        texture_vars: dict[str, BlockTextureInfo],
    ):
        if not model.elements:
            raise ValueError("Unable to render model, no elements found")

        self.wnd.clear()

        textures = dict[str, int]()
        for i, (name, info) in enumerate(texture_vars.items()):
            textures[name] = i
            self.load_texture_array(
                path=str(info.image_path),
                layers=info.layers,
            ).use(i)

        model_transform = Matrix44.identity(dtype="f4")
        # model_transform *= Matrix44.from_translation((-8, -8, -8))

        # TODO: order??? (see docstring)
        # if gui := model.display.get("gui"):
        #     model_transform *= Matrix44.from_eulers(gui.eulers)
        #     model_transform *= Matrix44.from_translation(gui.translation)

        for element in model.elements:
            element_transform = model_transform.copy()
            # if rotation := element.rotation:
            #     # TODO: rescale??
            #     origin = np.array(rotation.origin)
            #     element_transform *= Matrix44.from_translation(-origin)
            #     element_transform *= Matrix44.from_eulers(rotation.eulers)
            #     element_transform *= Matrix44.from_translation(origin)

            self.uniform("m_model").write(element_transform)

            for direction in FACE_ORDER:
                if not (face := element.faces.get(direction)):
                    continue

                # TODO: face.rotation

                match direction:
                    case "up" | "down":
                        light = LIGHT_UP
                    case "north" | "south":
                        light = LIGHT_LEFT
                    case "east" | "west":
                        light = LIGHT_RIGHT

                self.uniform("light").value = light
                self.uniform("texture0").value = textures[face.texture.lstrip("#")]

                vao = get_element_face_vao(element, direction)

                vao.render(self.prog)

        self.ctx.finish()

        image = Image.frombytes(
            mode="RGBA",
            size=self.wnd.fbo.size,
            data=self.wnd.fbo.read(components=4),
        ).transpose(Image.FLIP_TOP_BOTTOM)

        image.save("out.png", format="png")

    def uniform(self, name: str):
        uniform = self.prog[name]
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


def get_element_face_vao(element: ModelElement, direction: FaceName) -> VAO:
    x1, y1, z1 = element.from_
    x2, y2, z2 = element.to

    face = element.faces[direction]
    if face.uv:
        u1, v1, u2, v2 = face.uv
    else:
        u1, v1, u2, v2 = get_default_uv(element, direction)

    # fmt: off
    match direction:
        case "south":
            verts = [
                x1 + x2, y1,      z1 + z2,
                x1 + x2, y1 + y2, z1 + z2,
                x1,      y1,      z1 + z2,
                x1 + x2, y1 + y2, z1 + z2,
                x1,      y1 + y2, z1 + z2,
                x1,      y1,      z1 + z2,
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
                x1 + x2, y1,      z1,
                x1 + x2, y1 + y2, z1,
                x1 + x2, y1,      z1 + z2,
                x1 + x2, y1 + y2, z1,
                x1 + x2, y1 + y2, z1 + z2,
                x1 + x2, y1,      z1 + z2,
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
                x1 + x2, y1,      z1,
                x1 + x2, y1,      z1 + z2,
                x1,      y1,      z1 + z2,
                x1 + x2, y1,      z1,
                x1,      y1,      z1 + z2,
                x1,      y1,      z1,
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
                x1,      y1,      z1 + z2,
                x1,      y1 + y2, z1 + z2,
                x1,      y1 + y2, z1,
                x1,      y1,      z1 + z2,
                x1,      y1 + y2, z1,
                x1,      y1,      z1,
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
                x1 + x2, y1 + y2, z1,
                x1 + x2, y1,      z1,
                x1,      y1,      z1,
                x1 + x2, y1 + y2, z1,
                x1,      y1,      z1,
                x1,      y1 + y2, z1,
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
                x1 + x2, y1 + y2, z1,
                x1,      y1 + y2, z1,
                x1 + x2, y1 + y2, z1 + z2,
                x1,      y1 + y2, z1,
                x1,      y1 + y2, z1 + z2,
                x1 + x2, y1 + y2, z1 + z2,
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
