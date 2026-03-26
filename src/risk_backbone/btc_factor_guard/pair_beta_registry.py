"""
Build-4 / btc_factor_guard / pair_beta_registry
Store and expose β_j for each pair.

β_j = Cov(r_j, r_BTC) / Var(r_BTC)
Invariant: every active pair must have a β_j or explicit policy.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PairBeta(BaseModel, frozen=True):
    """Beta of a pair to BTC factor."""

    pair: str
    beta: float  # β_j
    confidence: float = 1.0  # 0-1, how confident in this estimate
    source: str = "precalibrated"  # "precalibrated" | "estimated" | "default"


class PairBetaRegistry:
    """Registry of pair betas to BTC factor."""

    def __init__(self, default_beta: float = 0.8) -> None:
        self._betas: dict[str, PairBeta] = {}
        self._default_beta = default_beta

    def set_beta(self, pair: str, beta: float, confidence: float = 1.0, source: str = "precalibrated") -> None:
        self._betas[pair] = PairBeta(pair=pair, beta=beta, confidence=confidence, source=source)

    def get_beta(self, pair: str) -> PairBeta:
        """Get beta for a pair. Returns default if not explicitly set."""
        if pair in self._betas:
            return self._betas[pair]
        return PairBeta(pair=pair, beta=self._default_beta, confidence=0.5, source="default")

    def has_explicit_beta(self, pair: str) -> bool:
        return pair in self._betas

    def get_all(self) -> tuple[PairBeta, ...]:
        return tuple(self._betas.values())

    @property
    def count(self) -> int:
        return len(self._betas)
