import logging
import re
from functools import cached_property
from typing import Iterator

from github import Github
from github.ContentFile import ContentFile
from hexdoc.core import ResourceLocation
from hexdoc.minecraft.assets import PNGTexture
from hexdoc.model import HexdocModel, HexdocTypeAdapter
from hexdoc.utils import isinstance_or_raise

from hexdoc_minecraft.piston_meta import fetch_model

logger = logging.getLogger(__name__)


class TextureContent(HexdocModel):
    name: ResourceLocation
    texture: str | None


class MinecraftAssetsRepo(HexdocModel, arbitrary_types_allowed=True):
    github: Github
    ref: str
    version: str

    @cached_property
    def repo(self):
        return self.github.get_repo("PrismarineJS/minecraft-assets")

    def texture_content(self):
        contents = self.repo.get_contents(
            f"data/{self.version}/texture_content.json", self.ref
        )
        assert isinstance_or_raise(contents, ContentFile)

        ta = HexdocTypeAdapter(list[TextureContent])
        return fetch_model(ta, contents.download_url)

    def raw_file_url(self, path: str):
        return (
            f"https://raw.githubusercontent.com/{self.repo.full_name}/{self.ref}/{path}"
        )

    def find_version_tree(self) -> tuple[str, str]:
        """path, sha"""
        contents = self.repo.get_contents("data", self.ref)
        assert isinstance_or_raise(contents, list)

        for file in contents:
            if file.type == "dir" and file.name == self.version:
                return file.path, file.sha

        raise FileNotFoundError(
            f"Directory not found in {self.repo.full_name}: data/{self.version}"
        )

    def scrape_image_textures(self) -> Iterator[tuple[ResourceLocation, PNGTexture]]:
        tree_path, tree_sha = self.find_version_tree()
        tree = self.repo.get_git_tree(tree_sha, recursive=True)

        for element in tree.tree:
            if element.type == "blob" and element.path.endswith(".png"):
                url = self.raw_file_url(f"{tree_path}/{element.path}")

                # inexplicably, minecraft-assets changes block & item to blocks & items
                # so we need to undo that to make it actually follow the assets format
                # https://github.com/PrismarineJS/minecraft-jar-extractor/blob/f1cf968e20c46f56efbfc179d50dc9cf4403878c/image_names.js#L300
                texture_id = "textures" / ResourceLocation(
                    namespace="minecraft",
                    path=re.sub(r"^(block|item)s/", r"\1/", element.path),
                )

                # TODO: support AnimatedTexture?
                logger.info(f"Scraped texture {texture_id}: {url}")
                yield texture_id, PNGTexture(url=url, pixelated=True)
