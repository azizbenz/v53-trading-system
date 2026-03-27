"""
Build-9 / edge_tracker_prudent_minimal / sample_size_tracker
Track the number of useful observations.

An edge estimate from N=5 is not the same as N=50.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SampleAdequacy(StrEnum):
    INSUFFICIENT = "insufficient"  # N < min_required
    MARGINAL = "marginal"  # min_required <= N < comfortable
    ADEQUATE = "adequate"  # N >= comfortable


class SampleSizeResult(BaseModel, frozen=True):
    """Sample size assessment."""

    scope: str
    sample_size: int
    adequacy: SampleAdequacy
    min_required: int
    comfortable_size: int


# Thresholds
_MIN_REQUIRED = 10
_COMFORTABLE = 30


def assess_sample_size(
    scope: str,
    sample_size: int,
    min_required: int = _MIN_REQUIRED,
    comfortable: int = _COMFORTABLE,
) -> SampleSizeResult:
    """Assess whether sample size is sufficient for edge estimation."""
    if sample_size < min_required:
        adequacy = SampleAdequacy.INSUFFICIENT
    elif sample_size < comfortable:
        adequacy = SampleAdequacy.MARGINAL
    else:
        adequacy = SampleAdequacy.ADEQUATE

    return SampleSizeResult(
        scope=scope,
        sample_size=sample_size,
        adequacy=adequacy,
        min_required=min_required,
        comfortable_size=comfortable,
    )
