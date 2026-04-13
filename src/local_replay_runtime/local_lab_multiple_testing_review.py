"""Local IA Lab multiple-testing review sidecar over current calibration evidence."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from calibration_methods import HolmBonferroniResult, apply_holm_bonferroni
from local_replay_runtime.edge_gate_calibration import EdgeGateCalibrationReport
from local_replay_runtime.local_lab_tail_risk_review import LocalLabTailRiskReview


class LocalLabMultipleTestingStatus(StrEnum):
    """Bounded Local IA Lab statuses for MI-12."""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class LocalLabMultipleTestingFamilyReview(BaseModel, frozen=True):
    """One hypothesis family review for Local IA Lab multiple-testing."""

    family_id: str = Field(..., min_length=1)
    threshold_ids: tuple[str, ...] = ()
    evidence_mode: str = Field(..., min_length=1)
    family_size: int = Field(default=0, ge=0)
    correction_required: bool = False
    correction_status: str = Field(default="not_evaluated", min_length=1)
    family_alpha: float | None = Field(default=None, gt=0.0, le=1.0)
    comparable_p_value_count: int = Field(default=0, ge=0)
    corrected_rejection_count: int = Field(default=0, ge=0)
    holm_bonferroni_result: HolmBonferroniResult | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


class LocalLabMultipleTestingReview(BaseModel, frozen=True):
    """Audit-ready Local IA Lab MI-12 review."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    review_status: LocalLabMultipleTestingStatus
    review_ready: bool = False
    multi_test_correction: str = Field(default="not_evaluated", min_length=1)
    correction_required: bool = False
    family_count: int = Field(default=0, ge=0)
    ready_family_count: int = Field(default=0, ge=0)
    partial_family_count: int = Field(default=0, ge=0)
    blocked_family_count: int = Field(default=0, ge=0)
    correction_required_family_count: int = Field(default=0, ge=0)
    corrected_family_count: int = Field(default=0, ge=0)
    families: tuple[LocalLabMultipleTestingFamilyReview, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def build_local_lab_multiple_testing_review(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    edge_report: EdgeGateCalibrationReport,
    tail_risk_review: LocalLabTailRiskReview,
) -> LocalLabMultipleTestingReview:
    """Build the bounded Local IA Lab MI-12 review."""

    families = (
        _build_interval_publication_family(
            family_id="edge_gate_interval_publication",
            threshold_ids=tuple(threshold.threshold_id for threshold in edge_report.thresholds),
        ),
        _build_interval_publication_family(
            family_id="tail_risk_interval_publication",
            threshold_ids=tuple(breaker.threshold_id for breaker in tail_risk_review.breakers),
        ),
    )

    ready_family_count = sum(1 for family in families if family.correction_status.startswith("not_required"))
    partial_family_count = sum(1 for family in families if family.correction_status == "pending_inputs")
    blocked_family_count = sum(1 for family in families if family.blocking_reasons)
    correction_required_family_count = sum(1 for family in families if family.correction_required)
    corrected_family_count = sum(
        1 for family in families if family.correction_status == "holm_bonferroni_applied"
    )
    blocking_reasons = tuple(
        dict.fromkeys(reason for family in families for reason in family.blocking_reasons)
    )
    caution_flags = tuple(
        dict.fromkeys(flag for family in families for flag in family.caution_flags)
    )

    if blocked_family_count > 0:
        review_status = LocalLabMultipleTestingStatus.BLOCKED
    elif partial_family_count > 0:
        review_status = LocalLabMultipleTestingStatus.PARTIAL
    else:
        review_status = LocalLabMultipleTestingStatus.READY

    multi_test_correction = _summarize_multi_test_correction(families)
    return LocalLabMultipleTestingReview(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        review_status=review_status,
        review_ready=review_status == LocalLabMultipleTestingStatus.READY,
        multi_test_correction=multi_test_correction,
        correction_required=correction_required_family_count > 0,
        family_count=len(families),
        ready_family_count=ready_family_count,
        partial_family_count=partial_family_count,
        blocked_family_count=blocked_family_count,
        correction_required_family_count=correction_required_family_count,
        corrected_family_count=corrected_family_count,
        families=families,
        blocking_reasons=blocking_reasons,
        caution_flags=caution_flags,
    )


def _build_interval_publication_family(
    *,
    family_id: str,
    threshold_ids: tuple[str, ...],
) -> LocalLabMultipleTestingFamilyReview:
    if not threshold_ids:
        return LocalLabMultipleTestingFamilyReview(
            family_id=family_id,
            threshold_ids=(),
            evidence_mode="interval_publication",
            family_size=0,
            correction_required=False,
            correction_status="not_required_empty_family",
            caution_flags=("MULTI_TEST_EMPTY_FAMILY",),
        )
    return LocalLabMultipleTestingFamilyReview(
        family_id=family_id,
        threshold_ids=threshold_ids,
        evidence_mode="interval_publication",
        family_size=len(threshold_ids),
        correction_required=False,
        correction_status="not_required_interval_publication",
        caution_flags=("MULTI_TEST_INTERVAL_PUBLICATION_ONLY",),
    )


def build_hypothesis_test_family_review(
    *,
    family_id: str,
    hypotheses: tuple[tuple[str, float], ...],
    family_alpha: float = 0.05,
) -> LocalLabMultipleTestingFamilyReview:
    """Build one future-ready hypothesis-test family review using Holm-Bonferroni."""

    if not hypotheses:
        return LocalLabMultipleTestingFamilyReview(
            family_id=family_id,
            threshold_ids=(),
            evidence_mode="hypothesis_test",
            family_size=0,
            correction_required=False,
            correction_status="not_required_empty_family",
            caution_flags=("MULTI_TEST_EMPTY_FAMILY",),
        )
    holm_result = apply_holm_bonferroni(hypotheses, family_alpha=family_alpha)
    corrected_rejection_count = sum(
        1 for decision in holm_result.adjusted_hypotheses if decision.rejected
    )
    return LocalLabMultipleTestingFamilyReview(
        family_id=family_id,
        threshold_ids=tuple(hypothesis_id for hypothesis_id, _ in hypotheses),
        evidence_mode="hypothesis_test",
        family_size=len(hypotheses),
        correction_required=len(hypotheses) > 1,
        correction_status="holm_bonferroni_applied",
        family_alpha=family_alpha,
        comparable_p_value_count=len(hypotheses),
        corrected_rejection_count=corrected_rejection_count,
        holm_bonferroni_result=holm_result,
    )


def _summarize_multi_test_correction(
    families: tuple[LocalLabMultipleTestingFamilyReview, ...],
) -> str:
    statuses = {family.correction_status for family in families}
    if not statuses:
        return "not_evaluated"
    if statuses == {"not_required_interval_publication"}:
        return "not_required_interval_publication"
    if "holm_bonferroni_applied" in statuses:
        return "holm_bonferroni_applied"
    if any(family.blocking_reasons for family in families):
        return "blocked"
    if "pending_inputs" in statuses:
        return "pending_inputs"
    if len(statuses) == 1:
        return next(iter(statuses))
    return "mixed"


__all__ = [
    "LocalLabMultipleTestingFamilyReview",
    "LocalLabMultipleTestingReview",
    "LocalLabMultipleTestingStatus",
    "build_hypothesis_test_family_review",
    "build_local_lab_multiple_testing_review",
]
