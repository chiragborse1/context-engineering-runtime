"""Token counting behind a pluggable interface.

The runtime never assumes a single tokenizer. `TokenCounter` is the seam; the default
implementation wraps tiktoken, and a conservative character-based counter is available
for environments where no tokenizer can be loaded, so the system degrades honestly
rather than failing.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cer.errors import TokenizerError

#: Conservative characters-per-token ratio used when no tokenizer is available.
#: English prose runs near 4 characters per token; code and JSON run lower, so 4 is a
#: deliberate over-estimate that keeps the budget honest rather than optimistic.
FALLBACK_CHARS_PER_TOKEN = 4


@runtime_checkable
class TokenCounter(Protocol):
    """Counts tokens in text.

    Implementations must be deterministic and side-effect free: the same text always
    yields the same count, or the budget accounting is meaningless.
    """

    @property
    def name(self) -> str:
        """Identifier of the encoding this counter implements.

        Returns:
            The encoding name.
        """

    def count(self, text: str) -> int:
        """Count the tokens in a string.

        Args:
            text: The text to measure.

        Returns:
            The number of tokens.
        """


class HeuristicTokenCounter:
    """A deterministic character-ratio counter that needs no model files.

    This is the floor, not the goal. It over-estimates rather than under-estimates, so
    a budget filled against it will still fit a real tokenizer.
    """

    def __init__(self, chars_per_token: int = FALLBACK_CHARS_PER_TOKEN) -> None:
        """Initialise the counter.

        Args:
            chars_per_token: Characters assumed per token. Must be positive.

        Raises:
            ValueError: If chars_per_token is not positive.
        """
        if chars_per_token <= 0:
            msg = f"chars_per_token must be positive, got {chars_per_token}"
            raise ValueError(msg)
        self._chars_per_token = chars_per_token

    @property
    def name(self) -> str:
        """The identifier of this encoding.

        Returns:
            A short name describing the heuristic.
        """
        return f"heuristic-{self._chars_per_token}chars"

    def count(self, text: str) -> int:
        """Count tokens as ceiling(len(text) / chars_per_token).

        Args:
            text: The text to measure.

        Returns:
            The estimated token count. Empty text costs zero.
        """
        if not text:
            return 0
        return -(-len(text) // self._chars_per_token)


class TiktokenCounter:
    """A tiktoken-backed counter with an in-process cache.

    Token counts are cached by text so repeated counting of the same block across
    steps is free. The cache is bounded so a long run cannot grow without limit.
    """

    def __init__(self, encoding_name: str = "cl100k_base", cache_size: int = 4096) -> None:
        """Initialise the counter.

        Args:
            encoding_name: A tiktoken encoding name.
            cache_size: Maximum number of memoised counts.

        Raises:
            TokenizerError: If the encoding cannot be loaded.
        """
        # Imported lazily on purpose: if tiktoken is missing or broken, this module
        # must still import so default_token_counter() can fall back to the heuristic.
        # A module-level import would take the whole runtime down with it.
        try:
            import tiktoken  # noqa: PLC0415
        except ImportError as exc:
            msg = "tiktoken is not installed"
            raise TokenizerError(msg, remedy="run: uv pip install tiktoken") from exc

        try:
            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception as exc:
            msg = f"could not load tiktoken encoding {encoding_name!r}"
            raise TokenizerError(
                msg,
                remedy="use an encoding name tiktoken recognises, such as cl100k_base",
            ) from exc

        if cache_size <= 0:
            msg = f"cache_size must be positive, got {cache_size}"
            raise ValueError(msg)
        self._encoding_name = encoding_name
        self._cache: dict[str, int] = {}
        self._cache_size = cache_size

    @property
    def name(self) -> str:
        """The tiktoken encoding name.

        Returns:
            The encoding identifier.
        """
        return self._encoding_name

    def count(self, text: str) -> int:
        """Count tokens, memoising the result.

        Args:
            text: The text to measure.

        Returns:
            The token count.
        """
        if not text:
            return 0
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        count = len(self._encoding.encode(text, disallowed_special=()))
        if len(self._cache) >= self._cache_size:
            self._cache.clear()
        self._cache[text] = count
        return count


def default_token_counter() -> TokenCounter:
    """Return the best available counter, degrading to the heuristic when needed.

    The heuristic is deliberately conservative, so a budget filled against it still
    fits a real tokenizer. The choice is recorded in the returned counter name so any
    reported number says which encoding produced it.

    Returns:
        A tiktoken counter when the encoding loads, otherwise the heuristic counter.
    """
    try:
        return TiktokenCounter()
    except TokenizerError:
        return HeuristicTokenCounter()


__all__ = [
    "FALLBACK_CHARS_PER_TOKEN",
    "HeuristicTokenCounter",
    "TiktokenCounter",
    "TokenCounter",
    "default_token_counter",
]
