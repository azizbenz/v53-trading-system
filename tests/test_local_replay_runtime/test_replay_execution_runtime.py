"""Tests for the LOCAL_REPLAY execution-realism seam."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import yaml

from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeGateConfig
from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ReplayExecutionEvaluationRequest,
    ReplayExecutionProviderKind,
    ShadowExecutionSimulatorConfig,
    build_edge_gate_calibration_artifact,
    build_replay_parity_diagnostics,
    calibrate_edge_gate_thresholds,
    evaluate_replay_execution,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-execution-seam-1",
        source_path="inmemory://execution-seam",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.91,
                penalized_score=0.88,
                final_score=0.84,
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.84,
                production_expected_cost=0.00063,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=20.0,
                feature_values={"spread_bps": 3.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                raw_score=0.78,
                penalized_score=0.72,
                final_score=0.68,
                expected_edge_bps=10.0,
                spread_bps=4.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.4,
                target_decision_state="executed",
                production_decision_state="reduced",
                production_final_score=0.68,
                production_expected_cost=0.00073,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=11.0,
                feature_values={"spread_bps": 4.0},
            ),
        ),
    )


def _rich_execution_dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-execution-seam-rich",
        source_path="inmemory://execution-seam-rich",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-rich-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                close_price=100.0,
                raw_score=0.9,
                penalized_score=0.88,
                final_score=0.86,
                expected_edge_bps=24.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.5,
                side="buy",
                maker_fee_rate=0.0002,
                taker_fee_rate=0.0010,
                tick_size=0.01,
                step_size=0.001,
                min_notional=10.0,
                mid_price=100.0,
                post_fill_mid_price=99.0,
                fill_prices=(100.25,),
                fill_quantities=(5.0,),
                target_decision_state="executed",
                production_decision_state="reduced",
                candidate_size=1_000.0,
                final_size=1_000.0,
                gross_return_bps=14.0,
                feature_values={"spread_bps": 3.0},
            ),
        ),
    )


def _write_execution_runtime_projection(
    path: Path,
    *,
    spread_ceiling_bps: float = 24.0,
    slippage_intercept_bps: float = 2.0,
    slippage_sqrt_coefficient: float = 8.0,
) -> None:
    path.write_text(
        json.dumps(
            {
                "correlation_id": "corr-exec-runtime",
                "export_dir": "build/local_lab",
                "run_id": "local-lab-run-1",
                "projection_status": "ready",
                "projection_ready": True,
                "execution_review_status": "ready",
                "execution_review_ready": True,
                "consumer_count": 3,
                "ready_consumer_count": 3,
                "partial_consumer_count": 0,
                "blocked_consumer_count": 0,
                "blocking_reasons": [],
                "caution_flags": ["THR-X05_ACCEPTED_EVENTS_ONLY"],
                "consumers": [
                    {
                        "consumer_id": "rate_limiter",
                        "consumer_interface": "quota_ratio_ceiling",
                        "threshold_id": "THR-X03",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "quota_ratio_ceiling_v1",
                        "unit": "quota_ratio",
                        "projection_value": 0.8,
                        "projection_value_semantics": "max_observed_quota_ratio_before_throttle",
                        "hard_cap_human": 0.8,
                        "hard_cap_binding": False,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                    {
                        "consumer_id": "spread_guard",
                        "consumer_interface": "spread_bps_ceiling",
                        "threshold_id": "THR-X04",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "lognormal_mu_plus_2sigma_capped",
                        "unit": "bps",
                        "projection_value": spread_ceiling_bps,
                        "projection_value_semantics": "max_observed_spread_bps_before_no_trade",
                        "hard_cap_human": 50.0,
                        "hard_cap_binding": False,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                    {
                        "consumer_id": "slippage_model",
                        "consumer_interface": "sqrt_size_slippage_predictor",
                        "threshold_id": "THR-X05",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "size_slippage_huber_v1",
                        "unit": "bps",
                        "projection_value": 18.0,
                        "projection_value_semantics": "reference_slippage_bps_at_q95_size",
                        "reference_size": 4.0,
                        "size_proxy": "final_size",
                        "intercept_bps": slippage_intercept_bps,
                        "sqrt_size_coefficient": slippage_sqrt_coefficient,
                        "r_squared": 0.55,
                        "mean_absolute_error_bps": 1.5,
                        "blocking_reasons": [],
                        "caution_flags": ["THR-X05_ACCEPTED_EVENTS_ONLY"],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_fee_aware_edge_gate_calibration(root: Path) -> None:
    records = (
        build_dtr(
            dtr_id="edge-gate-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0008,
            gross_return=0.0038,
            ce_expected=0.0028,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="edge-gate-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0009,
            gross_return=0.0041,
            ce_expected=0.0030,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="edge-gate-3",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0012,
            realized_cost=0.0010,
            gross_return=0.0040,
            ce_expected=0.0028,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="edge-gate-4",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0013,
            realized_cost=0.0011,
            gross_return=0.0047,
            ce_expected=0.0034,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
        build_dtr(
            dtr_id="edge-gate-5",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0014,
            realized_cost=0.0012,
            gross_return=0.0048,
            ce_expected=0.0034,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_240.0,
        ),
        build_dtr(
            dtr_id="edge-gate-6",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0015,
            realized_cost=0.0013,
            gross_return=0.0050,
            ce_expected=0.0035,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_300.0,
        ),
    )
    report = calibrate_edge_gate_thresholds(
        records,
        config=EdgeGateCalibrationConfig(
            min_positive_trades=5,
            min_cost_observations=6,
            bootstrap_samples=250,
            rng_seed=7,
        ),
        generated_at=datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc),
    )
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by="operator.aziz",
        config=EdgeGateCalibrationConfig(
            min_positive_trades=5,
            min_cost_observations=6,
            bootstrap_samples=250,
            rng_seed=7,
        ),
        signed_at=datetime(2026, 4, 10, 13, 5, tzinfo=timezone.utc),
    )
    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "edge_gate.yml").write_text(
        yaml.safe_dump(artifact.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


def test_evaluate_replay_execution_uses_typed_shadow_provider() -> None:
    result = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=_dataset(),
            execution_label="research_fast_mode",
        )
    )

    assert result.request.execution_label == "research_fast_mode"
    assert result.request.provider.provider_kind == ReplayExecutionProviderKind.SHADOW_SIMULATOR
    assert len(result.dtr_records) == 2
    assert result.parity_diagnostics.parity_status == "ok"
    assert result.parity_diagnostics_payload["fill_model_version"] == "shadow_execution_simulator.v1"


def test_build_replay_parity_diagnostics_accepts_precomputed_dtrs() -> None:
    dataset = _dataset()
    result = evaluate_replay_execution(ReplayExecutionEvaluationRequest(dataset=dataset))

    diagnostics = build_replay_parity_diagnostics(dataset, result.dtr_records)

    assert diagnostics.parity_status == result.parity_diagnostics.parity_status
    assert diagnostics.decision_match_rate == result.parity_diagnostics.decision_match_rate
    assert diagnostics.fill_realism_status == "FILL_REALISM_MODEL_ONLY"
    assert diagnostics.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
    assert diagnostics.slippage_model_source == "REPLAY_PROXY"
    assert "PARTIAL_FILL_MODEL_PROXY" in diagnostics.execution_fidelity_gap_codes
    assert diagnostics.order_type_selection_source == "CANONICAL_ORDER_DECIDER"


def test_evaluate_replay_execution_loads_projection_models_from_path(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "local_lab_execution_runtime_projection.json"
    _write_execution_runtime_projection(projection_path)

    result = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=_dataset(),
            execution_runtime_projection_path=str(projection_path),
        )
    )

    payload = result.parity_diagnostics_payload

    assert payload["canonical_execution_backbone_status"] == (
        "CANONICAL_EXECUTION_BACKBONE_PARTIAL"
    )
    assert payload["execution_label_source"] == "PARTIAL_CANONICAL_EXECUTION"
    assert payload["fee_model_source"] == "REPLAY_PROXY"
    assert payload["spread_model_source"] == "CANONICAL_SPREAD_GUARD"
    assert payload["slippage_model_source"] == "CANONICAL_EXECUTION_BACKBONE"
    assert payload["partial_fill_model_source"] == "REPLAY_PROXY"
    assert payload["venue_constraints_source"] == "REPLAY_PROXY"
    assert "FEE_MODEL_PROXY" in payload["execution_fidelity_gap_codes"]
    assert payload["spread_guard_model_loaded"] is True
    assert payload["slippage_model_loaded"] is True
    assert payload["execution_runtime_projection_ref"] == str(projection_path)
    assert "canonical_spread_guard" in payload["replay_cost_components"]
    assert "canonical_slippage_model" in payload["replay_cost_components"]
    assert "spread_guard_threshold" in payload["canonical_expected_cost_components"]


def test_evaluate_replay_execution_can_activate_remaining_canonical_cost_components(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "local_lab_execution_runtime_projection.json"
    _write_execution_runtime_projection(projection_path)

    result = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=_rich_execution_dataset(),
            execution_runtime_projection_path=str(projection_path),
        )
    )

    payload = result.parity_diagnostics_payload

    assert payload["execution_label_source"] == "PARTIAL_CANONICAL_EXECUTION"
    assert payload["fee_model_source"] == "CANONICAL_EXECUTION_COST_METER"
    assert payload["spread_model_source"] == "CANONICAL_SPREAD_GUARD"
    assert payload["slippage_model_source"] == "CANONICAL_EXECUTION_BACKBONE"
    assert payload["partial_fill_model_source"] == "CANONICAL_PARTIAL_FILL_COST_METER"
    assert payload["adverse_selection_source"] == "CANONICAL_ADVERSE_SELECTION_METER"
    assert payload["order_type_selection_source"] == "CANONICAL_ORDER_DECIDER"
    assert payload["venue_constraints_source"] == "CANONICAL_VENUE_CONSTRAINT_SNAPSHOT"
    assert payload["execution_fidelity_gap_codes"] == []


def test_evaluate_replay_execution_projection_can_raise_expected_cost(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "local_lab_execution_runtime_projection.json"
    _write_execution_runtime_projection(
        projection_path,
        spread_ceiling_bps=50.0,
        slippage_intercept_bps=5.0,
        slippage_sqrt_coefficient=6.0,
    )

    baseline = evaluate_replay_execution(ReplayExecutionEvaluationRequest(dataset=_dataset()))
    projected = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=_dataset(),
            execution_runtime_projection_path=str(projection_path),
        )
    )

    assert projected.dtr_records[0].expected_cost > baseline.dtr_records[0].expected_cost
    assert projected.dtr_records[0].expected_cost == 0.0015


def test_evaluate_replay_execution_projection_spread_guard_can_block_rows(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "local_lab_execution_runtime_projection.json"
    _write_execution_runtime_projection(
        projection_path,
        spread_ceiling_bps=3.5,
    )

    result = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=_dataset(),
            execution_runtime_projection_path=str(projection_path),
        )
    )

    blocked = result.dtr_records[1]

    assert blocked.decision_state == "hard_blocked"
    assert blocked.hard_blocked is True
    assert blocked.hard_block_reasons == ("SPREAD_GUARD_THRESHOLD_EXCEEDED",)
    assert "SPREAD_GUARD_THRESHOLD_EXCEEDED" in blocked.cause_chain


def test_evaluate_replay_execution_can_apply_fee_aware_edge_gate(
    tmp_path: Path,
) -> None:
    _write_fee_aware_edge_gate_calibration(tmp_path)

    result = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=_dataset(),
            simulator_config=ShadowExecutionSimulatorConfig(
                fee_aware_edge_gate_config=FeeAwareEdgeGateConfig(
                    calibration_root=tmp_path
                )
            ),
        )
    )

    assert result.dtr_records[0].decision_state == "phantom"
    assert result.dtr_records[0].primary_reason == "EDGE_INSUFFICIENT_VS_FEES"
