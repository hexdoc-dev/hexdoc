import inspect
import logging
import os
import platform
import sys
from importlib.resources import Package
from pathlib import Path
from textwrap import dedent

from hexdoc.__version__ import VERSION
from hexdoc.core import (
    Properties,
)
from hexdoc.plugin import ModPlugin, PluginManager
from hexdoc.plugin.manager import flatten, import_package

logger = logging.getLogger(__name__)


def get_header(
    props: Properties,
    pm: PluginManager,
    mod_plugin: ModPlugin,
):
    python_version = platform.python_version()
    plugins = ", ".join(_plugins(pm))
    jinja_template_roots = ", ".join(_jinja_template_roots(mod_plugin))

    return dedent(
        f"""\
        Python:         {python_version} ({sys.platform})
        hexdoc:         {VERSION}
        plugins:        {plugins}
        mod_plugin:     {mod_plugin.modid}-{mod_plugin.full_version}
        cwd:            {Path.cwd()}
        props_dir:      {_relative_path(props.props_dir)}
        mod_templates:  {jinja_template_roots}
        site_url:       {props.env.github_pages_url}
        """
    ).rstrip()


def _plugins(pm: PluginManager):
    seen = set[str]()
    for _, dist in pm.inner.list_plugin_distinfo():
        if dist.project_name == "hexdoc":
            continue
        project_name = dist.project_name.removeprefix("hexdoc-")
        plugin_name = f"{project_name}-{dist.version}"
        if plugin_name not in seen:
            seen.add(plugin_name)
            yield plugin_name


def _jinja_template_roots(mod_plugin: ModPlugin):
    for package, folder in flatten([mod_plugin.jinja_template_root() or []]):
        module_path = _get_package_path(package)
        folder_path = module_path / folder
        yield _relative_path(folder_path)


def _get_package_path(package: Package):
    module = import_package(package)
    module_path = Path(inspect.getfile(module))
    return module_path.parent if module_path.suffix else module_path


def _relative_path(path: Path):
    cwd = Path.cwd()
    if path == cwd:
        return "."

    try:
        path = path.relative_to(cwd)
    except ValueError:
        return str(path)

    return f".{os.sep}{path}"
