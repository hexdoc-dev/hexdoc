from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Annotated, Any, Mapping, Protocol, TypeVar, get_args

from ordered_set import OrderedSet, OrderedSetInitializer
from pydantic import AfterValidator, GetCoreSchemaHandler, HttpUrl
from pydantic_core import core_schema

_T = TypeVar("_T")


class Sortable(ABC):
    """ABC for classes which can be sorted."""

    @property
    @abstractmethod
    def _cmp_key(self) -> Any:
        ...

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Sortable):
            return self._cmp_key < other._cmp_key
        return NotImplemented


_T_Sortable = TypeVar("_T_Sortable", bound=Sortable)

_T_covariant = TypeVar("_T_covariant", covariant=True)


def sorted_dict(d: Mapping[_T, _T_Sortable]) -> dict[_T, _T_Sortable]:
    return dict(sorted(d.items(), key=lambda item: item[1]))


class IProperty(Protocol[_T_covariant]):
    def __get__(self, __instance: Any, __owner: type | None = None, /) -> _T_covariant:
        ...


@unique
class TryGetEnum(Enum):
    @classmethod
    def get(cls, value: Any):
        try:
            return cls(value)
        except ValueError:
            return None


# https://docs.pydantic.dev/latest/concepts/types/#generic-containers
class PydanticOrderedSet(OrderedSet[_T]):
    def __init__(self, initial: OrderedSetInitializer[_T] | None = None):
        super().__init__(initial or [])

    @classmethod
    def collect(cls, *initial: _T):
        return cls(initial)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        match get_args(source):
            case [type_arg]:
                pass
            case []:
                type_arg = Any
            case args:
                raise ValueError(f"Expected 0 or 1 type args, got {len(args)}: {args}")

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls),
                cls._get_non_instance_schema(type_arg, handler),
            ],
            serialization=cls._get_ser_schema(type_arg, handler),
        )

    @classmethod
    def _get_non_instance_schema(
        cls,
        type_arg: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        # validate from OrderedSetInitializer
        return core_schema.no_info_after_validator_function(
            function=PydanticOrderedSet,
            schema=handler.generate_schema(OrderedSetInitializer[type_arg]),
        )

    @classmethod
    def _get_ser_schema(
        cls,
        type_arg: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.SerSchema:
        # serialize to list
        return core_schema.plain_serializer_function_ser_schema(
            function=cls._get_items,
            return_schema=handler.generate_schema(list[type_arg]),
        )

    def _get_items(self):
        return self.items


NoTrailingSlashHttpUrl = Annotated[
    str,
    HttpUrl,
    AfterValidator(lambda u: str(u).rstrip("/")),
]


def clamping_validator(lower: float, upper: float):
    def validator(value: float):
        return max(lower, min(upper, value))

    return AfterValidator(validator)
