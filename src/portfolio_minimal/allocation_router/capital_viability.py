"""Capital-bucket viability diagnostics for min-notional and fragmentation evidence."""

from __future__ import annotations

from statistics import median

from pydantic import BaseModel, Field


class PairMinNotionalAssessment(BaseModel, frozen=True):
    """Pair-level min-notional feasibility before execution normalization."""

    pair: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=1)
    planned_notional: float | None = Field(default=None, ge=0.0)
    min_notional: float | None = Field(default=None, ge=0.0)
    min_notional_viable: bool | None = None
    min_notional_block_count: int = Field(default=0, ge=0)
    min_notional_block_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    min_notional_status: str = "MIN_NOTIONAL_NOT_PROVEN"
    min_notional_reason_codes: tuple[str, ...] = ()


class CapitalFragmentationAssessment(BaseModel, frozen=True):
    """Bucket-level fragmentation evidence for small-capital readiness."""

    capital_bucket: int = Field(..., ge=1)
    candidate_pair_count: int = Field(default=0, ge=0)
    active_pair_count: int = Field(default=0, ge=0)
    max_active_pairs: int | None = Field(default=None, ge=0)
    mean_allocated_notional: float | None = Field(default=None, ge=0.0)
    median_allocated_notional: float | None = Field(default=None, ge=0.0)
    min_allocated_notional: float | None = Field(default=None, ge=0.0)
    fragmentation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    pair_universe_too_wide_status: str = "FRAGMENTATION_NOT_PROVEN"
    recommended_max_active_pairs: int | None = Field(default=None, ge=0)


def assess_pair_min_notional_viability(
    *,
    pair: str,
    capital_bucket: int,
    planned_notional: float | None,
    min_notional: float | None,
    size_reduced: bool = False,
    fragmented: bool = False,
) -> PairMinNotionalAssessment:
    """Classify pair-level min-notional feasibility without inventing venue evidence."""

    if planned_notional is None or min_notional is None:
        return PairMinNotionalAssessment(
            pair=pair,
            capital_bucket=capital_bucket,
            planned_notional=planned_notional,
            min_notional=min_notional,
            min_notional_status="MIN_NOTIONAL_NOT_PROVEN",
            min_notional_reason_codes=("MIN_NOTIONAL_NOT_PROVEN",),
        )
    if planned_notional >= min_notional:
        return PairMinNotionalAssessment(
            pair=pair,
            capital_bucket=capital_bucket,
            planned_notional=planned_notional,
            min_notional=min_notional,
            min_notional_viable=True,
            min_notional_block_rate=0.0,
            min_notional_status="MIN_NOTIONAL_PROVEN",
        )
    reason_codes = ["MIN_NOTIONAL_NOT_VIABLE_FOR_BUCKET", "PAIR_BLOCKED_BY_MIN_NOTIONAL"]
    if size_reduced:
        reason_codes.append("PAIR_BLOCKED_BY_SIZE_REDUCTION")
    if fragmented:
        reason_codes.append("PAIR_BLOCKED_BY_CAPITAL_FRAGMENTATION")
    return PairMinNotionalAssessment(
        pair=pair,
        capital_bucket=capital_bucket,
        planned_notional=planned_notional,
        min_notional=min_notional,
        min_notional_viable=False,
        min_notional_block_count=1,
        min_notional_block_rate=1.0,
        min_notional_status="MIN_NOTIONAL_NOT_VIABLE_FOR_BUCKET",
        min_notional_reason_codes=tuple(reason_codes),
    )


def analyze_capital_fragmentation(
    *,
    capital_bucket: int,
    candidate_pair_count: int,
    allocated_notionals: tuple[float, ...],
    max_active_pairs: int | None,
    high_fragmentation_threshold: float = 0.5,
) -> CapitalFragmentationAssessment:
    """Summarize whether a pair universe is too wide for a bucket."""

    if not allocated_notionals or max_active_pairs is None:
        return CapitalFragmentationAssessment(
            capital_bucket=capital_bucket,
            candidate_pair_count=candidate_pair_count,
            active_pair_count=len(allocated_notionals),
            max_active_pairs=max_active_pairs,
            pair_universe_too_wide_status="FRAGMENTATION_NOT_PROVEN",
        )
    active_pair_count = len(allocated_notionals)
    mean_allocated_notional = sum(allocated_notionals) / active_pair_count
    median_allocated_notional = float(median(allocated_notionals))
    min_allocated_notional = min(allocated_notionals)
    notional_fragmentation_rate = (
        0.0
        if mean_allocated_notional <= 0.0
        else max(0.0, min(1.0, 1.0 - (min_allocated_notional / mean_allocated_notional)))
    )
    universe_fragmentation_rate = (
        0.0
        if candidate_pair_count <= 0
        else max(
            0.0,
            min(
                1.0,
                (candidate_pair_count - min(candidate_pair_count, max_active_pairs))
                / candidate_pair_count,
            ),
        )
    )
    fragmentation_rate = max(notional_fragmentation_rate, universe_fragmentation_rate)
    if candidate_pair_count > max_active_pairs:
        status = "PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL"
    elif fragmentation_rate >= high_fragmentation_threshold:
        status = "FRAGMENTATION_HIGH"
    else:
        status = "FRAGMENTATION_ACCEPTABLE"
    recommended_max_active_pairs = min(candidate_pair_count, max_active_pairs)
    return CapitalFragmentationAssessment(
        capital_bucket=capital_bucket,
        candidate_pair_count=candidate_pair_count,
        active_pair_count=active_pair_count,
        max_active_pairs=max_active_pairs,
        mean_allocated_notional=mean_allocated_notional,
        median_allocated_notional=median_allocated_notional,
        min_allocated_notional=min_allocated_notional,
        fragmentation_rate=fragmentation_rate,
        pair_universe_too_wide_status=status,
        recommended_max_active_pairs=recommended_max_active_pairs,
    )


__all__ = [
    "CapitalFragmentationAssessment",
    "PairMinNotionalAssessment",
    "analyze_capital_fragmentation",
    "assess_pair_min_notional_viability",
]
