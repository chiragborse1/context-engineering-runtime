"""Tests for the runtime configuration object."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cer.config import CacheConfig, ContextConfig, StoreConfig
from cer.types import TokenBudget


class TestTokenBudgetDefaults:
    """The default budget is sane."""

    def test_default_budget(self) -> None:
        """A default config ships with a usable budget."""
        config = ContextConfig()
        assert config.budget.total == 8000
        assert config.budget.available == 7000


class TestStoreConfig:
    """Behaviour of the store configuration."""

    def test_defaults(self) -> None:
        """The in-memory backend is the default so nothing touches disk by default."""
        assert StoreConfig().backend == "memory"

    @pytest.mark.parametrize("backend", ["memory", "filesystem", "s3"])
    def test_known_backends(self, backend: str) -> None:
        """All three known backends are accepted."""
        assert StoreConfig(backend=backend).backend == backend

    def test_unknown_backend_rejected(self) -> None:
        """An unrecognised backend is rejected with a helpful message."""
        with pytest.raises(ValidationError, match="unknown store backend"):
            StoreConfig(backend="nope")

    def test_negative_threshold_rejected(self) -> None:
        """A negative spill threshold is rejected."""
        with pytest.raises(ValidationError):
            StoreConfig(spill_threshold_tokens=-1)


class TestCacheConfig:
    """Behaviour of the cache pricing configuration."""

    def test_cache_read_is_cheaper_than_write(self) -> None:
        """Reading the cache should never cost more than writing it."""
        cache = CacheConfig()
        assert cache.cache_read_multiplier < cache.cache_write_multiplier

    def test_zero_write_multiplier_rejected(self) -> None:
        """A zero write multiplier is rejected as nonsensical."""
        with pytest.raises(ValidationError):
            CacheConfig(cache_write_multiplier=0)


class TestContextConfig:
    """Behaviour of the top-level configuration."""

    def test_unknown_solver_rejected(self) -> None:
        """An unrecognised solver is rejected."""
        with pytest.raises(ValidationError, match="unknown solver"):
            ContextConfig(solver="magic")

    def test_unknown_layout_rejected(self) -> None:
        """An unrecognised layout is rejected."""
        with pytest.raises(ValidationError, match="unknown layout"):
            ContextConfig(layout="random")

    def test_extra_fields_rejected(self) -> None:
        """Unknown configuration keys are rejected so typos surface loudly."""
        with pytest.raises(ValidationError):
            ContextConfig(nonsense=1)  # type: ignore[call-arg]

    def test_explicit_budget(self) -> None:
        """A caller can supply their own budget."""
        config = ContextConfig(budget=TokenBudget(total=100, reserve=10))
        assert config.budget.available == 90
