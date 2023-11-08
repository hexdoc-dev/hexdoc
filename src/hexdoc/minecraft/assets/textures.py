from __future__ import annotations

import logging
import re
from functools import cached_property
from pathlib import Path
from typing import Annotated, Iterator, Literal, Self

from pydantic import AfterValidator, Field, TypeAdapter, model_validator

from hexdoc.core import ItemStack, ModResourceLoader, Properties, ResourceLocation
from hexdoc.model import HexdocModel, InlineItemModel, InlineModel
from hexdoc.model.base import DEFAULT_CONFIG

from ..i18n import I18nContext, LocalizedStr
from ..tags import Tag

# 16x16 hashtag icon for tags
TAG_TEXTURE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAANUlEQVQ4y2NgGJRAXV39v7q6+n9cfGTARKllFBvAiOxMUjTevHmTkSouGPhAHA0DWnmBrgAANLIZgSXEQxIAAAAASUVORK5CYII="

# purple and black square
MISSING_TEXTURE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAACXBIWXMAAC4jAAAuIwF4pT92AAAAJElEQVQoz2NkwAF+MPzAKs7EQCIY1UAMYMQV3hwMHKOhRD8NAPogBA/DVsDEAAAAAElFTkSuQmCC"

NUM_GASLIGHTING_TEXTURES = 4


def normalize_texture_id(id: ResourceLocation) -> ResourceLocation:
    path = id.path.removeprefix("textures/")

    if not path.endswith(".png"):
        path += ".png"

    path = re.sub(r"^(item|block)s/", "\1/", path)

    return id.with_path(path)


TextureLocation = Annotated[ResourceLocation, AfterValidator(normalize_texture_id)]
"""A normalized resource location of a texture image in resources/assets/*/textures.

Path: `resources/assets/{namespace}/textures/{type}/{path}.png`

Format: `{namespace}:{type}/{path}.png`
"""

TextureLocationAdapter = TypeAdapter(TextureLocation, config=DEFAULT_CONFIG)


class Texture(InlineModel):
    file_id: TextureLocation
    url: str | None

    @classmethod
    def load_all(cls, root: Path, loader: ModResourceLoader):
        """Load all textures from all internal resource dirs.

        This is generally only called once.
        """
        for resource_dir, id, path in loader.find_resources(
            "assets",
            namespace="*",
            folder="textures",
            glob="**/*.png",
            allow_missing=True,
        ):
            # don't reexport external textures, since they won't be in this repo
            if resource_dir.external:
                continue

            relative_path = path.resolve().relative_to(root)
            url = f"{loader.props.env.asset_url}/{relative_path.as_posix()}"

            meta_path = path.with_suffix(".png.mcmeta")
            if meta_path.is_file():
                yield AnimatedTexture(
                    file_id=id,
                    url=url,
                    meta=AnimationMeta.model_validate_json(meta_path.read_bytes()),
                )
            else:
                yield Texture(file_id=id, url=url)

    @classmethod
    def load_id(cls, id: ResourceLocation, context: TextureContext):
        id = TextureLocationAdapter.validate_python(id)
        return cls.find(id, props=context.props, textures=context.png_textures)

    @classmethod
    def find(
        cls,
        *ids: ResourceLocation,
        props: Properties,
        textures: dict[TextureLocation, Texture],
    ):
        """Returns the first existing texture from the lookup table, or the "missing
        texture" texture if it's in `props.texture.missing`, or raises `KeyError`.

        This is called frequently and does not load any files.
        """
        for id in ids:
            id = TextureLocationAdapter.validate_python(id)
            if id in textures:
                return textures[id]

        # fallback/error
        message = f"No texture for {', '.join(str(i) for i in ids)}"

        for missing_id in props.textures.missing:
            for id in ids:
                if id.match(missing_id):
                    logging.getLogger(__name__).warning(message)
                    return Texture(file_id=id, url=MISSING_TEXTURE)

        raise ValueError(message)


