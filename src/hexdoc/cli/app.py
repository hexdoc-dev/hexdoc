import code
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Any, Optional

import typer
from packaging.version import Version
from typer import Argument, Option
from yarl import URL

from hexdoc.__version__ import VERSION
from hexdoc.core import ModResourceLoader, ResourceLocation
from hexdoc.data.metadata import HexdocMetadata
from hexdoc.data.sitemap import (
    delete_updated_books,
    dump_sitemap,
    load_sitemap,
)
from hexdoc.graphics.render import BlockRenderer, DebugType
from hexdoc.jinja.render import create_jinja_env, get_templates, render_book
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import (
    AnimatedTexture,
    PNGTexture,
    TextureContext,
)
from hexdoc.minecraft.assets.load_assets import render_block
from hexdoc.minecraft.models.item import ItemModel
from hexdoc.minecraft.models.load import load_model
from hexdoc.patchouli import BookContext, FormattingContext
from hexdoc.plugin import ModPluginWithBook
from hexdoc.utils import git_root, setup_logging, write_to_path
from hexdoc.utils.logging import repl_readfunc

from . import ci
from .utils.args import (
    DEFAULT_MERGE_DST,
    DEFAULT_MERGE_SRC,
    BranchOption,
    DefaultTyper,
    PathArgument,
    PropsOption,
    ReleaseOption,
    VerbosityOption,
)
from .utils.load import (
    init_context,
    load_common_data,
    render_textures_and_export_metadata,
)

logger = logging.getLogger(__name__)


def set_default_env():
    """Sets placeholder values for unneeded environment variables."""
    for key, value in {
        "GITHUB_REPOSITORY": "placeholder/placeholder",
        "GITHUB_SHA": "",
        "GITHUB_PAGES_URL": "",
    }.items():
        os.environ.setdefault(key, value)


@dataclass(kw_only=True)
class LoadedBookInfo:
    language: str
    i18n: I18n
    context: dict[str, Any]
    book_id: ResourceLocation
    book: Any


app = DefaultTyper()
app.add_typer(ci.app)


def version_callback(value: bool):
    if value:
        print(f"hexdoc {VERSION}")
        raise typer.Exit()


@app.callback()
def callback(
    verbosity: VerbosityOption = 0,
    quiet_lang: Optional[list[str]] = None,
    version: Annotated[
        bool,
        Option("--version", "-V", callback=version_callback, is_eager=True),
    ] = False,
):
    if quiet_lang:
        logger.warning(
            "`--quiet-lang` is deprecated, use `props.lang.{lang}.quiet` instead."
        )
    setup_logging(verbosity, ci=False, quiet_langs=quiet_lang)


@app.command()
def repl(*, props_file: PropsOption):
    """Start a Python shell with some helpful extra locals added from hexdoc."""

    repl_locals = dict[str, Any](
        props_path=props_file,
    )

    try:
        props, pm, book_plugin, plugin = load_common_data(props_file, branch="")
        repl_locals |= dict(
            props=props,
            pm=pm,
            plugin=plugin,
        )

        loader = ModResourceLoader.load_all(
            props,
            pm,
            export=False,
        )
        repl_locals["loader"] = loader

        if props.book_id:
            book_id, book_data = book_plugin.load_book_data(props.book_id, loader)
        else:
            book_id = None
            book_data = {}

        i18n = I18n.load_all(
            loader,
            enabled=book_plugin.is_i18n_enabled(book_data),
        )[props.default_lang]

        all_metadata = loader.load_metadata(model_type=HexdocMetadata)
        repl_locals["all_metadata"] = all_metadata

        if book_id and book_data:
            context = init_context(
                book_id=book_id,
                book_data=book_data,
                pm=pm,
                loader=loader,
                i18n=i18n,
                all_metadata=all_metadata,
            )
            book = book_plugin.validate_book(book_data, context=context)
            repl_locals |= dict(
                book=book,
                context=context,
            )
    except Exception as e:
        print(e)

    code.interact(
        banner=dedent(
            f"""\
            [hexdoc repl] Python {sys.version}
            Locals: {', '.join(sorted(repl_locals.keys()))}"""
        ),
        readfunc=repl_readfunc(),
        local=repl_locals,
        exitmsg="",
    )


