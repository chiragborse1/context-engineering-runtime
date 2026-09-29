"""Tests for the typed exception hierarchy."""

from __future__ import annotations

import pytest

from cer.errors import (
    BudgetExceededError,
    CERError,
    CompactionError,
    ConfigError,
    IdempotencyError,
    LegibilityError,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    SolverError,
    StoreBackendError,
    StoreError,
    StoreIntegrityError,
    StoreNotFoundError,
    TokenizerError,
)

ALL_ERRORS = [
    BudgetExceededError,
    CERError,
    CompactionError,
    ConfigError,
    IdempotencyError,
    LegibilityError,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    SolverError,
    StoreBackendError,
    StoreError,
    StoreIntegrityError,
    StoreNotFoundError,
    TokenizerError,
]


@pytest.mark.parametrize("cls", ALL_ERRORS)
def test_every_error_derives_from_base(cls: type[CERError]) -> None:
    """Every error in the hierarchy is catchable as CERError."""
    assert issubclass(cls, CERError)


def test_message_only() -> None:
    """With no remedy, the rendered error is just the message."""
    err = ConfigError("bad config")
    assert str(err) == "bad config"
    assert err.message == "bad config"
    assert err.remedy == ""


def test_message_with_remedy() -> None:
    """With a remedy, the rendered error appends it."""
    err = ConfigError("bad config", remedy="set total")
    assert str(err) == "bad config -> set total"
    assert err.remedy == "set total"


@pytest.mark.parametrize(
    ("child", "parent"),
    [
        (StoreNotFoundError, StoreError),
        (StoreIntegrityError, StoreError),
        (StoreBackendError, StoreError),
        (IdempotencyError, CompactionError),
        (ProviderNotConfiguredError, ProviderError),
        (ProviderResponseError, ProviderError),
    ],
)
def test_hierarchy(child: type[CERError], parent: type[CERError]) -> None:
    """Specialised errors are catchable through their parent class."""
    assert issubclass(child, parent)
    assert issubclass(parent, CERError)


def test_remedy_is_optional() -> None:
    """The remedy keyword defaults to empty."""
    err = CERError("boom")
    assert err.remedy == ""
