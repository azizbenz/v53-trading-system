"""Bounded trained loss-risk surrogate for Local IA Lab research only."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from local_replay_runtime.local_lab_scope_matrix import (
    LocalLabScopeAnalysisMatrix,
    build_local_lab_scope_slug,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


_FEATURE_NAMES = (
    "raw_score",
    "penalized_score",
    "final_score",
    "expected_cost",
    "ce_expected",
    "candidate_size",
    "final_size",
    "ranking_position",
)


class LocalLabLossSurrogateModel(BaseModel, frozen=True):
    """Transparent trained linear model over no-lookahead Local IA Lab features."""

    model_family: str = Field(default="transparent_linear_loss_surrogate_v1", min_length=1)
    model_kind: str = Field(default="diagonal_lda_linear_score", min_length=1)
    feature_names: tuple[str, ...] = _FEATURE_NAMES
    feature_means: tuple[float, ...] = ()
    feature_scales: tuple[float, ...] = ()
    coefficients: tuple[float, ...] = ()
    intercept: float = 0.0
    trained_record_count: int = Field(default=0, ge=0)
    positive_loss_count: int = Field(default=0, ge=0)
    negative_non_loss_count: int = Field(default=0, ge=0)
    no_lookahead_only: bool = True


class LocalLabLossSurrogateRecordScore(BaseModel, frozen=True):
    """Per-record loss-risk score used for local research only."""

    dtr_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    predicted_loss_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    score_margin: float = 0.0
    actual_loss: bool = False
    net_return_after_cost: float = 0.0


class LocalLabLossSurrogateScopeScore(BaseModel, frozen=True):
    """Per-scope Local IA Lab surrogate summary."""

    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    executed_record_count: int = Field(default=0, ge=0)
    loss_count: int = Field(default=0, ge=0)
    actual_loss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    mean_predicted_loss_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    top_risk_dtr_id: str = ""
    top_risk_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_band: str = Field(default="not_scored", min_length=1)


class LocalLabLossSurrogateReport(BaseModel, frozen=True):
    """Audit-ready trained Local IA Lab sidecar."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    ready: bool = False
    scope_count: int = Field(default=0, ge=0)
    scored_scope_count: int = Field(default=0, ge=0)
    executed_record_count: int = Field(default=0, ge=0)
    trained_record_count: int = Field(default=0, ge=0)
    loss_count: int = Field(default=0, ge=0)
    non_loss_count: int = Field(default=0, ge=0)
    highest_risk_scope_slug: str = ""
    highest_risk_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    label_definition: str = Field(
        default="loss = executed trade with gross_return - realized_cost <= 0",
        min_length=1,
    )
    feature_policy: str = Field(
        default="no_lookahead_decision_time_features_only",
        min_length=1,
    )
    model: LocalLabLossSurrogateModel | None = None
    scopes: tuple[LocalLabLossSurrogateScopeScore, ...] = ()
    record_scores: tuple[LocalLabLossSurrogateRecordScore, ...] = ()


def build_local_lab_loss_surrogate_report(
    *,
    correlation_id: str,
    export_dir: str,
    records: tuple[DTRRecord, ...],
    scope_matrix: LocalLabScopeAnalysisMatrix | None = None,
    selected_pair: str | None = None,
    selected_engine_id: str | None = None,
    min_training_records: int = 4,
) -> LocalLabLossSurrogateReport:
    """Fit a transparent local-only loss surrogate over governed DTR records."""

    scoped_records = _filter_records(
        records,
        scope_matrix=scope_matrix,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
    )
    executed_records = tuple(
        record
        for record in scoped_records
        if record.decision_state == DecisionState.EXECUTED
    )
    loss_records = tuple(record for record in executed_records if _is_loss(record))
    non_loss_records = tuple(record for record in executed_records if not _is_loss(record))

    if not scoped_records:
        return LocalLabLossSurrogateReport(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status="no_scopes",
        )

    if len(executed_records) < min_training_records:
        return _build_untrained_report(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status="insufficient_executed_records",
            scoped_records=scoped_records,
            executed_records=executed_records,
            loss_records=loss_records,
            non_loss_records=non_loss_records,
        )

    if not loss_records or not non_loss_records:
        return _build_untrained_report(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status="single_class_only",
            scoped_records=scoped_records,
            executed_records=executed_records,
            loss_records=loss_records,
            non_loss_records=non_loss_records,
        )

    model = _fit_model(executed_records, loss_records=loss_records, non_loss_records=non_loss_records)
    record_scores = tuple(
        _score_record(record, model=model)
        for record in executed_records
    )
    scope_scores = _build_scope_scores(
        scoped_records=scoped_records,
        record_scores=record_scores,
    )
    highest_scope = max(scope_scores, key=lambda scope: scope.top_risk_probability)
    return LocalLabLossSurrogateReport(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status="trained",
        ready=True,
        scope_count=len({(record.pair, record.engine_id) for record in scoped_records}),
        scored_scope_count=len(scope_scores),
        executed_record_count=len(executed_records),
        trained_record_count=model.trained_record_count,
        loss_count=len(loss_records),
        non_loss_count=len(non_loss_records),
        highest_risk_scope_slug=highest_scope.scope_slug,
        highest_risk_probability=highest_scope.top_risk_probability,
        model=model,
        scopes=scope_scores,
        record_scores=record_scores,
    )


