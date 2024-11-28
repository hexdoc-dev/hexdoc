# pyright: reportPrivateUsage=false

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import (
    Any,
    ClassVar,
    Generator,
    Iterable,
    LiteralString,
    Self,
    TypeVar,
    Unpack,
)

import more_itertools
from pydantic import (
    ConfigDict,
    GetJsonSchemaHandler,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    model_validator,
)
from pydantic.functional_validators import ModelWrapValidatorHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import InitErrorDetails, PydanticCustomError, core_schema as cs
from typing_extensions import override

from hexdoc.core.resource import ResourceLocation
from hexdoc.plugin import PluginManager
from hexdoc.utils import (
    Inherit,
    InheritType,
    NoValue,
    NoValueType,
    classproperty,
)

from .base import HexdocModel

_T_UnionModel = TypeVar("_T_UnionModel", bound="UnionModel")

TagValue = str | NoValueType

_RESOLVED = "__resolved"

# sentinel value to check if we already loaded the tagged union subtypes hook
_is_loaded = False


class UnionModel(HexdocModel):
    @classmethod
    def _resolve_union(
        cls,
        value: Any,
        context: dict[str, Any] | None,
        *,
        model_types: Iterable[type[_T_UnionModel]],
        allow_ambiguous: bool,
        error_name: LiteralString = "HexdocUnionMatchError",
        error_text: Iterable[LiteralString] = [],
        error_data: dict[str, Any] = {},
    ) -> _T_UnionModel:
        # try all the types
        exceptions: list[InitErrorDetails] = []
        matches: dict[type[_T_UnionModel], _T_UnionModel] = {}

        for model_type in model_types:
            try:
                result = matches[model_type] = model_type.model_validate(
                    value,
                    context=context,
                )
                if allow_ambiguous:
                    return result
            except (ValueError, AssertionError, ValidationError) as e:
                exceptions.append(
                    InitErrorDetails(
                        type=PydanticCustomError(
                            error_name,
                            "{exception_class}: {exception}",
                            {
                                "exception_class": e.__class__.__name__,
                                "exception": str(e),
                            },
                        ),
                        loc=(
                            cls.__name__,
                            model_type.__name__,
                        ),
                        input=value,
                    )
                )

        # ensure we only matched one
        # if allow_ambiguous is True, we should have returned a value already
        match len(matches):
            case 1:
                return matches.popitem()[1]
            case x if x > 1:
                ambiguous_types = ", ".join(str(t) for t in matches.keys())
                reason = f"Ambiguous union match: {ambiguous_types}"
            case _:
                reason = "No match found"

        # something went wrong, raise an exception
        error = PydanticCustomError(
            f"{error_name}Group",
            "\n  ".join(
                (
                    "Failed to match union {class_name}: {reason}",
                    "Types: {types}",
                    "Value: {value}",
                    *error_text,
                )
            ),
            {
                "class_name": str(cls),
                "reason": reason,
                "types": ", ".join(str(t) for t in model_types),
                "value": repr(value),
                **error_data,
            },
        )

        if exceptions:
            exceptions.insert(
                0,
                InitErrorDetails(
                    type=error,
                    loc=(cls.__name__,),
                    input=value,
                ),
            )
            raise ValidationError.from_exception_data(error_name, exceptions)

        raise RuntimeError(str(error))


