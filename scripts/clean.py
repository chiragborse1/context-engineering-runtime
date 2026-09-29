"""Remove build, cache and runtime artifacts.

Invoked by `make clean`. Kept as a Python script rather than a shell one-liner so
it behaves identically on Linux, macOS and Windows.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ARTIFACT_DIRS = (
    "build",
    "dist",
    "htmlcov",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    ".cer-work",
)
ARTIFACT_FILES = (".coverage", "coverage.xml", "requirements-ci.txt")


def main() -> int:
    """Delete build and cache artifacts from the repository root.

    Returns:
        Process exit code, always 0.
    """
    root = Path(__file__).resolve().parent.parent
    for name in ARTIFACT_DIRS:
        target = root / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            print(f"removed {name}/")
    for name in ARTIFACT_FILES:
        target = root / name
        if target.is_file():
            target.unlink()
            print(f"removed {name}")
    print("clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
