"""The single configuration object for the runtime.

There are no global mutable singletons. Every component receives the configuration it
needs explicitly, which is what makes the whole system testable and serializable.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cer.types import TokenBudget


class StoreConfig(BaseModel):
    """Settings for the content-addressed store.

    Attributes:
        backend: Which storage backend to use: memory, filesystem or s3.
        root: Directory used by the filesystem backend.
        spill_threshold_tokens: Artifacts at or above this many tokens are offloaded
            to the store and replaced by a lightweight reference.
    """

    model_config = ConfigDict(extra="forbid")

    backend: str = Field(default="memory")
    root: str = Field(default=".cer-work/store")
    spill_threshold_tokens: int = Field(default=200, ge=0)

    @model_validator(mode="after")
    def _check_backend(self) -> StoreConfig:
        """Reject an unknown backend name.

        Returns:
            The validated config.

        Raises:
            ValueError: If the backend is not recognised.
        """
        allowed = {"memory", "filesystem", "s3"}
        if self.backend not in allowed:
            msg = f"unknown store backend {self.backend!r}, expected one of {sorted(allowed)}"
            raise ValueError(msg)
        return self


class CacheConfig(BaseModel):
    """Pricing and policy for the modelled provider prefix cache.

    The runtime models cache behaviour rather than querying a provider, so the same
    numbers reproduce offline. The assumptions are explicit so the result is auditable.

    Attributes:
        cache_write_multiplier: Cost of writing the cacheable prefix, as a multiple
            of the base input token price.
        cache_read_multiplier: Cost of reading the cacheable prefix, as a multiple of
            the base input token price.
        min_cacheable_prefix_tokens: Providers ignore cacheable prefixes below this
            many tokens.
    """

    model_config = ConfigDict(extra="forbid")

    cache_write_multiplier: float = Field(default=1.25, gt=0)
    cache_read_multiplier: float = Field(default=0.1, ge=0)
    min_cacheable_prefix_tokens: int = Field(default=1024, ge=0)


class ContextConfig(BaseModel):
    """The one configuration object the runtime is built from.

    Every component takes the slice of configuration it needs, so nothing is global
    and nothing is hidden.

    Attributes:
        budget: The token budget applied to each assembled request.
        store: Content-store settings.
        cache: Prefix-cache pricing model.
        solver: Which allocation solver to use, greedy or exact_dp.
        layout: Which layout to use, currently cache_aware.
    """

    model_config = ConfigDict(extra="forbid")

    budget: TokenBudget = Field(default_factory=lambda: TokenBudget(total=8000, reserve=1000))
    store: StoreConfig = Field(default_factory=StoreConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    solver: str = Field(default="greedy")
    layout: str = Field(default="cache_aware")

    @model_validator(mode="after")
    def _check_solver(self) -> ContextConfig:
        """Reject an unknown solver or layout name.

        Returns:
            The validated config.

        Raises:
            ValueError: If the solver or layout is not recognised.
        """
        allowed_solvers = {"greedy", "exact_dp"}
        if self.solver not in allowed_solvers:
            msg = f"unknown solver {self.solver!r}, expected one of {sorted(allowed_solvers)}"
            raise ValueError(msg)
        allowed_layouts = {"cache_aware", "append_only"}
        if self.layout not in allowed_layouts:
            msg = f"unknown layout {self.layout!r}, expected one of {sorted(allowed_layouts)}"
            raise ValueError(msg)
        return self


__all__ = ["CacheConfig", "ContextConfig", "StoreConfig"]
