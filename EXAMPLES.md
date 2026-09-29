# EXAMPLES.md

Three end-to-end scenarios. Each one is labelled with the vertical slice that
delivers it, so this document never claims something that does not exist yet. As each
slice lands, the example is promoted from planned to runnable and verified by CI.

---

## 1. Keep a long agent run inside its budget

**Delivered by slices 2-9 and 11.** The headline scenario: a research agent that
reads many files and calls many tools, over many steps, without ever exceeding its
context budget and without ever silently losing information.

```python
from cer import ContextConfig, ContextRuntime, TokenBudget
from cer.providers import MockProvider

config = ContextConfig(
    budget=TokenBudget(total=8000, reserve=1000),
    store={"backend": "filesystem", "spill_threshold_tokens": 200},
)
runtime = ContextRuntime(config, provider=MockProvider())

runtime.ingest.goal("Find every place the auth token is cached")
runtime.step("grep -r access_token src/")   # tool output spills out of band
runtime.step("read src/auth/cache.py")       # becomes a reference, not a blob
print(runtime.last_assembly.tokens)          # never exceeds the budget
```

The interesting part is what the model actually receives. The 50KB grep result is a
hash reference, the goal sits in the stable prefix, and the only thing in the volatile
tail is the current turn.


## 2. Measure the cache-aware layout against naive append-only

**Delivered by slice 5.** The claim the README leads with, expressed as a runnable
comparison rather than a table.

```python
from cer.bench import compare_layouts

result = compare_layouts(steps=40, system_tokens=900, goal_tokens=300)
print(result.cache_aware.cached_token_ratio)   # ~0.82
print(result.append_only.cached_token_ratio)   # ~0.01
print(result.savings)                          # measured, not asserted
```

Both layouts carry the same information. One reorders it so the byte-identical prefix
stays cacheable. The cost difference across a 40-step run is the single largest lever
in the project, and it is measured rather than asserted.


## 3. Compact without losing the ability to recover

**Delivered by slices 7, 8 and 10.** The legibility invariant in practice: summarize
an old stretch of the transcript, then prove the original is still retrievable.

```python
view = runtime.compact(budget=TokenBudget(total=4000))

for block in view.blocks:
    if block.provenance.lossy:
        # The agent can see that this is a summary, not a silent deletion.
        print(f"summary of {len(block.provenance.source_hashes)} blocks")
        for h in block.provenance.source_hashes:
            original = runtime.store.read(h)     # reversible, always
            print(f"  {h[:12]}: {len(original)} bytes")
```

Nothing is dropped quietly. A summary is a visible, labelled, reversible substitution,
and the invariant suite in CI fails the build if any code path produces a lossy block
whose originals cannot be recovered.


---

## Running the offline demo

Once the runtime lands, the whole story above runs with no API key:

```bash
make demo
```

That target is the acceptance test for this project. It uses the deterministic
`MockProvider`, touches no network, and prints real measured output. If it fails on a
clean checkout, the project is not done.