@app.command()
def build(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    clean: bool = False,
    props_file: PropsOption,
) -> Path:
    """Export resources and render the web book.

    For developers: returns the site path (eg. `/v/latest/main`).
    """

    props, pm, book_plugin, plugin = load_common_data(props_file, branch)

    if props.env.hexdoc_subdirectory:
        output_dir /= props.env.hexdoc_subdirectory

    logger.info("Exporting resources.")
    with ModResourceLoader.clean_and_load_all(props, pm, export=True) as loader:
        site_path = plugin.site_path(versioned=release)
        site_dir = output_dir / site_path

        asset_loader = plugin.asset_loader(
            loader=loader,
            site_url=props.env.github_pages_url.joinpath(*site_path.parts),
            asset_url=props.env.asset_url,
            render_dir=site_dir,
        )

        all_metadata = render_textures_and_export_metadata(loader, asset_loader)

        if not props.book_id:
            logger.info("Skipping book load because props.book_id is not set.")
            return site_dir

        book_id, book_data = book_plugin.load_book_data(props.book_id, loader)

        all_i18n = I18n.load_all(
            loader,
            enabled=book_plugin.is_i18n_enabled(book_data),
        )

        logger.info("Loading books for all languages.")
        books = list[LoadedBookInfo]()
        for language, i18n in all_i18n.items():
            try:
                context = init_context(
                    book_id=book_id,
                    book_data=book_data,
                    pm=pm,
                    loader=loader,
                    i18n=i18n,
                    all_metadata=all_metadata,
                )
                book = book_plugin.validate_book(book_data, context=context)
                books.append(
                    LoadedBookInfo(
                        language=language,
                        i18n=i18n,
                        context=context,
                        book_id=book_id,
                        book=book,
                    )
                )
            except Exception:
                if not props.lang[language].ignore_errors:
                    raise
                logger.exception(f"Failed to load book for {language}")

        if not props.template:
            logger.info("Skipping book render because props.template is not set.")
            return site_dir

        if not isinstance(plugin, ModPluginWithBook):
            raise ValueError(
                f"ModPlugin registered for modid `{props.modid}` (from props.modid)"
                f" does not inherit from ModPluginWithBook: {plugin}"
            )

        logger.info("Setting up Jinja template environment.")
        env = create_jinja_env(pm, props.template.include, props_file)

        logger.info(f"Rendering book for {len(books)} language(s).")
        for book_info in books:
            try:
                templates = get_templates(
                    props=props,
                    pm=pm,
                    book=book_info.book,
                    context=book_info.context,
                    env=env,
                )
                if not templates:
                    raise RuntimeError(
                        "No templates to render, check your props.template configuration "
                        f"(in {props_file.as_posix()})"
                    )

                book_ctx = BookContext.of(book_info.context)
                formatting_ctx = FormattingContext.of(book_info.context)
                texture_ctx = TextureContext.of(book_info.context)

                site_book_path = plugin.site_book_path(
                    book_info.language,
                    versioned=release,
                )
                if clean:
                    shutil.rmtree(output_dir / site_book_path, ignore_errors=True)

                template_args: dict[str, Any] = book_info.context | {
                    "all_metadata": all_metadata,
                    "png_textures": PNGTexture.get_lookup(texture_ctx.textures),
                    "animations": sorted(  # this MUST be sorted to avoid flaky tests
                        AnimatedTexture.get_lookup(texture_ctx.textures).values(),
                        key=lambda t: t.css_class,
                    ),
                    "book": book_info.book,
                    "book_links": book_ctx.book_links,
                }

                render_book(
                    props=props,
                    pm=pm,
                    plugin=plugin,
                    lang=book_info.language,
                    book_id=book_info.book_id,
                    i18n=book_info.i18n,
                    macros=formatting_ctx.macros,
                    env=env,
                    templates=templates,
                    output_dir=output_dir,
                    version=plugin.mod_version if release else f"latest/{branch}",
                    site_path=site_book_path,
                    versioned=release,
                    template_args=template_args,
                )
            except Exception:
                if not props.lang[book_info.language].ignore_errors:
                    raise
                logger.exception(f"Failed to render book for {book_info.language}")

    logger.info("Done.")
    return site_dir


@app.command()
def merge(
    *,
    props_file: PropsOption,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
    release: ReleaseOption = False,
):
    props, _, _, plugin = load_common_data(props_file, branch="", book=True)
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    if props.env.hexdoc_subdirectory:
        src /= props.env.hexdoc_subdirectory
        dst /= props.env.hexdoc_subdirectory

    dst.mkdir(parents=True, exist_ok=True)

    # remove any stale data that we're about to replace
    delete_updated_books(src=src, dst=dst, release=release)

    # do the merge
    shutil.copytree(src=src, dst=dst, dirs_exist_ok=True)

    # rebuild the sitemap
    sitemap, minecraft_sitemap = load_sitemap(dst)
    dump_sitemap(dst, sitemap, minecraft_sitemap)

    # find paths for redirect pages
    redirects = dict[Path, str]()

    root_version: Version | None = None
    root_redirect: str | None = None

    for version, item in sitemap.items():
        if version.startswith("latest"):  # TODO: check type of item instead
            continue

        redirects[plugin.site_root / version] = item.default_marker.redirect_contents
        for lang, marker in item.markers.items():
            redirects[plugin.site_root / version / lang] = marker.redirect_contents

        item_version = Version(version)
        if not root_version or item_version > root_version:
            root_version = item_version
            root_redirect = item.default_marker.redirect_contents

    if root_redirect is None:
        # TODO: use plugin to build this path
        # TODO: refactor
        if item := sitemap.get(f"latest/{props.default_branch}"):
            root_redirect = item.default_marker.redirect_contents
        elif sitemap:
            key = sorted(sitemap.keys())[0]
            root_redirect = sitemap[key].default_marker.redirect_contents
            logger.warning(
                f"No book exists for the default branch `{props.default_branch}`, generating root redirect to `{key}` (check the value of `default_branch` in hexdoc.toml)"
            )
        else:
            logger.error("No books found, skipping root redirect")

    if root_redirect is not None:
        redirects[Path()] = root_redirect

    # write redirect pages
    if props.template.redirect:
        filename, _ = props.template.redirect
        for path, redirect_contents in redirects.items():
            write_to_path(dst / path / filename, redirect_contents)

    # bypass Jekyll on GitHub Pages
    (dst / ".nojekyll").touch()


