from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time

from backtest_artifact_import import CapitalProfileBuildInput, build_capital_bucket_profile
from cockpit.state_economic_sterilization import read_economic_sterilization
from cockpit.state_replay_metrics import ReplayMetricsSnapshot

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
        "executed_only_net_return": 0.011,
        "executed_only_net_return_status": "EXECUTED_NET_RETURN_PROVEN",
        "true_net_equity_max_drawdown": 0.02,
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
        "run_id": f"sterilization-{capital_bucket}",
        "strategy_ladder_manifest_ref": f"E:/audit/sterilization/{capital_bucket}/run_manifest.json",
        "execution_fidelity_status": "FULL_CANONICAL_EXECUTION",
        "execution_fidelity_gap_codes": (),
        "created_at": created_at,
        "expires_at": created_at + timedelta(days=7),
    }


def test_economic_sterilization_ratio_and_sample_warning() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        source_path="E:/tmp/replay_metrics.json",
        total_records=10,
        total_opportunities=10,
        selected_count=2,
        executed_count=2,
        hard_blocked_count=1,
    )
    snapshot = read_economic_sterilization(replay)
    assert snapshot.economic_sterilization_ratio == 0.8
    assert snapshot.status == "insufficient_sample"


def test_economic_sterilization_marks_critical_for_large_sample() -> None:
    scratch = scratch_dir("economic_sterilization_critical")
    try:
        replay_path = scratch / "replay_metrics.json"
        profiles = (
            build_capital_bucket_profile(
                CapitalProfileBuildInput(
                    **_ready_profile_kwargs(400),
                )
            ),
        )
        replay = ReplayMetricsSnapshot(
            source_status="ok",
            source_path=str(replay_path),
            total_records=100,
            total_opportunities=100,
            selected_count=10,
            executed_count=10,
            executed_only_net_return=0.011,
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            fee_source_status="FEE_SOURCE_PROVEN",
            impact_source_status="IMPACT_SOURCE_PROVEN",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_readiness_status="DEPTH20_AVAILABLE",
            shadow_extension_required=False,
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            true_net_equity_max_drawdown=0.02,
            true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            replay_live_cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            capital_bucket_profiles=profiles,
            small_capital_viability_status="MEASURED",
            min_notional_viability_status="MEASURED",
            capital_fragmentation_status="MEASURED",
            multi_asset_risk_control_status="FULLY_PROVEN",
            covariance_model_status="EXPLICIT",
        )
        replay_path.write_text("{}", encoding="utf-8")
        snapshot = read_economic_sterilization(replay)
        assert snapshot.status == "critical"
    finally:
        cleanup_scratch(scratch)


def test_economic_sterilization_marks_zero_record_replay_as_placeholder() -> None:
    scratch = scratch_dir("economic_sterilization_placeholder")
    try:
        replay_path = scratch / "replay_metrics.json"
        replay_path.write_text("{}", encoding="utf-8")
        replay = ReplayMetricsSnapshot(
            source_status="ok",
            source_path=str(replay_path),
            total_records=0,
            total_opportunities=0,
            selected_count=0,
            executed_count=0,
            ce_net=0.05,
        )

        snapshot = read_economic_sterilization(replay)

        assert snapshot.status == "placeholder"
        assert snapshot.ce_net_label == "Expected CE net"
        assert snapshot.exec_rate_label == "Exec rate (executed / total records)"
        assert snapshot.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
        assert "REPLAY_METRICS_NOT_MEASURED" in snapshot.reason_codes
    finally:
        cleanup_scratch(scratch)


def test_economic_sterilization_marks_stale_replay_as_not_green() -> None:
    scratch = scratch_dir("economic_sterilization_stale")
    try:
        replay_path = scratch / "replay_metrics.json"
        replay_path.write_text("{}", encoding="utf-8")
        stale_epoch = time.time() - 900.0
        os.utime(replay_path, (stale_epoch, stale_epoch))
        replay = ReplayMetricsSnapshot(
            source_status="stale",
            source_path=str(replay_path),
            total_records=100,
            total_opportunities=100,
            selected_count=60,
            executed_count=40,
            ce_net=0.05,
        )

        snapshot = read_economic_sterilization(replay)

        assert snapshot.source_status == "stale"
        assert snapshot.status == "stale"
        assert "REPLAY_METRICS_STALE" in snapshot.reason_codes
    finally:
        cleanup_scratch(scratch)


def test_economic_sterilization_marks_partial_cost_model_as_partial_not_green() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=100,
        total_opportunities=100,
        selected_count=60,
        executed_count=40,
        ce_net=0.05,
    )

    snapshot = read_economic_sterilization(replay)

    assert snapshot.status == "partial"
    assert snapshot.cost_blocked_count is None
    assert snapshot.cost_blocked_count_status == "SOURCE_UNAVAILABLE"
    assert snapshot.cost_model_completeness_status == "COST_MODEL_NOT_PROVEN"
    assert snapshot.small_capital_viability_status == "BLOCKED_BY_BACKTEST"
    assert snapshot.kelly_status == "NOT_IMPLEMENTED_BY_DESIGN_FOR_NOW"
    assert snapshot.portfolio_multi_asset_status == "BASELINE_CAPS_ONLY"
    assert snapshot.executed_only_net_return_status == "EXECUTED_NET_RETURN_NOT_PROVEN"
    assert snapshot.true_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    assert snapshot.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY"
    assert "REPLAY_COST_MODEL_PARTIAL" in snapshot.reason_codes


def test_economic_sterilization_carries_depth_fill_and_parity_blockers() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        total_records=100,
        total_opportunities=100,
        selected_count=60,
        executed_count=40,
        ce_net=0.05,
        book_depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
        impact_depth_readiness_status="LIMITED_DEPTH_PARTIAL",
        shadow_extension_required=True,
        shadow_extension_reason="SHADOW_EXTENDED_REQUIRED",
        minimum_shadow_days_required=45,
        shadow_extension_status="SHADOW_EXTENDED_45D",
        fill_realism_status="FILL_REALISM_MODEL_ONLY",
        fill_source_status="FILL_SOURCE_REPLAY_MODEL",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        cost_model_completeness_status="COST_MODEL_PARTIAL_IMPACT_MISSING",
    )

    snapshot = read_economic_sterilization(replay)

    assert snapshot.book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
    assert snapshot.impact_depth_readiness_status == "LIMITED_DEPTH_PARTIAL"
    assert snapshot.shadow_extension_required is True
    assert snapshot.minimum_shadow_days_required == 45
    assert snapshot.fill_realism_status == "FILL_REALISM_MODEL_ONLY"
    assert snapshot.cost_parity_status == "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
