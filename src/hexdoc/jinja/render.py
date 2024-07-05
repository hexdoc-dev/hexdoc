# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportUnknownLambdaType=false, reportUnknownVariableType=false

import logging
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from _hexdoc_favicons import Favicons
from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    PrefixLoader,
    StrictUndefined,
    Template,
    TemplateNotFound,
)
from jinja2.sandbox import SandboxedEnvironment

from hexdoc.core import MinecraftVersion, Properties, ResourceLocation
from hexdoc.core.properties import JINJA_NAMESPACE_ALIASES
from hexdoc.data.sitemap import MARKER_NAME, LatestSitemapMarker, VersionedSitemapMarker
from hexdoc.minecraft import I18n
from hexdoc.plugin import ModPluginWithBook, PluginManager
from hexdoc.utils import ContextSource, write_to_path

from .extensions import DefaultMacroExtension, IncludeRawExtension
from .filters import (
    hexdoc_item,
    hexdoc_localize,
    hexdoc_smart_var,
    hexdoc_texture,
    hexdoc_wrap,
)

logger = logging.getLogger(__name__)


class HexdocTemplateLoader(BaseLoader):
    def __init__(
        self,
        included: dict[str, BaseLoader],
        extra: dict[str, BaseLoader],
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
                logger.debug(
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

    env = create_jinja_env_with_loader(
        HexdocTemplateLoader(
            included=included,
            extra=extra,
            props_file=props_file,
        )
    )

    return pm.update_jinja_env(env, include)


def create_jinja_env_with_loader(loader: BaseLoader):
    env = SandboxedEnvironment(
        loader=loader,
        undefined=StrictUndefined,
        lstrip_blocks=True,
        trim_blocks=True,
        autoescape=True,
        extensions=[
            IncludeRawExtension,
            DefaultMacroExtension,
        ],
    )

    env.filters |= {  # pyright: ignore[reportAttributeAccessIssue]
        "hexdoc_wrap": hexdoc_wrap,
        "hexdoc_localize": hexdoc_localize,
        "hexdoc_texture": hexdoc_texture,
        "hexdoc_item": hexdoc_item,
        "hexdoc_smart_var": hexdoc_smart_var,
    }

    return env


def get_templates(
    *,
    props: Properties,
    pm: PluginManager,
    book: Any,
    context: ContextSource,
    env: Environment,
) -> dict[Path, tuple[Template, Mapping[str, Any]]]:
    assert props.template is not None

    if props.template.override_default_render:
        template_names = {k: (v, {}) for k, v in props.template.render.items()}
    else:
        template_names = pm.default_rendered_templates(
            modids=props.template.render_from,
            book=book,
            context=context,
        )

    template_names |= {k: (v, {}) for k, v in props.template.extend_render.items()}

    return {
        Path(path): (env.get_template(template_name), args)
        for path, (template_name, args) in template_names.items()
    }


def render_book(
    *,
    props: Properties,
    pm: PluginManager,
    plugin: ModPluginWithBook,
    lang: str,
    book_id: ResourceLocation,
    i18n: I18n,
    macros: dict[str, str],
    env: Environment,
    templates: dict[Path, tuple[Template, Mapping[str, Any]]],
    output_dir: Path,
    site_path: Path,
    version: str,
    versioned: bool,
    template_args: dict[str, Any],
):
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    output_dir /= site_path
    page_url = props.env.github_pages_url.joinpath(*site_path.parts)

    # eg. `/v/latest/main/en_us` -> `../../../..`, `/` -> `.`
    relative_site_url = "/".join(".." for _ in site_path.parts) or "."

    logger.info(f"Rendering {output_dir}.")

    output_dir.mkdir(parents=True, exist_ok=True)

    if icon := props.template.icon:
        icon_href = icon.name

        shutil.copy(icon, output_dir)

        with Favicons(icon, output_dir, base_url="") as favicons:
            favicons.sgenerate()
            favicons_html = favicons.html()
            favicons_formats = favicons.formats()
    else:
        icon_href = None
        favicons_html = []
        favicons_formats = []

    lang_name = i18n.localize_lang()

    minecraft_version = MinecraftVersion.get()

    template_args |= {
        "props": props,
        "i18n": i18n,
        "site_url": str(props.env.github_pages_url),
        "relative_site_url": relative_site_url,
        "page_url": str(page_url),
        "source_url": str(props.env.source_url),
        "version": version,
        "lang": lang,
        "lang_name": lang_name,
        "is_bleeding_edge": version.startswith("latest"),
        "favicons_html": favicons_html,
        "favicons_formats": favicons_formats,
        "icon_href": icon_href,
        "safari_pinned_tab_href": "https://raw.githubusercontent.com/hexdoc-dev/hexdoc/main/media/safari-pinned-tab.svg",
        "safari_pinned_tab_color": "#332233",
        "minecraft_version": minecraft_version or "???",
        "full_version": plugin.full_version,
        "navbar": {  # default navbar links (ignored if set in props)
            "center": [
                {"text": "GitHub", "href": {"variable": "source_url"}},
            ],
        },
        "_": lambda key: hexdoc_localize(  # i18n helper
            key,
            do_format=False,
            props=props,
            book_id=book_id,
            i18n=i18n,
            macros=macros,
            pm=pm,
        ),
        "_f": lambda key: hexdoc_localize(  # i18n helper with patchi formatting
            key,
            do_format=True,
            props=props,
            book_id=book_id,
            i18n=i18n,
            macros=macros,
            pm=pm,
        ),
        **props.template.args,
    }
    pm.update_template_args(template_args)

    for filename, (template, extra_args) in templates.items():
        file = template.render(template_args | dict(extra_args))
        stripped_file = strip_empty_lines(file)
        write_to_path(output_dir / filename, stripped_file)

    if props.template.static_dir:
        shutil.copytree(props.template.static_dir, output_dir, dirs_exist_ok=True)

    # redirect file for this book
    if props.template.redirect:
        _, redirect_template_name = props.template.redirect
        redirect_template = env.get_template(redirect_template_name)
        redirect_contents = strip_empty_lines(redirect_template.render(template_args))
    else:
        redirect_contents = ""

    # marker file for updating the sitemap later
    # we use this because matrix doesn't have outputs
    # this feels scuffed but it does work
    marker_path = "/" + "/".join(site_path.parts)
    is_default_lang = lang == props.default_lang

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
