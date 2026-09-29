# ADR 0002 - Greedy ratio allocation with an exact DP for validation

- Status: Accepted
- Date: 2026-09-29

## Context

Choosing which blocks fit in a token budget is 0/1 knapsack over blocks with sizes
`s_i` and utility `u_i = value_i * exp(-lambda_i * staleness_i)`.

## Decision

Ship two solvers behind one interface:

- `SOLVER_GREEDY` (default). Sort by `u_i / s_i` descending, take while budget allows.
  O(n log n).
- `SOLVER_EXACT_DP`. Classic 0/1 knapsack table. O(n * B). For validation,
  benchmarks, and small contexts.

The greedy optimality bound is documented honestly, and the benchmark suite measures
the actual gap between greedy and the exact optimum on real workloads.

## Consequences

- The default policy is explainable: spend tokens on the highest utility per token.
- The claim that greedy is near-optimal is measured, not asserted.
- The DP is unusable at realistic budgets, which is why it is not the default.

## Alternatives considered

- Greedy only. Leaves the central claim unmeasured.
- DP only. O(n * B) does not scale to real budgets.
- An LP relaxation with branch and bound. Better bounds, much more machinery, and
  harder to explain in a debug log.
