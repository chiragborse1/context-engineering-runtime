# DECISIONS.md

Every autonomous decision made during this build, with reasoning and the
alternatives that were rejected. Ambiguity is not a blocker; an undocumented decision
is. This file is the record.

## D-001 - Pure Python core, no Rust component

**Decision.** The entire runtime is pure Python 3.12. No Rust store or solver.

**Reasoning.** The brief explicitly allows this if the Rust toolchain fights back, and
the project thesis is measurement, not throughput. The hot paths (streaming store reads,
greedy sort) are not the bottleneck; the model call is. Adding a cargo build step adds
CI fragility, cross-platform toolchain friction, and build complexity for no
measurable win. A Rust acceleration can be added later behind the same traits if
benchmarks ever demand it.

**Rejected.** Rust core for store/solver. Would double the build surface for
unmeasurable gain at this scale.

## D-002 - Zero vendor SDKs and zero agent frameworks in the core

**Decision.** Core dependencies are exactly `pydantic` and `tiktoken`. No `openai`,
`anthropic`, `google`, or `cohere` import anywhere in `src/`. No LangChain or similar.

**Reasoning.** This is the differentiator and the anti-wrapper defence. All model access
goes through one internal `Provider` trait. The whole test suite and all benchmarks run
offline against a deterministic `MockProvider`.

**Enforcement.** `scripts/dependency_audit.py` is an executable check run in CI. It
fails on any forbidden core dependency or any vendor import in `src/`. The allowlist
is explicit, so a new core dep is a deliberate act, not an accident.

**Rejected.** Optional vendor extras. Deferred; the Provider trait is the seam if they
are ever needed.

## D-003 - MIT license

**Decision.** MIT.

**Reasoning.** Maximum adoption friction for a developer-infrastructure library. Apache-2.0
adds a patent grant that is nice-to-have but not decisive here.

**Rejected.** Apache-2.0. The patent clause is not load-bearing for this project.

## D-004 - pydantic for all public types

**Decision.** Every public type is a pydantic `BaseModel`, frozen where it is a value
object.

**Reasoning.** Runtime validation at the boundaries (config, serialized blocks, provider
responses) plus first-class JSON schema. Immutability prevents a component from
mutating another component output in flight.

**Rejected.** dataclasses. No validation, no schema, and the hand-rolled validation is
where bugs live.

## D-005 - Streaming store reads, never full materialization

**Decision.** `ContextStore.open()` returns an iterator of byte chunks, never a string
or bytes object, for the whole body.

**Reasoning.** MCP tool output routinely returns 50KB JSON blobs; a full-file read into
memory for a reference the model will never see is the exact failure mode the runtime
exists to prevent. Streaming keeps peak memory independent of artifact size.

**Rejected.** `read()` returning `str`. Convenient, and it reintroduces the problem.

## D-006 - Legibility enforced as an error, not a warning

**Decision.** A lossy operation that cannot be made visible and reversible raises
`LegibilityError`. It does not degrade gracefully.

**Reasoning.** Section 2.9 of the brief calls this the single most important design
rule. A warning would let a regression ship. A hard failure in the invariant suite and
its CI gate makes the safety property structural rather than aspirational. Violating it
is a programming error, not a runtime condition.

**Rejected.** Telemetry-only enforcement. Silent failures are precisely the failure mode
being guarded against.

## D-007 - Greedy ratio solver as the default, exact DP shipped alongside

**Decision.** `SOLVER_GREEDY` (ratio-based, O(n log n)) is the default. `SOLVER_EXACT_DP`
(O(n * B)) ships for validation, benchmarks, and small contexts. The greedy optimality
bound is documented honestly and the actual gap is measured in the benchmark suite.

**Reasoning.** The 0/1 knapsack formulation is correct and gives a principled,
explainable policy ("highest utility per token") instead of the arbitrary heuristics
common in competing systems. Greedy is fast and debuggable; the DP proves how far off it
is on real workloads instead of asking the reader to trust a bound.

**Rejected.** Greedy only. Would leave the central claim unmeasured. DP only. O(n * B) is
unusable at realistic budgets.

## D-008 - Cache-aware layout as the headline, implemented first

**Decision.** The stable-prefix layout is built before the compaction strategies and is
the first thing in the README.

**Reasoning.** Naive prompt caching needs an exact prefix match, and agent context is
append-only, so it barely fires. Reordering into a byte-identical stable prefix recovers
the cache on every step and typically beats any summarization algorithm by a wide
margin. It is cheap to implement and disproportionately valuable, so it ships first.

**Rejected.** Leading with summarization. Lower leverage, higher risk (silent quality
loss), and harder to measure.

## D-009 - Cache accounting is modelled, not provider-queried

**Decision.** The runtime models provider prefix-cache behaviour from an explicit,
configurable policy (cache-write price, cache-read price, minimum cacheable prefix) and
reports cached versus uncached tokens per assembly.

**Reasoning.** Real cache-hit telemetry is provider-specific and unavailable offline. A
transparent, provider-parameterized model produces comparable, reproducible numbers on
a clean checkout with no API key. The model is explicit about its assumptions so the
number is auditable rather than magic.

**Rejected.** Reporting a real provider bill. Impossible in CI, and the point is
comparing layouts, not reconciling an invoice.


## D-010 - Python toolchain driven by uv

**Decision.** `uv` for venv, dependency resolution, and running tools. Makefile targets
wrap it.

**Reasoning.** Fast, reproducible, single binary, and it works identically on the
Windows dev machine and Linux CI. A `make demo` that behaves the same everywhere is a
requirement of the brief, not a preference.

**Rejected.** Plain `pip` + `venv`. Slower and drifts between environments.

## D-011 - Cross-platform Makefile without a shell dependency

**Decision.** The Makefile avoids `rm -rf` and other shell-isms; `clean` delegates to
`scripts/clean.py`.

**Reasoning.** The dev machine is Windows with GNU Make from Scoop and no bash on PATH.
Hard-coding a POSIX shell would make the local `make demo` fail while CI stayed green,
which is exactly the kind of false-green this project is arguing against.

**Rejected.** `SHELL := bash`. Broken locally; the brief requires local and CI parity.