def _filter_records(
    records: tuple[DTRRecord, ...],
    *,
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    selected_pair: str | None,
    selected_engine_id: str | None,
) -> tuple[DTRRecord, ...]:
    if scope_matrix is not None and scope_matrix.scopes:
        allowed = {(row.pair, row.engine_id) for row in scope_matrix.scopes}
        return tuple(record for record in records if (record.pair, record.engine_id) in allowed)
    filtered = records
    if selected_pair is not None:
        filtered = tuple(record for record in filtered if record.pair == selected_pair)
    if selected_engine_id is not None:
        filtered = tuple(record for record in filtered if record.engine_id == selected_engine_id)
    return filtered


def _fit_model(
    records: tuple[DTRRecord, ...],
    *,
    loss_records: tuple[DTRRecord, ...],
    non_loss_records: tuple[DTRRecord, ...],
) -> LocalLabLossSurrogateModel:
    feature_vectors = tuple(_feature_vector(record) for record in records)
    means = tuple(sum(values[index] for values in feature_vectors) / len(feature_vectors) for index in range(len(_FEATURE_NAMES)))
    scales = []
    for index in range(len(_FEATURE_NAMES)):
        variance = sum((values[index] - means[index]) ** 2 for values in feature_vectors) / len(feature_vectors)
        scale = math.sqrt(variance)
        scales.append(scale if scale > 1e-9 else 1.0)
    scales_tuple = tuple(scales)

    normalized_loss = tuple(_normalize(_feature_vector(record), means, scales_tuple) for record in loss_records)
    normalized_non_loss = tuple(_normalize(_feature_vector(record), means, scales_tuple) for record in non_loss_records)
    positive_mean = tuple(
        sum(values[index] for values in normalized_loss) / len(normalized_loss)
        for index in range(len(_FEATURE_NAMES))
    )
    negative_mean = tuple(
        sum(values[index] for values in normalized_non_loss) / len(normalized_non_loss)
        for index in range(len(_FEATURE_NAMES))
    )
    coefficients = tuple(
        round(positive_mean[index] - negative_mean[index], 6)
        for index in range(len(_FEATURE_NAMES))
    )
    intercept = round(
        -0.5
        * sum(
            coefficients[index] * (positive_mean[index] + negative_mean[index])
            for index in range(len(_FEATURE_NAMES))
        ),
        6,
    )
    return LocalLabLossSurrogateModel(
        feature_means=tuple(round(value, 6) for value in means),
        feature_scales=tuple(round(value, 6) for value in scales_tuple),
        coefficients=coefficients,
        intercept=intercept,
        trained_record_count=len(records),
        positive_loss_count=len(loss_records),
        negative_non_loss_count=len(non_loss_records),
    )


def _build_untrained_report(
    *,
    correlation_id: str,
    export_dir: str,
    status: str,
    scoped_records: tuple[DTRRecord, ...],
    executed_records: tuple[DTRRecord, ...],
    loss_records: tuple[DTRRecord, ...],
    non_loss_records: tuple[DTRRecord, ...],
) -> LocalLabLossSurrogateReport:
    scope_scores = _build_scope_scores(scoped_records=scoped_records, record_scores=())
    return LocalLabLossSurrogateReport(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status=status,
        ready=False,
        scope_count=len({(record.pair, record.engine_id) for record in scoped_records}),
        scored_scope_count=0,
        executed_record_count=len(executed_records),
        trained_record_count=len(executed_records),
        loss_count=len(loss_records),
        non_loss_count=len(non_loss_records),
        scopes=scope_scores,
        record_scores=(),
    )


