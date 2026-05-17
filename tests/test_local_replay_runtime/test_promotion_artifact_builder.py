from __future__ import annotations

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    ReplayBookDepthAvailability,
    ReplayCostParityEvidence,
    ReplayFeeProvenance,
    ReplayFillRealismEvidence,
    ReplayImpactProvenance,
    ReplayRunManifest,
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    build_replay_metrics_summary,
    build_replay_promotion_artifact_bundle,
    build_sample_size_survival_artifact,
)
from local_replay_runtime.promotion_artifact_builder import SampleSizeSurvivalBuildInput
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _manifest(*, run_id: str = "run-promotion-1", engines: tuple[str, ...] = ("engine_a",), pairs: tuple[str, ...] = ("BTCUSDT",)) -> ReplayRunManifest:
    return ReplayRunManifest(
        run_id=run_id,
        strategy_id="strategy-promotion-a",
        strategy_version="a.v5.0",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v5.0.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=engines,
        tested_pairs=pairs,
        dataset_manifest_id="dataset-promotion-1",
        timeframe_scope="2026-03-01/2026-03-31",
        feature_set_version="5.0.0",
        transform_set_version="5.0.0",
        formula_set_version="formula.v5",
        scoring_version="score.v5",
        regime_version="regime.v5",
        risk_policy_version="risk.v5",
        cost_model_version="cost.v5",
        performance_mode="research_fast_mode",
        artifact_schema_version="5.0.0",
        artifact_hash="artifact-promotion-1",
        clock_id="clock-promotion-1",
        start_timestamp_ms=1_700_000_000_000,
        end_timestamp_ms=1_700_259_200_000,
        tick_count=1024,
        record_count=1,
    )


def test_build_sample_size_survival_artifact_marks_collapse_after_filters() -> None:
    artifact = build_sample_size_survival_artifact(
        SampleSizeSurvivalBuildInput(
            run_id="run-collapse-1",
            scope="engine",
            scope_id="engine_c",
            raw_candidate_count=20,
            after_hard_filters_count=12,
            after_cost_filters_count=0,
            after_risk_filters_count=0,
            selected_count=0,
            executed_count=0,
            reduced_count=0,
            no_fill_count=0,
            sample_days=30,
        )
    )

    assert artifact.sample_size_survival_status == "SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS"
    assert "SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS" in artifact.sample_size_blockers


def test_build_replay_promotion_artifact_bundle_keeps_cd_local_fields_local() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-c-1",
            pair="BTCUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0030,
            ce_expected=0.0007,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-d-1",
            pair="ETHUSDT",
            engine_id="engine_d",
            decision_state=DecisionState.REJECTED_RANKING,
            expected_cost=0.0011,
            realized_cost=0.0,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )
    summary = build_replay_metrics_summary(records, total_opportunities=2)
    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(engines=("engine_c", "engine_d"), pairs=("BTCUSDT", "ETHUSDT")),
        metrics_summary=summary,
        dtr_records=records,
    )

    artifacts = {item.engine_id: item for item in bundle.engine_promotion_artifacts}
    engine_c = artifacts["engine_c"]
    engine_d = artifacts["engine_d"]

    assert engine_c.shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert engine_d.shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert engine_c.engine_c is not None
    assert engine_c.engine_d is None
    assert engine_d.engine_d is not None
    assert engine_d.engine_c is None
    assert engine_c.engine_c.breakout_confirmation_score_status == "NOT_PROVEN"
    assert engine_d.engine_d.reentry_age_status == "NOT_PROVEN"
    assert "execution_fragility" not in engine_c.model_dump(mode="json")
    assert engine_c.promotion_status != "ENGINE_PROMOTION_READY"
    assert engine_d.promotion_status != "ENGINE_PROMOTION_READY"


