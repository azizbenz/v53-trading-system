"""
Build-7 / engine_b / excess_detector_B
Detect exploitable local excess for mean-reversion.

Entry condition: |z_t| > z*
Quality depends on z-score magnitude, structure (range vs breakout),
and recent compression/expansion context.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ExcessVerdict(StrEnum):
    EXPLOITABLE = "exploitable"
    MARGINAL = "marginal"
    NO_EXCESS = "no_excess"
    INVALID = "invalid"


class ExcessInput(BaseModel, frozen=True):
    """Inputs for excess detection."""

    pair: str
    z_score: float
    z_score_valid: bool = True
    structure_is_range: float = 0.5  # [0,1] — 1=pure range, 0=trending
    recent_expansion: float = 0.0  # [0,1] — recent volatility expansion


class ExcessResult(BaseModel, frozen=True):
    """Result of excess detection."""

    pair: str
    verdict: ExcessVerdict
    z_score: float
    abs_z: float
    excess_score: float  # [0, 1] — quality of the excess
    reason: str = ""


# Thresholds
_Z_STAR = 1.5  # minimum |z| for exploitable excess
_Z_MARGINAL = 1.0  # minimum |z| for marginal
_Z_MAX = 4.0  # beyond this, likely breakout not reversion


def detect_excess(inputs: ExcessInput) -> ExcessResult:
    """Detect whether a local excess is exploitable for mean reversion.

    Excess score components:
    - z_quality: how far beyond z* the deviation is (capped)
    - range_bonus: extra quality if market is in range
    - expansion_penalty: reduce quality if recent expansion suggests breakout
    """
    abs_z = abs(inputs.z_score)

    if not inputs.z_score_valid:
        return ExcessResult(
            pair=inputs.pair,
            verdict=ExcessVerdict.INVALID,
            z_score=inputs.z_score,
            abs_z=abs_z,
            excess_score=0.0,
            reason="z-score invalid (zero dispersion)",
        )

    if abs_z > _Z_MAX:
        return ExcessResult(
            pair=inputs.pair,
            verdict=ExcessVerdict.NO_EXCESS,
            z_score=inputs.z_score,
            abs_z=abs_z,
            excess_score=0.0,
            reason=f"|z|={abs_z:.2f} > {_Z_MAX} — likely breakout, not reversion",
        )

    if abs_z < _Z_MARGINAL:
        return ExcessResult(
            pair=inputs.pair,
            verdict=ExcessVerdict.NO_EXCESS,
            z_score=inputs.z_score,
            abs_z=abs_z,
            excess_score=0.0,
            reason=f"|z|={abs_z:.2f} < {_Z_MARGINAL} — insufficient deviation",
        )

    # z_quality: normalized quality in [0, 1]
    z_quality = min((abs_z - _Z_MARGINAL) / (_Z_MAX - _Z_MARGINAL), 1.0)

    # range_bonus: mean reversion works better in range
    range_bonus = 0.15 * inputs.structure_is_range

    # expansion_penalty: recent expansion suggests breakout risk
    expansion_penalty = 0.20 * inputs.recent_expansion

    excess_score = max(0.0, min(1.0, z_quality + range_bonus - expansion_penalty))

    if abs_z >= _Z_STAR:
        verdict = ExcessVerdict.EXPLOITABLE
        reason = ""
    else:
        verdict = ExcessVerdict.MARGINAL
        reason = f"|z|={abs_z:.2f} marginal ({_Z_MARGINAL}-{_Z_STAR})"

    return ExcessResult(
        pair=inputs.pair,
        verdict=verdict,
        z_score=inputs.z_score,
        abs_z=abs_z,
        excess_score=excess_score,
        reason=reason,
    )
