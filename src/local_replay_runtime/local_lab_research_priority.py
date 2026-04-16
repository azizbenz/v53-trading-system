"""Interpretable Local IA Lab research-priority scorer."""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import BaseModel, Field, model_validator

from local_replay_runtime.local_lab_loss_surrogate import (
    LocalLabLossSurrogateReport,
    LocalLabLossSurrogateScopeScore,
)
from local_replay_runtime.local_lab_scope_matrix import (
    LocalLabScopeAnalysisMatrix,
    LocalLabScopeAnalysisRow,
    build_local_lab_scope_slug,
)
from meta_learning.contracts import TradeLossAttribution, TradeLossAttributionReport


class LocalLabResearchPriorityWeights(BaseModel, frozen=True):
    """Transparent weights for the Local IA Lab priority scorer."""

    loss_rate_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    cost_drift_weight: float = Field(default=0.18, ge=0.0, le=1.0)
    sterilization_weight: float = Field(default=0.13, ge=0.0, le=1.0)
    edge_degraded_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    trace_coverage_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    unclassified_loss_weight: float = Field(default=0.04, ge=0.0, le=1.0)
    proof_gap_weight: float = Field(default=0.03, ge=0.0, le=1.0)
    release_gap_weight: float = Field(default=0.02, ge=0.0, le=1.0)
    surrogate_risk_weight: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_total_weight(self) -> "LocalLabResearchPriorityWeights":
        total = (
            self.loss_rate_weight
            + self.cost_drift_weight
            + self.sterilization_weight
            + self.edge_degraded_weight
            + self.trace_coverage_weight
            + self.unclassified_loss_weight
            + self.proof_gap_weight
            + self.release_gap_weight
            + self.surrogate_risk_weight
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("LocalLabResearchPriorityWeights must sum to 1.0")
        return self


class LocalLabResearchPriorityFeatures(BaseModel, frozen=True):
    """Feature vector used by the Local IA Lab priority scorer."""

    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    loss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    mean_loss_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    cost_drift_count: int = Field(default=0, ge=0)
    sterilization_count: int = Field(default=0, ge=0)
    edge_degraded_count: int = Field(default=0, ge=0)
    trace_coverage_count: int = Field(default=0, ge=0)
    unclassified_loss_count: int = Field(default=0, ge=0)
    proof_gap_count: int = Field(default=0, ge=0)
    release_gap_count: int = Field(default=0, ge=0)
    proof_ready: bool = False
    release_ready: bool = False
    loss_surrogate_status: str = Field(default="not_evaluated", min_length=1)
    loss_surrogate_ready: bool = False
    surrogate_mean_predicted_loss_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    surrogate_top_risk_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_threshold_ids: tuple[str, ...] = ()


class LocalLabResearchPriorityScope(BaseModel, frozen=True):
    """One ranked Local IA Lab scope for the next bounded research step."""

    priority_rank: int = Field(..., ge=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    features: LocalLabResearchPriorityFeatures
    priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    priority_band: str = Field(default="defer", min_length=1)
    recommended_next_action: str = Field(default="collect_more_evidence", min_length=1)
    reason_codes: tuple[str, ...] = ()
    recommended_threshold_ids: tuple[str, ...] = ()


class LocalLabResearchPriorityReport(BaseModel, frozen=True):
    """Audit-ready ranking of Local IA Lab follow-up scopes."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    model_family: str = Field(default="interpretable_priority_model_v1", min_length=1)
    model_kind: str = Field(default="transparent_weighted_score", min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    scope_count: int = Field(default=0, ge=0)
    priority_scope_count: int = Field(default=0, ge=0)
    highest_priority_scope_slug: str = ""
    highest_priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_threshold_ids: tuple[str, ...] = ()
    scopes: tuple[LocalLabResearchPriorityScope, ...] = ()


_DEFAULT_WEIGHTS = LocalLabResearchPriorityWeights()


def build_local_lab_research_priority_report(
    *,
    correlation_id: str,
    export_dir: str,
    loss_reports: tuple[TradeLossAttributionReport, ...],
    scope_matrix: LocalLabScopeAnalysisMatrix | None = None,
    selected_pair: str | None = None,
    selected_engine_id: str | None = None,
    artifact_proof_ready: bool = False,
    artifact_proof_validation_reasons: tuple[str, ...] = (),
    release_ready_for_shadow: bool = False,
    release_blocking_reasons: tuple[str, ...] = (),
    loss_surrogate_report: LocalLabLossSurrogateReport | None = None,
    weights: LocalLabResearchPriorityWeights = _DEFAULT_WEIGHTS,
) -> LocalLabResearchPriorityReport:
    """Rank Local IA Lab scopes for the next bounded research cycle."""

    scoped_attributions = _group_scoped_attributions(loss_reports)
    surrogate_scopes = _group_surrogate_scopes(loss_surrogate_report)
    scope_keys = _discover_scope_keys(
        scope_matrix=scope_matrix,
        scoped_attributions=scoped_attributions,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
    )

    ranked_scopes: list[LocalLabResearchPriorityScope] = []
    all_threshold_ids: set[str] = set()
    for pair, engine_id, scope_slug in scope_keys:
        scope_row = _resolve_scope_row(scope_matrix, pair=pair, engine_id=engine_id)
        losses = tuple(
            attribution
            for attribution in scoped_attributions[(pair, engine_id)]
            if attribution.attribution_status == "loss"
        )
        features = _build_features(
            pair=pair,
            engine_id=engine_id,
            scope_slug=scope_slug,
            scoped_attributions=scoped_attributions[(pair, engine_id)],
            losses=losses,
            scope_row=scope_row,
            artifact_proof_ready=artifact_proof_ready,
            artifact_proof_validation_reasons=artifact_proof_validation_reasons,
            release_ready_for_shadow=release_ready_for_shadow,
            release_blocking_reasons=release_blocking_reasons,
            surrogate_scope_score=surrogate_scopes.get((pair, engine_id)),
            loss_surrogate_report=loss_surrogate_report,
        )
        all_threshold_ids.update(features.recommended_threshold_ids)
        ranked_scopes.append(
            LocalLabResearchPriorityScope(
                priority_rank=1,
                pair=pair,
                engine_id=engine_id,
                scope_slug=scope_slug,
                features=features,
                priority_score=_build_priority_score(features, weights=weights),
                priority_band="defer",
                recommended_next_action="collect_more_evidence",
                reason_codes=(),
                recommended_threshold_ids=features.recommended_threshold_ids,
            )
        )

    ranked_scopes = sorted(
        ranked_scopes,
        key=lambda scope: (-scope.priority_score, scope.pair, scope.engine_id),
    )
    enriched_scopes = []
    for index, scope in enumerate(ranked_scopes):
        priority_band = _build_priority_band(scope.priority_score)
        enriched_scopes.append(
            scope.model_copy(
                update={
                    "priority_rank": index + 1,
                    "priority_band": priority_band,
                    "recommended_next_action": _build_next_action(scope.features),
                    "reason_codes": _build_reason_codes(scope.features),
                }
            )
        )

    priority_scope_count = sum(
        1
        for scope in enriched_scopes
        if scope.priority_band in {"research_now", "research_next"}
    )
    highest_priority_scope_slug = ""
    highest_priority_score = 0.0
    if any(scope.features.losing_trade_count > 0 for scope in enriched_scopes):
        highest_priority_scope_slug = enriched_scopes[0].scope_slug
        highest_priority_score = enriched_scopes[0].priority_score

    return LocalLabResearchPriorityReport(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status=_build_report_status(enriched_scopes, priority_scope_count),
        scope_count=len(enriched_scopes),
        priority_scope_count=priority_scope_count,
        highest_priority_scope_slug=highest_priority_scope_slug,
        highest_priority_score=highest_priority_score,
        recommended_threshold_ids=tuple(sorted(all_threshold_ids)),
        scopes=tuple(enriched_scopes),
    )


def _group_scoped_attributions(
    loss_reports: tuple[TradeLossAttributionReport, ...],
) -> dict[tuple[str, str], tuple[TradeLossAttribution, ...]]:
    grouped: dict[tuple[str, str], list[TradeLossAttribution]] = defaultdict(list)
    for report in loss_reports:
        for attribution in report.attributions:
            grouped[(attribution.pair, attribution.engine_id)].append(attribution)
    return {key: tuple(value) for key, value in grouped.items()}


def _discover_scope_keys(
    *,
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    scoped_attributions: dict[tuple[str, str], tuple[TradeLossAttribution, ...]],
    selected_pair: str | None,
    selected_engine_id: str | None,
) -> tuple[tuple[str, str, str], ...]:
    if scope_matrix is not None and scope_matrix.scopes:
        return tuple((row.pair, row.engine_id, row.scope_slug) for row in scope_matrix.scopes)

    if scoped_attributions:
        return tuple(
            (pair, engine_id, build_local_lab_scope_slug(pair, engine_id))
            for pair, engine_id in sorted(scoped_attributions)
        )
    if selected_pair and selected_engine_id:
        return (
            (
                selected_pair,
                selected_engine_id,
                build_local_lab_scope_slug(selected_pair, selected_engine_id),
            ),
        )
    return ()


def _resolve_scope_row(
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    *,
    pair: str,
    engine_id: str,
) -> LocalLabScopeAnalysisRow | None:
    if scope_matrix is None:
        return None
    for row in scope_matrix.scopes:
        if row.pair == pair and row.engine_id == engine_id:
            return row
    return None


def _group_surrogate_scopes(
    loss_surrogate_report: LocalLabLossSurrogateReport | None,
) -> dict[tuple[str, str], LocalLabLossSurrogateScopeScore]:
    if loss_surrogate_report is None:
        return {}
    return {
        (scope.pair, scope.engine_id): scope
        for scope in loss_surrogate_report.scopes
    }


def _build_features(
    *,
    pair: str,
    engine_id: str,
    scope_slug: str,
    scoped_attributions: tuple[TradeLossAttribution, ...],
    losses: tuple[TradeLossAttribution, ...],
    scope_row: LocalLabScopeAnalysisRow | None,
    artifact_proof_ready: bool,
    artifact_proof_validation_reasons: tuple[str, ...],
    release_ready_for_shadow: bool,
    release_blocking_reasons: tuple[str, ...],
    surrogate_scope_score: LocalLabLossSurrogateScopeScore | None,
    loss_surrogate_report: LocalLabLossSurrogateReport | None,
) -> LocalLabResearchPriorityFeatures:
    executed_records = (
        scope_row.executed_records
        if scope_row is not None
        else sum(1 for attribution in scoped_attributions if attribution.decision_state == "executed")
    )
    losing_trade_count = scope_row.losing_trade_count if scope_row is not None else len(losses)
    failure_modes = Counter(attribution.primary_failure_mode for attribution in losses)
    recommended_threshold_ids = tuple(
        sorted(
            {
                threshold_id
                for attribution in losses
                for threshold_id in attribution.recommended_threshold_ids
            }
        )
    )
    proof_gap_reasons = (
        tuple(scope_row.artifact_proof_validation_reasons)
        if scope_row is not None
        else tuple(artifact_proof_validation_reasons)
    )
    release_gap_reasons = (
        tuple(scope_row.release_blocking_reasons)
        if scope_row is not None
        else tuple(release_blocking_reasons)
    )
    return LocalLabResearchPriorityFeatures(
        pair=pair,
        engine_id=engine_id,
        scope_slug=scope_slug,
        executed_records=executed_records,
        losing_trade_count=losing_trade_count,
        loss_rate=_ratio(losing_trade_count, executed_records),
        mean_loss_confidence=_mean_confidence(losses),
        cost_drift_count=failure_modes["cost_drift"],
        sterilization_count=failure_modes["sterilization"],
        edge_degraded_count=failure_modes["edge_degraded"],
        trace_coverage_count=failure_modes["trace_coverage"],
        unclassified_loss_count=failure_modes["unclassified_loss"],
        proof_gap_count=len(proof_gap_reasons),
        release_gap_count=len(release_gap_reasons),
        proof_ready=scope_row.artifact_proof_ready if scope_row is not None else artifact_proof_ready,
        release_ready=scope_row.release_ready if scope_row is not None else release_ready_for_shadow,
        loss_surrogate_status=(
            "not_evaluated"
            if loss_surrogate_report is None
            else loss_surrogate_report.status
        ),
        loss_surrogate_ready=False if loss_surrogate_report is None else loss_surrogate_report.ready,
        surrogate_mean_predicted_loss_probability=(
            0.0
            if surrogate_scope_score is None
            or surrogate_scope_score.mean_predicted_loss_probability is None
            else surrogate_scope_score.mean_predicted_loss_probability
        ),
        surrogate_top_risk_probability=(
            0.0 if surrogate_scope_score is None else surrogate_scope_score.top_risk_probability
        ),
        recommended_threshold_ids=recommended_threshold_ids,
    )


def _build_priority_score(
    features: LocalLabResearchPriorityFeatures,
    *,
    weights: LocalLabResearchPriorityWeights,
) -> float:
    loss_denominator = features.losing_trade_count
    surrogate_risk = max(
        features.surrogate_mean_predicted_loss_probability,
        features.surrogate_top_risk_probability,
    )
    score = (
        weights.loss_rate_weight * features.loss_rate
        + weights.cost_drift_weight * _ratio(features.cost_drift_count, loss_denominator)
        + weights.sterilization_weight * _ratio(features.sterilization_count, loss_denominator)
        + weights.edge_degraded_weight * _ratio(features.edge_degraded_count, loss_denominator)
        + weights.trace_coverage_weight * _ratio(features.trace_coverage_count, loss_denominator)
        + weights.unclassified_loss_weight * _ratio(features.unclassified_loss_count, loss_denominator)
        + weights.proof_gap_weight * (0.0 if features.proof_ready else 1.0)
        + weights.release_gap_weight * (0.0 if features.release_ready else 1.0)
        + weights.surrogate_risk_weight * surrogate_risk
    )
    return round(max(0.0, min(score, 1.0)), 6)


def _build_priority_band(score: float) -> str:
    if score >= 0.75:
        return "research_now"
    if score >= 0.35:
        return "research_next"
    if score >= 0.20:
        return "monitor"
    return "defer"


def _build_next_action(features: LocalLabResearchPriorityFeatures) -> str:
    surrogate_risk = max(
        features.surrogate_mean_predicted_loss_probability,
        features.surrogate_top_risk_probability,
    )
    if features.trace_coverage_count > 0:
        return "improve_trace_capture"
    if features.recommended_threshold_ids:
        return "replay_recalibration_candidate"
    if features.loss_surrogate_ready and surrogate_risk >= 0.70:
        return "replay_high_risk_scope"
    if features.sterilization_count > 0:
        return "review_scope_sterilization"
    if features.unclassified_loss_count > 0:
        return "manual_loss_review"
    if features.losing_trade_count > 0:
        return "collect_more_evidence"
    return "keep_collecting_evidence"


def _build_reason_codes(features: LocalLabResearchPriorityFeatures) -> tuple[str, ...]:
    reason_codes: list[str] = []
    surrogate_risk = max(
        features.surrogate_mean_predicted_loss_probability,
        features.surrogate_top_risk_probability,
    )
    if features.loss_rate >= 0.50:
        reason_codes.append("LOSS_RATE_ELEVATED")
    if features.cost_drift_count > 0:
        reason_codes.append("COST_DRIFT_PRESENT")
    if features.sterilization_count > 0:
        reason_codes.append("STERILIZATION_PRESENT")
    if features.edge_degraded_count > 0:
        reason_codes.append("EDGE_DEGRADED_PRESENT")
    if features.trace_coverage_count > 0:
        reason_codes.append("TRACE_COVERAGE_PRESENT")
    if features.unclassified_loss_count > 0:
        reason_codes.append("MANUAL_REVIEW_REQUIRED")
    if features.loss_surrogate_ready:
        reason_codes.append("LOSS_SURROGATE_READY")
    elif features.loss_surrogate_status not in {"not_evaluated", "no_scopes"}:
        reason_codes.append("LOSS_SURROGATE_NOT_READY")
    if surrogate_risk >= 0.70:
        reason_codes.append("SURROGATE_HIGH_RISK_SCOPE")
    elif surrogate_risk >= 0.45:
        reason_codes.append("SURROGATE_ELEVATED_RISK_SCOPE")
    if features.recommended_threshold_ids:
        reason_codes.append("THRESHOLD_RECALIBRATION_AVAILABLE")
    if not features.proof_ready:
        reason_codes.append("PROOF_NOT_READY")
    if not features.release_ready:
        reason_codes.append("RELEASE_NOT_READY")
    if not reason_codes:
        reason_codes.append("NO_ELEVATED_RESEARCH_PRIORITY")
    return tuple(reason_codes)


def _build_report_status(
    ranked_scopes: list[LocalLabResearchPriorityScope],
    priority_scope_count: int,
) -> str:
    if not ranked_scopes:
        return "no_scopes"
    if not any(scope.features.losing_trade_count > 0 for scope in ranked_scopes):
        return "no_losing_scopes"
    if priority_scope_count > 0:
        return "ready"
    return "monitor_only"


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return min(max(numerator / denominator, 0.0), 1.0)


def _mean_confidence(losses: tuple[TradeLossAttribution, ...]) -> float:
    if not losses:
        return 0.0
    return round(sum(loss.confidence for loss in losses) / len(losses), 6)


__all__ = [
    "LocalLabResearchPriorityFeatures",
    "LocalLabResearchPriorityReport",
    "LocalLabResearchPriorityScope",
    "LocalLabResearchPriorityWeights",
    "build_local_lab_research_priority_report",
]
