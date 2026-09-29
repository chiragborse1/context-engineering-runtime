"""Tests for token counting."""

from __future__ import annotations

import builtins

import pytest

from cer.errors import TokenizerError
from cer.tokens import (
    FALLBACK_CHARS_PER_TOKEN,
    HeuristicTokenCounter,
    TiktokenCounter,
    TokenCounter,
    default_token_counter,
)

TEXT = "the quick brown fox jumps over the lazy dog"


class TestHeuristicTokenCounter:
    """The offline fallback counter."""

    def test_empty_text_is_free(self) -> None:
        """Empty text costs zero tokens."""
        assert HeuristicTokenCounter().count("") == 0

    def test_rounds_up(self) -> None:
        """A partial token still costs a whole token."""
        counter = HeuristicTokenCounter(chars_per_token=4)
        assert counter.count("a") == 1
        assert counter.count("abcd") == 1
        assert counter.count("abcde") == 2

    def test_is_deterministic(self) -> None:
        """The same text always counts the same."""
        counter = HeuristicTokenCounter()
        assert counter.count(TEXT) == counter.count(TEXT)

    def test_monotonic_in_length(self) -> None:
        """Longer text never counts fewer tokens."""
        counter = HeuristicTokenCounter()
        counts = [counter.count("a" * n) for n in range(0, 40, 4)]
        assert counts == sorted(counts)

    def test_name_reports_the_ratio(self) -> None:
        """The name says which assumption produced the number."""
        assert "4" in HeuristicTokenCounter().name

    def test_rejects_non_positive_ratio(self) -> None:
        """A nonsensical ratio is rejected at construction."""
        with pytest.raises(ValueError, match="must be positive"):
            HeuristicTokenCounter(chars_per_token=0)

    def test_default_ratio_is_four(self) -> None:
        """The default assumption is the documented one."""
        assert FALLBACK_CHARS_PER_TOKEN == 4


class TestTiktokenCounter:
    """The tiktoken-backed counter."""

    def test_counts_real_text(self) -> None:
        """A real encoding produces a real, non-zero count."""
        counter = TiktokenCounter()
        assert counter.name == "cl100k_base"
        assert counter.count(TEXT) > 0

    def test_empty_text_is_free(self) -> None:
        """Empty text costs zero tokens."""
        assert TiktokenCounter().count("") == 0

    def test_is_deterministic(self) -> None:
        """Repeated counting yields the same answer."""
        counter = TiktokenCounter()
        assert counter.count(TEXT) == counter.count(TEXT)

    def test_cache_does_not_change_results(self) -> None:
        """Memoisation is transparent to callers."""
        counter = TiktokenCounter()
        first = counter.count(TEXT)
        second = counter.count(TEXT)
        assert first == second

    def test_unknown_encoding_is_actionable(self) -> None:
        """An unknown encoding raises a typed error with a remedy."""
        with pytest.raises(TokenizerError) as exc:
            TiktokenCounter(encoding_name="not-a-real-encoding")
        assert exc.value.remedy

    def test_rejects_non_positive_cache(self) -> None:
        """A zero-sized cache is rejected."""
        with pytest.raises(ValueError, match="cache_size must be positive"):
            TiktokenCounter(cache_size=0)

    def test_cache_is_bounded(self) -> None:
        """The memo cache cannot grow without limit."""
        counter = TiktokenCounter(cache_size=4)
        for i in range(50):
            counter.count(f"text number {i}")
        assert len(counter._cache) <= 4


class TestDefaultCounter:
    """The factory that picks a counter."""

    def test_returns_a_working_counter(self) -> None:
        """The default counter satisfies the protocol and measures text."""
        counter = default_token_counter()
        assert isinstance(counter, TokenCounter)
        assert counter.count(TEXT) > 0

    def test_name_is_reported(self) -> None:
        """Whatever counter is chosen, its name is discoverable."""
        assert isinstance(default_token_counter().name, str)

    def test_falls_back_when_encoding_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A broken tokenizer degrades to the heuristic rather than crashing.

        The runtime must stay usable with no tokenizer at all, so this path is the
        difference between a degraded system and a dead one.
        """

        def boom(*_args: object, **_kwargs: object) -> None:
            msg = "no tokenizer here"
            raise TokenizerError(msg)

        monkeypatch.setattr("cer.tokens.TiktokenCounter", boom)
        counter = default_token_counter()
        assert isinstance(counter, HeuristicTokenCounter)
        assert counter.count(TEXT) > 0

    def test_missing_tiktoken_is_actionable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A missing tokenizer raises a typed error, not an ImportError.

        The runtime must survive a machine with no tokenizer at all, so this path
        has to produce an actionable typed error that default_token_counter can catch.
        """
        real_import = builtins.__import__

        def blocked(name: str, *args: object, **kwargs: object) -> object:
            if name == "tiktoken":
                msg = "no tiktoken"
                raise ImportError(msg)
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(builtins, "__import__", blocked)
        with pytest.raises(TokenizerError) as exc:
            TiktokenCounter()
        assert "tiktoken" in str(exc.value)
        assert exc.value.remedy
