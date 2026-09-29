# ADR 0001 - Cache-aware stable-prefix layout

- Status: Accepted
- Date: 2026-09-29

## Context

Provider prompt caches fire on an exact prefix match. Agent context is append-only,
so a naive layout invalidates the cache on every single step: appending one token
changes the prefix and the entire cache is lost.

## Decision

The assembler lays context out in fixed segments, in this order:

```
[ SYSTEM + TOOLS ]     stable for the whole run
[ GOALS / PLAN ]      stable for the task
[ PINNED FACTS ]      append-only, rarely changes
[ ---- cache boundary ---- ]
[ RECENT TURNS ]      volatile, changes every step
```

Blocks are assigned to segments by role, not by arrival order. The stable prefix is
byte-identical across steps within a run.

## Consequences

- The provider prefix cache hits on every request after the first.
- Only the volatile tail is re-processed and re-priced.
- Reordering is observable to the model, so the layout is part of the contract and is
  covered by tests.
- This is the highest-leverage change in the project and ships first.

## Alternatives considered

- Keep append-only order. Maximum familiarity, minimum cache efficiency.
- Cache each segment separately. Providers cache one prefix, not arbitrary segments.
- Summarize instead of reorder. Higher risk, lower and less predictable leverage.
