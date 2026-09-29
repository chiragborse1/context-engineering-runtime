"""Shared pytest fixtures.

The whole suite runs offline against the deterministic MockProvider. No test may
reach the network or require an API key.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee no test can accidentally pick up a real API key.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
    """
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "COHERE_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
