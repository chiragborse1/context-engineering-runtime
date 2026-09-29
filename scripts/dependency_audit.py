"""Dependency audit: prove the core carries no vendor SDK and no heavy framework.

This is an executable version of the claim the README makes. It inspects the
project metadata and the source tree, and fails if any forbidden dependency or
vendor import appears.

Run by `make audit` and in CI.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Vendor SDKs that must never appear in core code or core dependencies.
FORBIDDEN_VENDOR = (
    "openai",
    "anthropic",
    "google",
    "cohere",
    "mistralai",
)

#: Heavy agent frameworks the project deliberately does not depend on.
FORBIDDEN_FRAMEWORKS = (
    "langchain",
    "langgraph",
    "llama-index",
    "llamaindex",
    "autogen",
    "crewai",
    "semantic-kernel",
)

#: Packages allowed in the core dependency set.
ALLOWED_CORE = {
    "context-engineering-runtime",
    "pydantic",
    "pydantic-core",
    "annotated-types",
    "typing-extensions",
    "typing-inspection",
    "tiktoken",
    "regex",
}


def normalize(name: str) -> str:
    """Return a comparable form of a distribution name.

    Args:
        name: Distribution name as written in metadata.

    Returns:
        The name lowercased with separators normalized to hyphens.
    """
    return name.strip().lower().replace("_", "-")


def dist_name(req: str) -> str:
    """Extract the distribution name from a requirement specifier.

    Args:
        req: Requirement string such as "pydantic>=2.9,<3".

    Returns:
        The bare distribution name.
    """
    for sep in ("[", ";", "<", ">", "=", "!", "~", " "):
        req = req.split(sep, maxsplit=1)[0]
    return normalize(req)


def load_core_dependencies() -> list[str]:
    """Read the core dependency list from pyproject.toml.

    Returns:
        The list of core requirement strings.
    """
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    return list(project.get("dependencies", []))


def audit_source_imports() -> list[str]:
    """Scan the source tree for forbidden vendor imports.

    Returns:
        A list of violations, empty when the source tree is clean.
    """
    violations: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for vendor in FORBIDDEN_VENDOR:
                if stripped == f"import {vendor}" or stripped.startswith(f"from {vendor}."):
                    violations.append(f"{rel}:{lineno}: forbidden vendor import {stripped}")
    return violations


def main() -> int:
    """Run the dependency audit.

    Returns:
        0 when the project is clean, 1 otherwise.
    """
    core = load_core_dependencies()
    names = {dist_name(r) for r in core}
    import_violations = audit_source_imports()
    failures: list[str] = []

    for name in sorted(names):
        if name in FORBIDDEN_VENDOR:
            failures.append(f"core dependency must not vendor an SDK: {name}")
        if name in FORBIDDEN_FRAMEWORKS:
            failures.append(f"core dependency must not use an agent framework: {name}")
        if name not in ALLOWED_CORE:
            failures.append(f"undeclared core dependency: {name}")
    failures.extend(import_violations)

    print("Dependency audit")
    print("------------------")
    print(f"core dependencies ({len(names)}):")
    for name in sorted(names):
        print(f"  - {name}")
    print(f"vendor SDKs checked: {len(FORBIDDEN_VENDOR)}")
    print(f"agent frameworks checked: {len(FORBIDDEN_FRAMEWORKS)}")
    print(f"vendor imports in src/: {len(import_violations)}")

    if failures:
        print("")
        print("FAIL")
        for failure in failures:
            print(f"  ! {failure}")
        return 1

    print("")
    print("PASS: no vendor SDK, no agent framework, no undeclared core dependency.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
