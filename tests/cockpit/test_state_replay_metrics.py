from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import time

from backtest_artifact_import import CapitalProfileBuildInput, build_capital_bucket_profile
from cockpit.state_replay_metrics import ReplayMetricsSnapshot, read_replay_metrics

from ._operational_helpers import cleanup_scratch, scratch_dir


def _ready_profile_kwargs(capital_bucket: int) -> dict[str, object]:
    created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    return {
        "capital_bucket": capital_bucket,
        "pair_universe": ("BTCUSDT",),
        "allowed_pairs": ("BTCUSDT",),
        "max_active_pairs": 1,
        "record_count": 100,
        "min_notional_block_rate": 0.0,
        "capital_fragmentation_rate": 0.1,
        "executed_only_net_return": 0.01,
        "executed_only_net_return_status": "EXECUTED_NET_RETURN_PROVEN",
        "true_net_equity_max_drawdown": 0.05,
        "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        "fee_source_status": "FEE_SOURCE_PROVEN",
        "impact_source_status": "IMPACT_SOURCE_PROVEN",
        "cost_model_completeness_status": "COST_MODEL_COMPLETE",
        "fill_realism_status": "FILL_REALISM_PROVEN",
        "cost_parity_status": "REPLAY_LIVE_COST_PARITY_PROVEN",
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        "sample_size_survival_status": "MEASURED",
        "promotion_status": "CAPITAL_BUCKET_READY",
        "input_data_hash": "a" * 64,
        "method_version_hash": "capital.v1",
        "run_id": f"replay-metrics-{capital_bucket}",
        "strategy_ladder_manifest_ref": f"E:/audit/replay_metrics/{capital_bucket}/run_manifest.json",
        "execution_fidelity_status": "FULL_CANONICAL_EXECUTION",
        "execution_fidelity_gap_codes": (),
        "created_at": created_at,
        "expires_at": created_at + timedelta(days=7),
    }


def test_replay_snapshot_exposes_semantic_labels_and_total_record_exec_rate() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=40,
        executed_count=10,
        ce_net=0.0123,
        gross_return_mean=0.0042,
        drawdown_proxy=0.0011,
    )

    assert replay.expected_ce_label == "Expected CE net"
    assert "not realized profitability" in replay.expected_ce_caveat
    assert replay.expected_ce_realization_status == "EXPECTED_ONLY"
    assert replay.realized_profitability_status == "NOT_REALIZED_PNL"
    assert replay.exec_rate_total == 0.25
    assert replay.exec_rate_label == "Exec rate (executed / total records)"
    assert "selected-only" in replay.exec_rate_caveat
    assert replay.executed_only_net_return_label == "Executed-only net return"
    assert replay.executed_return_display_status == "EXECUTED_RETURN_NOT_PROVEN"
    assert replay.drawdown_proxy_label == "Drawdown proxy"
    assert replay.drawdown_proxy_status == "DRAWDOWN_PROXY_ONLY"
    assert "not promotion-grade" in replay.drawdown_proxy_caveat
    assert replay.economics_display_state == "partial_replay"
    assert replay.ce_net_value_class == "value-warn"
    assert replay.cost_model_completeness_status == "COST_MODEL_NOT_PROVEN"
    assert "Fee source=FEE_SOURCE_NOT_PROVEN" in replay.cost_model_caveat
    assert replay.small_capital_viability_status == "BLOCKED_BY_BACKTEST"
    assert "fail-closed min_notional protection is safety only" in replay.small_capital_caveat
    assert replay.kelly_status == "NOT_IMPLEMENTED_BY_DESIGN_FOR_NOW"
    assert replay.multi_asset_risk_control_status == "BASELINE_CAPS_ONLY"
    assert replay.true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    assert replay.drawdown_proxy_promotion_grade is False
    assert replay.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
    assert "SMALL_CAPITAL_VIABILITY_NOT_PROVEN" in replay.economics_reason_codes
    assert "EXECUTED_RETURN_NOT_PROVEN" in replay.economics_reason_codes
    assert "TRUE_DRAWDOWN_NOT_PROVEN" in replay.economics_reason_codes
    assert "PROMOTION_ECONOMICS_NOT_READY" in replay.economics_reason_codes


