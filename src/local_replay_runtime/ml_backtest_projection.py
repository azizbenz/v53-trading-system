"""Projection from governed replay/backtest rows into ML backtest contracts."""

from __future__ import annotations

from interface_contracts import (
    ML_BACKTEST_REALIZED_TARGET_POLICY,
    ML_BACKTEST_TARGET_POLICY,
    MlBacktestOutcomeContext,
    MlBacktestRouteFeatures,
    MlBacktestTrainingDataset,
    MlBacktestTrainingSample,
    canonical_feature_ids,
)
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


def _normalize_decision_state(value: object) -> str | None:
    if value is None:
        return None
    raw = getattr(value, "value", value)
    text = str(raw).strip()
    return text or None


def _recognized_numeric_feature_values(
    opportunity: HistoricalReplayOpportunity,
    *,
    allowed_feature_keys: tuple[str, ...],
) -> dict[str, float]:
    allowed = set(allowed_feature_keys)
    projected: dict[str, float] = {}
    for key, raw_value in opportunity.feature_values.items():
        if key not in allowed or isinstance(raw_value, str):
            continue
        if isinstance(raw_value, bool):
            projected[key] = 1.0 if raw_value else 0.0
            continue
        if isinstance(raw_value, (int, float)):
            projected[key] = float(raw_value)
    return projected


def project_historical_replay_opportunity_to_ml_sample(
    opportunity: HistoricalReplayOpportunity,
    *,
    dataset_id: str,
    allowed_feature_keys: tuple[str, ...] | None = None,
) -> MlBacktestTrainingSample:
    """Project one replay/backtest opportunity into an audit-ready ML training sample."""

    feature_keys = allowed_feature_keys or tuple(canonical_feature_ids())
    route_features = MlBacktestRouteFeatures(
        raw_score=opportunity.raw_score,
        penalized_score=(
            opportunity.raw_score
            if opportunity.penalized_score is None
            else opportunity.penalized_score
        ),
        final_score=(
            opportunity.raw_score
            if opportunity.final_score is None
            else opportunity.final_score
        ),
        expected_edge_bps=opportunity.expected_edge_bps,
        spread_bps=opportunity.spread_bps,
        slippage_bps=opportunity.slippage_bps,
        latency_penalty_bps=opportunity.latency_penalty_bps,
        fill_ratio=opportunity.fill_ratio,
        ranking_position=opportunity.ranking_position,
        candidate_size=opportunity.candidate_size,
        final_size=opportunity.final_size,
    )
    outcome = MlBacktestOutcomeContext(
        gross_return_bps=opportunity.gross_return_bps,
        projected_net_return_bps=opportunity.gross_return_bps - route_features.route_cost_bps_total,
        target_decision_state=_normalize_decision_state(opportunity.target_decision_state),
        production_decision_state=_normalize_decision_state(opportunity.production_decision_state),
        production_final_score=opportunity.production_final_score,
        production_expected_cost=opportunity.production_expected_cost,
        primary_reason=opportunity.primary_reason,
        hard_block_reasons=opportunity.hard_block_reasons,
    )
    return MlBacktestTrainingSample(
        dataset_id=dataset_id,
        opportunity_id=opportunity.opportunity_id,
        timestamp_ms=opportunity.timestamp_ms,
        pair=opportunity.pair,
        engine_id=opportunity.engine_id,
        regime=opportunity.regime,
        tier=opportunity.tier,
        shared_core_match=opportunity.shared_core_match,
        target_policy=ML_BACKTEST_TARGET_POLICY,
        recognized_feature_values=_recognized_numeric_feature_values(
            opportunity,
            allowed_feature_keys=feature_keys,
        ),
        route_features=route_features,
        outcome=outcome,
    )

def _replay_dtr_map(
    *,
    dataset_id: str,
    dtr_records: tuple[DTRRecord, ...],
) -> dict[str, DTRRecord]:
    prefix = f"{dataset_id}:"
    projected: dict[str, DTRRecord] = {}
    for record in dtr_records:
        if record.dtr_id.startswith(prefix):
            projected[record.dtr_id[len(prefix) :]] = record
    return projected


