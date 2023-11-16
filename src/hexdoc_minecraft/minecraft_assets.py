import re
from functools import cached_property
from typing import Iterator

import requests
from github import Github
from hexdoc.core import ResourceLocation
from hexdoc.minecraft.assets import PNGTexture
from hexdoc.model import HexdocModel
from hexdoc.utils import JSONValue, isinstance_or_raise


# TODO: remove
def fetch_minecraft_assets_json(*, ref: str, version: str, filename: str) -> JSONValue:
    url = (
        "https://raw.githubusercontent.com/PrismarineJS/minecraft-assets"
        f"/{ref}/data/{version}/{filename}"
    )

    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


class MinecraftAssetsRepo(HexdocModel, arbitrary_types_allowed=True):
    github: Github
    ref: str
    version: str

    @cached_property
    def repo(self):
        return self.github.get_repo("PrismarineJS/minecraft-assets")

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
                yield texture_id, PNGTexture(url=url, pixelated=True)
