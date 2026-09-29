# Context Engineering Runtime (CER)

> An LLM agent context window is not a log. It is a budget.

**Status:** pre-alpha scaffold. See [ROADMAP.md](ROADMAP.md) for what exists today.

CER is a provider-agnostic runtime that sits between an agent loop and a model
provider. The agent asks for a *task*; the runtime decides what the model actually
*sees*. Context is a managed, budgeted, evictable resource with an explicit
lifecycle and measurable efficacy.

## Why

Three failures happen at once in a long-running agent:

1. **Unbounded growth.** Every tool result and intermediate step is appended until
   the run dies, often after the expensive work is already done.
2. **Attention dilution.** Inside the window, the useful signal is buried. Degradation
   is positional and structural, not just a function of token count.
3. **Cost amplification.** The whole transcript is resent every turn, so an N-turn
   agent pays roughly O(N^2) tokens.

Existing tools address these separately: summarizers compress, vector RAG retrieves,
prompt caching discounts repeats. None of them treat context as a resource with a
budget and a lifecycle.

## Quickstart

```python
print("placeholder - replaced in PR 11 once the runtime exists")
```

## Design principles

- **Legibility.** Every lossy operation is visible and reversible. The agent can see
  that something was summarized and retrieve the original through its reference. A
  runtime that quietly drops context is worse than no runtime.
- **Endpoint independence.** Zero vendor SDKs in the core. All model access goes
  through one internal `Provider` trait, and the test suite runs offline.
- **Measurement over assertion.** Claims about token savings and quality are produced
  by a runnable harness, not a static table.

## Documentation

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, data flow, diagrams |
| [DESIGN.md](DESIGN.md) | Design written before the code, kept current |
| [DECISIONS.md](DECISIONS.md) | Every autonomous decision and its reasoning |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup and PR conventions |
| [CHANGELOG.md](CHANGELOG.md) | Keep a Changelog format |
| [EXAMPLES.md](EXAMPLES.md) | End-to-end usage scenarios |
| [ROADMAP.md](ROADMAP.md) | What is next and what is out of scope |

## License

MIT. See [LICENSE](LICENSE).