def test_replay_snapshot_zero_records_is_placeholder_and_not_green() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=0,
        executed_count=0,
        ce_net=0.0123,
    )

    assert replay.economics_display_state == "placeholder"
    assert replay.allow_positive_economics_tone is False
    assert replay.ce_net_value_class == "value-warn"
    assert "REPLAY_METRICS_NOT_MEASURED" in replay.economics_reason_codes


def test_read_replay_metrics_marks_stale_export_as_stale_not_green() -> None:
    scratch = scratch_dir("replay_metrics_stale")
    try:
        auto_exports = scratch / "auto_exports" / "2026-04-29"
        auto_exports.mkdir(parents=True, exist_ok=True)
        replay_path = auto_exports / "replay_metrics.json"
        replay_path.write_text(
            json.dumps(
                {
                    "total_records": 40,
                    "total_opportunities": 40,
                    "selected_count": 20,
                    "executed_count": 10,
                    "ce_net": 0.12,
                }
            ),
            encoding="utf-8",
        )
        stale_epoch = time.time() - 900.0
        os.utime(replay_path, (stale_epoch, stale_epoch))

        replay = read_replay_metrics(scratch / "auto_exports")

        assert replay.source_status == "stale"
        assert replay.economics_display_state == "stale"
        assert replay.allow_positive_economics_tone is False
        assert replay.ce_net_value_class == "value-warn"
    finally:
        cleanup_scratch(scratch)


def test_replay_snapshot_can_only_green_when_cost_model_is_complete() -> None:
    profiles = (
        build_capital_bucket_profile(
            CapitalProfileBuildInput(
                **_ready_profile_kwargs(400),
            )
        ),
    )
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=40,
        selected_count=20,
        executed_count=10,
        ce_net=0.0123,
        gross_return_mean=0.0042,
        executed_only_net_return=0.0101,
        executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        true_net_equity_max_drawdown=0.021,
        drawdown_proxy=0.0011,
        fee_source_status="FEE_SOURCE_PROVEN",
        impact_source_status="IMPACT_SOURCE_PROVEN",
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        book_depth_levels=20,
        impact_depth_readiness_status="DEPTH20_AVAILABLE",
        shadow_extension_required=False,
        shadow_extension_status="SHADOW_STANDARD_30D",
        cost_model_completeness_status="COST_MODEL_COMPLETE",
        fill_ratio_source="MEASURED",
        fill_realism_status="FILL_REALISM_PROVEN",
        fill_source_status="FILL_SOURCE_SHADOW_TELEMETRY",
        realized_slippage_status="FOLDED_IN_TOTAL_COST",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        replay_live_cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        small_capital_viability_status="MEASURED",
        min_notional_viability_status="MEASURED",
        capital_fragmentation_status="MEASURED",
        multi_asset_risk_control_status="FULLY_PROVEN",
        covariance_model_status="EXPLICIT",
        true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        capital_bucket_profiles=profiles,
    )

    assert replay.economics_display_state == "measured"
    assert replay.allow_positive_economics_tone is True
    assert replay.ce_net_value_class == "value-up"
    assert replay.executed_return_display_status == "PROVEN"
    assert replay.true_drawdown_display_status == "PROVEN"
    assert replay.book_depth_display_status == "DEPTH20_AVAILABLE"
    assert replay.fill_realism_display_status == "FILL_REALISM_PROVEN"
    assert replay.cost_parity_display_status == "REPLAY_LIVE_COST_PARITY_PROVEN"
    assert replay.promotion_economics_status == "PROMOTION_ECONOMICS_READY"