def _build_scope_scores(
    *,
    scoped_records: tuple[DTRRecord, ...],
    record_scores: tuple[LocalLabLossSurrogateRecordScore, ...],
) -> tuple[LocalLabLossSurrogateScopeScore, ...]:
    by_scope: dict[tuple[str, str], list[DTRRecord]] = {}
    for record in scoped_records:
        by_scope.setdefault((record.pair, record.engine_id), []).append(record)
    scores_by_scope: dict[tuple[str, str], list[LocalLabLossSurrogateRecordScore]] = {}
    for record_score in record_scores:
        scores_by_scope.setdefault((record_score.pair, record_score.engine_id), []).append(record_score)

    scope_scores: list[LocalLabLossSurrogateScopeScore] = []
    for (pair, engine_id), scope_records in sorted(by_scope.items()):
        executed_records = [record for record in scope_records if record.decision_state == DecisionState.EXECUTED]
        loss_count = sum(1 for record in executed_records if _is_loss(record))
        scored = scores_by_scope.get((pair, engine_id), [])
        top_score = max(scored, key=lambda item: item.predicted_loss_probability) if scored else None
        mean_probability = None
        if scored:
            mean_probability = round(
                sum(item.predicted_loss_probability for item in scored) / len(scored),
                6,
            )
        scope_scores.append(
            LocalLabLossSurrogateScopeScore(
                pair=pair,
                engine_id=engine_id,
                scope_slug=build_local_lab_scope_slug(pair, engine_id),
                executed_record_count=len(executed_records),
                loss_count=loss_count,
                actual_loss_rate=_ratio(loss_count, len(executed_records)),
                mean_predicted_loss_probability=mean_probability,
                top_risk_dtr_id="" if top_score is None else top_score.dtr_id,
                top_risk_probability=0.0 if top_score is None else top_score.predicted_loss_probability,
                risk_band=_risk_band(0.0 if top_score is None else top_score.predicted_loss_probability),
            )
        )
    return tuple(scope_scores)


def _score_record(
    record: DTRRecord,
    *,
    model: LocalLabLossSurrogateModel,
) -> LocalLabLossSurrogateRecordScore:
    feature_vector = _feature_vector(record)
    normalized = _normalize(feature_vector, model.feature_means, model.feature_scales)
    margin = sum(
        model.coefficients[index] * normalized[index]
        for index in range(len(model.feature_names))
    ) + model.intercept
    probability = _sigmoid(margin)
    return LocalLabLossSurrogateRecordScore(
        dtr_id=record.dtr_id,
        pair=record.pair,
        engine_id=record.engine_id,
        scope_slug=build_local_lab_scope_slug(record.pair, record.engine_id),
        predicted_loss_probability=round(probability, 6),
        score_margin=round(margin, 6),
        actual_loss=_is_loss(record),
        net_return_after_cost=round(_net_return_after_cost(record), 6),
    )


def _feature_vector(record: DTRRecord) -> tuple[float, ...]:
    return (
        float(record.raw_score),
        float(record.penalized_score),
        float(record.final_score),
        float(record.expected_cost),
        float(record.ce_expected),
        float(record.candidate_size),
        float(record.final_size),
        float(record.ranking_position),
    )


def _normalize(values: tuple[float, ...], means: tuple[float, ...], scales: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(
        (values[index] - means[index]) / scales[index]
        for index in range(len(values))
    )


def _is_loss(record: DTRRecord) -> bool:
    return _net_return_after_cost(record) <= 0.0


def _net_return_after_cost(record: DTRRecord) -> float:
    return float(record.gross_return - record.realized_cost)


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        exp_term = math.exp(-value)
        return 1.0 / (1.0 + exp_term)
    exp_term = math.exp(value)
    return exp_term / (1.0 + exp_term)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(min(max(numerator / denominator, 0.0), 1.0), 6)


def _risk_band(probability: float) -> str:
    if probability >= 0.70:
        return "high_risk"
    if probability >= 0.45:
        return "elevated_risk"
    if probability > 0.0:
        return "low_risk"
    return "not_scored"


__all__ = [
    "LocalLabLossSurrogateModel",
    "LocalLabLossSurrogateRecordScore",
    "LocalLabLossSurrogateReport",
    "LocalLabLossSurrogateScopeScore",
    "build_local_lab_loss_surrogate_report",
]
