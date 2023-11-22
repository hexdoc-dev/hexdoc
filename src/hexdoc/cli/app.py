import code
import logging
import os
import shutil
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from textwrap import dedent
from typing import Any, Union

from packaging.version import Version
from typer import Typer

from hexdoc.core import ModResourceLoader
from hexdoc.data.metadata import HexdocMetadata
from hexdoc.minecraft import I18n
from hexdoc.minecraft.assets import (
    AnimatedTexture,
    PNGTexture,
)
from hexdoc.utils import git_root, write_to_path

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
from .utils.logging import repl_readfunc
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
)

app.add_typer(render_block.app)
app.add_typer(ci.app)


@app.command()
def repl(
    *,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
    allow_missing: bool = False,
):
    """Start a Python shell with some helpful extra locals added from hexdoc."""

    repl_locals = dict[str, Any](
        props_path=props_file,
    )

    try:
        props, pm, plugin = load_common_data(props_file, verbosity, "")
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

        i18n = I18n.load_all(loader, allow_missing)[props.default_lang]

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
def export(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
    allow_missing: bool = False,
):
    """Run hexdoc, but skip rendering the web book - just export the book resources."""
    props, pm, plugin = load_common_data(props_file, verbosity, branch)

    with ModResourceLoader.clean_and_load_all(
        props,
        pm,
        export=True,
    ) as loader:
        site_path = plugin.site_path(versioned=release)

        asset_loader = plugin.asset_loader(
            loader=loader,
            # TODO: urlencode
            site_url=f"{props.env.github_pages_url}/{site_path.as_posix()}",
            asset_url=props.env.asset_url,
            render_dir=output_dir / site_path,
        )

        all_metadata = render_textures_and_export_metadata(loader, asset_loader)

        all_i18n = I18n.load_all(loader, allow_missing)
        i18n = all_i18n[props.default_lang]

        if props.book_id:
            load_book(
                book_id=props.book_id,
                pm=pm,
                loader=loader,
                i18n=i18n,
                all_metadata=all_metadata,
            )

    # for CI
    return props, all_i18n, output_dir / site_path


@app.command()
def render(
    output_dir: PathArgument = DEFAULT_MERGE_SRC,
    *,
    branch: BranchOption,
    release: ReleaseOption = False,
    clean: bool = False,
    lang: Union[str, None] = None,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
    allow_missing: bool = False,
):
    """Export resources and render the web book."""

    # load data
    props, pm, plugin = load_common_data(props_file, verbosity, branch, book=True)
    if not props.book_id:
        raise ValueError("Expected a value for props.book, got None")
    if not props.template:
        raise ValueError("Expected a value for props.template, got None")

    if not lang:
        lang = props.default_lang

    with ModResourceLoader.load_all(
        props,
        pm,
        export=True,
    ) as loader:
        all_metadata = loader.load_metadata(model_type=HexdocMetadata)

        i18n = I18n.load(loader, lang, allow_missing)

        book, context = load_book(
            book_id=props.book_id,
            pm=pm,
            loader=loader,
            i18n=i18n,
            all_metadata=all_metadata,
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

    site_path = plugin.site_book_path(lang, versioned=release)
    if clean:
        shutil.rmtree(output_dir / site_path, ignore_errors=True)

    render_book(
        props=props,
        pm=pm,
        plugin=plugin,
        lang=lang,
        book=book,
        i18n=i18n,
        env=env,
        templates=templates,
        output_dir=output_dir,
        all_metadata=all_metadata,
        version=plugin.mod_version if release else f"latest/{branch}",
        site_path=site_path,
        png_textures=PNGTexture.get_lookup(context.textures),
        animations=sorted(  # this MUST be sorted to avoid flaky tests
            AnimatedTexture.get_lookup(context.textures).values(),
            key=lambda t: t.css_class,
        ),
        versioned=release,
    )

    logger.info("Done.")


@app.command()
def merge(
    *,
    props_file: PropsOption,
    verbosity: VerbosityOption = 0,
    src: Path = DEFAULT_MERGE_SRC,
    dst: Path = DEFAULT_MERGE_DST,
):
    props, _, plugin = load_common_data(props_file, verbosity, "", book=True)
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
        props_file=props_file,
        verbosity=verbosity,
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