def test_replay_snapshot_keeps_missing_capital_profiles_non_green() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=40,
        selected_count=20,
        executed_count=10,
        ce_net=0.0123,
        gross_return_mean=0.0042,
        executed_only_net_return=0.0101,
        executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        true_net_equity_max_drawdown=0.021,
        true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        fee_source_status="FEE_SOURCE_PROVEN",
        impact_source_status="IMPACT_SOURCE_PROVEN",
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        book_depth_levels=20,
        impact_depth_readiness_status="DEPTH20_AVAILABLE",
        shadow_extension_required=False,
        cost_model_completeness_status="COST_MODEL_COMPLETE",
        fill_ratio_source="MEASURED",
        fill_realism_status="FILL_REALISM_PROVEN",
        fill_source_status="FILL_SOURCE_SHADOW_TELEMETRY",
        realized_slippage_status="FOLDED_IN_TOTAL_COST",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        replay_live_cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        small_capital_viability_status="MEASURED",
        min_notional_viability_status="MEASURED",
        capital_fragmentation_status="MEASURED",
    )

    assert replay.capital_profile_artifact_status == "CAPITAL_BUCKET_NOT_PROVEN"
    assert replay.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
    assert replay.economics_display_state == "partial_replay"
    assert "CAPITAL_BUCKET_NOT_PROVEN" in replay.economics_reason_codes


def test_replay_snapshot_keeps_missing_fee_or_impact_non_green() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=40,
        selected_count=20,
        executed_count=10,
        ce_net=0.0123,
        gross_return_mean=0.0042,
        executed_only_net_return=0.0101,
        executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        true_net_equity_max_drawdown=0.021,
        drawdown_proxy=0.0011,
        fee_source_status="FEE_SOURCE_NOT_PROVEN",
        impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        book_depth_levels=20,
        impact_depth_readiness_status="DEPTH20_AVAILABLE",
        shadow_extension_required=False,
        cost_model_completeness_status="COST_MODEL_PARTIAL_FEE_MISSING",
        fill_ratio_source="MEASURED",
        fill_realism_status="FILL_REALISM_PROVEN",
        realized_slippage_status="FOLDED_IN_TOTAL_COST",
        replay_live_cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
    )

    assert replay.cost_model_is_complete is False
    assert replay.economics_display_state == "partial_replay"
    assert "FEE_SOURCE_NOT_PROVEN" in replay.economics_reason_codes
    assert "COST_MODEL_NOT_PROMOTION_READY" in replay.economics_reason_codes


def test_replay_snapshot_keeps_limited_depth_fill_and_parity_non_green() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=40,
        selected_count=20,
        executed_count=10,
        ce_net=0.0123,
        gross_return_mean=0.0042,
        executed_only_net_return=0.0101,
        executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        true_net_equity_max_drawdown=0.021,
        true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        fee_source_status="FEE_SOURCE_CONFIGURED",
        impact_source_status="IMPACT_SOURCE_LIMITED_DEPTH_MODEL",
        book_depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
        book_depth_levels=10,
        impact_depth_readiness_status="LIMITED_DEPTH_PARTIAL",
        shadow_extension_required=True,
        shadow_extension_status="SHADOW_EXTENDED_45D",
        minimum_shadow_days_required=45,
        cost_model_completeness_status="COST_MODEL_PARTIAL_IMPACT_MISSING",
        fill_ratio_source="REPLAY_MODEL",
        fill_realism_status="FILL_REALISM_MODEL_ONLY",
        fill_source_status="FILL_SOURCE_REPLAY_MODEL",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        replay_live_cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
    )

    assert replay.book_depth_display_status == "LIMITED_DEPTH_PARTIAL"
    assert replay.fill_realism_display_status == "FILL_REALISM_NOT_PROVEN"
    assert replay.cost_parity_display_status == "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    assert replay.shadow_extension_display_status == "SHADOW_EXTENDED_REQUIRED"
    assert replay.cost_model_is_complete is False
    assert replay.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
    assert "LIMITED_DEPTH_PARTIAL" in replay.economics_reason_codes
    assert "SHADOW_EXTENDED_REQUIRED" in replay.economics_reason_codes
    assert "FILL_REALISM_NOT_PROVEN" in replay.economics_reason_codes
    assert "REPLAY_LIVE_COST_PARITY_NOT_PROVEN" in replay.economics_reason_codes