def test_engine_promotion_cannot_be_ready_from_expected_ce_alone() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0030,
            ce_expected=0.0008,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )
    summary = build_replay_metrics_summary(records, total_opportunities=1, initial_capital=400.0)
    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(),
        metrics_summary=summary,
        dtr_records=records,
        min_required_candidates=1,
        min_required_executions=1,
        min_required_days=1,
    )
    artifact = bundle.engine_promotion_artifacts[0]

    assert artifact.expected_ce_net is not None
    assert artifact.executed_only_net_return_status == "EXECUTED_NET_RETURN_NOT_PROVEN"
    assert artifact.promotion_status == "ENGINE_PROMOTION_BLOCKED_BY_COST_COMPLETENESS"
    assert "PROMOTION_BLOCKED_BY_COST_COMPLETENESS" in artifact.promotion_blockers


def test_pair_promotion_blocks_when_true_drawdown_is_not_proven_even_if_costs_are_complete() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-a-drawdown",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0030,
            ce_expected=0.0008,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )
    summary = build_replay_metrics_summary(
        records,
        total_opportunities=1,
        fee_provenance=ReplayFeeProvenance(fee_source_status="FEE_SOURCE_PROVEN"),
        impact_provenance=ReplayImpactProvenance(
            impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
            impact_depth_level=20,
        ),
        book_depth_availability=ReplayBookDepthAvailability(
            book_depth_levels=20,
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_level_used=20,
        ),
        fill_realism=ReplayFillRealismEvidence(
            fill_realism_status="FILL_REALISM_PROVEN",
            fill_source_status="FILL_SOURCE_SHADOW_TELEMETRY",
            measured_fill_flag=True,
        ),
        cost_parity=ReplayCostParityEvidence(
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            live_cost_components=("fee_bps",),
            parity_sample_count=10,
        ),
    )
    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(),
        metrics_summary=summary,
        dtr_records=records,
        min_required_candidates=1,
        min_required_executions=1,
        min_required_days=1,
    )
    pair_artifact = bundle.pair_promotion_artifacts[0]

    assert pair_artifact.executed_only_net_return_status == "EXECUTED_NET_RETURN_PROVEN"
    assert pair_artifact.true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"
    assert pair_artifact.promotion_status == "PAIR_BLOCKED_DRAWDOWN"


def test_strategy_promotion_blocks_on_sample_size_and_hashes_are_deterministic() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-a-sample",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0030,
            ce_expected=0.0008,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )
    summary = build_replay_metrics_summary(
        records,
        total_opportunities=1,
        initial_capital=400.0,
        fee_provenance=ReplayFeeProvenance(fee_source_status="FEE_SOURCE_PROVEN"),
        impact_provenance=ReplayImpactProvenance(
            impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
            impact_depth_level=20,
        ),
        book_depth_availability=ReplayBookDepthAvailability(
            book_depth_levels=20,
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_level_used=20,
        ),
        fill_realism=ReplayFillRealismEvidence(
            fill_realism_status="FILL_REALISM_PROVEN",
            fill_source_status="FILL_SOURCE_SHADOW_TELEMETRY",
            measured_fill_flag=True,
        ),
        cost_parity=ReplayCostParityEvidence(
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            live_cost_components=("fee_bps",),
            parity_sample_count=10,
        ),
    )
    bundle_a = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(run_id="run-promotion-hash-1"),
        metrics_summary=summary,
        dtr_records=records,
        min_required_candidates=10,
        min_required_executions=5,
        min_required_days=30,
    )
    bundle_b = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(run_id="run-promotion-hash-1"),
        metrics_summary=summary,
        dtr_records=records,
        min_required_candidates=10,
        min_required_executions=5,
        min_required_days=30,
    )

    strategy_a = bundle_a.strategy_promotion_artifacts[0]
    strategy_b = bundle_b.strategy_promotion_artifacts[0]

    assert strategy_a.promotion_status == "STRATEGY_PROMOTION_BLOCKED_BY_SAMPLE_SIZE"
    assert strategy_a.artifact_hash == strategy_b.artifact_hash
    assert strategy_a.true_net_equity_max_drawdown is not None
    assert strategy_a.executed_only_net_return_status == "EXECUTED_NET_RETURN_PROVEN"


