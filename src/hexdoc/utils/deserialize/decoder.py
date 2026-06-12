from fnmatch import fnmatch
from typing import Callable, Mapping, TypeVar

_T = TypeVar("_T")


def pick_decoder(
    suffix: str,
    decoders: Mapping[tuple[str, ...], Callable[[str], _T]],
) -> Callable[[str], _T]:
    for globs, decoder in decoders.items():
        for pattern in globs:
            if fnmatch(suffix, pattern):
                return decoder

    raise FileNotFoundError(f"No decoder matched file suffix: {suffix}")
