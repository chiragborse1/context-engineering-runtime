# Context Engineering Runtime - developer entry points.
# Every target works offline on a clean checkout with no API key.
# Cross-platform: works with GNU Make on Linux, macOS, and Windows.

PY := uv run python
UV := uv

.DEFAULT_GOAL := help

.PHONY: help install build test test-fast lint format typecheck security audit check \
        coverage demo bench bench-quick quickstart clean docs-check tidy

## help: show this help
help:
	@echo "Context Engineering Runtime (CER)"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Create .venv and install the project with dev extras"
	@echo ""
	@echo "Build and verify:"
	@echo "  make build          Build the wheel and sdist"
	@echo "  make test           Full test suite with the coverage gate (80 percent min)"
	@echo "  make test-fast      Tests without coverage, skipping slow and network"
	@echo "  make lint           ruff check plus ruff format --check"
	@echo "  make format         Apply ruff format and safe autofixes"
	@echo "  make typecheck      mypy in strict mode"
	@echo "  make security       bandit scan"
	@echo "  make audit          pip-audit plus the dependency license audit"
	@echo "  make check          build + lint + typecheck + test + security"
	@echo ""
	@echo "Run:"
	@echo "  make demo           Offline end-to-end demo, no API key required"
	@echo "  make bench          Full benchmark and ablation suite into bench/results"
	@echo "  make bench-quick    Fast benchmark subset for a quick signal"
	@echo "  make quickstart     Verify the README quickstart actually runs"
	@echo ""
	@echo "Housekeeping:"
	@echo "  make clean          Remove build, cache and runtime artifacts"
	@echo "  make docs-check     Check that every required doc exists and is substantial"
	@echo "  make tidy           Sync local git user.name and user.email"

install:
	$(UV) venv --python 3.12
	$(UV) pip install -e ".[dev]"
	@echo "Installed. Now run: make demo"

build:
	$(UV) build

test:
	$(UV) run pytest -m "not network"

test-fast:
	$(UV) run pytest -m "not slow and not network" --no-cov -q

lint:
	$(UV) run ruff check src tests scripts bench examples
	$(UV) run ruff format --check src tests scripts bench examples

format:
	$(UV) run ruff check --fix src tests scripts bench examples
	$(UV) run ruff format src tests scripts bench examples

typecheck:
	$(UV) run mypy

security:
	$(UV) run bandit -r src -c pyproject.toml -ll

audit:
	$(UV) run pip-audit
	$(PY) scripts/dependency_audit.py

check: build lint typecheck test security

## demo: run the offline demo (no API key, deterministic MockProvider)
demo:
	$(PY) -m cer.demo

## bench: run the full benchmark and ablation suite
bench:
	$(PY) -m cer.bench run --out bench/results

bench-quick:
	$(PY) -m cer.bench run --quick --out bench/results

## quickstart: verify the README quickstart is copy-pasteable
quickstart:
	$(PY) scripts/verify_quickstart.py

docs-check:
	$(PY) scripts/check_docs.py

clean:
	$(PY) scripts/clean.py

tidy:
	git config user.name "Chirag Borse"
	git config user.email "chiragborse877@gmail.com"
