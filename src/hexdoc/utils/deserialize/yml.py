from typing import Any, TypeVar

import yaml

_T_co = TypeVar("_T_co", covariant=True)


def decode_yaml_dict(data: str | bytes) -> dict[str, Any]:
    match data:
        case str():
            decoded = yaml.full_load(data)
        case _:
            decoded = yaml.full_load(data)
    return decoded


def decode_and_flatten_yaml_dict(data: str) -> dict[str, str]:
    decoded = decode_yaml_dict(data)
    return _flatten_inner(decoded, "")


def _flatten_inner(obj: dict[str, Any], prefix: str) -> dict[str, str]:
    out: dict[str, str] = {}

    for key_stub, value in obj.items():
        if key_stub == ".":
            key = prefix
        elif not prefix:
            key = key_stub
        elif not key_stub:
            key = prefix
        elif prefix[-1] in ":_-/":
            key = prefix + key_stub
        else:
            key = f"{prefix}.{key_stub}"

        match value:
            case dict():
                _update_disallow_duplicates(out, _flatten_inner(value, key))  # type: ignore
            case str():
                _update_disallow_duplicates(out, {key: value})
            case _:
                raise TypeError(value)

    return out


def _update_disallow_duplicates(base: dict[str, _T_co], new: dict[str, _T_co]):
    for key, value in new.items():
        if key in base:
            raise ValueError(f"Duplicate key {key}\nold=`{base[key]}`\nnew=`{value}`")
        base[key] = value