@app.command()
def serve(
    *,
    props_file: PropsOption,
    port: int = 8000,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
    branch: BranchOption,
    release: bool = True,
    clean: bool = False,
    do_merge: Annotated[bool, Option("--merge/--no-merge")] = True,
):
    book_root = dst
    relative_root = book_root.resolve().relative_to(Path.cwd())

    base_url = URL.build(scheme="http", host="localhost", port=port)
    book_url = base_url.joinpath(*relative_root.parts)

    repo_root = git_root(props_file.parent)
    asset_root = repo_root.relative_to(Path.cwd())

    os.environ |= {
        # prepend a slash to the path so it can find the texture in the local repo
        # eg. http://localhost:8000/_site/src/docs/Common/...
        # vs. http://localhost:8000/Common/...
        "DEBUG_GITHUBUSERCONTENT": str(base_url.joinpath(*asset_root.parts)),
        "GITHUB_PAGES_URL": str(book_url),
    }

    print()
    logger.info(f"hexdoc build --{'' if release else 'no-'}release")
    build(
        branch=branch,
        props_file=props_file,
        output_dir=src,
        release=True,
        clean=clean,
    )

    if do_merge:
        print()
        logger.info("hexdoc merge")
        merge(
            src=src,
            dst=dst,
            props_file=props_file,
        )

    print()
    logger.info(f"Serving web book at {book_url} (press ctrl+c to exit)\n")
    with HTTPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        # ignore KeyboardInterrupt to stop Typer from printing "Aborted."
        # because it keeps printing after nodemon exits and breaking the output
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


@app.command()
def render_model(
    model_id: str,
    *,
    props_file: PropsOption,
    output_path: Annotated[Path, Option("--output", "-o")] = Path("out.png"),
    axes: bool = False,
    normals: bool = False,
):
    """Use hexdoc's block rendering to render an item or block model."""
    set_default_env()
    props, pm, *_ = load_common_data(props_file, branch="")

    debug = DebugType.NONE
    if axes:
        debug |= DebugType.AXES
    if normals:
        debug |= DebugType.NORMALS

    with ModResourceLoader.load_all(props, pm, export=False) as loader:
        _, model = load_model(loader, ResourceLocation.from_str(model_id))
        while isinstance(model, ItemModel) and model.parent:
            _, model = load_model(loader, model.parent)

        if isinstance(model, ItemModel):
            raise ValueError(f"Invalid block id: {model_id}")

        with BlockRenderer(loader=loader, debug=debug) as renderer:
            renderer.render_block_model(model, output_path)


@app.command()
def render_models(
    model_ids: Annotated[Optional[list[str]], Argument()] = None,
    *,
    props_file: PropsOption,
    render_all: Annotated[bool, Option("--all")] = False,
    output_dir: Annotated[Path, Option("--output", "-o")] = Path("out"),
    site_url_str: Annotated[Optional[str], Option("--site-url")] = None,
    export_resources: bool = True,
):
    if not (model_ids or render_all):
        raise ValueError("At least one model id must be provided if --all is missing")

    site_url = URL(site_url_str or "")

    set_default_env()
    props, pm, _, plugin = load_common_data(props_file, branch="")

    with ModResourceLoader.load_all(props, pm, export=export_resources) as loader:
        if model_ids:
            with BlockRenderer(loader=loader, output_dir=output_dir) as renderer:
                for model_id in model_ids:
                    model_id = ResourceLocation.from_str(model_id)
                    render_block(model_id, renderer, site_url)
        else:
            asset_loader = plugin.asset_loader(
                loader=loader,
                site_url=site_url,
                asset_url=props.env.asset_url,
                render_dir=output_dir,
            )
            render_textures_and_export_metadata(loader, asset_loader)

    logger.info("Done.")


@app.command(deprecated=True)
def export(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    props_file: PropsOption,
):
    logger.warning("This command is deprecated, use `hexdoc build` instead.")
    build(
        output_dir,
        branch=branch,
        release=release,
        props_file=props_file,
    )


@app.command(deprecated=True)
def render(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    clean: bool = False,
    lang: Optional[str] = None,
    props_file: PropsOption,
):
    logger.warning("This command is deprecated, use `hexdoc build` instead.")
    if lang is not None:
        logger.warning(
            "`--lang` is deprecated and has been removed from `hexdoc build`."
        )
    build(
        output_dir,
        branch=branch,
        release=release,
        clean=clean,
        props_file=props_file,
    )


if __name__ == "__main__":
    app()
