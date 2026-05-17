"""Governed validation for transported supplementary refs."""

from __future__ import annotations

from pathlib import Path
import re

from pydantic import BaseModel, Field

FORBIDDEN_DIRECTIONAL_SUPPLEMENTARY_REF_KEYS: tuple[str, ...] = (
    "direction_up_300s_fee_safe",
    "buy_probability",
    "sell_probability",
    "market_will_go_up",
    "side",
    "long",
    "short",
    "label",
    "direct_trade_decision",
)

_FORBIDDEN_KEY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        key,
        re.compile(rf'"{re.escape(key)}"\s*:'),
    )
    for key in FORBIDDEN_DIRECTIONAL_SUPPLEMENTARY_REF_KEYS
)
_TEXT_LIKE_SUFFIXES = frozenset({".json", ".jsonl", ".txt", ".md"})


class SupplementaryRefsGovernanceResult(BaseModel, frozen=True):
    """Typed result of validating transported supplementary refs."""

    accepted_refs: tuple[str, ...] = ()
    rejected: bool = False
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


def _detect_forbidden_directional_key(ref: str) -> str | None:
    ref_path = Path(ref)
    stem = ref_path.stem.strip().lower()
    if stem in FORBIDDEN_DIRECTIONAL_SUPPLEMENTARY_REF_KEYS:
        return stem
    if ref_path.suffix.lower() not in _TEXT_LIKE_SUFFIXES:
        return None
    try:
        payload = ref_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for key, pattern in _FORBIDDEN_KEY_PATTERNS:
        if pattern.search(payload):
            return key
    return None


def _validate_supplementary_refs(
    supplementary_refs: tuple[str, ...],
    *,
    forbidden_reason_code: str,
) -> SupplementaryRefsGovernanceResult:
    for ref in supplementary_refs:
        forbidden_key = _detect_forbidden_directional_key(ref)
        if forbidden_key is not None:
            return SupplementaryRefsGovernanceResult(
                rejected=True,
                reason_codes=(
                    forbidden_reason_code,
                    f"{forbidden_reason_code}:{forbidden_key}",
                ),
            )
    return SupplementaryRefsGovernanceResult(accepted_refs=tuple(supplementary_refs))


def validate_ml_supplementary_refs(
    supplementary_refs: tuple[str, ...],
) -> SupplementaryRefsGovernanceResult:
    """Reject forbidden directional ML transport refs before runtime scoring."""

    return _validate_supplementary_refs(
        supplementary_refs,
        forbidden_reason_code="ML_DIRECTIONAL_REF_FORBIDDEN",
    )


def validate_regime_detector_supplementary_refs(
    supplementary_refs: tuple[str, ...],
) -> SupplementaryRefsGovernanceResult:
    """Reject forbidden directional regime transport refs before runtime use."""

    return _validate_supplementary_refs(
        supplementary_refs,
        forbidden_reason_code="REGIME_DIRECTIONAL_REF_FORBIDDEN",
    )


__all__ = [
    "FORBIDDEN_DIRECTIONAL_SUPPLEMENTARY_REF_KEYS",
    "SupplementaryRefsGovernanceResult",
    "validate_ml_supplementary_refs",
    "validate_regime_detector_supplementary_refs",
]
