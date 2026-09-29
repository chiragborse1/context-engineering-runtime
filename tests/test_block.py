"""Tests for the typed context block."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cer.block import ROLES, ContextBlock, role_for
from cer.types import Provenance, Utility

HASH_A = "a" * 64
HASH_B = "b" * 64


def make_block(**overrides: object) -> ContextBlock:
    """Build a valid block, overriding fields as needed.

    Args:
        overrides: Field values to replace.

    Returns:
        A constructed block.
    """
    defaults: dict[str, object] = {
        "block_id": "b1",
        "kind": "message",
        "role": ROLES["turn_assistant"],
        "text": "hello",
        "tokens": 2,
        "provenance": Provenance(op="ingest"),
    }
    defaults.update(overrides)
    return ContextBlock(**defaults)  # type: ignore[arg-type]


class TestRoles:
    """The role table."""

    def test_system_roles_are_in_the_system_segment(self) -> None:
        """System and tools form the immutable head of the prompt."""
        assert ROLES["system"].segment == "system"
        assert ROLES["tools"].segment == "system"

    def test_goal_and_facts_are_stable(self) -> None:
        """Goals, plans and pinned facts form the cacheable middle."""
        for name in ("goal", "plan", "pinned_fact", "summary", "reference"):
            assert ROLES[name].segment == "stable"

    def test_turns_are_volatile(self) -> None:
        """Conversation turns change every step."""
        for name in ("turn_user", "turn_assistant", "tool_call", "tool_result"):
            assert ROLES[name].segment == "volatile"

    def test_errors_outrank_turns(self) -> None:
        """An error is more important than an ordinary turn."""
        assert ROLES["error"].priority < ROLES["turn_assistant"].priority

    @pytest.mark.parametrize(
        ("kind", "expected"),
        [
            ("message", "turn_assistant"),
            ("tool_call", "tool_call"),
            ("tool_result", "tool_result"),
            ("file", "reference"),
            ("summary", "summary"),
            ("fact", "pinned_fact"),
            ("error", "error"),
            ("goal", "goal"),
            ("plan", "plan"),
        ],
    )
    def test_role_for_kind(self, kind: str, expected: str) -> None:
        """Every artifact kind maps to a registered role."""
        assert role_for(kind).name == expected  # type: ignore[arg-type]


class TestContextBlock:
    """Core block behaviour."""

    def test_inline_block(self) -> None:
        """A block with text is not a reference."""
        block = make_block()
        assert block.is_reference is False
        assert block.is_lossy is False

    def test_reference_block(self) -> None:
        """A block with a hash is a reference."""
        block = make_block(text="", ref=HASH_A, kind="file", role=ROLES["reference"])
        assert block.is_reference is True

    def test_rejects_tokens_without_content(self) -> None:
        """Claiming tokens with no content is an accounting error."""
        with pytest.raises(ValidationError, match="no content"):
            make_block(text="", ref="", tokens=5)

    def test_allows_zero_token_empty_block(self) -> None:
        """A free marker with no content is legal."""
        assert make_block(text="", ref="", tokens=0).tokens == 0

    def test_rejects_malformed_ref(self) -> None:
        """A reference must be a 64-character hex digest."""
        with pytest.raises(ValidationError):
            make_block(text="", ref="not-a-hash", tokens=3)

    def test_rejects_malformed_pair_id(self) -> None:
        """A pair id must be a safe identifier."""
        with pytest.raises(ValidationError):
            make_block(pair_id="bad id with spaces")

    def test_is_frozen(self) -> None:
        """Blocks are immutable once constructed."""
        block = make_block()
        with pytest.raises(ValidationError):
            block.tokens = 99  # type: ignore[misc]


class TestDensity:
    """The greedy ratio."""

    def test_density_is_utility_per_token(self) -> None:
        """Density is the value the solver sorts on."""
        block = make_block(tokens=4, utility=Utility(value=2.0))
        assert block.density() == pytest.approx(0.5)

    def test_free_block_has_infinite_density(self) -> None:
        """A zero-token block is free, so it should always be included."""
        assert make_block(tokens=0).density() == float("inf")

    def test_utility_at_decays(self) -> None:
        """Utility decays with staleness."""
        block = make_block(utility=Utility(value=1.0, created_step=0, lam=1.0))
        assert block.utility_at(0) == pytest.approx(1.0)
        assert block.utility_at(2) < block.utility_at(0)


class TestLegibilityOnSummaries:
    """A summary must be visible and reversible by construction."""

    @staticmethod
    def source_block() -> ContextBlock:
        """Build a block whose body lives in the store.

        Returns:
            An offloaded reference block.
        """
        return make_block(
            block_id="src",
            kind="file",
            role=ROLES["reference"],
            text="",
            ref=HASH_A,
            tokens=4,
            provenance=Provenance(op="ingest", source_hashes=(HASH_A,)),
        )

    def test_summary_is_marked_lossy(self) -> None:
        """The agent must be able to see that a substitution happened."""
        summary = self.source_block().as_summary_of([self.source_block()], "text", 3)
        assert summary.is_lossy is True

    def test_summary_carries_source_hashes(self) -> None:
        """The originals must be retrievable through the summary."""
        source = self.source_block()
        summary = source.as_summary_of([source], "text", 3)
        assert HASH_A in summary.provenance.source_hashes

    def test_summary_becomes_a_summary_block(self) -> None:
        """The summary takes the summary role and segment."""
        source = self.source_block()
        summary = source.as_summary_of([source], "text", 3)
        assert summary.kind == "summary"
        assert summary.role.name == "summary"
        assert summary.role.segment == "stable"

    def test_provenance_is_transitive(self) -> None:
        """A summary of a summary still points at the original artifacts."""
        source = self.source_block()
        first = source.as_summary_of([source], "one", 3)
        second = first.as_summary_of([first], "two", 2)
        assert second.provenance.source_hashes == (HASH_A,)

    def test_refuses_unrecoverable_summary(self) -> None:
        """A summary with no retrievable source is rejected."""
        with pytest.raises(ValueError, match="retrievable source"):
            make_block(text="hello", tokens=2).as_summary_of([make_block()], "x", 1)

    def test_deduplicates_sources(self) -> None:
        """The same artifact summarized twice yields one hash."""
        source = self.source_block()
        summary = source.as_summary_of([source, source], "text", 3)
        assert summary.provenance.source_hashes.count(HASH_A) == 1

    def test_is_never_pinned(self) -> None:
        """A summary of a pinned block is still a summary, not a pinned block."""
        source = self.source_block()
        summary = source.as_summary_of([source], "text", 3)
        assert summary.pinned is False

    def test_with_text_replaces_a_reference(self) -> None:
        """Rehydrating a reference turns it back into inline content."""
        source = make_block(text="", ref=HASH_A, kind="file", role=ROLES["reference"])
        restored = source.with_text("rehydrated body", 3)
        assert restored.text == "rehydrated body"
        assert restored.ref == ""
        assert restored.tokens == 3
        assert restored.is_reference is False
