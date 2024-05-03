from __future__ import annotations

import json
import logging
from collections import defaultdict
from functools import total_ordering
from typing import Any, Callable, Self

from pydantic import ValidationInfo, model_validator
from pydantic.functional_validators import ModelWrapValidatorHandler

from hexdoc.core import (
    ItemStack,
    ModResourceLoader,
    ResourceLocation,
    ValueIfVersion,
)
from hexdoc.core.properties import LangProps
from hexdoc.model import HexdocModel, ValidationContextModel
from hexdoc.model.base import DEFAULT_CONFIG
from hexdoc.utils import decode_and_flatten_json_dict
from hexdoc.utils.json_schema import inherited, json_schema_extra_config, type_str

logger = logging.getLogger(__name__)


@total_ordering
class LocalizedStr(HexdocModel, frozen=True):
    """Represents a string which has been localized."""

    model_config = DEFAULT_CONFIG | json_schema_extra_config(type_str, inherited)

    key: str
    value: str

    @classmethod
    def skip_i18n(cls, key: str) -> Self:
        """Returns an instance of this class with `value = key`."""
        return cls(key=key, value=key)

    @classmethod
    def with_value(cls, value: str) -> Self:
        """Returns an instance of this class with an empty key."""
        return cls(key="", value=value)

    @model_validator(mode="wrap")
    @classmethod
    def _check_localize(
        cls,
        value: str | Any,
        handler: ModelWrapValidatorHandler[Self],
        info: ValidationInfo,
    ) -> Self:
        # NOTE: if we need LocalizedStr to work as a dict key, add another check which
        # returns cls.skip_i18n(value) if info.context is falsy
        if not isinstance(value, str):
            return handler(value)

        i18n = I18n.of(info)
        return cls._localize(i18n, value)

    @classmethod
    def _localize(cls, i18n: I18n, key: str) -> Self:
        return cls.model_validate(i18n.localize(key))

    def map(self, fn: Callable[[str], str]) -> Self:
        """Returns a copy of this object with `new.value = fn(old.value)`."""
        return self.model_copy(update={"value": fn(self.value)})

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: Self | str | Any):
        match other:
            case LocalizedStr():
                return self.value == other.value
            case str():
                return self.value == other
            case _:
                return super().__eq__(other)

    def __lt__(self, other: Self | str):
        match other:
            case LocalizedStr():
                return self.value < other.value
            case str():
                return self.value < other


class LocalizedItem(LocalizedStr, frozen=True):
    @classmethod
    def _localize(cls, i18n: I18n, key: str) -> Self:
        return cls.model_validate(i18n.localize_item(key))


