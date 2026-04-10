"""Deterministic AAOIFI pair-screening helpers."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from pydantic import ValidationError

from .contracts import (
    AaoifiPairScreeningResult,
    AaoifiPairScreeningSnapshot,
    ShariaPolicy,
)

AAOIFI_MAX_DEBT_TO_TOTAL_ASSETS = Decimal("0.33")
AAOIFI_MAX_CASH_AND_INTEREST_BEARING_TO_TOTAL_ASSETS = Decimal("0.33")
AAOIFI_MAX_INTEREST_INCOME_TO_TOTAL_REVENUE = Decimal("0.05")


def load_pair_screening_snapshot(
    metadata: Mapping[str, object],
) -> AaoifiPairScreeningSnapshot | None:
    """Load an optional AAOIFI screening snapshot from request metadata."""

    value = metadata.get("pair_screening")
    if value is None:
        return None
    if isinstance(value, AaoifiPairScreeningSnapshot):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("pair_screening metadata must be a mapping")
    try:
        return AaoifiPairScreeningSnapshot.model_validate(dict(value))
    except ValidationError as exc:
        raise ValueError("pair_screening metadata is invalid") from exc


def evaluate_pair_screening(
    snapshot: AaoifiPairScreeningSnapshot,
    *,
    policy: ShariaPolicy,
) -> AaoifiPairScreeningResult:
    """Apply fixed AAOIFI thresholds without calibration."""

    failure_codes: list[str] = []
    if snapshot.debt_to_total_assets > AAOIFI_MAX_DEBT_TO_TOTAL_ASSETS:
        failure_codes.append("AAOIFI_DEBT_RATIO_EXCEEDED")
    if (
        snapshot.cash_and_interest_bearing_to_total_assets
        > AAOIFI_MAX_CASH_AND_INTEREST_BEARING_TO_TOTAL_ASSETS
    ):
        failure_codes.append("AAOIFI_CASH_RATIO_EXCEEDED")
    if snapshot.interest_income_to_total_revenue > AAOIFI_MAX_INTEREST_INCOME_TO_TOTAL_REVENUE:
        failure_codes.append("AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED")

    passed = not failure_codes
    if passed:
        detail = (
            f"{snapshot.pair.upper()} passed AAOIFI screening via "
            f"{snapshot.screening_provider}@{snapshot.provider_version}"
        )
    else:
        detail = (
            f"{snapshot.pair.upper()} failed AAOIFI screening: "
            f"{', '.join(failure_codes)}"
        )
    return AaoifiPairScreeningResult(
        passed=passed,
        policy_version=policy.policy_version,
        failure_codes=tuple(failure_codes),
        detail=detail,
    )


__all__ = [
    "AAOIFI_MAX_CASH_AND_INTEREST_BEARING_TO_TOTAL_ASSETS",
    "AAOIFI_MAX_DEBT_TO_TOTAL_ASSETS",
    "AAOIFI_MAX_INTEREST_INCOME_TO_TOTAL_REVENUE",
    "evaluate_pair_screening",
    "load_pair_screening_snapshot",
]
