"""Context Engineering Runtime (CER).

CER treats LLM context as a managed, budgeted, evictable resource rather than an
append-only log. It sits between an agent loop and a model provider: the agent asks
for a task, and the runtime decides what the model actually sees.

Four components, each independently testable:

1. Ingestor - the single typed entry point for every artifact.
2. Store - content-addressed blob store with streaming reads and an FTS5 index.
3. Compaction - pluggable, composable strategies that shrink a transcript legibly.
4. Assembler - fills a token budget from a priority-ranked block list.

The runtime is provider-agnostic. All model access goes through a single internal
Provider trait, and the deterministic MockProvider lets the whole test suite run
offline with no API key.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
