"""Typed exception hierarchy for CER.

Every error raised by the runtime derives from CERError and carries an actionable
message plus a remedy. The core contains no bare except handlers.
"""

from __future__ import annotations


class CERError(Exception):
    """Base class for every error raised by CER.

    Attributes:
        message: Human-readable description of what went wrong.
        remedy: Concrete next step the caller can take.
    """

    def __init__(self, message: str, *, remedy: str = "") -> None:
        """Initialize the error.

        Args:
            message: What went wrong.
            remedy: What the caller should do about it.
        """
        self.message = message
        self.remedy = remedy
        super().__init__(self._render())

    def _render(self) -> str:
        """Render the error as one line, including the remedy when present.

        Returns:
            The formatted error text.
        """
        if self.remedy:
            return f"{self.message} -> {self.remedy}"
        return self.message


class ConfigError(CERError):
    """Raised when a configuration object is internally inconsistent."""


class TokenizerError(CERError):
    """Raised when a token counter fails to encode or decode text."""


class StoreError(CERError):
    """Base class for context-store failures."""


class StoreNotFoundError(StoreError):
    """Raised when a content hash is absent from the store."""


class StoreIntegrityError(StoreError):
    """Raised when stored bytes do not match the expected content hash."""


class StoreBackendError(StoreError):
    """Raised when a backend fails for a reason other than a missing key."""


class BudgetExceededError(CERError):
    """Raised when an indivisible block cannot fit the remaining budget."""


class CompactionError(CERError):
    """Base class for compaction-strategy failures."""


class IdempotencyError(CompactionError):
    """Raised when a compaction strategy violates its idempotency contract."""


class SolverError(CERError):
    """Raised when the allocation solver cannot produce a valid allocation."""


class ProviderError(CERError):
    """Base class for model-provider failures."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a provider is used before it has an endpoint or credentials."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns a malformed or unsuccessful response."""


class LegibilityError(CERError):
    """Raised when a lossy operation cannot be made visible and reversible.

    This is the runtime core safety property. Compaction may only happen when the
    result stays legible: the agent must be able to see that something was
    summarized and must be able to retrieve the original through its reference.
    Violating it is a programming error, so it fails loudly rather than silently
    degrading the agent.
    """


__all__ = [
    "BudgetExceededError",
    "CERError",
    "CompactionError",
    "ConfigError",
    "IdempotencyError",
    "LegibilityError",
    "ProviderError",
    "ProviderNotConfiguredError",
    "ProviderResponseError",
    "SolverError",
    "StoreBackendError",
    "StoreError",
    "StoreIntegrityError",
    "StoreNotFoundError",
    "TokenizerError",
]