class AnimatedTexture(Texture):
    meta: AnimationMeta

    @property
    def class_name(self):
        return self.file_id.class_name

    @property
    def time_seconds(self):
        return self.time / 20

    @cached_property
    def time(self):
        return sum(time for _, time in self._normalized_frames)

    @property
    def frames(self):
        start = 0
        for index, time in self._normalized_frames:
            yield AnimatedTextureFrame(
                index=index,
                start=start,
                time=time,
                animation_time=self.time,
            )
            start += time

    @property
    def _normalized_frames(self):
        """index, time"""
        animation = self.meta.animation

        for i, frame in enumerate(animation.frames):
            match frame:
                case int(index):
                    time = None
                case AnimationMetaFrame(index=index, time=time):
                    pass

            if index is None:
                index = i
            if time is None:
                time = animation.frametime

            yield index, time


class AnimatedTextureFrame(HexdocModel):
    index: int
    start: int
    time: int
    animation_time: int

    @property
    def start_percent(self):
        return self._format_time(self.start)

    @property
    def end_percent(self):
        return self._format_time(self.start + self.time, backoff=True)

    def _format_time(self, time: int, *, backoff: bool = False) -> str:
        percent = 100 * time / self.animation_time
        if backoff and percent < 100:
            percent -= 0.01
        return f"{percent:.2f}".rstrip("0").rstrip(".")


class AnimationMeta(HexdocModel):
    animation: AnimationMetaTag


class AnimationMetaTag(HexdocModel):
    interpolate: Literal[False]  # TODO: handle interpolation
    width: None = None  # TODO: handle non-square textures
    height: None = None
    frametime: int = 1
    frames: list[int | AnimationMetaFrame]


class AnimationMetaFrame(HexdocModel):
    index: int | None = None
    time: int | None = None


class TextureContext(I18nContext):
    png_textures: dict[TextureLocation, Texture] = Field(default_factory=dict)
    item_textures: dict[ResourceLocation, Texture] = Field(default_factory=dict)
    gaslighting_items: set[ResourceLocation] = Field(default_factory=set)

    @model_validator(mode="after")
    def _post_root(self) -> Self:
        self.gaslighting_items |= Tag.load(
            id=ResourceLocation("hexdoc", "gaslighting"),
            registry="items",
            context=self,
        ).value_ids_set

        return self


def get_item_texture(
    item: ResourceLocation | ItemStack,
    item_textures: dict[ResourceLocation, Texture],
) -> Texture:
    texture_id = TextureLocationAdapter.validate_python("item" / item.id)
    if texture_id not in item_textures:
        raise ValueError(f"No texture loaded for item: {item}")
    return item_textures[texture_id]


class ItemWithNormalTexture(InlineItemModel):
    id: ItemStack
    name: LocalizedStr
    texture: Texture

    @classmethod
    def load_id(cls, item: ItemStack, context: TextureContext):
        """Implements InlineModel."""
        return cls(
            id=item,
            name=context.i18n.localize_item(item),
            texture=get_item_texture(item, context.item_textures),
        )

    @property
    def gaslighting(self):
        return False


class ItemWithGaslightingTexture(InlineItemModel):
    id: ItemStack
    name: LocalizedStr
    textures: list[Texture]

    @classmethod
    def load_id(cls, item: ItemStack, context: TextureContext):
        """Implements InlineModel."""
        if item.id not in context.gaslighting_items:
            raise ValueError("Item does not have a gaslighting texture")
        return cls(
            id=item,
            name=context.i18n.localize_item(item),
            textures=list(cls._get_gaslit_ids(item, context.item_textures)),
        )

    @classmethod
    def _get_gaslit_ids(
        cls,
        item: ItemStack,
        item_textures: dict[ResourceLocation, Texture],
    ) -> Iterator[Texture]:
        for index in range(NUM_GASLIGHTING_TEXTURES):
            gaslit_id = item.id + f"_{index}"
            texture_id = TextureLocationAdapter.validate_python("item" / gaslit_id)
            yield get_item_texture(texture_id, item_textures)

    @property
    def gaslighting(self):
        return True


ItemWithTexture = ItemWithGaslightingTexture | ItemWithNormalTexture


class TagWithTexture(InlineModel):
    id: ResourceLocation
    name: LocalizedStr
    texture: Texture

    @classmethod
    def load_id(cls, id: ResourceLocation, context: TextureContext):
        return cls(
            id=id,
            name=context.i18n.localize_item_tag(id),
            texture=Texture(file_id=id, url=TAG_TEXTURE),
        )

    @property
    def gaslighting(self):
        return False
