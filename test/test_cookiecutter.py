# pyright: reportUnknownMemberType=false

from pytest import MonkeyPatch
from pytest_cookies.plugin import Cookies


def test_cookiecutter(cookies: Cookies, monkeypatch: MonkeyPatch):
    result = cookies.bake(
        {
            "output_directory": "output",
            "modid": "mod",
            "pattern_regex": "hex_latest",
        }
    )

    assert result.exception is None
    assert result.project_path is not None

    monkeypatch.syspath_prepend(result.project_path / "doc" / "src")

    import hexdoc_mod  # type: ignore
