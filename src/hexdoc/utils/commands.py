import subprocess
import textwrap
from pathlib import Path
from subprocess import CalledProcessError
from typing import Callable, Sequence, TypeVar

_T = TypeVar("_T")


def run(
    args: str | Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    type: Callable[[str], _T] = str,
) -> _T:
    """Runs a command using `subprocess.run`, returning the stripped stdout as UTF-8.

    If `type` is provided, converts the stripped stdout to that type.

    If the command fails, raises `CalledProcessError` with stdout/stderr as notes.
    """
    try:
        result = subprocess.run(
            args=args,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        return type(result.stdout.strip())
    except CalledProcessError as e:
        for name, value in [("stdout", e.stdout), ("stderr", e.stderr)]:
            if value:
                e.add_note(f"{name}:\n" + textwrap.indent(str(value).strip(), "  "))
        raise