def project_historical_replay_opportunity_to_ml_sample_with_replay_dtr(
    opportunity: HistoricalReplayOpportunity,
    *,
    dataset_id: str,
    dtr_record: DTRRecord,
    allowed_feature_keys: tuple[str, ...] | None = None,
) -> MlBacktestTrainingSample:
    """Project one replay opportunity with aligned DTR evidence into an ML sample."""

    base_sample = project_historical_replay_opportunity_to_ml_sample(
        opportunity,
        dataset_id=dataset_id,
        allowed_feature_keys=allowed_feature_keys,
    )
    realized_net_return_bps = (dtr_record.gross_return - dtr_record.realized_cost) * 10_000.0
    outcome = base_sample.outcome.model_copy(
        update={
            "realized_net_return_bps": realized_net_return_bps,
            "replay_decision_state": _normalize_decision_state(dtr_record.decision_state),
            "replay_dtr_id": dtr_record.dtr_id,
            "replay_expected_cost_fraction": dtr_record.expected_cost,
            "replay_realized_cost_fraction": dtr_record.realized_cost,
            "replay_gross_return_fraction": dtr_record.gross_return,
            "replay_ce_expected_fraction": dtr_record.ce_expected,
        }
    )
    return base_sample.model_copy(
        update={
            "target_policy": ML_BACKTEST_REALIZED_TARGET_POLICY,
            "outcome": outcome,
        }
    )


def build_ml_backtest_training_dataset(
    dataset: HistoricalReplayDataset,
    *,
    allowed_feature_keys: tuple[str, ...] | None = None,
) -> MlBacktestTrainingDataset:
    """Build the governed ML backtest-input dataset from historical replay rows."""

    samples = tuple(
        project_historical_replay_opportunity_to_ml_sample(
            opportunity,
            dataset_id=dataset.dataset_id,
            allowed_feature_keys=allowed_feature_keys,
        )
        for opportunity in dataset.rows
    )
    recognized_feature_keys = tuple(
        sorted(
            {
                feature_key
                for sample in samples
                for feature_key in sample.recognized_feature_values
            }
        )
    )
    return MlBacktestTrainingDataset(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        source=dataset.source,
        target_policy=ML_BACKTEST_TARGET_POLICY,
        samples=samples,
        pair_scope=dataset.pair_scope,
        engine_scope=dataset.engine_scope,
        recognized_feature_keys=recognized_feature_keys,
        shared_core_match=dataset.shared_core_match,
    )


def build_ml_backtest_training_dataset_from_replay_and_dtr(
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
    *,
    allowed_feature_keys: tuple[str, ...] | None = None,
) -> MlBacktestTrainingDataset:
    """Build a stricter ML dataset from replay rows aligned with governed DTR evidence."""

    dtr_map = _replay_dtr_map(
        dataset_id=dataset.dataset_id,
        dtr_records=dtr_records,
    )
    samples = tuple(
        project_historical_replay_opportunity_to_ml_sample_with_replay_dtr(
            opportunity,
            dataset_id=dataset.dataset_id,
            dtr_record=dtr_map[opportunity.opportunity_id],
            allowed_feature_keys=allowed_feature_keys,
        )
        for opportunity in dataset.rows
        if opportunity.opportunity_id in dtr_map
    )
    if not samples:
        raise ValueError("No replay DTR records aligned with historical opportunities")
    recognized_feature_keys = tuple(
        sorted(
            {
                feature_key
                for sample in samples
                for feature_key in sample.recognized_feature_values
            }
        )
    )
    return MlBacktestTrainingDataset(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        source=f"{dataset.source}+replay_dtr",
        target_policy=ML_BACKTEST_REALIZED_TARGET_POLICY,
        samples=samples,
        pair_scope=tuple(sorted({sample.pair for sample in samples})),
        engine_scope=tuple(sorted({sample.engine_id for sample in samples})),
        recognized_feature_keys=recognized_feature_keys,
        shared_core_match=all(sample.shared_core_match for sample in samples),
    )


__all__ = [
    "project_historical_replay_opportunity_to_ml_sample",
    "project_historical_replay_opportunity_to_ml_sample_with_replay_dtr",
    "build_ml_backtest_training_dataset",
    "build_ml_backtest_training_dataset_from_replay_and_dtr",
]
