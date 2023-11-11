from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Self

from hexdoc.core.loader import LoaderContext, ModResourceLoader
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir
from hexdoc.utils import JSONDict, isinstance_or_raise

from .base import HexdocModel, ValidationContext
from .inline import InlineModel

logger = logging.getLogger(__name__)

# TODO: i'm pretty sure there's redundancy between id.py and inline.py


class IDModel(HexdocModel):
    id: ResourceLocation
    resource_dir: PathResourceDir

    @classmethod
    def load(
        cls,
        resource_dir: PathResourceDir,
        id: ResourceLocation,
        data: JSONDict,
        context: ValidationContext,
    ) -> Self:
        logger.debug(f"Load {cls} at {id}")
        return cls.model_validate(
            data | {"id": id, "resource_dir": resource_dir},
            context=context,
        )


class ResourceModel(IDModel, InlineModel, ABC):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: ValidationContext):
        assert isinstance_or_raise(context, LoaderContext)
        resource_dir, data = cls.load_resource(id, context.loader)
        return cls.load(resource_dir, id, data, context)

    @classmethod
    @abstractmethod
    def load_resource(
        cls,
        id: ResourceLocation,
        loader: ModResourceLoader,
    ) -> tuple[PathResourceDir, JSONDict]:
        ...
