# ADR 0003 - Legibility as a hard invariant

- Status: Accepted
- Date: 2026-09-29

## Context

The single most important rule in this project: compaction must never silently lose
information the agent needs. A runtime that quietly drops context is worse than no
runtime, because it produces confident wrong behaviour with no diagnostic.

## Decision

Every lossy operation must be legible and reversible:

1. The agent can see that something was summarized.
2. The agent can retrieve the original through its content reference.
3. The agent knows the provenance, meaning which originals produced this summary.

Mechanically, any block with `provenance.lossy == True` must have non-empty
`source_hashes`, must resolve to retrievable content in the store, and must be marked
in the rendered output. A violation raises `LegibilityError` rather than degrading
silently.

## Consequences

- A dedicated test suite and a CI gate enforce it.
- Summaries remain retrievable, so the agent can self-correct.
- Telemetry-only enforcement was rejected: a warning lets the regression ship.

## Alternatives considered

- Telemetry only. Silent failure is exactly the failure mode being guarded against.
- Never compact. Safe but useless; the budget still has to fit.
- Trust the summarizer. Unverifiable and unmeasured.
