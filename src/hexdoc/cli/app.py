import code
import logging
import os
import shutil
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from textwrap import dedent
from typing import Any, Optional

from packaging.version import Version
from typer import Typer
from yarl import URL

from hexdoc.core import ModResourceLoader
from hexdoc.data.metadata import HexdocMetadata
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import (
    AnimatedTexture,
    PNGTexture,
)
from hexdoc.minecraft.assets.textures import TextureContext
from hexdoc.patchouli import Book
from hexdoc.plugin.mod_plugin import ModPluginWithBook
from hexdoc.utils import git_root, setup_logging, write_to_path
from hexdoc.utils.logging import repl_readfunc

from . import ci, render_block
from .utils.args import (
    DEFAULT_MERGE_DST,
    DEFAULT_MERGE_SRC,
    BranchOption,
    PathArgument,
    PropsOption,
    ReleaseOption,
    VerbosityOption,
)
from .utils.load import (
    load_book,
    load_common_data,
    render_textures_and_export_metadata,
)
from .utils.render import create_jinja_env, render_book
from .utils.sitemap import (
    delete_updated_books,
    dump_sitemap,
    load_sitemap,
)

logger = logging.getLogger(__name__)

app = Typer(
    pretty_exceptions_enable=False,
    context_settings={
        "help_option_names": ["--help", "-h"],
    },
    add_completion=False,
)
app.add_typer(render_block.app)
app.add_typer(ci.app)


@app.callback()
def callback(
    verbosity: VerbosityOption = 0,
    quiet_lang: Optional[list[str]] = None,
):
    setup_logging(verbosity, ci=False, quiet_langs=quiet_lang)


@app.command()
def repl(*, props_file: PropsOption):
    """Start a Python shell with some helpful extra locals added from hexdoc."""

    repl_locals = dict[str, Any](
        props_path=props_file,
    )

    try:
        props, pm, plugin = load_common_data(props_file, branch="")
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

        i18n = I18n.load_all(loader)[props.default_lang]

        all_metadata = loader.load_metadata(model_type=HexdocMetadata)
        repl_locals["all_metadata"] = all_metadata

        if props.book_id:
            book, context = load_book(
                book_id=props.book_id,
                pm=pm,
                loader=loader,
                i18n=i18n,
                all_metadata=all_metadata,
            )
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

    props, pm, plugin = load_common_data(props_file, branch)

    logger.info("Exporting resources.")
    with ModResourceLoader.clean_and_load_all(
        props,
        pm,
        export=True,
    ) as loader:
        site_path = plugin.site_path(versioned=release)
        site_dir = output_dir / site_path

        asset_loader = plugin.asset_loader(
            loader=loader,
            site_url=props.env.github_pages_url.joinpath(*site_path.parts),
            asset_url=props.env.asset_url,
            render_dir=site_dir,
        )

        all_metadata = render_textures_and_export_metadata(loader, asset_loader)

        all_i18n = I18n.load_all(loader)

        if not props.book_id:
            logger.info("Skipping book load because props.book_id is not set.")
            return site_dir

        logger.info("Loading books for all languages.")
        books = list[tuple[str, I18n, Book, dict[str, Any]]]()
        for language, i18n in all_i18n.items():
            try:
                book, context = load_book(
                    book_id=props.book_id,
                    pm=pm,
                    loader=loader,
                    i18n=i18n,
                    all_metadata=all_metadata,
                )
                books.append((language, i18n, book, context))
            except Exception:
                if release or language == props.default_lang:
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

        if props.template.override_default_render:
            template_names = props.template.render
        else:
            template_names = pm.default_rendered_templates(props.template.include)

        template_names |= props.template.extend_render

        templates = {
            Path(path): env.get_template(template_name)
            for path, template_name in template_names.items()
        }
        if not templates:
            raise RuntimeError(
                "No templates to render, check your props.template configuration "
                f"(in {props_file.as_posix()})"
            )

        logger.info(f"Rendering book for {len(books)} language(s).")
        for language, i18n, book, context in books:
            try:
                site_book_path = plugin.site_book_path(language, versioned=release)
                if clean:
                    shutil.rmtree(output_dir / site_book_path, ignore_errors=True)

                texture_ctx = TextureContext.of(context)

                render_book(
                    props=props,
                    pm=pm,
                    plugin=plugin,
                    lang=language,
                    book=book,
                    i18n=i18n,
                    env=env,
                    templates=templates,
                    output_dir=output_dir,
                    all_metadata=all_metadata,
                    version=plugin.mod_version if release else f"latest/{branch}",
                    site_path=site_book_path,
                    png_textures=PNGTexture.get_lookup(texture_ctx.textures),
                    animations=sorted(  # this MUST be sorted to avoid flaky tests
                        AnimatedTexture.get_lookup(texture_ctx.textures).values(),
                        key=lambda t: t.css_class,
                    ),
                    versioned=release,
                )
            except Exception:
                if release or language == props.default_lang:
                    raise
                logger.exception(f"Failed to render book for {language}")

    logger.info("Done.")
    return site_dir


@app.command()
def merge(
    *,
    props_file: PropsOption,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
):
    props, _, plugin = load_common_data(props_file, branch="", book=True)
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    dst.mkdir(parents=True, exist_ok=True)

    # remove any stale data that we're about to replace
    delete_updated_books(src=src, dst=dst)

    # do the merge
    shutil.copytree(src=src, dst=dst, dirs_exist_ok=True)

    # rebuild the sitemap
    sitemap = load_sitemap(dst)
    dump_sitemap(dst, sitemap)

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
        if item := sitemap.get(f"latest/{props.default_branch}"):
            root_redirect = item.default_marker.redirect_contents

    if root_redirect is not None:
        redirects[Path()] = root_redirect

    # write redirect pages
    if props.template.redirect:
        filename, _ = props.template.redirect
        for path, redirect_contents in redirects.items():
            write_to_path(dst / path / filename, redirect_contents)


@app.command()
def serve(
    *,
    props_file: PropsOption,
    port: int = 8000,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
    branch: BranchOption,
    try_release: bool = True,
    clean: bool = False,
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

    build_latest = True

    if try_release:
        try:
            print()
            logger.info("hexdoc build --release")
            build(
                branch=branch,
                props_file=props_file,
                output_dir=src,
                release=True,
                clean=clean,
            )
            build_latest = False
        except Exception:
            logger.exception("Release build failed")
            time.sleep(2)

    if build_latest:
        print()
        logger.info("hexdoc build --no-release")
        build(
            branch=branch,
            props_file=props_file,
            output_dir=src,
            release=False,
            clean=clean,
        )

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
