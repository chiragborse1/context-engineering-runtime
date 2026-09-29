# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository scaffold: `pyproject.toml`, Makefile, ruff / mypy strict / pytest
  configuration, pre-commit hooks, and a GitHub Actions pipeline covering build,
  test, lint, typecheck and security scan.
- Typed exception hierarchy (`cer.errors`) and core value types (`cer.types`).
- Single configuration object (`cer.config`) with no global mutable state.
- Executable documentation and dependency checks under `scripts/`.
- GitHub Actions gates for the legibility suite and benchmark reproducibility activate
  conditionally, so a red CI always means a real regression rather than a slice that
  has not landed yet.

### Added (planned)

- Typed block model, token counting and budget types.
- Content-addressed blob store with streaming reads and an FTS5 metadata index.
- `ContextIngestor` with out-of-band offload and the reference protocol.
- Cache-aware stable-prefix layout with measured savings.
- Greedy and exact-DP knapsack allocators.
- Compaction strategies: sliding window, recursive summarization, tool-call pairing,
  semantic eviction, pinned fact retention.
- `ContextAssembler` with block priority and budget fill.
- The legibility invariant suite and its CI gate.
- Benchmark harness, ablation runner and the deterministic `MockProvider`.
- OpenTelemetry export.
