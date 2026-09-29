# DESIGN.md - Context Engineering Runtime

This document was written before the first line of core code and is kept current as
the implementation evolves. It records the architecture, data flow, edge cases,
performance reasoning, and the tradeoffs behind each choice.

---

## 1. Problem statement

An LLM agent context window has an opaque cost function and three simultaneous
failure modes:

1. **Unbounded growth.** Tool results, file reads, and intermediate reasoning are
   appended monotonically until the run dies, usually after the expensive work is
   already done.
2. **Attention dilution.** Inside the window, the useful signal is buried. Degradation
   is positional and structural, not merely a function of total token count.
3. **Cost amplification.** The entire transcript is resent every turn, so an N-step
   agent pays roughly O(N^2) tokens. This dominates agent infrastructure cost and is
   almost always paid unknowingly.

Existing tools treat these separately. Conversation summarizers compress. Vector RAG
retrieves. Prompt caching discounts repeats. None of them manage context as a
budgeted resource with an explicit lifecycle and measurable efficacy.

## 2. Thesis

> Context is a managed, budgeted, evictable resource, not an append-only log.

The runtime sits between the agent loop and the model provider and owns context. The
agent asks for a *task*; the runtime decides what the model actually *sees*. Nothing
reaches the provider unmediated.

## 3. Component architecture

Four components, each independently testable, with no hidden coupling:

### 3.1 ContextIngestor (ingress)

The single typed entry point for every artifact: tool output, file, message, error,
goal, plan.

- Classifies by artifact kind using declared type plus content sniffing.
- Computes a SHA-256 content hash.
- Spills large bodies out of band into the store and returns a lightweight typed
  reference instead.
- In-band artifacts (below the spill threshold) return inline content.
- Attaches `Provenance` to every artifact so the legibility invariant is
  satisfiable by construction.

Nothing else in the runtime is permitted to write to the store. The ingestor is the
enforcement point.

### 3.2 ContextStore (storage)

Content-addressed blob store keyed by SHA-256.

- Pluggable backend: in-memory, filesystem, S3-compatible.
- `open(ref) -> Iterator[bytes]` returns a **stream**, not a string, so bodies are
  never fully materialized in memory. This is what makes 50KB MCP tool output a
  non-event.
- Metadata in SQLite with an FTS5 index for lexical search over artifact metadata and
  lightweight text bodies.
- Content pinning that survives eviction: a pinned hash is never removed by the
  eviction pass.
- Integrity verification: a read that hashes to something other than the key raises
  `StoreIntegrityError` rather than returning corrupt bytes.

### 3.3 CompactionStrategy (transformation)

Pluggable and composable. Takes a token-bounded view and produces a smaller one that
preserves a contract rather than a vibe.

| Strategy | Behaviour |
|---|---|
| `SlidingWindow` | Baseline. Keep the last K turns verbatim. |
| `RecursiveSummarization` | Hierarchical. Summarize, then summarize the summary. |
| `SemanticEviction` | Embed, evict lowest relevance to the current goal. |
| `PinnedFactRetention` | Extract durable facts and goals, keep them verbatim. |
| `ToolCallPairing` | Never split a request/response pair, never drop an error. |

**Hard correctness rules.**

1. Compaction is **idempotent**: compacting an already-compacted view returns an
   equivalent view, and a second pass never shrinks further or changes provenance
   in a way that breaks rehydration.
2. The token counter is **monotonic** in the sense that the reported size never
   grows across a compaction pass.
3. Pinned content is **never** summarized or evicted.
4. A tool-call request and its result are **atomic**. Splitting them produces a
   malformed transcript that the model will confidently misinterpret.
5. Errors are **never** dropped.

### 3.4 ContextAssembler (construction)

Builds the final request from a priority-ranked block list, filling to a token budget
via a configurable allocation policy. This is where the knapsack solver lives.

## 4. The caching insight (headline contribution)

Naive prompt caching only fires on an **exact prefix match**. Append one token and the
whole cache is invalidated. Agent context is append-only, so naive caching helps
almost nothing.

Cache-aware layout reorders context into immutable segments:

```
[ SYSTEM + TOOLS ]   stable across every step in a run
[ GOALS / PLAN ]    stable per task
[ PINNED FACTS ]    append-only, rarely changes
[ ---- cache boundary ---- ]
[ RECENT TURNS ]    volatile, changes every step
```

The stable prefix is byte-identical across steps, so the provider prefix cache hits on
every request. Only the volatile tail is re-processed.

This single change typically dwarfs the savings from any summarization algorithm,
and almost no open-source agent framework implements it. It is the first thing in the
README.

**Measurement.** The runtime models a provider prefix cache with an explicit policy
(cache-write price, cache-read price, minimum cacheable prefix) and reports, per
assembly, how many tokens fell inside the cacheable prefix versus how many a naive
append-only layout would have cached. The number is measured, not asserted.

## 5. The allocation solver (mathematical core)

Model context as blocks with sizes `s_i` and utility that decays with staleness:

```
u_i(step) = value_i * exp(-lambda_i * staleness_i(step))
```

Then maximize total utility subject to a hard token budget:

```
maximize    SUM_i  u_i(step) * x_i
subject to  SUM_i  s_i * x_i <= B
            x_i in {0, 1}
```

