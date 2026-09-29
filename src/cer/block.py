"""The typed context block: the unit the runtime budgets, lays out and compacts.

A block is the single thing the assembler places and the single thing compaction may
act on. Carrying the token count, the role, the pin flag and the provenance on the block
itself is what makes the legibility invariant checkable rather than aspirational.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cer.types import ArtifactKind, BlockRole, Provenance, Utility

#: The standard role table. Roles decide both layout segment and assembler priority,
#: so they are defined once here rather than scattered through the strategies.
ROLES: dict[str, BlockRole] = {
    "system": BlockRole(name="system", segment="system", priority=0),
    "tools": BlockRole(name="tools", segment="system", priority=1),
    "goal": BlockRole(name="goal", segment="stable", priority=2),
    "plan": BlockRole(name="plan", segment="stable", priority=3),
    "pinned_fact": BlockRole(name="pinned_fact", segment="stable", priority=4),
    "summary": BlockRole(name="summary", segment="stable", priority=5),
    "reference": BlockRole(name="reference", segment="stable", priority=6),
    "turn_user": BlockRole(name="turn_user", segment="volatile", priority=10),
    "turn_assistant": BlockRole(name="turn_assistant", segment="volatile", priority=11),
    "tool_call": BlockRole(name="tool_call", segment="volatile", priority=12),
    "tool_result": BlockRole(name="tool_result", segment="volatile", priority=13),
    "error": BlockRole(name="error", segment="volatile", priority=8),
}


def role_for(kind: ArtifactKind) -> BlockRole:
    """Return the standard role for an artifact kind.

    Args:
        kind: The artifact kind.

    Returns:
        The matching block role.

    Raises:
        KeyError: If the kind has no registered role.
    """
    mapping: dict[ArtifactKind, str] = {
        "message": "turn_assistant",
        "tool_call": "tool_call",
        "tool_result": "tool_result",
        "file": "reference",
        "summary": "summary",
        "fact": "pinned_fact",
        "error": "error",
        "goal": "goal",
        "plan": "plan",
    }
    return ROLES[mapping[kind]]


class ContextBlock(BaseModel):
    """One addressable piece of context.

    A block either carries its content inline, or carries a reference to content held
    out of band in the store. It never carries both: a block that inlined a large body
    would defeat the offload the ingestor performed.

    Attributes:
        block_id: Stable identifier, unique within a run.
        kind: What sort of artifact this block represents.
        role: The structural role, which decides layout segment and priority.
        text: Inline content, empty for an offloaded reference.
        ref: Content hash of the offloaded body, empty for inline content.
        tokens: Token cost of this block as presented to the model.
        pinned: Pinned blocks survive eviction and are never summarized.
        pair_id: Correlates a tool_call with its tool_result. Blocks sharing a pair_id
            are atomic and may never be split.
        step: The agent step at which the block was created.
        provenance: Where the block came from, and whether anything was lost.
        utility: Intrinsic value and decay rate for the allocation solver.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    block_id: str = Field(min_length=1)
    kind: ArtifactKind
    role: BlockRole
    text: str = ""
    ref: str = Field(default="", pattern=r"^$|^[0-9a-f]{64}$")
    tokens: int = Field(ge=0)
    pinned: bool = False
    pair_id: str = Field(default="", pattern=r"^$|^[a-zA-Z0-9_-]+$")
    step: int = Field(default=0, ge=0)
    provenance: Provenance
    utility: Utility = Field(default_factory=lambda: Utility(value=1.0))

    @model_validator(mode="after")
    def _check_content(self) -> ContextBlock:
        """A block must carry content, a reference, or be an explicit empty marker.

        Raises:
            ValueError: If the block claims tokens but carries neither text nor a
                reference, which would be a silent accounting error.
        """
        if not self.text and not self.ref and self.tokens > 0:
            msg = f"block {self.block_id} claims {self.tokens} tokens but has no content"
            raise ValueError(msg)
        return self

    @property
    def is_reference(self) -> bool:
        """True when the body lives in the store rather than inline.

        Returns:
            Whether this block is an offloaded reference.
        """
        return bool(self.ref)

    @property
    def is_lossy(self) -> bool:
        """True when producing this block may have lost information.

        Returns:
            The lossiness flag from provenance.
        """
        return self.provenance.lossy

    def utility_at(self, step: int) -> float:
        """Return this block decayed utility at a given step.

        Args:
            step: The current agent step.

        Returns:
            The decayed utility.
        """
        return self.utility.at(step)

    def density(self) -> float:
        """Return utility per token, the greedy ratio the solver sorts on.

        A zero-token block has infinite density, which correctly makes it free to
        include: it costs nothing.

        Returns:
            Utility divided by token cost, or infinity when the block is free.
        """
        if self.tokens <= 0:
            return float("inf")
        return self.utility.value / self.tokens

    def with_text(self, text: str, tokens: int) -> Self:
        """Return a copy carrying inline content.

        Args:
            text: The inline content.
            tokens: The token cost of that content.

        Returns:
            A new block with the content set and no reference.
        """
        return self.model_copy(update={"text": text, "ref": "", "tokens": tokens})

    def as_summary_of(
        self,
        sources: list[ContextBlock],
        text: str,
        tokens: int,
        *,
        detail: str = "",
    ) -> Self:
        """Return a summary block that is legible and reversible by construction.

        The returned block is marked lossy and carries every source hash, so the legibility
        invariant holds by construction rather than by convention. Sources that were
        themselves summaries contribute their own transitive sources, so a summary of a
        summary still points at the original artifacts.

        Args:
            sources: The blocks this summary replaces.
            text: The summary text.
            tokens: The token cost of the summary.
            detail: A human-readable note describing what was summarized.

        Returns:
            A new summary block.
        """
        hashes: list[str] = []
        for source in sources:
            hashes.extend(source.provenance.source_hashes)
            if source.ref:
                hashes.append(source.ref)
        unique = tuple(dict.fromkeys(hashes))
        if not unique:
            msg = "a summary must reference at least one retrievable source"
            raise ValueError(msg)
        provenance = Provenance(
            op="summarize",
            source_hashes=unique,
            step=self.step,
            lossy=True,
            detail=detail or f"summarized {len(sources)} blocks",
        )
        return self.model_copy(
            update={
                "kind": "summary",
                "role": ROLES["summary"],
                "text": text,
                "ref": "",
                "tokens": tokens,
                "pinned": False,
                "pair_id": "",
                "provenance": provenance,
            }
        )


__all__ = ["ROLES", "ContextBlock", "role_for"]
