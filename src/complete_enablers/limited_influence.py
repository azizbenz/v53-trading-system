"""Governed Build-14 phase-2 limited influence evaluator."""

from __future__ import annotations

from complete_enablers.contracts import (
    Build14InfluenceReport,
    Build14InfluenceSignal,
    Build14ObservationInput,
)
from complete_enablers.enums import (
    Build14InfluenceAction,
    Build14InfluenceMode,
    Build14Severity,
    Build14SignalFamily,
)
from complete_enablers.execution_fragility_score import build_execution_fragility_score
from complete_enablers.market_toxicity_snapshot import build_market_toxicity_snapshot


_SEVERITY_RANK = {
    Build14Severity.NOMINAL: 0,
    Build14Severity.ELEVATED: 1,
    Build14Severity.CRITICAL: 2,
}


def _reason_code(reader_name: str, status: Build14Severity) -> str:
    return f"{reader_name}_{status.value}"


def evaluate_build14_limited_influence(
    observation: Build14ObservationInput,
) -> Build14InfluenceReport:
    """Evaluate the bounded Build-14 phase-2 recommendation from existing readers."""

    snapshots = (
        build_market_toxicity_snapshot(observation),
        build_execution_fragility_score(observation),
    )
    severities = {snapshot.status for snapshot in snapshots}
    reason_codes = tuple(
        _reason_code(snapshot.reader_name, snapshot.status)
        for snapshot in snapshots
        if snapshot.status != Build14Severity.NOMINAL
    )
    overall_severity = max(
        severities,
        key=lambda severity: _SEVERITY_RANK[severity],
    )

    if severities == {Build14Severity.CRITICAL}:
        signal = Build14InfluenceSignal(
            correlation_id=observation.correlation_id,
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.SOFT_VETO,
            severity=Build14Severity.CRITICAL,
            families=(Build14SignalFamily.MICROSTRUCTURE, Build14SignalFamily.AI_EDGE),
            summary="Build-14 soft veto: toxicity and execution fragility are both critical",
            reason_codes=reason_codes,
            confidence_penalty_weight=0.25,
            recommended_budget_factor=0.0,
            requires_manual_review=True,
            candidate_effect="soft_veto",
        )
    elif overall_severity == Build14Severity.CRITICAL:
        signal = Build14InfluenceSignal(
            correlation_id=observation.correlation_id,
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.REVIEW_ONLY,
            severity=Build14Severity.CRITICAL,
            families=tuple(sorted({snapshot.signal_family for snapshot in snapshots if snapshot.status == Build14Severity.CRITICAL}, key=lambda item: item.value)),
            summary="Build-14 review only: a critical enriched reader requires manual review before live-light",
            reason_codes=reason_codes,
            confidence_penalty_weight=0.15,
            recommended_budget_factor=0.0,
            requires_manual_review=True,
            candidate_effect="review_only",
        )
    elif overall_severity == Build14Severity.ELEVATED:
        elevated_families = tuple(
            sorted(
                {snapshot.signal_family for snapshot in snapshots if snapshot.status == Build14Severity.ELEVATED},
                key=lambda item: item.value,
            )
        )
        both_elevated = len(elevated_families) == 2
        signal = Build14InfluenceSignal(
            correlation_id=observation.correlation_id,
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.DOWNGRADE_CONFIDENCE,
            severity=Build14Severity.ELEVATED,
            families=elevated_families,
            summary="Build-14 limited influence: elevated enriched readers reduce live-light confidence and budget",
            reason_codes=reason_codes,
            confidence_penalty_weight=0.15 if both_elevated else 0.10,
            recommended_budget_factor=0.75 if both_elevated else 0.85,
            requires_manual_review=False,
            candidate_effect="confidence_downgrade",
        )
    else:
        signal = Build14InfluenceSignal(
            correlation_id=observation.correlation_id,
            influence_mode=Build14InfluenceMode.READ_ONLY,
            action=Build14InfluenceAction.OBSERVE,
            severity=Build14Severity.NOMINAL,
            families=tuple(sorted({snapshot.signal_family for snapshot in snapshots}, key=lambda item: item.value)),
            summary="Build-14 remains observational: no bounded influence is required",
            reason_codes=(),
            confidence_penalty_weight=0.0,
            recommended_budget_factor=1.0,
            requires_manual_review=False,
            candidate_effect="observe_only",
        )

    return Build14InfluenceReport(
        correlation_id=observation.correlation_id,
        snapshots=snapshots,
        signal=signal,
    )


__all__ = [
    "evaluate_build14_limited_influence",
]