This is 0/1 knapsack. Greedy by `u_i / s_i` ratio is optimal for the fractional
relaxation and is within a provable bound of the integer optimum, so we ship greedy
as the default and report the bound honestly. An exact dynamic program is also shipped
for validation and small contexts.

| Solver | Complexity | Role |
|---|---|---|
| `SOLVER_GREEDY` | O(n log n) | Default production policy. |
| `SOLVER_EXACT_DP` | O(n * B) | Validation, benchmarks, small contexts. |

**Honest statement of the bound.** For greedy-by-ratio on 0/1 knapsack, if `G` is the
greedy value and `OPT` the optimum, then `G >= (1 - 1/e) * OPT` when the fractional
relaxation is solved exactly. This is the classic result for the greedy set-cover-style
argument and it is what we report. We do not claim greedy is optimal; the benchmark
suite measures the actual gap against the exact DP on real workloads and publishes it.

Why it matters: "spend tokens on the highest utility-per-token" is a clean,
explainable, debuggable policy. Most competing systems use arbitrary heuristics that
cannot be justified or measured.

## 6. The legibility invariant (the safety property)

> Compaction must never silently lose information the agent needs.

Every lossy operation must be **legible and reversible**:

- The agent can **see** that something was summarized (a visible summary block with
  provenance, not a silent deletion).
- The agent can **retrieve** the original through its content reference.
- The agent **knows the provenance**: which originals produced this summary.

A runtime that quietly drops context is worse than no runtime, because it produces
confident wrong behaviour with no diagnostic. Legibility is the safety property and
it is designed in from line one, enforced by a dedicated test suite and a CI gate.

**Mechanically:** any block with `provenance.lossy == True` must (a) have a
non-empty `source_hashes`, (b) resolve to retrievable content in the store, and (c) be
marked in the rendered output so the model can see the substitution. Violations raise
`LegibilityError`.

## 7. Data flow

```
agent  ->  ContextRuntime.run(task)
             |
             |  1. ingest task + artifacts through ContextIngestor
             |     (classify, hash, spill large bodies, attach provenance)
             |  2. append transcript blocks, tagging tool pairs as atomic
             |  3. compact via the composed CompactionStrategy chain
             |     (idempotent, pinned-safe, pair-safe, error-safe)
             |  4. lay out into cache-aware segments
             |     (stable prefix byte-identical across steps)
             |  5. assemble under budget via the knapsack solver
             |  6. call the Provider once, with cache accounting
             |  7. ingest the response, append, repeat
             v
        response
```

## 8. Edge cases (designed for explicitly)

| Edge case | Handling |
|---|---|
| Artifact larger than the budget | Offloaded; the reference is tiny. Assembly places the reference, never the body. |
| Single block larger than total budget | `BudgetExceededError` naming the block. The runtime does not silently truncate. |
| Tool call with no matching result | Kept, marked incomplete, never split from a later orphan result. |
| Store backend unavailable | `StoreBackendError` with a remedy. Never a silent fallback to memory. |
| Tokenizer unavailable for a provider | Conservative character-based fallback, recorded in the assembly so numbers are honest. |
| Embeddings absent (SemanticEviction) | Degrades to lexical overlap via the FTS5 index. Records the degradation. |
| Compaction produces no reduction | Idempotency check fires; `IdempotencyError` if the view changed anyway. |
| Zero-value goal and empty budget | Returns an empty, valid assembly with a diagnostic, not an exception. |
## 9. Performance reasoning

- Store reads are streamed, so peak memory is independent of artifact size.
- Token counts are cached by content hash, so repeated counting is free.
- The greedy solver is O(n log n) and dominates nothing; it is not the bottleneck.
- FTS5 keeps lexical search sublinear in corpus size.
- The stable-prefix layout is the largest cost lever, and it is O(1) to implement.

Benchmarks are committed as code and results are written to `bench/results/`. Numbers
are reproducible from a clean checkout with no API key.

## 10. Tradeoffs and rejected alternatives

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Core language | Python 3.12 | Rust core | This project is about measurement, not throughput. A Rust store/solver would add toolchain friction for no measurable win at this scale. Rust is a legitimate later optimization if benchmarks demand it. |
| Heavy frameworks | None | LangChain / LlamaIndex | A framework dependency would undercut the whole thesis and make the dependency audit meaningless. |
| Store | SQLite + FTS5 + files | Postgres, Chroma, FAISS | Zero-dependency, single-file, works offline, FTS5 is built in. Vector search is optional behind a trait. |
| Vector index | Optional, behind a trait | Required core dependency | The core must work with no embeddings available. |
| Summarization | Interface owned, impl swappable | Hard-wired to one model | Summarization quality is provider-dependent; the interface is ours. |
| Config | One pydantic `ContextConfig` | Globals, env sprawl | Explicit config is testable and serializable. No global mutable singletons. |

## 11. Testability contract

- The `MockProvider` is deterministic and offline, so the entire suite and all
  benchmarks run in CI with no API key.
- Every component is independently constructible and independently testable.
- Property-based tests cover parsers and round-trips; golden files cover anything
  token- or output-sensitive; concurrency tests cover anything concurrent.