class I18n(ValidationContextModel):
    """Handles localization of strings."""

    lookup: dict[str, LocalizedStr]
    lang: str
    default_i18n: I18n | None
    enabled: bool
    lang_props: LangProps

    @classmethod
    def list_all(cls, loader: ModResourceLoader):
        # don't list languages which this particular mod doesn't support
        # eg. if Hex has translations for ru_ru but an addon doesn't
        return set(
            id.path
            for resource_dir, id, _ in cls._load_lang_resources(loader)
            if not resource_dir.external
        )

    @classmethod
    def load_all(cls, loader: ModResourceLoader, enabled: bool):
        # lang -> (key -> value)
        lookups = defaultdict[str, dict[str, LocalizedStr]](dict)
        internal_langs = set[str]()

        for resource_dir, lang_id, data in cls._load_lang_resources(loader):
            lang = lang_id.path
            lookups[lang] |= cls.parse_lookup(data)
            if not resource_dir.external:
                internal_langs.add(lang)

        default_lang = loader.props.default_lang
        default_lookup = lookups[default_lang]
        default_i18n = cls(
            lookup=default_lookup,
            lang=default_lang,
            default_i18n=None,
            enabled=enabled,
            lang_props=loader.props.lang[default_lang],
        )

        return {default_lang: default_i18n} | {
            lang: cls(
                lookup=lookup,
                lang=lang,
                default_i18n=default_i18n,
                enabled=enabled,
                lang_props=loader.props.lang[lang],
            )
            for lang, lookup in lookups.items()
            if lang in internal_langs and lang != default_lang
        }

    @classmethod
    def load(
        cls,
        loader: ModResourceLoader,
        enabled: bool,
        lang: str,
    ) -> Self:
        lookup = dict[str, LocalizedStr]()
        is_internal = False

        for resource_dir, _, data in cls._load_lang_resources(loader, lang):
            lookup |= cls.parse_lookup(data)
            if not resource_dir.external:
                is_internal = True

        if enabled and not is_internal:
            raise FileNotFoundError(
                f"Lang {lang} exists, but {loader.props.modid} does not support it"
            )

        default_lang = loader.props.default_lang
        default_i18n = None
        if lang != default_lang:
            default_i18n = cls.load(loader, enabled, default_lang)

        return cls(
            lookup=lookup,
            lang=lang,
            default_i18n=default_i18n,
            enabled=enabled,
            lang_props=loader.props.lang[lang],
        )

    @classmethod
    def parse_lookup(cls, raw_lookup: dict[str, str]) -> dict[str, LocalizedStr]:
        return {
            key: LocalizedStr(key=key, value=value.replace("%%", "%"))
            for key, value in raw_lookup.items()
        }

    @classmethod
    def _load_lang_resources(cls, loader: ModResourceLoader, lang: str = "*"):
        return loader.load_resources(
            "assets",
            namespace="*",
            folder="lang",
            glob=[
                f"{lang}.json",
                f"{lang}.json5",
                f"{lang}.flatten.json",
                f"{lang}.flatten.json5",
            ],
            decode=decode_and_flatten_json_dict,
            export=cls._export,
        )

    @classmethod
    def _export(cls, new: dict[str, str], current: dict[str, str] | None):
        return json.dumps((current or {}) | new)

    @model_validator(mode="after")
    def _warn_if_disabled(self):
        if not self.enabled:
            logger.info(
                f"I18n is disabled for {self.lang}. Warnings about missing translations"
                + " will only be logged in verbose mode."
            )
        elif self.lang_props.quiet:
            logger.info(
                f"Quiet mode is enabled for {self.lang}. Warnings about missing"
                + " translations will only be logged in verbose mode."
            )
        return self

    @property
    def is_default(self):
        return self.default_i18n is None

    def localize(
        self,
        *keys: str,
        default: str | None = None,
        silent: bool = False,
    ) -> LocalizedStr:
        """Looks up the given string in the lang table if i18n is enabled. Otherwise,
        returns the original key.

        If multiple keys are provided, returns the value of the first key which exists.
        That is, subsequent keys are treated as fallbacks for the first.

        Raises ValueError if i18n is enabled and default is None but the key has no
        corresponding localized value.
        """

        for key in keys:
            if key in self.lookup:
                return self.lookup[key]

        if silent or not self.enabled or self.lang_props.quiet:
            log_level = logging.DEBUG
        else:
            log_level = logging.WARNING

        log_keys = set(keys) - self._logged_missing_keys
        if log_keys:
            self._logged_missing_keys.update(log_keys)
            match list(log_keys):
                case [key]:
                    message = f"key {key}"
                case _:
                    message = "keys " + ", ".join(log_keys)
            logger.log(log_level, f"No translation in {self.lang} for {message}")

        if default is not None:
            return LocalizedStr.skip_i18n(default)

        if self.default_i18n:
            return self.default_i18n.localize(*keys, default=default, silent=silent)

        return LocalizedStr.skip_i18n(keys[0])

    def localize_pattern(
        self,
        op_id: ResourceLocation,
        silent: bool = False,
    ) -> LocalizedStr:
        """Localizes the given pattern id (internal name, eg. brainsweep).

        Raises ValueError if i18n is enabled but the key has no localization.
        """
        key_group = ValueIfVersion(">=1.20", "action", "spell")()

        # prefer the book-specific translation if it exists
        return self.localize(
            f"hexcasting.{key_group}.book.{op_id}",
            f"hexcasting.{key_group}.{op_id}",
            silent=silent,
        )

    def localize_item(
        self,
        item: str | ResourceLocation | ItemStack,
        silent: bool = False,
    ) -> LocalizedItem:
        """Localizes the given item resource name.

        Raises ValueError if i18n is enabled but the key has no localization.
        """
        match item:
            case str():
                item = ItemStack.from_str(item)
            case ResourceLocation(namespace=namespace, path=path):
                item = ItemStack(namespace=namespace, path=path)
            case _:
                pass

        localized = self.localize(
            item.i18n_key(),
            item.i18n_key("block"),
            silent=silent,
        )
        return LocalizedItem(key=localized.key, value=localized.value)

    def localize_entity(self, entity: ResourceLocation, type: str | None = None):
        if type:
            entity = type / entity
        return self.localize(entity.i18n_key("entity"))

    def localize_key(self, key: str, silent: bool = False) -> LocalizedStr:
        if not key.startswith("key."):
            key = "key." + key
        return self.localize(key, silent=silent)

    def localize_item_tag(self, tag: ResourceLocation, silent: bool = False):
        localized = self.localize(
            f"tag.{tag.namespace}.{tag.path}",
            f"tag.item.{tag.namespace}.{tag.path}",
            f"tag.block.{tag.namespace}.{tag.path}",
            default=self.fallback_tag_name(tag),
            silent=silent,
        )
        return LocalizedStr(key=localized.key, value=f"Tag: {localized.value}")

    def fallback_tag_name(self, tag: ResourceLocation):
        """Generates a more-or-less reasonable fallback name for a tag.

        For example:
        * `forge:ores` -> Ores
        * `c:saplings/almond` -> Almond Saplings
        * `c:tea_ingredients/gloopy/weak` -> Tea Ingredients, Gloopy, Weak
        """

        if tag.path.count("/") == 1:
            before, after = tag.path.split("/")
            return f"{after} {before}".title()

        return tag.path.replace("_", " ").replace("/", ", ").title()

    def localize_texture(self, texture_id: ResourceLocation, silent: bool = False):
        path = texture_id.path.removeprefix("textures/").removesuffix(".png")
        root, rest = path.split("/", 1)

        # TODO: refactor / extensibilify
        if root == "mob_effect":
            root = "effect"

        return self.localize(f"{root}.{texture_id.namespace}.{rest}", silent=silent)

    def localize_lang(self, silent: bool = False):
        name = self.localize("language.name", silent=silent)
        region = self.localize("language.region", silent=silent)
        return f"{name} ({region})"

    @model_validator(mode="after")
    def _init_logger_cache(self):
        self._logged_missing_keys = set[str]()
        return self
