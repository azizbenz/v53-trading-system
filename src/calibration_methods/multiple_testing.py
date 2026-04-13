"""Bounded Local IA Lab multiple-testing helpers."""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field


class MultipleTestingError(ValueError):
    """Raised when bounded multiple-testing helpers receive invalid inputs."""


class HolmBonferroniAdjustedHypothesis(BaseModel, frozen=True):
    """One Holm-Bonferroni step-down decision."""

    hypothesis_id: str = Field(..., min_length=1)
    raw_p_value: float = Field(..., ge=0.0, le=1.0)
    adjusted_alpha: float = Field(..., gt=0.0, le=1.0)
    rejected: bool


class HolmBonferroniResult(BaseModel, frozen=True):
    """Audit-ready Holm-Bonferroni correction result."""

    method_version: str = "holm_bonferroni_v1"
    family_alpha: float = Field(..., gt=0.0, le=1.0)
    hypothesis_count: int = Field(..., ge=1)
    any_rejected: bool = False
    all_rejected: bool = False
    adjusted_hypotheses: tuple[HolmBonferroniAdjustedHypothesis, ...]


def apply_holm_bonferroni(
    hypotheses: Iterable[tuple[str, float]],
    *,
    family_alpha: float = 0.05,
) -> HolmBonferroniResult:
    """Apply a bounded Holm-Bonferroni step-down correction."""

    if family_alpha <= 0.0 or family_alpha > 1.0:
        raise MultipleTestingError("family_alpha must be in (0, 1]")

    normalized = []
    for hypothesis_id, raw_p_value in hypotheses:
        if not hypothesis_id:
            raise MultipleTestingError("hypothesis_id must be non-empty")
        if raw_p_value < 0.0 or raw_p_value > 1.0:
            raise MultipleTestingError("raw_p_value must be in [0, 1]")
        normalized.append((hypothesis_id, float(raw_p_value)))

    if not normalized:
        raise MultipleTestingError("Holm-Bonferroni requires at least one hypothesis")
    hypothesis_ids = tuple(hypothesis_id for hypothesis_id, _ in normalized)
    if len(set(hypothesis_ids)) != len(hypothesis_ids):
        raise MultipleTestingError("hypothesis_id values must be unique")

    ordered = sorted(normalized, key=lambda item: (item[1], item[0]))
    total = len(ordered)
    decisions: dict[str, HolmBonferroniAdjustedHypothesis] = {}
    keep_rejecting = True
    for index, (hypothesis_id, raw_p_value) in enumerate(ordered):
        adjusted_alpha = family_alpha / (total - index)
        rejected = keep_rejecting and raw_p_value <= adjusted_alpha
        if not rejected:
            keep_rejecting = False
        decisions[hypothesis_id] = HolmBonferroniAdjustedHypothesis(
            hypothesis_id=hypothesis_id,
            raw_p_value=raw_p_value,
            adjusted_alpha=adjusted_alpha,
            rejected=rejected,
        )

    adjusted_hypotheses = tuple(decisions[hypothesis_id] for hypothesis_id in hypothesis_ids)
    rejected_count = sum(1 for item in adjusted_hypotheses if item.rejected)
    return HolmBonferroniResult(
        family_alpha=family_alpha,
        hypothesis_count=total,
        any_rejected=rejected_count > 0,
        all_rejected=rejected_count == total,
        adjusted_hypotheses=adjusted_hypotheses,
    )


__all__ = [
    "HolmBonferroniAdjustedHypothesis",
    "HolmBonferroniResult",
    "MultipleTestingError",
    "apply_holm_bonferroni",
]
