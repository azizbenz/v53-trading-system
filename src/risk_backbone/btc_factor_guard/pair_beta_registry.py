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
    source: str = "precalibrated"  # "precalibrated" | "estimated" | "manual"
    as_of_ts: float | None = None
    regime_tag: str = ""


class PairBetaRegistry:
    """Registry of pair betas to BTC factor."""

    def __init__(self) -> None:
        self._betas: dict[str, PairBeta] = {}

    def set_beta(
        self,
        pair: str,
        beta: float,
        confidence: float = 1.0,
        source: str = "precalibrated",
        *,
        as_of_ts: float | None = None,
        regime_tag: str = "",
    ) -> None:
        self._betas[pair] = PairBeta(
            pair=pair,
            beta=beta,
            confidence=confidence,
            source=source,
            as_of_ts=as_of_ts,
            regime_tag=regime_tag,
        )

    def get_beta(self, pair: str) -> PairBeta:
        """Get beta for a pair. Raises if no explicit mapping exists."""
        if pair not in self._betas:
            raise KeyError(f"missing explicit beta mapping for pair {pair}")
        return self._betas[pair]

    def has_explicit_beta(self, pair: str) -> bool:
        return pair in self._betas

    def is_fresh(self, pair: str, *, now: float, max_age_s: float) -> bool:
        beta = self.get_beta(pair)
        if beta.as_of_ts is None:
            return False
        return (now - beta.as_of_ts) <= max_age_s

    def get_all(self) -> tuple[PairBeta, ...]:
        return tuple(self._betas.values())

    @property
    def count(self) -> int:
        return len(self._betas)