def test_read_replay_metrics_parses_promotion_artifacts_and_keeps_them_non_green() -> None:
    scratch = scratch_dir("replay_metrics_promotion_artifacts")
    try:
        auto_exports = scratch / "auto_exports" / "2026-05-02"
        auto_exports.mkdir(parents=True, exist_ok=True)
        (auto_exports / "replay_metrics.json").write_text(
            json.dumps(
                {
                    "total_records": 10,
                    "selected_count": 5,
                    "executed_count": 2,
                    "ce_net": 0.12,
                    "engine_promotion_artifacts": [
                        {
                            "schema_version": "v1",
                            "run_id": "run-1",
                            "engine_id": "engine_c",
                            "shared_physics_mapping_status": "PARTIAL_BY_DESIGN",
                            "executed_only_net_return_status": "EXECUTED_NET_RETURN_NOT_PROVEN",
                            "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
                            "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
                            "promotion_status": "ENGINE_PROMOTION_NOT_READY",
                            "engine_c": {
                                "breakout_confirmation_score_status": "NOT_PROVEN"
                            },
                        }
                    ],
                    "pair_promotion_artifacts": [
                        {
                            "schema_version": "v1",
                            "run_id": "run-1",
                            "pair": "BTCUSDT",
                            "executed_only_net_return_status": "EXECUTED_NET_RETURN_NOT_PROVEN",
                            "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
                            "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
                            "promotion_status": "PAIR_NOT_PROVEN",
                        }
                    ],
                    "strategy_promotion_artifacts": [
                        {
                            "schema_version": "v1",
                            "run_id": "run-1",
                            "strategy_id": "strategy-a",
                            "executed_only_net_return_status": "EXECUTED_NET_RETURN_NOT_PROVEN",
                            "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
                            "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
                            "promotion_status": "STRATEGY_PROMOTION_NOT_READY",
                        }
                    ],
                    "sample_size_survival_artifacts": [
                        {
                            "schema_version": "v1",
                            "run_id": "run-1",
                            "scope": "engine",
                            "id": "engine_c",
                            "raw_candidate_count": 10,
                            "selected_count": 2,
                            "executed_count": 1,
                            "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        replay = read_replay_metrics(scratch / "auto_exports")

        assert replay.engine_promotion_artifacts[0].promotion_status == "ENGINE_PROMOTION_NOT_READY"
        assert replay.engine_promotion_artifacts[0].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
        assert replay.pair_promotion_artifacts[0].promotion_status == "PAIR_NOT_PROVEN"
        assert replay.strategy_promotion_artifacts[0].promotion_status == "STRATEGY_PROMOTION_NOT_READY"
        assert replay.sample_size_survival_artifacts[0].sample_size_survival_status == "SAMPLE_SIZE_NOT_PROVEN"
        assert replay.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
    finally:
        cleanup_scratch(scratch)


def test_read_replay_metrics_keeps_old_artifacts_compatible() -> None:
    scratch = scratch_dir("replay_metrics_compat")
    try:
        auto_exports = scratch / "auto_exports" / "2026-05-01"
        auto_exports.mkdir(parents=True, exist_ok=True)
        (auto_exports / "replay_metrics.json").write_text(
            json.dumps(
                {
                    "total_records": 40,
                    "selected_count": 20,
                    "executed_count": 10,
                    "ce_net": 0.12,
                    "fee_source_status": "NOT_PROVEN",
                    "impact_source_status": "NOT_PROVEN",
                    "cost_model_completeness_status": "PARTIAL_NO_FEE_NO_IMPACT",
                }
            ),
            encoding="utf-8",
        )

        replay = read_replay_metrics(scratch / "auto_exports")

        assert replay.fee_source_status == "FEE_SOURCE_NOT_PROVEN"
        assert replay.impact_source_status == "IMPACT_SOURCE_NOT_PROVEN"
        assert replay.cost_model_completeness_status == "COST_MODEL_NOT_PROVEN"
        assert replay.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
    finally:
        cleanup_scratch(scratch)
