import shutil
from collections import defaultdict
from pathlib import Path

from packaging.version import Version
from pydantic import Field, TypeAdapter
from pydantic.alias_generators import to_camel

from hexdoc.model import DEFAULT_CONFIG, HexdocModel
from hexdoc.utils import write_to_path

MARKER_NAME = ".sitemap-marker.json"


class BaseSitemapMarker(HexdocModel):
    version: str
    lang: str
    lang_name: str
    path: str
    is_default_lang: bool
    full_version: str
    minecraft_version: str | None
    redirect_contents: str
    """Pre-rendered HTML file to create a redirect for this page."""

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate_json(path.read_text("utf-8"))


class VersionedSitemapMarker(BaseSitemapMarker):
    mod_version: str
    plugin_version: str

    def __gt__(self, other: BaseSitemapMarker) -> bool:
        match other:
            case VersionedSitemapMarker():
                return Version(self.plugin_version) > Version(other.plugin_version)
            case LatestSitemapMarker():
                return True
            case _:
                return NotImplemented


class LatestSitemapMarker(BaseSitemapMarker):
    branch: str
    is_default_branch: bool

    def __gt__(self, other: BaseSitemapMarker) -> bool:
        match other:
            case VersionedSitemapMarker():
                return False
            case LatestSitemapMarker():
                return self.is_default_branch and not other.is_default_branch
            case _:
                return NotImplemented


SitemapMarker = VersionedSitemapMarker | LatestSitemapMarker


# TODO: there should be a VersionedSitemapItem and a LatestSitemapItem
class SitemapItem(HexdocModel, alias_generator=to_camel):
    default_lang: str = ""
    default_path: str = ""

    markers: dict[str, SitemapMarker] = Field(default_factory=dict)
    lang_names: dict[str, str] = Field(default_factory=dict)
    lang_paths: dict[str, str] = Field(default_factory=dict)

    @property
    def default_marker(self):
        return self.markers[self.default_lang]

    def add_marker(self, marker: SitemapMarker):
        if (old_marker := self.markers.get(marker.lang)) and old_marker > marker:
            return

        self.markers[marker.lang] = marker
        self.lang_paths[marker.lang] = marker.path
        self.lang_names[marker.lang] = marker.lang_name or marker.lang

        if marker.is_default_lang:
            self.default_lang = marker.lang
            self.default_path = marker.path


Sitemap = dict[str, SitemapItem]


def delete_updated_books(*, src: Path, dst: Path):
    src_markers = src.rglob(MARKER_NAME)
    for marker in src_markers:
        src_dir = marker.parent
        dst_dir = dst / src_dir.relative_to(src)
        shutil.rmtree(dst_dir, ignore_errors=True)


def load_sitemap(root: Path) -> Sitemap:
    sitemap: Sitemap = defaultdict(SitemapItem)

    # crawl the new tree to rebuild the sitemap
    for marker_path in root.rglob(MARKER_NAME):
        try:
            marker = VersionedSitemapMarker.load(marker_path)
        except ValueError:
            marker = LatestSitemapMarker.load(marker_path)
        sitemap[marker.version].add_marker(marker)

    return sitemap


def dump_sitemap(root: Path, sitemap: Sitemap):
    # dump the sitemap using a TypeAdapter so it serializes the items properly
    ta = TypeAdapter(Sitemap, config=DEFAULT_CONFIG)

    write_to_path(
        root / "meta" / "sitemap.json",
        ta.dump_json(sitemap, by_alias=True),
    )
