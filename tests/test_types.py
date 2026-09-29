"""Tests for the core value types."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from cer.types import (
    AllocationPolicy,
    BlockRole,
    Provenance,
    TokenBudget,
    Utility,
)


class TestTokenBudget:
    """Behaviour of the token budget type."""

    def test_available_excludes_reserve(self) -> None:
        """Available tokens are the total minus the reserve."""
        budget = TokenBudget(total=1000, reserve=200)
        assert budget.available == 800

    def test_no_reserve_means_all_available(self) -> None:
        """A zero reserve leaves the full total allocatable."""
        assert TokenBudget(total=500).available == 500

    def test_reserve_must_be_smaller_than_total(self) -> None:
        """A reserve that consumes the whole budget is rejected."""
        with pytest.raises(ValidationError, match="must be smaller"):
            TokenBudget(total=100, reserve=100)

    def test_reserve_larger_than_total_is_rejected(self) -> None:
        """An over-large reserve is rejected."""
        with pytest.raises(ValidationError):
            TokenBudget(total=100, reserve=200)

    def test_total_must_be_positive(self) -> None:
        """A zero total is rejected."""
        with pytest.raises(ValidationError):
            TokenBudget(total=0)

    def test_is_frozen(self) -> None:
        """Budgets are immutable."""
        budget = TokenBudget(total=10)
        with pytest.raises(ValidationError):
            budget.total = 20  # type: ignore[misc]


class TestUtility:
    """Behaviour of the decaying utility type."""

    def test_zero_decay_keeps_value(self) -> None:
        """With no decay rate, utility never falls."""
        util = Utility(value=1.0, created_step=0, lam=0.0)
        assert util.at(0) == pytest.approx(1.0)
        assert util.at(100) == pytest.approx(1.0)

    def test_exponential_decay(self) -> None:
        """Utility decays as exp(-lambda * staleness)."""
        util = Utility(value=2.0, created_step=0, lam=0.5)
        assert util.at(2) == pytest.approx(2.0 * math.exp(-1.0))

    def test_future_step_does_not_inflate_utility(self) -> None:
        """A step before creation is clamped, so utility never exceeds value."""
        util = Utility(value=1.0, created_step=10, lam=1.0)
        assert util.at(0) == pytest.approx(1.0)

    def test_decay_is_monotonic(self) -> None:
        """Utility never increases as the agent advances."""
        util = Utility(value=1.0, created_step=0, lam=0.2)
        values = [util.at(step) for step in range(10)]
        assert values == sorted(values, reverse=True)

    def test_negative_lambda_is_rejected(self) -> None:
        """A negative decay rate is rejected."""
        with pytest.raises(ValidationError):
            Utility(value=1.0, lam=-1.0)


class TestProvenance:
    """Behaviour of the provenance record."""

    def test_merge_unions_source_hashes(self) -> None:
        """Merging preserves both source chains in order."""
        a = Provenance(op="ingest", source_hashes=("aaa", "bbb"))
        b = Provenance(op="summarize", source_hashes=("ccc",))
        merged = a.merge(b)
        assert merged.source_hashes == ("ccc", "aaa", "bbb")
        assert merged.op == "ingest"

    def test_merge_deduplicates(self) -> None:
        """Duplicate hashes collapse."""
        a = Provenance(op="ingest", source_hashes=("aaa",))
        b = Provenance(op="summarize", source_hashes=("aaa", "bbb"))
        assert a.merge(b).source_hashes == ("aaa", "bbb")

    def test_merge_ors_lossiness(self) -> None:
        """If either side is lossy, the merge is lossy."""
        a = Provenance(op="ingest", lossy=False)
        b = Provenance(op="summarize", lossy=True)
        assert a.merge(b).lossy is True
        assert b.merge(a).lossy is True

    def test_merge_concatenates_detail(self) -> None:
        """Detail from both sides survives the merge."""
        a = Provenance(op="ingest", detail="read 3 files")
        b = Provenance(op="summarize", detail="summarized 18 turns")
        assert a.merge(b).detail == "summarized 18 turns; read 3 files"

    def test_with_detail_appends(self) -> None:
        """with_detail appends without losing the original."""
        prov = Provenance(op="ingest", detail="first")
        assert prov.with_detail("second").detail == "first; second"

    def test_with_detail_on_empty(self) -> None:
        """with_detail on an empty detail is a plain assignment."""
        assert Provenance(op="ingest").with_detail("only").detail == "only"

    def test_created_at_is_populated(self) -> None:
        """A timestamp is recorded by default."""
        assert Provenance(op="ingest").created_at > 0


class TestBlockRole:
    """Behaviour of the block role type."""

    def test_valid_segment(self) -> None:
        """A role carries its segment and priority."""
        role = BlockRole(name="pinned_fact", segment="stable", priority=10)
        assert role.segment == "stable"
        assert role.priority == 10

    def test_invalid_segment_is_rejected(self) -> None:
        """An unknown segment is rejected at validation time."""
        with pytest.raises(ValidationError):
            BlockRole(name="x", segment="nonsense", priority=0)

    def test_negative_priority_is_rejected(self) -> None:
        """Priority must be non-negative."""
        with pytest.raises(ValidationError):
            BlockRole(name="x", segment="volatile", priority=-1)


class TestAllocationPolicy:
    """Behaviour of the allocation policy type."""

    def test_defaults(self) -> None:
        """Priority is respected by default."""
        policy = AllocationPolicy(name="greedy")
        assert policy.respect_priority is True

    def test_priority_can_be_disabled(self) -> None:
        """Priority ordering can be turned off for pure utility allocation."""
        policy = AllocationPolicy(name="pure", respect_priority=False)
        assert policy.respect_priority is False
