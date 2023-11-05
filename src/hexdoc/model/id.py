from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Self, dataclass_transform

from hexdoc.core.loader import LoaderContext, ModResourceLoader
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir
from hexdoc.utils import JSONDict

from .base import HexdocModel, ValidationContext
from .inline import InlineModel


@dataclass_transform()
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
        logging.getLogger(__name__).debug(f"Load {cls} at {id}")
        return cls.model_validate(
            data | {"id": id, "resource_dir": resource_dir},
            context=context,
        )


@dataclass_transform()
class InlineIDModel(IDModel, InlineModel, ABC):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: LoaderContext):
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
