from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Iterator, Self

from pydantic import Field

from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.core.resource import BaseResourceLocation
from hexdoc.model import HexdocModel
from hexdoc.utils import PydanticOrderedSet, decode_json_dict


@dataclass
class TagLoader:
    namespace: str
    registry: str
    path: str

    @property
    def id(self):
        return ResourceLocation(self.namespace, self.path)

    def load(self, loader: ModResourceLoader):
        return Tag.load(
            id=self.id,
            registry=self.registry,
            loader=loader,
        )


class OptionalTagValue(HexdocModel, frozen=True):
    id: ResourceLocation
    required: bool


TagValue = ResourceLocation | OptionalTagValue


class Tag(HexdocModel):
    GASLIGHTING_ITEMS: ClassVar = TagLoader("hexdoc", "items", "gaslighting")
    """Item/block ids that gaslight you. This tag isn't real, it's all in your head.

    File: `hexdoc/tags/items/gaslighting.json`
    """
    SPOILERED_ADVANCEMENTS: ClassVar = TagLoader("hexdoc", "advancements", "spoilered")
    """Advancements for entries that should be blurred in the web book.

    File: `hexdoc/tags/advancements/spoilered.json`
    """

    registry: str = Field(exclude=True)
    values: PydanticOrderedSet[TagValue]
    replace: bool = False

    @classmethod
    def load(
        cls,
        registry: str,
        id: ResourceLocation,
        loader: ModResourceLoader,
    ) -> Self:
        values = PydanticOrderedSet[TagValue]()
        replace = False

        for _, _, tag in loader.load_resources(
            "data",
            folder=f"tags/{registry}",
            id=id,
            decode=lambda raw_data: Tag._convert(
                registry=registry,
                raw_data=raw_data,
            ),
            # TODO: i have no idea why pyright doesn't like this.
            export=cls._export,  # pyright: ignore[reportGeneralTypeIssues]
        ):
            if tag.replace:
                values.clear()
            for value in tag._load_values(loader):
                values.add(value)

        return cls(registry=registry, values=values, replace=replace)

    @classmethod
    def _convert(cls, *, registry: str, raw_data: str) -> Self:
        data = decode_json_dict(raw_data)
        return cls.model_validate(data | {"registry": registry})

    @property
    def value_ids(self) -> Iterator[ResourceLocation]:
        for value in self.values:
            match value:
                case ResourceLocation():
                    yield value
                case OptionalTagValue(id=id):
                    yield id

    @property
    def value_ids_set(self):
        return set(self.value_ids)

    def __ror__(self, other: set[ResourceLocation]):
        new = set(other)
        new |= self.value_ids_set
        return new

    def __contains__(self, x: Any) -> bool:
        if isinstance(x, BaseResourceLocation):
            return x.id in self.value_ids_set
        return NotImplemented

    def _export(self, current: Self | None):
        if self.replace or current is None:
            tag = self
        else:
            tag = self.model_copy(
                update={"raw_values": current.values | self.values},
            )
        return tag.model_dump_json(by_alias=True)

    def _load_values(self, loader: ModResourceLoader) -> Iterator[TagValue]:
        for value in self.values:
            match value:
                case (
                    (ResourceLocation() as child_id)
                    | OptionalTagValue(id=child_id)
                ) if child_id.is_tag:
                    try:
                        child = Tag.load(self.registry, child_id, loader)
                        yield from child._load_values(loader)
                    except FileNotFoundError:
                        yield value
                case _:
                    yield value
