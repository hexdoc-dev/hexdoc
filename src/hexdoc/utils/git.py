from pathlib import Path

from hexdoc.utils import commands


def git_root(cwd: str | Path) -> Path:
    return commands.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        type=Path,
    )