class InternallyTaggedUnion(UnionModel):
    """Implements [internally tagged unions](https://serde.rs/enum-representations.html#internally-tagged)
    using the [Registry pattern](https://charlesreid1.github.io/python-patterns-the-registry.html).

    To ensure your subtypes are loaded even if they're not imported by any file, add a
    Pluggy hook implementation for `hexdoc_load_tagged_unions() -> list[Package]`.

    Subclasses MUST NOT be generic unless they provide a default value for all
    `__init_subclass__` arguments. See pydantic/7171 for more info.

    Args:
        key: The dict key for the internal tag. If None, the parent's value is used.
        value: The expected tag value for this class. Should be None for types which
            shouldn't be instantiated (eg. abstract classes).
    """

    # inherited
    _tag_key: ClassVar[str | None] = None
    _tag_value: ClassVar[TagValue | None] = None

    # per-class
    __all_subtypes: ClassVar[set[type[Self]]]
    __concrete_subtypes: ClassVar[defaultdict[TagValue, set[type[Self]]]]

    def __init_subclass__(
        cls,
        *,
        key: str | InheritType | None = Inherit,
        value: TagValue | InheritType | None = Inherit,
        **kwargs: Unpack[ConfigDict],
    ):
        super().__init_subclass__(**kwargs)

        # inherited data
        if key is not Inherit:
            cls._tag_key = key
        if value is not Inherit:
            cls._tag_value = value

        # don't bother with rest of init if it's not part of a union
        if cls._tag_key is None:
            if cls._tag_value is None:
                return
            raise ValueError(
                f"Expected value=None for {cls} with key=None, got {value}"
            )

        # per-class data and lookups
        cls.__all_subtypes = set()
        cls.__concrete_subtypes = defaultdict(set)

        # add to all the parents
        for supertype in cls._supertypes():
            supertype.__all_subtypes.add(cls)
            if cls._tag_value is not None:
                supertype.__concrete_subtypes[cls._tag_value].add(cls)

    @classmethod
    def _tag_key_or_raise(cls) -> str:
        if cls._tag_key is None:
            raise NotImplementedError
        return cls._tag_key

    @classmethod
    def _supertypes(cls) -> Generator[type[InternallyTaggedUnion], None, None]:
        tag_key = cls._tag_key_or_raise()

        # we consider a type to be its own supertype/subtype
        yield cls

        # recursively yield bases
        # stop when we reach a non-union or a type with a different key (or no key)
        for base in cls.__bases__:
            if issubclass(base, InternallyTaggedUnion) and base._tag_key == tag_key:
                yield from base._supertypes()

    @model_validator(mode="wrap")
    @classmethod
    def _resolve_from_dict(
        cls,
        value: Any,
        handler: ModelWrapValidatorHandler[Self],
        info: ValidationInfo,
    ) -> Self:
        pm = PluginManager.of(info)

        # load plugins from entry points
        global _is_loaded
        if not _is_loaded:
            more_itertools.consume(pm.load_tagged_unions())
            _is_loaded = True

        # do this early so we know it's part of a union before returning anything
        tag_key = cls._tag_key_or_raise()

        # if it's already instantiated, just return it; otherwise ensure it's a dict
        match value:
            case InternallyTaggedUnion() if isinstance(value, cls):
                return value
            case dict() if _RESOLVED not in value:
                data: dict[str, Any] = value
                data[_RESOLVED] = True
            case _:
                return handler(value)

        # tag value, eg. "minecraft:crafting_shaped"
        tag_value = data.get(tag_key, NoValue)

        # list of matching types, eg. [ShapedCraftingRecipe, ModConditionalShapedCraftingRecipe]
        tag_types = cls.__concrete_subtypes.get(tag_value)
        if tag_types is None:
            raise TypeError(f"Unhandled tag: {tag_key}={tag_value} for {cls}: {data}")

        try:
            return cls._resolve_union(
                data,
                info.context,
                model_types=tag_types,
                allow_ambiguous=False,
                error_name="TaggedUnionMatchError",
                error_text=[
                    "Tag: {tag_key}={tag_value}",
                ],
                error_data={
                    "tag_key": cls._tag_key,
                    "tag_value": tag_value,
                },
            )
        except Exception:
            if _RESOLVED in data:
                data.pop(_RESOLVED)  # avoid interfering with other types
            raise

    @model_validator(mode="before")
    def _pop_temporary_keys(cls, value: Any) -> Any:
        if isinstance(value, dict) and _RESOLVED in value:
            # copy because this validator may be called multiple times
            # eg. two types with the same key
            value = value.copy()
            value.pop(_RESOLVED)
            assert value.pop(cls._tag_key, NoValue) == cls._tag_value
        return value  # pyright: ignore[reportUnknownVariableType]

    @classmethod
    @override
    def __get_pydantic_json_schema__(
        cls,
        core_schema: cs.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        base_schema = handler.resolve_ref_schema(
            super().__get_pydantic_json_schema__(core_schema, handler)
        )

        if cls._tag_key is None:
            return base_schema

        properties = base_schema.setdefault("properties", {})

        properties[cls._tag_key] = handler(cs.literal_schema([cls._tag_value]))
        base_schema.setdefault("required", []).append(cls._tag_key)

        if cls._tag_value is not None:
            return base_schema

        subtypes = {
            subtype
            for subtypes in cls.__concrete_subtypes.values()
            for subtype in subtypes
            if subtype is not cls
        }
        if not subtypes:
            return base_schema

        union_schema = cs.union_schema(
            [subtype.__pydantic_core_schema__ for subtype in subtypes],
        )
        json_schema = handler.resolve_ref_schema(handler(union_schema))

        if any_of := json_schema.get("anyOf"):
            other_schema = base_schema | {
                "additionalProperties": True,
                "properties": (
                    properties
                    | {
                        cls._tag_key: {
                            "allOf": [
                                handler(cls._tag_value_schema),
                                {
                                    "not": handler(
                                        cs.union_schema(
                                            [
                                                cs.literal_schema([subtype._tag_value])
                                                for subtype in subtypes
                                                if subtype._tag_value
                                                not in {None, NoValue}
                                            ]
                                        )
                                    )
                                },
                            ],
                        },
                    }
                ),
            }
            any_of.append(other_schema)

        return json_schema

    @classproperty
    @classmethod
    def _tag_value_type(cls) -> type[Any]:
        return str

    @classproperty
    @classmethod
    def _tag_value_schema(cls):
        return TypeAdapter(cls._tag_value_type).core_schema


class TypeTaggedUnion(InternallyTaggedUnion, key="type", value=None):
    _type: ClassVar[ResourceLocation | NoValueType | None] = None

    def __init_subclass__(
        cls,
        *,
        type: TagValue | InheritType | None = Inherit,
        **kwargs: Unpack[ConfigDict],
    ):
        super().__init_subclass__(value=type, **kwargs)

        match cls._tag_value:
            case str(raw_value):
                cls._type = ResourceLocation.from_str(raw_value)
            case value:
                cls._type = value

    @classproperty
    @classmethod
    def type(cls):
        return cls._type

    @classproperty
    @classmethod
    @override
    def _tag_value_type(cls) -> type[Any]:
        return ResourceLocation


class TemplateModel(HexdocModel, ABC):
    _template_id: ClassVar[ResourceLocation | None] = None

    def __init_subclass__(
        cls,
        *,
        template_id: str | ResourceLocation | InheritType | None = None,
        **kwargs: Unpack[ConfigDict],
    ) -> None:
        super().__init_subclass__(**kwargs)
        match template_id:
            case str():
                cls._template_id = ResourceLocation.from_str(template_id)
            case ResourceLocation() | None:
                cls._template_id = template_id
            case InheritType():
                pass

    @classproperty
    @classmethod
    @abstractmethod
    def template(cls) -> str:
        """Returns the Jinja template path for this class without any file extension.

        For example, return `"pages/{path}"`, not `"pages/{path}.html.jinja"`.
        """

    @classproperty
    @classmethod
    def template_id(cls):
        assert cls._template_id is not None, f"Template id not initialized: {cls}"
        return cls._template_id


class TypeTaggedTemplate(TypeTaggedUnion, TemplateModel, ABC, type=None):
    def __init_subclass__(
        cls,
        *,
        type: str | InheritType | None = Inherit,
        template_type: str | ResourceLocation | None = None,
        **kwargs: Unpack[ConfigDict],
    ) -> None:
        if template_type is None:
            match type:
                case str():
                    template_type = type
                case InheritType() if isinstance(cls.type, ResourceLocation):
                    template_type = cls.type
                case _:
                    pass

        super().__init_subclass__(
            type=type,
            # pyright doesn't seem to understand multiple inheritance here
            template_id=template_type,  # pyright: ignore[reportCallIssue]
            **kwargs,
        )
