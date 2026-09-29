"""Core value types shared across the runtime.

These are small, immutable and pydantic-validated so they can cross component
boundaries (ingestor to store to compaction to assembler to provider) without
defensive copying.
"""

from __future__ import annotations

import math
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ArtifactKind = Literal[
    "message",
    "tool_call",
    "tool_result",
    "file",
    "summary",
    "fact",
    "error",
    "goal",
    "plan",
]

Segment = Literal["system", "stable", "volatile"]


class _Frozen(BaseModel):
    """Base class for immutable value objects."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenBudget(_Frozen):
    """A token budget for a single assembled request.

    The total is a hard ceiling. The reserve is held back for the model own reply
    and is never allocated to context blocks.

    Attributes:
        total: Hard upper bound on tokens in the assembled request.
        reserve: Tokens reserved for generation.
    """

    total: int = Field(ge=1, description="Hard token ceiling for the request.")
    reserve: int = Field(default=0, ge=0, description="Tokens reserved for generation.")

    @property
    def available(self) -> int:
        """Tokens actually allocatable to context blocks.

        Returns:
            The difference between the total and the reserve.
        """
        return self.total - self.reserve

    @model_validator(mode="after")
    def _check_reserve(self) -> TokenBudget:
        """Ensure the reserve leaves at least one allocatable token.

        Returns:
            The validated budget.

        Raises:
            ValueError: If the reserve is not smaller than the total.
        """
        if self.reserve >= self.total:
            msg = f"reserve ({self.reserve}) must be smaller than total ({self.total})"
            raise ValueError(msg)
        return self


class AllocationPolicy(_Frozen):
    """Controls how the assembler fills a budget.

    Attributes:
        name: Identifier of the policy, used as a label in benchmark rows.
        respect_priority: When true, a lower-priority block is never included ahead
            of a higher-priority one unless the budget is exhausted.
    """

    name: str
    respect_priority: bool = True


class BlockRole(_Frozen):
    """Structural classification of a context block.

    Roles drive both the cache-aware layout, which decides which segment a block
    lands in, and the assembler ordering, where a lower priority number means more
    important.

    Attributes:
        name: Role identifier, for example system, goal, pinned_fact or turn.
        segment: Layout segment this role belongs to.
        priority: Lower values are more important.
    """

    name: str
    segment: Segment
    priority: int = Field(ge=0)


class Utility(_Frozen):
    """Utility of a block, decaying exponentially with staleness.

    Models u_i(step) = value_i * exp(-lambda_i * staleness_i(step)).

    Attributes:
        value: Intrinsic value assigned by policy.
        created_step: Step at which the underlying artifact was produced.
        lam: Exponential decay rate. Larger means faster decay.
    """

    value: float
    created_step: int = Field(default=0, ge=0)
    lam: float = Field(default=0.0, ge=0.0)

    def at(self, step: int) -> float:
        """Return decayed utility at the given agent step.

        Args:
            step: Current agent step index.

        Returns:
            The decayed utility value.
        """
        staleness = max(0, step - self.created_step)
        return self.value * math.exp(-self.lam * staleness)


class Provenance(_Frozen):
    """Where a piece of context came from, and whether it lost information.

    This is the spine of the legibility invariant. Every block produced by a lossy
    operation carries provenance pointing at the originals, plus their content
    hashes so the agent can rehydrate them from the store.

    Attributes:
        op: Operation that produced this block, for example ingest or summarize.
        source_hashes: Content hashes of the originals, in order.
        step: Agent step at which the operation happened.
        lossy: True when information may have been lost.
        detail: Human-readable note, for example "summarized 18 turns".
        created_at: Wall-clock timestamp of creation, seconds since the epoch.
    """

    op: str
    source_hashes: tuple[str, ...] = ()
    step: int = Field(default=0, ge=0)
    lossy: bool = False
    detail: str = ""
    created_at: float = Field(default_factory=time.time)

    def merge(self, other: Provenance) -> Provenance:
        """Combine with an upstream provenance, preserving both source chains.

        Args:
            other: Provenance of the upstream operation.

        Returns:
            A new provenance whose op is this one, with source hashes unioned and
            lossiness or-ed together.
        """
        return Provenance(
            op=self.op,
            source_hashes=tuple(dict.fromkeys(other.source_hashes + self.source_hashes)),
            step=self.step,
            lossy=self.lossy or other.lossy,
            detail=f"{other.detail}; {self.detail}" if other.detail else self.detail,
            created_at=self.created_at,
        )

    def with_detail(self, detail: str) -> Provenance:
        """Return a copy with extra detail appended.

        Args:
            detail: Text to append to the existing detail.

        Returns:
            A new provenance carrying the combined detail.
        """
        return Provenance(
            op=self.op,
            source_hashes=self.source_hashes,
            step=self.step,
            lossy=self.lossy,
            detail=f"{self.detail}; {detail}" if self.detail else detail,
            created_at=self.created_at,
        )


__all__ = [
    "AllocationPolicy",
    "ArtifactKind",
    "BlockRole",
    "Provenance",
    "Segment",
    "TokenBudget",
    "Utility",
]
