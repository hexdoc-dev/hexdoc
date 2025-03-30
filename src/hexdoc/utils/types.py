import functools
from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Annotated, Any, Callable, Mapping, ParamSpec, Protocol, get_args

from ordered_set import OrderedSet, OrderedSetInitializer
from pydantic import (
    AfterValidator,
    GetCoreSchemaHandler,
    GetPydanticSchema,
    HttpUrl,
)
from pydantic_core import core_schema
from typing_extensions import TypeVar
from yarl import URL

_T = TypeVar("_T")

_P = ParamSpec("_P")
_R = TypeVar("_R")

_T_float = TypeVar("_T_float", default=float)


Vec2 = tuple[_T_float, _T_float]
Vec3 = tuple[_T_float, _T_float, _T_float]
Vec4 = tuple[_T_float, _T_float, _T_float, _T_float]


class Sortable(ABC):
    """ABC for classes which can be sorted."""

    @property
    @abstractmethod
    def _cmp_key(self) -> Any: ...

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Sortable):
            return self._cmp_key < other._cmp_key
        return NotImplemented


_T_Sortable = TypeVar("_T_Sortable", bound=Sortable)

_T_covariant = TypeVar("_T_covariant", covariant=True)


def sorted_dict(d: Mapping[_T, _T_Sortable]) -> dict[_T, _T_Sortable]:
    return dict(sorted(d.items(), key=lambda item: item[1]))


class IProperty(Protocol[_T_covariant]):
    def __get__(
        self,
        __instance: Any,
        __owner: type | None = None,
        /,
    ) -> _T_covariant: ...


FieldOrProperty = _T_covariant | IProperty[_T_covariant]


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
        type_arg: Any
        match len(type_args := get_args(source)):
            case 0:
                type_arg = Any
            case 1:
                type_arg = type_args[0]
            case n:
                raise ValueError(f"Expected 0 or 1 type args, got {n}: {type_args}")

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
        )

    def _get_items(self):
        return self.items


PydanticURL = Annotated[
    URL,
    GetPydanticSchema(
        lambda typ, handler: core_schema.union_schema(
            [
                core_schema.is_instance_schema(typ),
                core_schema.no_info_after_validator_function(
                    function=lambda raw: URL(raw.rstrip("/")),
                    schema=handler.generate_schema(Annotated[str, HttpUrl]),
                ),
            ],
            serialization=core_schema.plain_serializer_function_ser_schema(
                function=lambda url: str(url).rstrip("/"),
            ),
        )
    ),
]


def clamping_validator(lower: float | None, upper: float | None):
    def validator(value: float):
        lower_ = lower if lower is not None else value
        upper_ = upper if upper is not None else value
        return max(lower_, min(upper_, value))

    return AfterValidator(validator)


# short alias for convenience
clamped = clamping_validator


def typed_partial(f: Callable[_P, _R]) -> Callable[_P, Callable[_P, _R]]:
    """Given a function, returns a function that takes arguments for that function and
    returns a function that calls the original function with the partial arguments and
    whatever's passed into it.

    Basically, this is a more strongly typed version of `functools.partial`.
    """

    @functools.wraps(f)
    def builder_builder(*partial_args: _P.args, **partial_kwargs: _P.kwargs):
        @functools.wraps(f)
        def builder(*args: _P.args, **kwargs: _P.kwargs):
            return f(*partial_args, *args, **partial_kwargs, **kwargs)

        return builder

    return builder_builder


def cast_nullable(value: _T) -> _T | None:
    """Tells the type checker that the given value could also be `None`.

    At runtime, just returns the value as-is.
    """
    return value
