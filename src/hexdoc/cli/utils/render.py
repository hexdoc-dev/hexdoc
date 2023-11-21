# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportUnknownLambdaType=false, reportUnknownVariableType=false

import logging
import shutil
from pathlib import Path
from typing import Any, Sequence

from _hexdoc_favicons import Favicons
from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    PackageLoader,
    PrefixLoader,
    StrictUndefined,
    Template,
    TemplateNotFound,
)
from jinja2.sandbox import SandboxedEnvironment

from hexdoc.core import MinecraftVersion, Properties
from hexdoc.core.properties import JINJA_NAMESPACE_ALIASES
from hexdoc.data import HexdocMetadata
from hexdoc.jinja import (
    IncludeRawExtension,
    hexdoc_localize,
    hexdoc_texture,
    hexdoc_wrap,
)
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import AnimatedTexture, PNGTexture, TextureLookup
from hexdoc.patchouli import Book
from hexdoc.plugin import ModPluginWithBook, PluginManager
from hexdoc.utils import write_to_path

from .sitemap import MARKER_NAME, LatestSitemapMarker, VersionedSitemapMarker

logger = logging.getLogger(__name__)


class HexdocTemplateLoader(BaseLoader):
    def __init__(
        self,
        included: dict[str, PackageLoader],
        extra: dict[str, PackageLoader],
        props_file: Path,
    ):
        self.inner = ChoiceLoader(
            [
                PrefixLoader(included, ":"),
                *included.values(),
            ]
        )
        self.extra = extra
        self.props_file = props_file

    def get_source(self, environment: Environment, template: str):
        for alias, replacement in JINJA_NAMESPACE_ALIASES.items():
            if template.startswith(f"{alias}:"):
                logger.info(
                    f"Replacing {alias} with {replacement} for template {template}"
                )
                template = replacement + template.removeprefix(alias)
                break

        try:
            return self.inner.get_source(environment, template)
        except TemplateNotFound as e:
            for modid, loader in self.extra.items():
                try:
                    loader.get_source(environment, template)
                except TemplateNotFound:
                    continue
                e.add_note(
                    f'  note: try adding "{modid}" to props.template.include '
                    f"in {self.props_file.as_posix()}"
                )
            raise


def create_jinja_env(pm: PluginManager, include: Sequence[str], props_file: Path):
    included, extra = pm.load_jinja_templates(include)

    env = SandboxedEnvironment(
        loader=HexdocTemplateLoader(
            included=included,
            extra=extra,
            props_file=props_file,
        ),
        undefined=StrictUndefined,
        lstrip_blocks=True,
        trim_blocks=True,
        autoescape=True,
        extensions=[
            IncludeRawExtension,
        ],
    )

    env.filters |= {  # pyright: ignore[reportGeneralTypeIssues]
        "hexdoc_wrap": hexdoc_wrap,
        "hexdoc_localize": hexdoc_localize,
        "hexdoc_texture": hexdoc_texture,
    }

    return pm.update_jinja_env(env)


def render_book(
    *,
    props: Properties,
    pm: PluginManager,
    plugin: ModPluginWithBook,
    lang: str,
    book: Book,
    i18n: I18n,
    env: Environment,
    templates: dict[Path, Template],
    output_dir: Path,
    site_path: Path,
    all_metadata: dict[str, HexdocMetadata],
    png_textures: TextureLookup[PNGTexture],
    animations: list[AnimatedTexture],
    version: str,
    versioned: bool,
):
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    output_dir /= site_path
    page_url = "/".join([props.env.github_pages_url, *site_path.parts])

    logger.info(f"Rendering {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(props.template.icon, output_dir)

    with Favicons(props.template.icon, output_dir, base_url="") as favicons:
        favicons.sgenerate()
        favicons_html = favicons.html()
        favicons_formats = favicons.formats()

    lang_name = i18n.localize_lang()

    template_args: dict[str, Any] = {
        "book": book,
        "props": props,
        "i18n": i18n,
        "site_url": props.env.github_pages_url,
        "page_url": page_url,
        "version": version,
        "lang": lang,
        "lang_name": lang_name,
        "all_metadata": all_metadata,
        "png_textures": png_textures,
        "animations": animations,
        "is_bleeding_edge": version.startswith("latest"),
        "link_bases": book.link_bases,
        "favicons_html": favicons_html,
        "favicons_formats": favicons_formats,
        "icon_href": props.template.icon.name,
        "safari_pinned_tab_href": "https://raw.githubusercontent.com/object-Object/hexdoc/main/media/safari-pinned-tab.svg",
        "safari_pinned_tab_color": "#332233",
        "_": lambda key: hexdoc_localize(  # i18n helper
            key,
            do_format=False,
            props=props,
            book=book,
            i18n=i18n,
            pm=pm,
        ),
        "_f": lambda key: hexdoc_localize(  # i18n helper with patchi formatting
            key,
            do_format=True,
            props=props,
            book=book,
            i18n=i18n,
            pm=pm,
        ),
        **props.template.args,
    }
    pm.update_template_args(template_args)

    for filename, template in templates.items():
        file = template.render(template_args)
        stripped_file = strip_empty_lines(file)
        write_to_path(output_dir / filename, stripped_file)

    if props.template.static_dir:
        shutil.copytree(props.template.static_dir, output_dir, dirs_exist_ok=True)

    # redirect file for this book
    _, redirect_template_name = props.template.redirect
    redirect_template = env.get_template(redirect_template_name)
    redirect_contents = strip_empty_lines(redirect_template.render(template_args))

    # marker file for updating the sitemap later
    # we use this because matrix doesn't have outputs
    # this feels scuffed but it does work
    marker_path = "/" + "/".join(site_path.parts)
    is_default_lang = lang == props.default_lang
    minecraft_version = MinecraftVersion.get()

    if versioned:
        marker = VersionedSitemapMarker(
            version=version,
            lang=lang,
            lang_name=lang_name,
            path=marker_path,
            is_default_lang=is_default_lang,
            full_version=plugin.full_version,
            minecraft_version=minecraft_version,
            redirect_contents=redirect_contents,
            mod_version=plugin.mod_version,
            plugin_version=plugin.plugin_version,
        )
    else:
        marker = LatestSitemapMarker(
            version=version,
            lang=lang,
            lang_name=lang_name,
            path=marker_path,
            is_default_lang=is_default_lang,
            full_version=plugin.full_version,
            minecraft_version=minecraft_version,
            redirect_contents=redirect_contents,
            branch=plugin.branch,
            is_default_branch=plugin.branch == props.default_branch,
        )

    (output_dir / MARKER_NAME).write_text(marker.model_dump_json(), "utf-8")


def strip_empty_lines(text: str) -> str:
    return "\n".join(s for s in text.splitlines() if s.strip())
