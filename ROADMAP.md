# ROADMAP

## Now (in progress)

The build proceeds as a sequence of vertical slices, each merged green:

| Slice | Content |
|---|---|
| 1 | Repo scaffold, CI, tooling, pre-commit, branch protection |
| 2 | Typed block model, token counting, budget types |
| 3 | Content-addressed blob store, streaming reads, FTS5 metadata index |
| 4 | `ContextIngestor` with offload and the reference protocol |
| 5 | Cache-aware stable-prefix layout with measured savings |
| 6 | Greedy and exact-DP knapsack allocators, with bound tests |
| 7 | `SlidingWindow`, `RecursiveSummarization`, `ToolCallPairing` |
| 8 | `SemanticEviction`, `PinnedFactRetention` |
| 9 | `ContextAssembler`, block priority, budget fill |
| 10 | The legibility invariant suite and its CI gate |
| 11 | Benchmark harness, ablation runner, `MockProvider` |
| 12 | OpenTelemetry export |
| 13 | Full documentation set, ADRs, examples |
| 14 | Profiling pass with real numbers |
| 15 | v0.1.0 release, changelog, social preview image |

## Next

- Optional vector index behind a trait, with lexical degradation when absent.
- S3-compatible store backend.
- Streaming structured output from providers.
- A cost model that prices real provider caches when telemetry is available.

## Deliberately out of scope

- **Being an agent framework.** CER is a runtime, not a loop, not a planner, not a
  tool registry. It owns context; the agent owns behaviour.
- **Vendor SDK integrations in the core.** Optional adapters live outside the core
  behind the `Provider` trait.
- **A hosted control plane.** This is a library.
- **Automatic strategy selection per task.** The solver allocates tokens; choosing a
  compaction strategy is a policy decision the operator should own until there is
  evidence for a better default than a documented one.
- **Beating the model.** The runtime cannot make a weak model good at reasoning. It
  makes the context it receives defensible.