def test_promotion_artifacts_carry_execution_fidelity_sources() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-a-fidelity",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0030,
            ce_expected=0.0008,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )
    summary = build_replay_metrics_summary(
        records,
        total_opportunities=1,
        cost_parity=ReplayCostParityEvidence(
            cost_parity_status="REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
            execution_label_source="PARTIAL_CANONICAL_EXECUTION",
            fee_model_source="CANONICAL_EXECUTION_COST_METER",
            spread_model_source="CANONICAL_SPREAD_GUARD",
            slippage_model_source="CANONICAL_EXECUTION_BACKBONE",
            partial_fill_model_source="CANONICAL_PARTIAL_FILL_COST_METER",
            adverse_selection_source="REPLAY_PROXY",
            order_type_selection_source="CANONICAL_ORDER_DECIDER",
            venue_constraints_source="CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
            execution_fidelity_gap_codes=("ADVERSE_SELECTION_PROXY",),
        ),
    )
    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(),
        metrics_summary=summary,
        dtr_records=records,
    )

    engine_artifact = bundle.engine_promotion_artifacts[0]
    strategy_artifact = bundle.strategy_promotion_artifacts[0]

    assert engine_artifact.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
    assert engine_artifact.fee_model_source == "CANONICAL_EXECUTION_COST_METER"
    assert engine_artifact.order_type_selection_source == "CANONICAL_ORDER_DECIDER"
    assert engine_artifact.execution_fidelity_gap_codes == ("ADVERSE_SELECTION_PROXY",)
    assert engine_artifact.promotion_status == "ENGINE_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY"
    assert "ADVERSE_SELECTION_PROXY" in engine_artifact.promotion_blockers
    assert strategy_artifact.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
    assert strategy_artifact.venue_constraints_source == "CANONICAL_VENUE_CONSTRAINT_SNAPSHOT"
    assert strategy_artifact.promotion_status == "STRATEGY_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY"


def test_promotion_artifacts_can_be_ready_when_execution_fidelity_gaps_clear() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-a-fidelity-ready",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0030,
            ce_expected=0.0008,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )
    summary = build_replay_metrics_summary(
        records,
        total_opportunities=1,
        initial_capital=400.0,
        fee_provenance=ReplayFeeProvenance(fee_source_status="FEE_SOURCE_PROVEN"),
        impact_provenance=ReplayImpactProvenance(
            impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
            impact_depth_level=20,
        ),
        book_depth_availability=ReplayBookDepthAvailability(
            book_depth_levels=20,
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_level_used=20,
        ),
        fill_realism=ReplayFillRealismEvidence(
            fill_realism_status="FILL_REALISM_PROVEN",
            fill_source_status="FILL_SOURCE_SHADOW_TELEMETRY",
            measured_fill_flag=True,
        ),
        cost_parity=ReplayCostParityEvidence(
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            execution_label_source="PARTIAL_CANONICAL_EXECUTION",
            fee_model_source="CANONICAL_EXECUTION_COST_METER",
            spread_model_source="CANONICAL_SPREAD_GUARD",
            slippage_model_source="CANONICAL_EXECUTION_BACKBONE",
            partial_fill_model_source="CANONICAL_PARTIAL_FILL_COST_METER",
            adverse_selection_source="CANONICAL_ADVERSE_SELECTION_METER",
            order_type_selection_source="CANONICAL_ORDER_DECIDER",
            venue_constraints_source="CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
            execution_fidelity_gap_codes=(),
            live_cost_components=("fee_bps",),
            parity_sample_count=10,
        ),
    )
    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(),
        metrics_summary=summary,
        dtr_records=records,
        min_required_candidates=1,
        min_required_executions=1,
        min_required_days=1,
    )

    engine_artifact = bundle.engine_promotion_artifacts[0]
    assert engine_artifact.promotion_status == "ENGINE_PROMOTION_READY"
    assert "ENGINE_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY" not in engine_artifact.promotion_blockers


