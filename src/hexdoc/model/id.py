from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Self

from pydantic.json_schema import SkipJsonSchema

from hexdoc.core.loader import ModResourceLoader
from hexdoc.core.resource import ResourceLocation
from hexdoc.core.resource_dir import PathResourceDir
from hexdoc.utils import TRACE, JSONDict

from .base import HexdocModel
from .inline import InlineModel

logger = logging.getLogger(__name__)

# TODO: i'm pretty sure there's redundancy between id.py and inline.py


class IDModel(HexdocModel):
    id: SkipJsonSchema[ResourceLocation]
    resource_dir: SkipJsonSchema[PathResourceDir]

    @classmethod
    def load(
        cls,
        resource_dir: PathResourceDir,
        id: ResourceLocation,
        data: JSONDict,
        context: dict[str, Any],
    ) -> Self:
        logger.log(TRACE, f"Load {cls} at {id}")
        return cls.model_validate(
            data | {"id": id, "resource_dir": resource_dir},
            context=context,
        )


class ResourceModel(IDModel, InlineModel, ABC):
    @classmethod
    def load_id(cls, id: ResourceLocation, context: dict[str, Any]):
        loader = ModResourceLoader.of(context)
        resource_dir, data = cls.load_resource(id, loader)
        return cls.load(resource_dir, id, data, context)

    @classmethod
    @abstractmethod
    def load_resource(
        cls,
        id: ResourceLocation,
        loader: ModResourceLoader,
    ) -> tuple[PathResourceDir, JSONDict]: ...
