# ADR 0004 - Pure Python core, provider-agnostic by construction

- Status: Accepted
- Date: 2026-09-29

## Context

The project is about measurement, not throughput. It must also work with a local
model and with no API key at all.

## Decision

- Pure Python 3.12 core. No Rust component.
- Core dependencies are exactly pydantic and tiktoken.
- No vendor SDK import anywhere in `src/`. No agent framework.
- All model access goes through one internal `Provider` trait.
- A deterministic `MockProvider` backs the entire test suite and benchmark suite.

## Consequences

- CI runs offline with no API key.
- The whole system works against Ollama, llama.cpp, or vLLM through an
  OpenAI-compatible adapter.
- `scripts/dependency_audit.py` enforces the dependency rule in CI.

## Alternatives considered

- A Rust store or solver. Build friction for no measurable win at this scale.
- Optional vendor extras in the core. The `Provider` trait is the seam if ever needed.
- LangChain as a substrate. Would undercut the thesis and void the dependency audit.
