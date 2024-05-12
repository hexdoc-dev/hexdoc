import logging
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from typing_extensions import override
from yarl import URL

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.graphics import ModelRenderer

from .model import BlockModel

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ModelLoader:
    loader: ModResourceLoader
    renderer: ModelRenderer
    site_dir: Path
    site_url: URL

    def __post_init__(self):
        self._cache = dict[ResourceLocation, URL]()

        self._strategies: list[ModelLoaderStrategy] = [
            FromProps(self),
            FromResources(self, internal=True),
            FromRenderer(self),
            FromResources(self, internal=False),
        ]

    @property
    def props(self):
        return self.loader.props

    def render_block(self, block_id: ResourceLocation):
        return self.render_model("block" / block_id)

    def render_item(self, item_id: ResourceLocation):
        return self.render_model("item" / item_id)

    def render_model(self, model_id: ResourceLocation):
        if result := self._cache.get(model_id):
            logger.debug(f"Cache hit: {model_id} = {result}")
            return result

        _, model = BlockModel.load_and_resolve(self.loader, model_id)
        for override_id, override_model in self._get_overrides(model_id, model):
            for strategy in self._strategies:
                try:
                    if result := strategy(override_id, override_model):
                        self._cache[model_id] = self._cache[override_id] = result
                        return result
                except Exception:
                    logger.debug(
                        f"Exception while rendering override: {override_id}",
                        exc_info=True,
                    )

        message = f"All strategies failed to render model: {model_id}"
        if self.props.textures.strict:
            raise ValueError(message)
        logger.error(message)

    def _get_overrides(self, model_id: ResourceLocation, model: BlockModel):
        # TODO: implement
        yield model_id, model


@dataclass
class ModelLoaderStrategy(ABC):
    ml: ModelLoader = field(repr=False)

    model_id: ResourceLocation = field(init=False, repr=False)
    model: BlockModel = field(init=False, repr=False)

    def __call__(self, model_id: ResourceLocation, model: BlockModel) -> URL | None:
        logger.debug(f"Attempting strategy: {self}")
        self.model_id = model_id
        self.model = model
        return self._execute()

    @abstractmethod
    def _execute(self) -> URL | None: ...

    def _from_existing_image(self, src: Path):
        fragment = self._get_fragment(src.suffix)
        shutil.copyfile(src, self.ml.site_dir / fragment)
        return self._fragment_to_url(fragment)

    def _get_fragment(self, suffix: str = ".png"):
        path = Path("renders") / self.model_id.namespace / self.model_id.path
        return path.with_suffix(suffix)

    def _fragment_to_url(self, fragment: Path):
        return self.ml.site_url.joinpath(*fragment.parts)


class FromProps(ModelLoaderStrategy):
    @override
    def _execute(self) -> URL | None:
        match self.ml.props.textures.overrides.models.get(self.model_id):
            case ResourceLocation() as texture_id:
                _, src = self.ml.loader.find_resource("assets", "", texture_id)
                return self._from_existing_image(src)
            case URL() as url:
                return url
            case None:
                logger.debug(f"No props override for model: {self.model_id}")
                return None


@dataclass
class FromResources(ModelLoaderStrategy):
    internal: bool

    @override
    def _execute(self) -> URL | None:
        preferred_suffix = self.ml.props.textures.animated.format.suffix

        src = None
        for resource_dir, _, path in self.ml.loader.find_resources(
            "assets",
            namespace=self.model_id.namespace,
            folder="hexdoc/renders",
            glob=self.model_id.path + ".{png,gif}",
            allow_missing=True,
        ):
            if resource_dir.internal == self.internal:
                src = path
                if path.suffix == preferred_suffix:
                    break

        if src:
            return self._from_existing_image(src)

        type_ = "internal" if self.internal else "external"
        logger.debug(f"No {type_} rendered resource for model: {self.model_id}")


class FromRenderer(ModelLoaderStrategy):
    @override
    def _execute(self) -> URL | None:
        fragment = self._get_fragment()
        suffix = self.ml.renderer.render_model(self.model, self.ml.site_dir / fragment)
        return self._fragment_to_url(fragment.with_suffix(suffix))
