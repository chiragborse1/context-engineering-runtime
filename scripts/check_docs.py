"""Verify the required documentation set exists and is substantial.

Implements the documentation requirement of the project brief as an executable
check, so a missing or stubbed document fails CI instead of being discovered at
release time.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Required documents and the minimum size in bytes each must reach.
REQUIRED = {
    "README.md": 1500,
    "ARCHITECTURE.md": 1500,
    "DECISIONS.md": 800,
    "CONTRIBUTING.md": 800,
    "CHANGELOG.md": 400,
    "LICENSE": 1000,
    "DESIGN.md": 1500,
    "ROADMAP.md": 600,
    "EXAMPLES.md": 800,
}

#: Minimum number of ADRs required under docs/adr.
MIN_ADRS = 3


def main() -> int:
    """Check every required document is present and non-trivial.

    Returns:
        0 when the documentation set is complete, 1 otherwise.
    """
    failures: list[str] = []
    for rel, min_bytes in REQUIRED.items():
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"missing required document: {rel}")
            continue
        size = path.stat().st_size
        if size < min_bytes:
            failures.append(f"{rel} is only {size} bytes, expected at least {min_bytes}")

    adr_dir = ROOT / "docs" / "adr"
    adrs = sorted(adr_dir.glob("*.md")) if adr_dir.is_dir() else []
    adr_ok = len(adrs) >= MIN_ADRS
    if not adr_ok:
        failures.append(f"expected at least {MIN_ADRS} ADRs under docs/adr, found {len(adrs)}")

    print("Documentation check")
    print("-------------------")
    for rel in REQUIRED:
        path = ROOT / rel
        if path.is_file():
            print(f"  [ok  ] {rel} ({path.stat().st_size} bytes)")
        else:
            print(f"  [MISS] {rel}")
    adr_mark = "ok  " if adr_ok else "MISS"
    print(f"  [{adr_mark}] docs/adr: {len(adrs)} record(s), need {MIN_ADRS}")

    if failures:
        print("")
        print("FAIL")
        for failure in failures:
            print(f"  ! {failure}")
        return 1

    print("")
    print("PASS: documentation set is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
