import code
import json
import logging
import os
import shutil
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Union

from typer import Option, Typer

from hexdoc.core import ModResourceLoader
from hexdoc.minecraft import I18n, Tag
from hexdoc.minecraft.assets import (
    AnimatedTexture,
    HexdocAssetLoader,
    PNGTexture,
)
from hexdoc.utils.git import git_root

from . import render_block
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
from .utils.logging import repl_readfunc
from .utils.render import create_jinja_env, render_book
from .utils.sitemap import (
    assert_version_exists,
    delete_root_book,
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
)
app.add_typer(render_block.app)


@app.command()
def list_langs(
    *,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
):
    """Get the available language codes as a JSON list."""
    props, pm, _ = load_common_data(props_file, verbosity, "")
    with ModResourceLoader.load_all(
        props,
        pm,
        export=False,
    ) as loader:
        langs = sorted(I18n.list_all(loader))
        print(json.dumps(langs))


@app.command()
def repl(
    *,
    props_file: PropsOption,
    lang: Union[str, None] = None,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    """Start a Python shell with some helpful extra locals added from hexdoc."""
    props, pm, _ = load_common_data(props_file, verbosity, "")

    loader = ModResourceLoader.load_all(
        props,
        pm,
        export=False,
    )

    _, book, i18n, context = load_book(
        props.book,
        props,
        pm,
        loader,
        lang,
        allow_missing,
    )

    repl_locals = dict(
        props=props,
        pm=pm,
        book=book,
        i18n=i18n,
        loader=loader,
        context=context,
    )

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
def export(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    props_file: PropsOption,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    """Run hexdoc, but skip rendering the web book - just export the book resources."""
    props, pm, plugin = load_common_data(props_file, verbosity, branch)

    loader = ModResourceLoader.clean_and_load_all(
        props,
        pm,
        export=True,
    )

    site_path = plugin.site_path(versioned=release)
    asset_loader = plugin.asset_loader(
        loader=loader,
        site_url=f"{loader.props.url}/{site_path.as_posix()}",  # TODO: urlencode
        asset_url=props.env.asset_url,
        render_dir=output_dir / site_path,
    )

    all_metadata = render_textures_and_export_metadata(loader, asset_loader)

    i18n = I18n.load_all(
        loader,
        allow_missing=allow_missing,
    )[props.default_lang]

    if props.book:
        load_book(
            book_id=props.book,
            pm=pm,
            loader=loader,
            i18n=i18n,
            all_metadata=all_metadata,
        )


@app.command()
def render(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    clean: bool = False,
    lang: Union[str, None] = None,
    props_file: PropsOption,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    """Export resources and render the web book."""

    # load data
    props, pm, plugin = load_common_data(props_file, verbosity, branch, book=True)

    if not props.book:
        raise ValueError("Expected a value for props.book, got None")
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    site_path = plugin.site_book_path(
        lang=lang or props.default_lang,
        versioned=release,
    )

    books, all_metadata = load_books(
        props.book,
        props,
        pm,
        lang,
        allow_missing,
    )

    # set up Jinja
    env = create_jinja_env(pm, props.template.include, props_file)

    template_names = (
        props.template.render
        if props.template.override_default_render
        else pm.default_rendered_templates(props.template.include)
    ) | props.template.extend_render

    templates = {
        Path(path): env.get_template(template_name)
        for path, template_name in template_names.items()
    }

    if not templates:
        raise RuntimeError(
            "No templates to render, check your props.template configuration "
            f"(in {props_file.as_posix()})"
        )

    if clean:
        shutil.rmtree(output_dir, ignore_errors=True)

    lang_names = {
        book_lang: i18n.localize_lang() for book_lang, (_, i18n, _) in books.items()
    }

    for book_lang, (book, i18n, context) in books.items():
        png_textures = PNGTexture.get_lookup(context.textures)
        animations = list(AnimatedTexture.get_lookup(context.textures).values())

        render_book(
            props=props,
            pm=pm,
            lang=book_lang,
            lang_names=lang_names,
            book=book,
            i18n=i18n,
            templates=templates,
            output_dir=output_dir,
            site_path=site_path,
            all_metadata=all_metadata,
            png_textures=png_textures,
            animations=animations,
            allow_missing=allow_missing,
            version=plugin.mod_version,
        )

    logger.info("Done.")


@app.command()
def merge(
    *,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
    release: ReleaseOption = False,
):
    # ensure at least the default language was built successfully
    if update_latest:
        assert_version_exists(root=src, version="latest")

    # TODO: figure out how to do this with pluggy (we don't have the props file here)
    # if is_release:
    #     assert_version_exists(src, GRADLE_VERSION)

    dst.mkdir(parents=True, exist_ok=True)

    # remove any stale data that we're about to replace
    delete_updated_books(src=src, dst=dst)
    if update_latest and release:
        delete_root_book(root=dst)

    # do the merge
    shutil.copytree(src=src, dst=dst, dirs_exist_ok=True)

    # rebuild the sitemap
    sitemap = load_sitemap(dst)
    dump_sitemap(dst, sitemap)


@app.command()
def serve(
    *,
    props_file: PropsOption,
    port: int = 8000,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
    branch: BranchOption,
    release: bool = True,  # generally want --release for development, looks nicer
    clean: bool = False,
    lang: Union[str, None] = None,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    book_root = dst
    relative_root = book_root.resolve().relative_to(Path.cwd())

    base_url = f"http://localhost:{port}"
    book_url = f"{base_url}/{relative_root.as_posix()}"

    repo_root = git_root(props_file.parent)
    asset_root = repo_root.relative_to(Path.cwd())

    os.environ |= {
        # prepend a slash to the path so it can find the texture in the local repo
        # eg. http://localhost:8000/_site/src/docs/Common/...
        # vs. http://localhost:8000/Common/...
        "DEBUG_GITHUBUSERCONTENT": f"{base_url}/{asset_root.as_posix()}",
        "GITHUB_PAGES_URL": book_url,
    }

    print("Exporting...")
    export(
        branch=branch,
        release=release,
        props_file=props_file,
        allow_missing=allow_missing,
        verbosity=verbosity,
    )

    print("Rendering...")
    render(
        branch=branch,
        props_file=props_file,
        output_dir=src,
        release=release,
        clean=clean,
        lang=lang,
        allow_missing=allow_missing,
        verbosity=verbosity,
    )

    print("Merging...")
    merge(
        src=src,
        dst=dst,
        release=release,
    )

    print(f"Serving web book at {book_url} (press ctrl+c to exit)\n")
    with HTTPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        # ignore KeyboardInterrupt to stop Typer from printing "Aborted."
        # because it keeps printing after nodemon exits and breaking the output
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    app()