def test_promotion_artifacts_distinguish_candidate_counts_from_replay_records() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-count-1-b400",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-count-1-b1500",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-count-2-b400",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-count-2-b1500",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )
    bucket_results = (
        StrategyLadderBucketReplayResult(
            candidate_id="cand-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=400,
            timestamp_ms=1_700_000_000_000,
            execution_state="phantom",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="cand-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=1500,
            timestamp_ms=1_700_000_000_000,
            execution_state="phantom",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="cand-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=400,
            timestamp_ms=1_700_000_060_000,
            execution_state="phantom",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="cand-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=1500,
            timestamp_ms=1_700_000_060_000,
            execution_state="phantom",
        ),
    )
    summary = build_replay_metrics_summary(
        records,
        total_opportunities=2,
    )

    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(run_id="run-count-semantics"),
        metrics_summary=summary,
        dtr_records=records,
        bucket_results=bucket_results,
        min_required_candidates=10,
        min_required_executions=5,
        min_required_days=30,
    )

    engine_artifact = bundle.engine_promotion_artifacts[0]
    pair_artifact = bundle.pair_promotion_artifacts[0]
    strategy_artifact = bundle.strategy_promotion_artifacts[0]

    assert engine_artifact.candidate_count == 2
    assert engine_artifact.engine_evaluation_count == 4
    assert engine_artifact.evaluation_record_count == 4
    assert engine_artifact.replay_expansion_factor == 2.0
    assert engine_artifact.replay_expansion_axis == "capital_bucket"
    assert pair_artifact.candidate_count == 2
    assert pair_artifact.record_count == 4
    assert pair_artifact.evaluation_record_count == 4
    assert pair_artifact.replay_expansion_factor == 2.0
    assert pair_artifact.replay_expansion_axis == "capital_bucket"
    assert strategy_artifact.candidate_count == 2
    assert strategy_artifact.evaluation_record_count == 4


def test_promotion_artifacts_use_candidate_event_identity_not_candidate_id_only() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-shared-1-b400",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-shared-1-b1500",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-shared-2-b400",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-shared-2-b1500",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )
    bucket_results = (
        StrategyLadderBucketReplayResult(
            candidate_id="cand-shared",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=400,
            timestamp_ms=1_700_000_000_000,
            execution_state="phantom",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="cand-shared",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=1500,
            timestamp_ms=1_700_000_000_000,
            execution_state="phantom",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="cand-shared",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=400,
            timestamp_ms=1_700_000_060_000,
            execution_state="phantom",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="cand-shared",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            capital_bucket=1500,
            timestamp_ms=1_700_000_060_000,
            execution_state="phantom",
        ),
    )
    candidate_events = (
        StrategyLadderCandidateEvent(
            run_id="run-candidate-identity",
            candidate_id="cand-shared",
            timestamp_ms=1_700_000_000_000,
            pair="BTCUSDT",
            timeframe="1m",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            candidate_source="COMPAT_FEATURE_DISCOVERY",
        ),
        StrategyLadderCandidateEvent(
            run_id="run-candidate-identity",
            candidate_id="cand-shared",
            timestamp_ms=1_700_000_060_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="strategy-promotion-a",
            candidate_source="COMPAT_FEATURE_DISCOVERY",
        ),
    )
    summary = build_replay_metrics_summary(
        records,
        total_opportunities=2,
    )

    bundle = build_replay_promotion_artifact_bundle(
        run_manifest=_manifest(run_id="run-candidate-identity"),
        metrics_summary=summary,
        dtr_records=records,
        bucket_results=bucket_results,
        candidate_events=candidate_events,
        min_required_candidates=10,
        min_required_executions=5,
        min_required_days=30,
    )

    pair_artifact = bundle.pair_promotion_artifacts[0]
    engine_artifact = bundle.engine_promotion_artifacts[0]

    assert pair_artifact.candidate_count == 2
    assert pair_artifact.record_count == 4
    assert pair_artifact.replay_expansion_factor == 2.0
    assert engine_artifact.candidate_count == 2
    assert engine_artifact.engine_evaluation_count == 4
