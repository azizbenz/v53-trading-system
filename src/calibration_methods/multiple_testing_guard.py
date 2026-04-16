"""Harvey-Liu-Zhu multiple-testing guard helpers for V5.3 promotion gates."""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts.domain_types import ALL_PAIRS

V53_CANONICAL_SHADOW_PAIR_FLOOR = 20
CURRENT_REPO_PAIR_UNIVERSE_COUNT = len(ALL_PAIRS)
_PAIR_COUNT_RULE = (
    "k_hlz = pairs_tested when pair_count_mode=observed_shadow; "
    "k_hlz = max(pairs_tested, promotion_pair_floor) when "
    "pair_count_mode=promotion_floor"
)


class MultipleTestingGuardError(ValueError):
    """Raised when HLZ multiple-testing guard inputs are invalid."""


class HarveyLiuZhuPairCountMode(StrEnum):
    """How the V5.3 pair-count seam resolves the effective HLZ test count."""

    OBSERVED_SHADOW = "observed_shadow"
    PROMOTION_FLOOR = "promotion_floor"


class HarveyLiuZhuTestCount(BaseModel, frozen=True):
    """Audit-ready V5.3 composition of the effective HLZ test count."""

    method_version: str = "harvey_liu_zhu_test_count_v1"
    pair_count_mode: HarveyLiuZhuPairCountMode
    observed_pair_count: int = Field(..., ge=1)
    promotion_pair_floor: int = Field(..., ge=1)
    repo_pair_universe_count: int = Field(..., ge=1)
    effective_test_count: int = Field(..., ge=1)
    floor_applied: bool = False
    composition_rule: str = _PAIR_COUNT_RULE


class HarveyLiuZhuDeflatedSharpeResult(BaseModel, frozen=True):
    """Audit-ready HLZ deflated Sharpe computation for V5.3 promotion gates."""

    method_version: str = "harvey_liu_zhu_deflated_sharpe_v1"
    raw_sharpe: float
    observation_count: int = Field(..., ge=2)
    pair_count_mode: HarveyLiuZhuPairCountMode
    observed_pair_count: int = Field(..., ge=1)
    promotion_pair_floor: int = Field(..., ge=1)
    repo_pair_universe_count: int = Field(..., ge=1)
    effective_test_count: int = Field(..., ge=1)
    floor_applied: bool = False
    scale_factor: float = Field(..., ge=0.0)
    deflated_sharpe: float
    composition_rule: str = _PAIR_COUNT_RULE


def compose_hlz_test_count(
    *,
    observed_pair_count: int,
    pair_count_mode: HarveyLiuZhuPairCountMode = HarveyLiuZhuPairCountMode.OBSERVED_SHADOW,
    promotion_pair_floor: int = V53_CANONICAL_SHADOW_PAIR_FLOOR,
    repo_pair_universe_count: int = CURRENT_REPO_PAIR_UNIVERSE_COUNT,
) -> HarveyLiuZhuTestCount:
    """Resolve the effective HLZ test count for a V5.3 pair universe."""

    if observed_pair_count < 1:
        raise MultipleTestingGuardError("observed_pair_count must be >= 1")
    if promotion_pair_floor < 1:
        raise MultipleTestingGuardError("promotion_pair_floor must be >= 1")
    if repo_pair_universe_count < 1:
        raise MultipleTestingGuardError("repo_pair_universe_count must be >= 1")

    floor_applied = (
        pair_count_mode == HarveyLiuZhuPairCountMode.PROMOTION_FLOOR
        and observed_pair_count < promotion_pair_floor
    )
    effective_test_count = (
        max(observed_pair_count, promotion_pair_floor)
        if pair_count_mode == HarveyLiuZhuPairCountMode.PROMOTION_FLOOR
        else observed_pair_count
    )
    return HarveyLiuZhuTestCount(
        pair_count_mode=pair_count_mode,
        observed_pair_count=observed_pair_count,
        promotion_pair_floor=promotion_pair_floor,
        repo_pair_universe_count=repo_pair_universe_count,
        effective_test_count=effective_test_count,
        floor_applied=floor_applied,
    )


def compute_harvey_liu_zhu_deflated_sharpe(
    raw_sharpe: float,
    *,
    observation_count: int,
    observed_pair_count: int,
    pair_count_mode: HarveyLiuZhuPairCountMode = HarveyLiuZhuPairCountMode.OBSERVED_SHADOW,
    promotion_pair_floor: int = V53_CANONICAL_SHADOW_PAIR_FLOOR,
    repo_pair_universe_count: int = CURRENT_REPO_PAIR_UNIVERSE_COUNT,
) -> HarveyLiuZhuDeflatedSharpeResult:
    """Apply the HLZ eq.(8) haircut using the V5.3 pair-count seam."""

    if not math.isfinite(raw_sharpe):
        raise MultipleTestingGuardError("raw_sharpe must be finite")
    if observation_count < 2:
        raise MultipleTestingGuardError("observation_count must be >= 2")

    test_count = compose_hlz_test_count(
        observed_pair_count=observed_pair_count,
        pair_count_mode=pair_count_mode,
        promotion_pair_floor=promotion_pair_floor,
        repo_pair_universe_count=repo_pair_universe_count,
    )
    if observation_count <= test_count.effective_test_count:
        raise MultipleTestingGuardError(
            "HLZ requires observation_count > effective_test_count for a positive radicand"
        )

    scale_factor = math.sqrt(
        (observation_count - test_count.effective_test_count) / float(observation_count - 1)
    )
    return HarveyLiuZhuDeflatedSharpeResult(
        raw_sharpe=float(raw_sharpe),
        observation_count=observation_count,
        pair_count_mode=test_count.pair_count_mode,
        observed_pair_count=test_count.observed_pair_count,
        promotion_pair_floor=test_count.promotion_pair_floor,
        repo_pair_universe_count=test_count.repo_pair_universe_count,
        effective_test_count=test_count.effective_test_count,
        floor_applied=test_count.floor_applied,
        scale_factor=scale_factor,
        deflated_sharpe=float(raw_sharpe) * scale_factor,
    )


__all__ = [
    "CURRENT_REPO_PAIR_UNIVERSE_COUNT",
    "V53_CANONICAL_SHADOW_PAIR_FLOOR",
    "HarveyLiuZhuDeflatedSharpeResult",
    "HarveyLiuZhuPairCountMode",
    "HarveyLiuZhuTestCount",
    "MultipleTestingGuardError",
    "compose_hlz_test_count",
    "compute_harvey_liu_zhu_deflated_sharpe",
]
