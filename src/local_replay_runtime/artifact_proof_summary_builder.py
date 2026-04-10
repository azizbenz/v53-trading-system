"""Conservative Local IA Lab proof-summary builder for governed artifact export."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import ArtifactProofSummary, validate_artifact_proof_summary
from meta_learning.contracts import TradeLossAttributionReport
from meta_minimal.meta_runtime import MetaRuntimeResult

from local_replay_runtime.artifact_ablation_study import LocalLabAblationStudy
from local_replay_runtime.walk_forward_review import WalkForwardReviewSummary


class LocalLabArtifactProofAssessment(BaseModel, frozen=True):
    """Audit-ready assessment of the current Local IA Lab proof surface."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    proof_summary: ArtifactProofSummary
    ready_for_vps_import: bool = False
    validation_reasons: tuple[str, ...] = ()
    pending_dimensions: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    dtr_coverage: float = Field(default=0.0, ge=0.0)
    incomplete_path_count: int = Field(default=0, ge=0)
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    regime_count: int = Field(default=0, ge=0)
    friction_regret_ratio: float = Field(default=0.0, ge=0.0)
    observed_block_rate_proxy: float = Field(default=0.0, ge=0.0)
    capital_efficiency_ratio: float | None = None


def _build_friction_regret_ratio(meta_result: MetaRuntimeResult) -> tuple[float, tuple[str, ...]]:
    ratios = tuple(
        max(record.realized_cost - record.expected_cost, 0.0) / record.expected_cost
        for record in meta_result.records
        if record.decision_state == "executed" and record.expected_cost > 0.0
    )
    if not ratios:
        return 1.0, ("FRICTION_REGRET_EVIDENCE_MISSING",)
    return sum(ratios) / len(ratios), ()


def _build_block_rate_proxy(meta_result: MetaRuntimeResult) -> float:
    total_records = meta_result.dtr_summary.total_records
    if total_records <= 0:
        return 1.0
    executed_records = meta_result.dtr_summary.by_state.get("executed", 0)
    return max(0.0, min(1.0, 1.0 - (executed_records / total_records)))


def _build_capital_efficiency_ratio(meta_result: MetaRuntimeResult) -> float | None:
    ratios = tuple(
        record.final_size / record.candidate_size
        for record in meta_result.records
        if record.decision_state == "executed" and record.candidate_size > 0.0
    )
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def build_local_lab_artifact_proof_assessment(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    meta_result: MetaRuntimeResult,
    trade_loss_attribution: TradeLossAttributionReport,
    walk_forward_review: WalkForwardReviewSummary,
    ablation_study: LocalLabAblationStudy | None = None,
) -> LocalLabArtifactProofAssessment:
    """Build a conservative canonical proof summary from current Local IA Lab evidence."""

    non_empty_regimes = tuple(
        dict.fromkeys(record.regime for record in meta_result.records if record.regime)
    )
    regime_count = len(non_empty_regimes)
    dtr_coverage = meta_result.dtr_summary.dtr_coverage
    incomplete_path_count = meta_result.dtr_summary.incomplete_path_count
    executed_records = trade_loss_attribution.executed_records
    losing_trade_count = trade_loss_attribution.losing_trade_count
    friction_regret_ratio, friction_flags = _build_friction_regret_ratio(meta_result)
    observed_block_rate_proxy = _build_block_rate_proxy(meta_result)
    capital_efficiency_ratio = _build_capital_efficiency_ratio(meta_result)
    has_unclassified_loss = any(
        attribution.attribution_status == "loss"
        and attribution.primary_failure_mode == "unclassified_loss"
        for attribution in trade_loss_attribution.attributions
    )

    ablation_delta_net_pnl = 0.0
    ablation_delta_ce: float | None = None
    block_rate_value = observed_block_rate_proxy
    ablation_ready = False
    ablation_blocking_reasons: tuple[str, ...] = ()
    if ablation_study is not None:
        ablation_ready = ablation_study.study_ready
        ablation_blocking_reasons = ablation_study.blocking_reasons
        if ablation_study.study_ready:
            ablation_delta_net_pnl = ablation_study.ablation_delta_net_pnl
            ablation_delta_ce = ablation_study.ablation_delta_ce
            block_rate_value = ablation_study.block_rate_delta

    anti_cowardice_pass = (
        dtr_coverage >= 0.95
        and incomplete_path_count == 0
        and meta_result.dtr_summary.synthetic_input_count == 0
    )
    friction_regret_pass = (
        not meta_result.break_even_report.has_cost_drift_alert
        and friction_regret_ratio <= 0.05
    )
    regime_segmentation_pass = regime_count >= 2
    operational_burden_pass = (
        meta_result.dtr_summary.total_records > 0
        and block_rate_value <= 0.10
        and not has_unclassified_loss
    )
    capital_efficiency_pass: bool | None
    if capital_efficiency_ratio is None:
        capital_efficiency_pass = None
    else:
        capital_efficiency_pass = capital_efficiency_ratio >= 0.80

    proof_summary = ArtifactProofSummary(
        anti_cowardice_pass=anti_cowardice_pass,
        friction_regret_pass=friction_regret_pass,
        walk_forward_pass=walk_forward_review.walk_forward_pass,
        regime_segmentation_pass=regime_segmentation_pass,
        operational_burden_pass=operational_burden_pass,
        capital_efficiency_pass=capital_efficiency_pass,
        ablation_delta_net_pnl=ablation_delta_net_pnl,
        ablation_delta_ce=ablation_delta_ce,
        friction_regret_value=friction_regret_ratio,
        block_rate_delta=block_rate_value,
    )

    pending_dimensions: list[str] = []
    caution_flags: list[str] = [
        "ANTI_COWARDICE_COVERAGE_PROXY_USED",
        "BLOCK_RATE_PROXY_USED",
    ]
    caution_flags.extend(friction_flags)
    if not ablation_ready:
        pending_dimensions.extend(
            ["ABLATION_DELTA_NET_PNL", "ABLATION_DELTA_CE"]
        )
        caution_flags.append("ABLATION_STUDY_NOT_READY")
        caution_flags.extend(ablation_blocking_reasons)
    if regime_count < 2:
        pending_dimensions.append("REGIME_SEGMENTATION")
    if capital_efficiency_ratio is None:
        pending_dimensions.append("CAPITAL_EFFICIENCY")
        caution_flags.append("CAPITAL_EFFICIENCY_EVIDENCE_MISSING")
    if not walk_forward_review.walk_forward_pass:
        pending_dimensions.append("WALK_FORWARD_HUMAN_REVIEW")
    if has_unclassified_loss:
        caution_flags.append("UNCLASSIFIED_LOSS_PRESENT")

    validation_reasons = validate_artifact_proof_summary(proof_summary)

    return LocalLabArtifactProofAssessment(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        proof_summary=proof_summary,
        ready_for_vps_import=not validation_reasons,
        validation_reasons=validation_reasons,
        pending_dimensions=tuple(dict.fromkeys(pending_dimensions)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        dtr_coverage=dtr_coverage,
        incomplete_path_count=incomplete_path_count,
        executed_records=executed_records,
        losing_trade_count=losing_trade_count,
        regime_count=regime_count,
        friction_regret_ratio=friction_regret_ratio,
        observed_block_rate_proxy=observed_block_rate_proxy,
        capital_efficiency_ratio=capital_efficiency_ratio,
    )


__all__ = [
    "LocalLabArtifactProofAssessment",
    "build_local_lab_artifact_proof_assessment",
]
