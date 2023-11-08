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
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import AnimatedTexture

from . import render_block
from .utils.args import (
    DEFAULT_MERGE_DST,
    DEFAULT_MERGE_SRC,
    PathArgument,
    PropsOption,
    ReleaseOption,
    UpdateLatestOption,
    VerbosityOption,
)
from .utils.load import load_book, load_book_and_loader, load_books, load_common_data
from .utils.logging import repl_readfunc
from .utils.render import create_jinja_env, render_book
from .utils.sitemap import (
    assert_version_exists,
    delete_root_book,
    delete_updated_books,
    dump_sitemap,
    load_sitemap,
)

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
    props, pm, _ = load_common_data(props_file, verbosity)
    with ModResourceLoader.load_all(
        props, pm, texture_render_dir=None, export=False
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
    props, pm, _ = load_common_data(props_file, verbosity)

    _, book, i18n, loader, context = load_book_and_loader(
        props.book,
        props,
        pm,
        lang,
        allow_missing,
        export=False,
        texture_render_dir=Path("out/tmp/textures"),
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
    *,
    props_file: PropsOption,
    lang: Union[str, None] = None,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    """Run hexdoc, but skip rendering the web book - just export the book resources."""
    props, pm, _ = load_common_data(props_file, verbosity)
    load_book(
        props.book,
        props,
        pm,
        lang,
        allow_missing,
        export=True,
        texture_render_dir=None,
    )


@app.command()
def render(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    props_file: PropsOption,
    update_latest: UpdateLatestOption = True,
    release: ReleaseOption = False,
    clean: bool = False,
    lang: Union[str, None] = None,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    """Export resources and render the web book."""

    # load data
    props, pm, version = load_common_data(props_file, verbosity)
    if not props.book:
        raise ValueError("Expected a value for props.book, got None")
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    books, all_metadata = load_books(
        props.book,
        props,
        pm,
        lang,
        allow_missing,
        texture_render_dir=output_dir / "textures",
    )

    logger = logging.getLogger(__name__)
    logger.info(f"update_latest={update_latest}, release={release}")

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
        lang_: f"{i18n.localize('language.name')} ({i18n.localize('language.region')})"
        for lang_, (_, i18n, _) in books.items()
    }

    for should_render, version_, is_root in [
        (update_latest, "latest", False),
        (release, version, False),
        (update_latest and release, version, True),
    ]:
        if not should_render:
            continue
        for lang_, (book, i18n, context) in books.items():
            textures = context.png_textures
            animations = sorted(
                (
                    texture
                    for texture in textures.values()
                    if isinstance(texture, AnimatedTexture)
                ),
                key=lambda t: t.class_name,
            )

            render_book(
                props=props,
                pm=pm,
                lang=lang_,
                lang_names=lang_names,
                book=book,
                i18n=i18n,
                templates=templates,
                output_dir=output_dir,
                all_metadata=all_metadata,
                textures=textures,
                animations=animations,
                allow_missing=allow_missing,
                version=version_,
                is_root=is_root,
            )

    logger.info("Done.")


@app.command()
def merge(
    *,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
    update_latest: UpdateLatestOption = True,
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
    do_merge: Annotated[bool, Option("--merge/--no-merge")] = False,
    update_latest: bool = True,
    release: bool = True,  # you'd generally want --release for development
    clean: bool = False,
    lang: Union[str, None] = None,
    allow_missing: bool = False,
    verbosity: VerbosityOption = 0,
):
    book_root = dst if do_merge else src

    book_path = book_root.resolve().relative_to(Path.cwd())

    book_url = f"/{book_path.as_posix()}"

    os.environ |= {
        "DEBUG_GITHUBUSERCONTENT": "",
        "GITHUB_PAGES_URL": book_url,
    }

    print("Rendering...")
    render(
        props_file=props_file,
        output_dir=src,
        update_latest=update_latest,
        release=release,
        clean=clean,
        lang=lang,
        allow_missing=allow_missing,
        verbosity=verbosity,
    )

    if do_merge:
        print("Merging...")
        merge(
            src=src,
            dst=dst,
            update_latest=update_latest,
            release=release,
        )

    print(
        f"Serving web book at http://localhost:{port}{book_url} (press ctrl+c to exit)\n"
    )
    with HTTPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        # ignore KeyboardInterrupt to stop Typer from printing "Aborted."
        # because it keeps printing after nodemon exits and breaking the output
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    app()
