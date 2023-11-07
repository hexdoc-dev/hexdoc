from importlib.resources import Package

import hexdoc
from hexdoc.plugin import (
    LoadJinjaTemplatesImpl,
    LoadTaggedUnionsImpl,
    hookimpl,
)

from .page import pages


class PatchouliPlugin(LoadTaggedUnionsImpl, LoadJinjaTemplatesImpl):
    @staticmethod
    @hookimpl
    def hexdoc_load_tagged_unions() -> Package | list[Package]:
        return pages

    @staticmethod
    @hookimpl
    def hexdoc_load_jinja_templates() -> tuple[Package, str]:
        return hexdoc, "_templates"
