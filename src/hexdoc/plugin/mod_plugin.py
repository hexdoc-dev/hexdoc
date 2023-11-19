from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.resources import Package
from pathlib import Path
from typing import TYPE_CHECKING

from typing_extensions import override

from .types import HookReturn

if TYPE_CHECKING:
    from hexdoc.core import ModResourceLoader
    from hexdoc.minecraft.assets import HexdocAssetLoader


@dataclass(kw_only=True)
class ModPlugin(ABC):
    """Hexdoc plugin hooks that are tied to a specific Minecraft mod.

    If you want to render a web book, subclass `ModPluginWithBook` instead.

    Abstract methods are required. All other methods can optionally be implemented to
    override or add functionality to hexdoc.

    Non-mod-specific hooks are implemented with normal Pluggy hooks instead.
    """

    branch: str

    # required hooks

    @property
    @abstractmethod
    def modid(self) -> str:
        """The modid of the Minecraft mod version that this plugin represents.

        For example: `hexcasting`
        """

    @property
    @abstractmethod
    def full_version(self) -> str:
        """The full PyPI version of this plugin.

        This should generally return `your_plugin.__gradle_version__.FULL_VERSION`.

        For example: `0.11.1.1.0rc7.dev20`
        """

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """The hexdoc-specific component of this plugin's version number.

        This should generally return `your_plugin.__version__.PY_VERSION`.

        For example: `1.0.dev20`
        """

    # optional hooks

    @property
    def compat_minecraft_version(self) -> str | None:
        """The version of Minecraft supported by the mod that this plugin represents.

        If no plugins implement this, models and validation for all Minecraft versions
        may be used. Currently, if two or more plugins provide different values, an
        error will be raised.

        This should generally return `your_plugin.__gradle_version__.MINECRAFT_VERSION`.

        For example: `1.20.1`
        """
        return None

    @property
    def mod_version(self) -> str | None:
        """The Minecraft mod version that this plugin represents.

        This should generally return `your_plugin.__gradle_version__.GRADLE_VERSION`.

        For example: `0.11.1-7`
        """
        return None

    def resource_dirs(self) -> HookReturn[Package]:
        """The module(s) that contain your plugin's Minecraft resources to be rendered.

        For example: `your_plugin._export.generated`
        """
        return []

    def jinja_template_root(self) -> tuple[Package, str] | None:
        """The module that contains the folder with your plugin's Jinja templates, and
        the name of that folder.

        For example: `your_plugin, "_templates"`
        """
        return None

    def default_rendered_templates(self) -> dict[str | Path, str]:
        """Extra templates to be rendered by default when your plugin is active.

        The key is the output path, and the value is the template to import and render.

        This hook is not called if `props.template.render` is set, since that option
        overrides all default templates.
        """
        return {}

    # utils

    def site_path(self, versioned: bool):
        if versioned:
            return self.versioned_site_path
        return self.latest_site_path

    @property
    def site_root(self) -> Path:
        """Base path for all rendered web pages.

        For example:
        * URL: `https://gamma-delta.github.io/HexMod/v/0.11.1-7/1.0.dev20/en_us`
        * value: `v`
        """
        return Path("v")

    @property
    def versioned_site_path(self) -> Path:
        """Base path for the web pages for the current version.

        For example:
        * URL: `https://hexdoc.hexxy.media/book/v/1!0.1.0.dev0` (decoded)
        * value: `book/v/1!0.1.0.dev0`
        """
        return self.site_root / self.full_version

    @property
    def latest_site_path(self) -> Path:
        """Base path for the latest web pages for a given branch.

        For example:
        * URL: `https://gamma-delta.github.io/HexMod/v/latest/main/en_us`
        * value: `v/latest/main`
        """
        return self.site_root / "latest" / self.branch

    def asset_loader(
        self,
        loader: ModResourceLoader,
        *,
        site_url: str,
        asset_url: str,
        render_dir: Path,
    ) -> HexdocAssetLoader:
        # unfortunately, this is necessary to avoid some *real* ugly circular imports
        from hexdoc.minecraft.assets import HexdocAssetLoader

        return HexdocAssetLoader(
            loader=loader,
            site_url=site_url,
            asset_url=asset_url,
            render_dir=render_dir,
        )


class VersionedModPlugin(ModPlugin):
    """Like `ModPlugin`, but the versioned site path uses the plugin and mod version."""

    @property
    @abstractmethod
    @override
    def mod_version(self) -> str:
        ...

    @property
    @override
    def versioned_site_path(self) -> Path:
        """Base path for the web pages for the current version.

        For example:
        * URL: `https://gamma-delta.github.io/HexMod/v/0.11.1-7/1.0.dev20/en_us`
        * value: `v/0.11.1-7/1.0.dev20`
        """
        return self.site_root / self.mod_version / self.plugin_version


class ModPluginWithBook(VersionedModPlugin):
    """Like `ModPlugin`, but with extra hooks to support rendering a web book."""

    @abstractmethod
    @override
    def resource_dirs(self) -> HookReturn[Package]:
        ...

    def site_book_path(self, lang: str, versioned: bool) -> Path:
        if versioned:
            return self.versioned_site_book_path(lang)
        return self.latest_site_book_path(lang)

    def versioned_site_book_path(self, lang: str) -> Path:
        """Base path for the rendered web book for the current version.

        For example:
        * URL: `https://gamma-delta.github.io/HexMod/v/0.11.1-7/1.0.dev20/en_us`
        * value: `v/0.11.1-7/1.0.dev20/en_us`
        """
        return self.versioned_site_path / lang

    def latest_site_book_path(self, lang: str) -> Path:
        """Base path for the latest rendered web book for a given branch.

        For example:
        * URL: `https://gamma-delta.github.io/HexMod/v/latest/main/en_us`
        * value: `v/latest/main/en_us`
        """
        return self.latest_site_path / lang
