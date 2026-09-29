"""Verify the README quickstart is copy-pasteable.

Extracts the Quickstart code block from README.md and executes it in a subprocess
with no network access and no API key. A broken quickstart fails CI.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

QUICKSTART_PATTERN = re.compile(
    r"^#{2,3}\s*Quickstart.*?^```(?:python|py)\s*\n(.*?)^```\s*$",
    re.S | re.M,
)


def extract_quickstart(readme: str) -> str | None:
    """Pull the first fenced python block that follows a Quickstart heading.

    Args:
        readme: Full README contents.

    Returns:
        The code to run, or None when no Quickstart block is found.
    """
    match = QUICKSTART_PATTERN.search(readme)
    return match.group(1) if match else None


def main() -> int:
    """Run the README quickstart and report the outcome.

    Returns:
        0 when the quickstart runs successfully, 1 otherwise.
    """
    readme_path = ROOT / "README.md"
    if not readme_path.is_file():
        print("FAIL: README.md is missing")
        return 1

    code = extract_quickstart(readme_path.read_text(encoding="utf-8"))
    if code is None:
        print("FAIL: no Quickstart python code block found in README.md")
        return 1

    print("README quickstart verification")
    print("----------------------------")
    print(code.strip())
    print("-" * 28)

    env = dict(os.environ)
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "COHERE_API_KEY"):
        env.pop(key, None)
    env["CER_OFFLINE"] = "1"

    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "quickstart.py"
        script.write_text(code, encoding="utf-8")
        proc = subprocess.run(  # noqa: S603
            [sys.executable, str(script)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print("")
        print(f"FAIL: quickstart exited with {proc.returncode}")
        return 1

    print("")
    print("PASS: README quickstart runs offline with no API key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
