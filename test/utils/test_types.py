import pytest
from pydantic import TypeAdapter, ValidationError
from yarl import URL

from hexdoc.model.types import Color
from hexdoc.utils.types import PydanticOrderedSet, PydanticURL

colors: list[str] = [
    "#0099FF",
    "#0099ff",
    "#09F",
    "#09f",
    "0099FF",
    "0099ff",
    "09F",
    "09f",
]


@pytest.mark.parametrize("s", colors)
def test_color(s: str):
    assert Color(s).value == "0099ff"


def test_ordered_set_round_trip():
    data = [3, 1, 3, 2, 1]
    ta = TypeAdapter(PydanticOrderedSet[int])

    ordered_set = ta.validate_python(data)

    assert ordered_set.items == [3, 1, 2]


def test_ordered_set_validation_error():
    data = [1, "a"]
    ta = TypeAdapter(PydanticOrderedSet[int])

    with pytest.raises(ValidationError):
        ta.validate_python(data)


@pytest.mark.parametrize(
    ["raw_url", "want_url"],
    [
        ["https://www.google.ca", URL("https://www.google.ca")],
        ["https://www.google.ca/", URL("https://www.google.ca")],
    ],
)
def test_url_validate(raw_url: str, want_url: URL):
    ta = TypeAdapter[URL](PydanticURL)

    assert ta.validate_python(raw_url) == URL(want_url)


@pytest.mark.parametrize(
    ["url", "want_raw_url"],
    [
        [URL("https://www.google.ca"), "https://www.google.ca"],
        [URL("https://www.google.ca/"), "https://www.google.ca"],
    ],
)
def test_url_serialize(url: URL, want_raw_url: str):
    ta = TypeAdapter[URL](PydanticURL)

    assert ta.dump_python(url) == want_raw_url
