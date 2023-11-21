import subprocess
from pathlib import Path


def git_root(cwd: str | Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return Path(result.stdout.strip())
