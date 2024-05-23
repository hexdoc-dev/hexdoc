import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from yarl import URL

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.core.resource import BaseResourceLocation
from hexdoc.minecraft.model import BlockModel
from hexdoc.utils import ValidationContext

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

    @property
    def props(self):
        return self.loader.props

    def render_block(self, block_id: BaseResourceLocation) -> LoadedModel:
        return self.render_model("block" / block_id.id)

    def render_item(self, item_id: BaseResourceLocation) -> LoadedModel:
        return self.render_model("item" / item_id.id)

    def render_model(self, model_id: BaseResourceLocation) -> LoadedModel:
        model_id = model_id.id
        logger.debug(f"Rendering model: {model_id}")
        for override_id in self._get_overrides(model_id):
            logger.debug(f"Attempting override: {override_id}")
            for strategy in self._model_strategies:
                logger.debug(f"Attempting model strategy: {strategy.__name__}")
                try:
                    if result := strategy(override_id):
                        self._model_cache[model_id] = result
                        self._model_cache[override_id] = result
                        return result
                except Exception:
                    # TODO: probably shouldn't just swallow all errors like this.
                    logger.debug(
                        f"Exception while rendering override: {override_id}",
                        exc_info=True,
                    )

        return LoadedModel(self._fail(f"Failed to render model: {model_id}"))

    def render_texture(self, texture_id: ResourceLocation) -> URL:
        if result := self._texture_cache.get(texture_id):
            return result

        try:
            _, path = self.loader.find_resource("assets", "", texture_id)
            result = self._render_existing_texture(path, texture_id)
            self._texture_cache[texture_id] = result
            return result
        except FileNotFoundError:
            # prevent infinite recursion if something really weird happens
            # use RuntimeError instead of assert so Pydantic doesn't catch it
            if texture_id == MISSING_TEXTURE_ID:
                raise RuntimeError(
                    f"Built-in missing texture {MISSING_TEXTURE_ID} not found"
                    + " (this should never happen)"
                )

            return self._fail(f"Failed to find texture: {texture_id}")

    def _fail(self, message: str):
        if self.props.textures.strict:
            raise ValueError(message)
        logger.error(message)
        missing = self.render_texture(MISSING_TEXTURE_ID)
        assert missing is not None
        return missing

    def _get_overrides(self, model_id: ResourceLocation):
        # TODO: implement (maybe)
        yield model_id

    def _load_model(self, model_id: ResourceLocation) -> LoadedModel | BlockModel:
        if result := self._model_cache.get(model_id):
            logger.debug(f"Cache hit: {model_id} = {result}")
            return result

        try:
            _, model = BlockModel.load_and_resolve(self.loader, model_id)
            return model
        except Exception as e:
            return LoadedModel(self._fail(f"Failed to load model: {model_id}: {e}"))

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
            case ResourceLocation() as texture_id:
                _, src = self.loader.find_resource("assets", "", texture_id)
                return LoadedModel(self._render_existing_texture(src, model_id))
            case URL() as url:
                return LoadedModel(url)
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
        fragment = self._get_fragment(model_id)
        suffix, image_type = self.renderer.render_model(model, self.site_dir / fragment)
        return LoadedModel(
            self._fragment_to_url(fragment.with_suffix(suffix)),
            model,
            image_type,
        )
