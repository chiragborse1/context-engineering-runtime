# Contributing to CER

Thanks for looking. This project is small and opinionated on purpose.

## Setup

```bash
git clone https://github.com/chiragborse1/context-engineering-runtime.git
cd context-engineering-runtime
make install
make demo
```

`make install` creates a Python 3.12 virtualenv and installs the project with dev
extras. `make demo` runs the full pipeline offline with no API key. If `make demo`
fails on a clean checkout, that is a bug, not a setup problem.

## Everyday commands

| Command | What it does |
|---|---|
| `make test` | Full suite with the 80 percent coverage gate. |
| `make test-fast` | Skips slow and network tests and the coverage gate. |
| `make lint` | ruff lint plus format check. |
| `make format` | Applies ruff fixes and formatting. |
| `make typecheck` | mypy in strict mode. |
| `make security` | bandit. |
| `make audit` | pip-audit plus the dependency/license audit. |
| `make check` | Everything CI runs, locally. |
| `make docs-check` | Confirms the required documentation set is present. |
| `make quickstart` | Executes the README quickstart to prove it works. |

## Ground rules

1. **Never commit to `main`.** One logical change, one branch, one PR.
2. **One concern per PR.** If the description needs the word "and" twice, split it.
3. **Conventional commits**, imperative mood, scoped: `feat(store): ...`,
   `fix(compact): ...`, `docs(adrs): ...`, `chore(ci): ...`.
4. **Squash merge** so `main` history stays readable.
5. Delete the branch after merge.
6. `main` is protected: a PR and one approval with green CI are required.

## Branch naming

`feat/<scope>-<short>`, `fix/<scope>-<short>`, `docs/<scope>`, `test/<scope>`,
`perf/<scope>`, `chore/<scope>`.

## What a PR needs

- A description covering **What**, **Why**, **How to verify**, and **Related issue**.
- Green CI: build, test, lint, typecheck, security scan.
- Tests for the change. Property-based tests for parsers and round-trips.
- A `DECISIONS.md` entry if you made an autonomous design call.
- Public API changes noted in `CHANGELOG.md` under Keep a Changelog groups.

## Code standards

- Full type annotations. mypy strict passes with no suppressions.
- No bare `except:`. Errors come from the `cer.errors` hierarchy and carry a remedy.
- Docstrings on every public symbol, Google style.
- No `Any` or bare `dict` in a public signature without a written justification.
- No `# pragma: no cover` to dodge the coverage gate.
- No vendor SDK imports in the core. `scripts/dependency_audit.py` enforces this.

## Honesty rules for benchmarks

If a benchmark did not run, say so. Do not commit a number you did not measure. The
results under `bench/results/` are produced by a script, and CI re-runs it to check
they reproduce. An unflattering result is more valuable than a flattering one you
cannot defend.
