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
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from typer import Argument, Option
from yarl import URL

from hexdoc.__version__ import VERSION
from hexdoc.core import I18n, ModResourceLoader, ResourceLocation
from hexdoc.core.properties import AnimationFormat
from hexdoc.data.metadata import HexdocMetadata
from hexdoc.data.sitemap import delete_updated_books, dump_sitemap, load_sitemap
from hexdoc.graphics import DebugType, ModelRenderer
from hexdoc.graphics.loader import ImageLoader
from hexdoc.jinja.render import create_jinja_env, get_templates, render_book
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
    export_metadata,
    init_context,
    load_common_data,
)

logger = logging.getLogger(__name__)


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
    setup_logging(verbosity, ci=False, quiet_langs=quiet_lang)

    if quiet_lang:
        logger.warning(
            "`--quiet-lang` is deprecated, use `props.lang.{lang}.quiet` instead."
        )

    if not os.getenv("CI"):
        set_any = False
        for key, value in {
            "GITHUB_REPOSITORY": "placeholder/placeholder",
            "GITHUB_SHA": "00000000",
            "GITHUB_PAGES_URL": "https://example.hexxy.media",
        }.items():
            if not os.getenv(key):
                os.environ[key] = value
                set_any = True
        if set_any:
            logger.info(
                "CI not detected, setting defaults for missing environment variables."
            )


@app.command()
def repl(*, props_file: PropsOption):
    """Start a Python shell with some helpful extra locals added from hexdoc."""

    repl_locals = dict[str, Any](
        props_path=props_file,
    )

    try:
        props, pm, book_plugin, plugin = load_common_data(props_file, branch="")

        loader = ModResourceLoader.load_all(
            props,
            pm,
            export=False,
        )

        renderer = ModelRenderer(loader=loader)

        image_loader = ImageLoader(
            loader=loader,
            renderer=renderer,
            site_url=URL(),
            site_dir=Path("out"),
        )

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

        repl_locals |= dict(
            props=props,
            pm=pm,
            plugin=plugin,
            loader=loader,
            renderer=renderer,
            image_loader=image_loader,
            all_metadata=all_metadata,
        )

        if book_id and book_data:
            with init_context(
                book_id=book_id,
                book_data=book_data,
                pm=pm,
                loader=loader,
                image_loader=image_loader,
                i18n=i18n,
                all_metadata=all_metadata,
            ) as context:
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
    clean_exports: bool = True,
    props_file: PropsOption,
) -> Path:
    """Export resources and render the web book.

    For developers: returns the site path (eg. `/v/latest/main`).
    """

    props, pm, book_plugin, plugin = load_common_data(props_file, branch)

    if props.env.hexdoc_subdirectory:
        output_dir /= props.env.hexdoc_subdirectory

    logger.info("Exporting resources.")
    with (
        ModResourceLoader.load_all(
            props, pm, export=True, clean=clean_exports
        ) as loader,
        ModelRenderer(loader=loader) as renderer,
    ):
        site_path = plugin.site_path(versioned=release)
        site_dir = output_dir / site_path

        image_loader = ImageLoader(
            loader=loader,
            renderer=renderer,
            site_dir=site_dir,
            site_url=URL().joinpath(*site_path.parts),
        )

        all_metadata = export_metadata(
            loader,
            site_url=props.env.github_pages_url.joinpath(*site_path.parts),
        )

        # FIXME: put this somewhere saner?
        logger.info("Exporting all image-related resources.")
        for folder in ["blockstates", "models", "textures"]:
            loader.export_resources(
                "assets",
                namespace="*",
                folder=folder,
                glob="**/*.*",
                allow_missing=True,
            )

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
                with init_context(
                    book_id=book_id,
                    book_data=book_data,
                    pm=pm,
                    loader=loader,
                    image_loader=image_loader,
                    i18n=i18n,
                    all_metadata=all_metadata,
                ) as context:
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

                site_book_path = plugin.site_book_path(
                    book_info.language,
                    versioned=release,
                )
                if clean:
                    shutil.rmtree(output_dir / site_book_path, ignore_errors=True)

                template_args: dict[str, Any] = book_info.context | {
                    "all_metadata": all_metadata,
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
    output_dir: Annotated[Path, Option("--output", "-o")] = Path("out"),
    axes: bool = False,
    normals: bool = False,
    size: Optional[int] = None,
    format: Optional[AnimationFormat] = None,
):
    """Use hexdoc's block rendering to render an item or block model."""
    props, pm, *_ = load_common_data(props_file, branch="")

    debug = DebugType.NONE
    if axes:
        debug |= DebugType.AXES
    if normals:
        debug |= DebugType.NORMALS

    if format:
        props.textures.animated.format = format

    with (
        ModResourceLoader.load_all(props, pm, export=False) as loader,
        ModelRenderer(
            loader=loader,
            debug=debug,
            block_size=size,
            item_size=size,
        ) as renderer,
    ):
        image_loader = ImageLoader(
            loader=loader,
            renderer=renderer,
            site_url=URL(),
            site_dir=output_dir,
        )
        result = image_loader.render_model(ResourceLocation.from_str(model_id))
        print(f"Rendered model {model_id} to {result.url}.")


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

    props, pm, *_ = load_common_data(props_file, branch="")

    with (
        ModResourceLoader.load_all(props, pm, export=export_resources) as loader,
        ModelRenderer(loader=loader) as renderer,
    ):
        image_loader = ImageLoader(
            loader=loader,
            renderer=renderer,
            site_url=site_url,
            site_dir=output_dir,
        )

        if model_ids:
            iterator = (ResourceLocation.from_str(model_id) for model_id in model_ids)
        else:
            iterator = (
                "item" / item_id
                for _, item_id, _ in loader.find_resources(
                    "assets",
                    namespace="*",
                    folder="models/item",
                    internal_only=True,
                )
            )

        with logging_redirect_tqdm():
            bar = tqdm(iterator)
            for model_id in bar:
                bar.set_postfix_str(str(model_id))
                try:
                    image_loader.render_model(model_id)
                except Exception:
                    logger.warning(f"Failed to render model: {model_id}")
                    if not props.textures.can_be_missing(model_id):
                        raise
                    logger.debug("Error:", exc_info=True)

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
