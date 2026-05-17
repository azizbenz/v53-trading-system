from __future__ import annotations

from cockpit.state_engine_why import read_engine_why_state
from cockpit.state_engines import EngineRuntimeStatus, EnginesGridSnapshot
from cockpit.state_feature_bridge import FeatureBridgeSnapshot
from cockpit.state_replay_metrics import EngineAggregate, ReplayMetricsSnapshot


def test_engine_why_marks_active_dormant_sample_too_small_and_suspended() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        source_path="E:/tmp/replay_metrics.json",
        engine_aggregates=(
            EngineAggregate(engine_id="engine_a", record_count=10, selected_count=1),
            EngineAggregate(engine_id="engine_b", record_count=0, selected_count=0),
        ),
    )
    feature_bridge = FeatureBridgeSnapshot(
        source_status="ok",
        engines=("engine_a", "engine_b"),
    )
    engines = EnginesGridSnapshot(
        engines=(
            EngineRuntimeStatus(engine_id="engine_a", status="active", record_count=10),
            EngineRuntimeStatus(engine_id="engine_b", status="dormant", record_count=0),
            EngineRuntimeStatus(
                engine_id="engine_c",
                status="suspended",
                suspended_reason="manual",
            ),
            EngineRuntimeStatus(engine_id="engine_d", status="unknown"),
        )
    )
    snapshot = read_engine_why_state(
        replay=replay,
        feature_bridge=feature_bridge,
        engines=engines,
    )
    rows = {row.engine_id: row for row in snapshot.engines}
    assert rows["engine_a"].status == "active"
    assert rows["engine_a"].sample_warning == "SAMPLE_TOO_SMALL"
    assert rows["engine_a"].expected_cost_status == "PARTIAL_EXECUTION_EVIDENCE"
    assert rows["engine_d"].expected_cost is None
    assert rows["engine_d"].expected_cost_status == "SOURCE_UNAVAILABLE"
    assert rows["engine_c"].engine_role == (
        "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context."
    )
    assert rows["engine_c"].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert rows["engine_c"].promotion_readiness_status == "ENGINE_PROMOTION_NOT_READY"
    assert "ENGINE_EXECUTED_RETURN_NOT_PROVEN" in rows["engine_c"].missing_promotion_evidence
    assert rows["engine_d"].engine_role == (
        "Re-entry / second-chance engine with first-episode linkage, anti-revenge, "
        "reformation, and realized-vol context."
    )
    assert rows["engine_d"].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert rows["engine_d"].promotion_readiness_status == "ENGINE_PROMOTION_NOT_READY"
    assert rows["engine_b"].status == "dormant"
    assert rows["engine_c"].status == "suspended"
    assert snapshot.active_count == 1
    assert snapshot.dormant_count >= 1
    assert snapshot.suspended_count == 1


def test_engine_why_surfaces_cd_replay_artifact_statuses_without_false_green() -> None:
    replay = ReplayMetricsSnapshot(
        source_status="ok",
        source_path="E:/tmp/replay_metrics.json",
        engine_aggregates=(
            EngineAggregate(
                engine_id="engine_c",
                engine_role="Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context.",
                shared_physics_mapping_status="PARTIAL_BY_DESIGN",
                record_count=42,
                selected_count=12,
                executed_count=5,
                execution_rate=5 / 42,
                expected_cost_mean=0.0011,
                cost_model_completeness_status="NOT_PROVEN",
                fill_realism_status="NOT_PROVEN",
                executed_only_net_return_status="EXECUTED_NET_RETURN_NOT_PROVEN",
                true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
                shadow_confirmation_status="NOT_PROVEN",
                promotion_status="NOT_SHADOW_READY",
            ),
            EngineAggregate(
                engine_id="engine_d",
                engine_role="Re-entry / second-chance engine with first-episode linkage, anti-revenge, reformation, and realized-vol context.",
                shared_physics_mapping_status="PARTIAL_BY_DESIGN",
                record_count=18,
                selected_count=4,
                expected_cost_mean=0.0014,
                cost_model_completeness_status="NOT_PROVEN",
                fill_realism_status="NOT_PROVEN",
                executed_only_net_return_status="EXECUTED_NET_RETURN_NOT_PROVEN",
                true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
                shadow_confirmation_status="NOT_PROVEN",
                promotion_status="NOT_SHADOW_READY",
            ),
        ),
    )
    feature_bridge = FeatureBridgeSnapshot(
        source_status="ok",
        engines=("engine_c", "engine_d"),
    )
    engines = EnginesGridSnapshot(
        engines=(
            EngineRuntimeStatus(engine_id="engine_c", status="active", record_count=42),
            EngineRuntimeStatus(engine_id="engine_d", status="active", record_count=18),
        )
    )

    snapshot = read_engine_why_state(
        replay=replay,
        feature_bridge=feature_bridge,
        engines=engines,
    )
    rows = {row.engine_id: row for row in snapshot.engines}

    assert rows["engine_c"].status == "active"
    assert rows["engine_c"].partial_by_design_caveat.startswith("Engine C/D local math is active")
    assert rows["engine_c"].promotion_readiness_status == "ENGINE_PROMOTION_NOT_READY"
    assert rows["engine_c"].executed_only_return_status == "EXECUTED_NET_RETURN_NOT_PROVEN"
    assert rows["engine_c"].true_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    assert rows["engine_c"].shadow_confirmation_status == "NOT_PROVEN"
    assert "ENGINE_COST_COMPLETENESS_NOT_PROVEN" in rows["engine_c"].missing_promotion_evidence
    assert "ENGINE_FILL_REALISM_NOT_PROVEN" in rows["engine_c"].missing_promotion_evidence
    assert rows["engine_d"].sample_warning == "SAMPLE_TOO_SMALL"
    assert rows["engine_d"].promotion_readiness_status == "ENGINE_PROMOTION_NOT_READY"
