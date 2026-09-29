# ARCHITECTURE

CER sits between an agent loop and a model provider and owns context. This document
describes the components, the data flow, and the module map.

## Component diagram

```mermaid
flowchart LR
    Agent["Agent loop"] -->|task| Runtime["ContextRuntime"]
    Runtime -->|ingest| Ing["ContextIngestor"]
    Ing -->|reference| Store["ContextStore<br/>(sha256 blobs)"]
    Ing -->|block| Compact["CompactionStrategy chain"]
    Compact -->|legible view| Layout["Cache-aware layout"]
    Layout -->|ranked blocks| Solver["Allocation solver<br/>greedy | exact DP"]
    Solver -->|assembled request| Provider["Provider"]
    Provider -->|response| Ing
    Store -->|stream| Layout
    Obs["OpenTelemetry"] -.-> Runtime

    subgraph Core["cer.core - no vendor SDKs, no frameworks"]
        Ing
        Store
        Compact
        Layout
        Solver
    end

    subgraph Providers["cer.providers - swappable"]
        Mock["MockProvider (deterministic, offline)"]
        OpenAICompat["OpenAI-compatible<br/>(Ollama, vLLM, llama.cpp)"]
        Anthropic["Anthropic"]
    end
```

## Sequence: one agent step

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant R as ContextRuntime
    participant I as ContextIngestor
    participant S as ContextStore
    participant C as Compaction
    participant L as Layout
    participant K as Solver
    participant P as Provider

    A->>R: run(task, step)
    R->>I: ingest(task)
    I->>I: classify and sha256
    I->>S: spill body if large
    I-->>R: ArtifactRef (typed)
    R->>C: compact(transcript, budget)
    C-->>R: legible view (provenance intact)
    R->>L: lay out into segments
    L-->>R: stable prefix and volatile tail
    R->>K: allocate(blocks, budget)
    K-->>R: selected blocks plus cache accounting
    R->>P: complete(request)
    P-->>R: response and usage
    R->>I: ingest(response)
    R-->>A: response
```

## Cache-aware layout

```mermaid
flowchart TB
    subgraph Run["A single run, steps 1 to N"]
        direction TB
        S1["SYSTEM + TOOLS<br/>byte-identical"] --> G1["GOALS / PLAN<br/>byte-identical"]
        G1 --> P1["PINNED FACTS<br/>byte-identical"]
        P1 --> B{{"cache boundary"}}
        B --> V1["RECENT TURNS<br/>changes every step"]
    end
    B -.->|prefix cache hits on every step| H["Provider cache"]
    V1 -.->|re-processed only| H
```

## Module map

| Module | Responsibility |
|---|---|
| `cer.types` | Immutable value types: `TokenBudget`, `Provenance`, `Utility`, `BlockRole`. |
| `cer.errors` | Typed exception hierarchy with remedies. |
| `cer.tokens` | The `TokenCounter` trait and the tiktoken-backed implementation. |
| `cer.store` | `ContextStore`, backends (memory / filesystem / S3), SQLite FTS5 metadata. |
| `cer.ingest` | `ContextIngestor`, artifact classification, offload, reference protocol. |
| `cer.layout` | Cache-aware segment layout and cache accounting. |
| `cer.solver` | `SOLVER_GREEDY` and `SOLVER_EXACT_DP` allocators. |
| `cer.compact` | Compaction strategies and composition. |
| `cer.assemble` | `ContextAssembler` and the allocation policy. |
| `cer.legibility` | The invariant checks and the `LegibilityError` guard. |
| `cer.providers` | The `Provider` trait and its adapters, including `MockProvider`. |
| `cer.config` | The single `ContextConfig` pydantic model. |
| `cer.runtime` | `ContextRuntime`, the facade that wires everything together. |
| `cer.bench` | Benchmark harness, ablation runner, Pareto frontier, efficacy index. |
| `cer.observability` | OpenTelemetry export. |

## Data flow summary

1. **Ingress.** Every artifact enters through `ContextIngestor`. It classifies by type,
   hashes the content, spills large bodies out of band, and returns a typed reference
   carrying provenance. Nothing reaches the provider unmediated.
2. **Storage.** `ContextStore` keeps bodies by content hash and hands back streams, not
   strings. Metadata lives in SQLite with an FTS5 index for lexical search. Pinned
   content survives eviction.
3. **Compaction.** A chain of strategies shrinks the transcript while preserving the
   contract: idempotent, pair-safe, error-safe, and pinned-safe. Every lossy step stays
   legible.
4. **Assembly.** Blocks are laid out into cache-aware segments, then the solver fills
   the token budget by utility per token, and the provider is called once.

## Invariants

| Invariant | Enforced by |
|---|---|
| Compaction is idempotent | `cer.compact` checks, plus the invariant suite. |
| Tool-call pairs are never split | `ToolCallPairing`, plus the invariant suite. |
| Errors are never dropped | `ToolCallPairing`, plus the invariant suite. |
| Pinned content is never evicted or summarized | Pin checks in compaction and the store. |
| Every lossy operation is visible and reversible | `cer.legibility`, gated in CI. |
| The reported token count never grows across a compaction pass | Compaction check. |
