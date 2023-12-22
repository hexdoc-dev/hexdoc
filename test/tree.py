import json
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Callable, Literal

if TYPE_CHECKING:
    from hexdoc.utils import JSONValue
else:
    from typing import Any as JSONValue

FileValue = JSONValue | tuple[Literal["a"], str] | Callable[[str | None], str]

FileTree = dict[str, "FileTree | FileValue"]


def write_file_tree(root: str | Path, tree: FileTree):
    for path, value in tree.items():
        path = Path(root, path)
        match value:
            case {**children} if path.suffix != ".json":
                # subtree
                path.mkdir(parents=True, exist_ok=True)
                write_file_tree(path, children)
            case {**json_data}:
                # JSON file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(json_data, indent="  "))
            case tuple((mode, text)):
                # append to existing file
                with path.open(mode) as f:
                    f.write(dedent(text))
            case str() as text:
                # anything else - usually just text
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(dedent(text))
            case int() | float() | bool() | None:
                raise TypeError(
                    f"Type {type(value)} is only allowed in JSON data: {value}"
                )
            case fn:
                assert not isinstance(fn, (list, dict))
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    current_value = path.read_text()
                except FileNotFoundError:
                    current_value = None
                path.write_text(dedent(fn(current_value)))
