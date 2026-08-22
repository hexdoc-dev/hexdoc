import logging
from dataclasses import dataclass
from pathlib import Path
from traceback import TracebackException
from typing import Callable

from yarl import URL

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.core.properties import (
    ItemOverride,
    ModelOverride,
    TextureOverride,
    URLOverride,
)
from hexdoc.core.resource import BaseResourceLocation
from hexdoc.utils import ValidationContext
from hexdoc.utils.logging import TRACE

from .model import BlockModel
from .renderer import ImageType, ModelRenderer
from .texture import ModelTexture

logger = logging.getLogger(__name__)

MISSING_TEXTURE_ID = ResourceLocation("hexdoc", "textures/item/missing.png")
TAG_TEXTURE_ID = ResourceLocation("hexdoc", "textures/item/tag.png")


@dataclass
class LoadedModel:
    url: URL
    model: BlockModel | None = None
    image_type: ImageType = ImageType.UNKNOWN


ModelLoaderStrategy = Callable[[ResourceLocation], LoadedModel | None]


@dataclass(kw_only=True)
class ImageLoader(ValidationContext):
    loader: ModResourceLoader
    renderer: ModelRenderer
    site_dir: Path
    site_url: URL  # this should probably be a relative path

    def __post_init__(self):
        # TODO: see cache comment in hexdoc.graphics.texture
        # (though it's less of an issue here since these aren't globals)
        self._model_cache = dict[ResourceLocation, LoadedModel]()
        self._texture_cache = dict[ResourceLocation, URL]()

        self._model_strategies: list[ModelLoaderStrategy] = [
            self._from_props,
            self._from_resources(internal=True),
            self._from_renderer,
            self._from_resources(internal=False),
        ]

        self._overridden_models = set[ResourceLocation]()
        self._exceptions = list[Exception]()

    @property
    def props(self):
        return self.loader.props

    def render_block(self, block_id: BaseResourceLocation) -> LoadedModel:
        return self.render_model("block" / block_id.id)

    def render_item(self, item_id: BaseResourceLocation) -> LoadedModel:
        return self.render_model("item" / item_id.id)

    def render_model(self, model_id: BaseResourceLocation) -> LoadedModel:
        self._overridden_models.clear()
        self._exceptions.clear()
        try:
            return self._render_model_recursive(model_id.id)
        except Exception as e:
            if self._exceptions:
                # FIXME: hack
                # necessary because of https://github.com/Textualize/rich/issues/1859
                group = ExceptionGroup(
                    "Caught errors while rendering model",
                    self._exceptions,
                )
                traceback = "".join(TracebackException.from_exception(group).format())
                if e.args:
                    e.args = (f"{e.args[0]}\n{traceback}", *e.args[1:])
                else:
                    e.args = (traceback,)
            raise e
        finally:
            self._overridden_models.clear()
            self._exceptions.clear()

    def _render_model_recursive(self, model_id: ResourceLocation):
        logger.debug(f"Rendering model: {model_id}")
        for strategy in self._model_strategies:
            logger.debug(f"Attempting model strategy: {strategy.__name__}")
            try:
                if result := strategy(model_id):
                    self._model_cache[model_id] = result
                    return result
            except Exception as e:
                logger.debug(
                    f"Exception while rendering override: {model_id}",
                    exc_info=True,
                )
                self._exceptions.append(e)

        raise ValueError(f"Failed to render model: {model_id}")

    def render_texture(self, texture_id: ResourceLocation) -> URL:
        if result := self._texture_cache.get(texture_id):
            return result

        try:
            _, path = self.loader.find_resource("assets", "", texture_id)
            result = self._render_existing_texture(path, texture_id)
            self._texture_cache[texture_id] = result
            return result
        except FileNotFoundError:
            raise ValueError(f"Failed to find texture: {texture_id}")

    def _load_model(self, model_id: ResourceLocation) -> LoadedModel | BlockModel:
        if result := self._model_cache.get(model_id):
            logger.log(TRACE, f"Cache hit: {model_id} = {result}")
            return result

        try:
            _, model = BlockModel.load_and_resolve(self.loader, model_id)
            return model
        except Exception as e:
            raise ValueError(f"Failed to load model: {model_id}: {e}") from e

    def _render_existing_texture(self, src: Path, output_id: ResourceLocation):
        fragment = self._get_fragment(output_id, src.suffix)
        texture = ModelTexture.load(self.loader, src)
        suffix = self.renderer.save_image(self.site_dir / fragment, texture.frames)
        return self._fragment_to_url(fragment.with_suffix(suffix))

    def _get_fragment(self, output_id: ResourceLocation, suffix: str = ".png"):
        path = Path("renders") / output_id.namespace / output_id.path
        return path.with_suffix(suffix)

    def _fragment_to_url(self, fragment: Path):
        return self.site_url.joinpath(*fragment.parts)

    def _find_texture(
        self,
        texture_id: ResourceLocation,
        *,
        folder: str,
        internal: bool,
    ):
        preferred_suffix = self.props.textures.animated.format.suffix

        path = None
        prev_dir = None
        for resource_dir, _, path in self.loader.find_resources(
            "assets",
            namespace=texture_id.namespace,
            folder=folder,
            glob=texture_id.path + ".*",
            allow_missing=True,
        ):
            if path.suffix not in {".png", ".gif"}:
                continue
            # after we find a match, only keep looking in the same resource dir
            # so we don't break the load order
            if prev_dir and prev_dir != resource_dir:
                break
            if resource_dir.internal == internal:
                path = path
                prev_dir = resource_dir
                if path.suffix == preferred_suffix:
                    break
        return path

    # model rendering strategies

    def _from_props(self, model_id: ResourceLocation):
        match self.props.textures.overrides.models.get(model_id):
            case URLOverride(url=url, pixelated=pixelated):
                return LoadedModel(
                    url,
                    image_type=ImageType.ITEM if pixelated else ImageType.BLOCK,
                )
            case TextureOverride(texture=texture_id):
                return LoadedModel(self.render_texture(texture_id))
            case ModelOverride(model=override_model_id):
                return self.render_model(override_model_id)
            case ItemOverride(item=item_id):
                return self.render_item(item_id)
            case None:
                logger.debug(f"No props override for model: {model_id}")
                return None

    def _from_resources(self, *, internal: bool):
        type_ = "internal" if internal else "external"

        def inner(model_id: ResourceLocation):
            if path := self._find_texture(
                model_id,
                folder="hexdoc/renders",
                internal=internal,
            ):
                return LoadedModel(self._render_existing_texture(path, model_id))
            logger.debug(f"No {type_} rendered resource for model: {model_id}")

        inner.__name__ = f"_from_resources({internal=})"
        return inner

    def _from_renderer(self, model_id: ResourceLocation):
        model = self._load_model(model_id)
        if not isinstance(model, BlockModel):
            return model

        try:
            return self._from_model(model)
        except Exception as e:
            logger.debug(f"Failed to render model {model.id}: {e}")
            self._exceptions.append(e)

        if not model.overrides:
            return None

        if model.id in self._overridden_models:
            logger.debug(f"Skipping override check for recursive override: {model.id}")
            return None
        self._overridden_models.add(model.id)

        # TODO: implement a smarter way of choosing an override?
        n = len(model.overrides)
        for i, override in enumerate(model.overrides):
            logger.debug(f"Rendering model override ({i + 1}/{n}): {override.model}")
            try:
                return self._render_model_recursive(override.model)
            except Exception as e:
                logger.debug(f"Failed to render override {override.model}: {e}")
                self._exceptions.append(e)

    def _from_model(self, model: BlockModel):
        fragment = self._get_fragment(model.id)
        suffix, image_type = self.renderer.render_model(model, self.site_dir / fragment)
        return LoadedModel(
            self._fragment_to_url(fragment.with_suffix(suffix)),
            model,
            image_type,
        )
