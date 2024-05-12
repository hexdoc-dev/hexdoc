import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from yarl import URL

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.minecraft.model import BlockModel
from hexdoc.utils import ValidationContext

from .renderer import ModelRenderer
from .texture import ModelTexture

logger = logging.getLogger(__name__)

MISSING_TEXTURE_ID = ResourceLocation("hexdoc", "textures/item/missing.png")

ModelLoaderStrategy = Callable[[BlockModel], URL | None]


@dataclass(kw_only=True)
class ModelLoader(ValidationContext):
    loader: ModResourceLoader
    renderer: ModelRenderer
    site_dir: Path
    site_url: URL  # this should probably be a relative path

    def __post_init__(self):
        # TODO: see cache comment in hexdoc.graphics.texture
        # (though it's less of an issue here since these aren't globals)
        self._model_cache = dict[ResourceLocation, URL]()
        self._texture_cache = dict[ResourceLocation, URL]()

        self._strategies: list[ModelLoaderStrategy] = [
            self._from_props,
            self._from_resources(internal=True),
            self._from_renderer,
            self._from_resources(internal=False),
        ]

    @property
    def props(self):
        return self.loader.props

    def render_block(self, block_id: ResourceLocation):
        return self.render_model("block" / block_id)

    def render_item(self, item_id: ResourceLocation):
        return self.render_model("item" / item_id)

    def render_model(self, model_id: ResourceLocation):
        model = self._load_model(model_id)
        if isinstance(model, URL):
            return model

        for override_model in self._get_overrides(model):
            if isinstance(override_model, URL):
                return override_model
            for strategy in self._strategies:
                logger.debug(f"Attempting model strategy: {strategy.__name__}")
                try:
                    if result := strategy(override_model):
                        self._model_cache[model_id] = result
                        self._model_cache[override_model.id] = result
                        return result
                except Exception:
                    # TODO: probably shouldn't just swallow all errors like this.
                    logger.debug(
                        f"Exception while rendering override: {override_model.id}",
                        exc_info=True,
                    )

        self._fail(f"All strategies failed to render model: {model_id}")

    def render_texture(self, texture_id: ResourceLocation) -> URL | None:
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

            self._fail(f"Failed to find texture: {texture_id}")

    def _fail(self, message: str):
        if self.props.textures.strict:
            raise ValueError(message)
        logger.error(message)
        return self.render_texture(MISSING_TEXTURE_ID)

    def _get_overrides(self, model: BlockModel):
        # TODO: implement (with _load_model)
        yield model

    def _load_model(self, model_id: ResourceLocation):
        if result := self._model_cache.get(model_id):
            logger.debug(f"Cache hit: {model_id} = {result}")
            return result

        _, model = BlockModel.load_and_resolve(self.loader, model_id)
        return model

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
            glob=texture_id.path + ".{png,gif}",
            allow_missing=True,
        ):
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

    def _from_props(self, model: BlockModel):
        match self.props.textures.overrides.models.get(model.id):
            case ResourceLocation() as texture_id:
                _, src = self.loader.find_resource("assets", "", texture_id)
                return self._render_existing_texture(src, model.id)
            case URL() as url:
                return url
            case None:
                logger.debug(f"No props override for model: {model.id}")
                return None

    def _from_resources(self, *, internal: bool):
        type_ = "internal" if internal else "external"

        def inner(model: BlockModel):
            if path := self._find_texture(
                model.id,
                folder="hexdoc/renders",
                internal=internal,
            ):
                return self._render_existing_texture(path, model.id)
            logger.debug(f"No {type_} rendered resource for model: {model.id}")

        inner.__name__ = f"_from_resources({internal=})"
        return inner

    def _from_renderer(self, model: BlockModel):
        fragment = self._get_fragment(model.id)
        suffix = self.renderer.render_model(model, self.site_dir / fragment)
        return self._fragment_to_url(fragment.with_suffix(suffix))
