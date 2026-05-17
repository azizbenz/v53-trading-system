"""Phase 2.5 adapter - why each engine is active, dormant, suspended, or unknown."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from cockpit.state_engines import CANONICAL_ENGINES, EnginesGridSnapshot
from cockpit.state_feature_bridge import FeatureBridgeSnapshot
from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp, worst_status
from cockpit.state_replay_metrics import ReplayMetricsSnapshot


_ENGINE_ROLE_BY_ID: dict[str, str] = {
    "engine_c": "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context.",
    "engine_d": "Re-entry / second-chance engine with first-episode linkage, anti-revenge, reformation, and realized-vol context.",
}
_ENGINE_SHARED_PHYSICS_MAPPING_STATUS_BY_ID: dict[str, str] = {
    "engine_c": "PARTIAL_BY_DESIGN",
    "engine_d": "PARTIAL_BY_DESIGN",
}
_C_D_PARTIAL_BY_DESIGN_CAVEAT = (
    "Engine C/D local math is active, but A/B-style shared scoring physics mapping "
    "is PARTIAL_BY_DESIGN. This is not a defect. Promotion readiness still requires "
    "engine-specific replay/shadow economics."
)


class EngineWhyRow(BaseModel, frozen=True):
    engine_id: str = Field(..., min_length=1)
    status: str = "unknown"
    why_status: str = ""
    engine_role: str = ""
    shared_physics_mapping_status: str = "NOT_APPLICABLE"
    partial_by_design_caveat: str = ""
    records: int = 0
    selected: int = 0
    blocked: bool = False
    blocked_reasons_top3: tuple[str, ...] = ()
    ce_net: float = 0.0
    expected_cost: float | None = None
    expected_cost_status: str = "SOURCE_UNAVAILABLE"
    realized_cost: float | None = None
    realized_cost_status: str = "SOURCE_UNAVAILABLE"
    cost_model_completeness_status: str = "UNKNOWN"
    promotion_readiness_status: str = ""
    missing_promotion_evidence: tuple[str, ...] = ()
    executed_only_return_status: str = ""
    true_drawdown_status: str = ""
    shadow_confirmation_status: str = ""
    sample_warning: str = ""


class EngineWhySnapshot(OperationalSourceSnapshot):
    engines: tuple[EngineWhyRow, ...] = ()
    active_count: int = 0
    dormant_count: int = 0
    suspended_count: int = 0


def read_engine_why_state(
    *,
    replay: ReplayMetricsSnapshot,
    feature_bridge: FeatureBridgeSnapshot,
    engines: EnginesGridSnapshot,
) -> EngineWhySnapshot:
    """Provide operator-readable reasons for A/B/C/D runtime state."""

    replay_path = Path(replay.source_path) if replay.source_path else None
    replay_stamp = source_stamp(path=replay_path, stale_after_seconds=300.0)
    aggregates = {aggregate.engine_id: aggregate for aggregate in replay.engine_aggregates}
    bridge_engines = set(feature_bridge.engines)
    existing = {row.engine_id: row for row in engines.engines}
    rows: list[EngineWhyRow] = []
    active_count = 0
    dormant_count = 0
    suspended_count = 0
    for engine_id in CANONICAL_ENGINES:
        agg = aggregates.get(engine_id)
        runtime_row = existing.get(engine_id)
        engine_role = _ENGINE_ROLE_BY_ID.get(
            engine_id,
            agg.engine_role if agg is not None else "",
        )
        shared_physics_mapping_status = _ENGINE_SHARED_PHYSICS_MAPPING_STATUS_BY_ID.get(
            engine_id,
            agg.shared_physics_mapping_status if agg is not None else "NOT_APPLICABLE",
        )
        is_partial_by_design = shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
        record_count = agg.record_count if agg is not None else 0
        selected_count = agg.selected_count if agg is not None else 0
        if runtime_row is not None and runtime_row.status == "suspended":
            status = "suspended"
            reasons = (runtime_row.suspended_reason or "suspended_via_governed_command",)
            why_status = "suspended_via_governed_command"
        elif record_count > 0:
            status = "active"
            reasons = ()
            why_status = (
                "records_present_not_selected"
                if selected_count == 0
                else "records_selected_in_latest_replay"
            )
        elif engine_id in bridge_engines or replay.source_status == "ok":
            status = "dormant"
            reasons = ("no_records_in_latest_replay_metrics",)
            why_status = "no_records_in_latest_replay_metrics"
        else:
            status = "unknown"
            reasons = ("engine_state_not_inferable",)
            why_status = "engine_state_not_inferable"
        if status == "active":
            active_count += 1
        elif status == "dormant":
            dormant_count += 1
        elif status == "suspended":
            suspended_count += 1
        sample_warning = "SAMPLE_TOO_SMALL" if 0 < record_count < 30 else ""
        promotion_readiness_status = ""
        missing_promotion_evidence: tuple[str, ...] = ()
        executed_only_return_status = ""
        true_drawdown_status = ""
        shadow_confirmation_status = ""
        if engine_id in {"engine_c", "engine_d"}:
            executed_only_return_status = (
                agg.executed_only_net_return_status
                if agg is not None
                else "EXECUTED_NET_RETURN_NOT_PROVEN"
            )
            true_drawdown_status = (
                agg.true_net_equity_drawdown_status
                if agg is not None
                else "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
            )
            shadow_confirmation_status = (
                agg.shadow_confirmation_status if agg is not None else "NOT_PROVEN"
            )
            promotion_status = agg.promotion_status if agg is not None else "NOT_SHADOW_READY"
            if promotion_status in {"SHADOW_READY", "ENGINE_SHADOW_READY"}:
                promotion_readiness_status = "ENGINE_SHADOW_READY"
            elif promotion_status == "SHADOW_READY_WITH_LIMITATIONS":
                promotion_readiness_status = "ENGINE_SHADOW_READY_WITH_LIMITATIONS"
            else:
                promotion_readiness_status = "ENGINE_PROMOTION_NOT_READY"
            missing_evidence: list[str] = [
                "ENGINE_ARCHITECTURE_VIABLE",
                "ENGINE_SHARED_PHYSICS_PARTIAL_BY_DESIGN",
            ]
            if agg is not None:
                missing_evidence.append("ENGINE_REPLAY_AGGREGATE_PRESENT")
            if executed_only_return_status not in {
                "EXECUTED_NET_RETURN_PROVEN",
                "EXECUTED_RETURN_PROVEN",
            }:
                missing_evidence.append("ENGINE_EXECUTED_RETURN_NOT_PROVEN")
            if true_drawdown_status not in {
                "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
                "MEASURED",
                "PROVEN",
            }:
                missing_evidence.append("ENGINE_TRUE_DRAWDOWN_NOT_PROVEN")
            if agg is None or agg.cost_model_completeness_status not in {
                "COMPLETE",
                "COST_MODEL_COMPLETE",
            }:
                missing_evidence.append("ENGINE_COST_COMPLETENESS_NOT_PROVEN")
            if agg is None or agg.fill_realism_status not in {
                "FILL_REALISM_PROVEN",
                "FILL_REALISM_SHADOW_MEASURED",
                "MEASURED",
                "PROVEN",
            }:
                missing_evidence.append("ENGINE_FILL_REALISM_NOT_PROVEN")
            if shadow_confirmation_status not in {"MEASURED", "PROVEN", "CONFIRMED"}:
                missing_evidence.append("ENGINE_SHADOW_ARTIFACT_MISSING")
            missing_promotion_evidence = tuple(dict.fromkeys(missing_evidence))
        rows.append(
            EngineWhyRow(
                engine_id=engine_id,
                status=status,
                why_status=why_status,
                engine_role=engine_role,
                shared_physics_mapping_status=shared_physics_mapping_status,
                partial_by_design_caveat=(
                    _C_D_PARTIAL_BY_DESIGN_CAVEAT if is_partial_by_design else ""
                ),
                records=record_count,
                selected=selected_count,
                blocked=status == "suspended" or (agg.hard_blocked_count > 0 if agg else False),
                blocked_reasons_top3=reasons[:3],
                ce_net=agg.ce_net if agg is not None else 0.0,
                expected_cost=agg.expected_cost_mean if agg is not None else None,
                expected_cost_status=(
                    "PARTIAL_EXECUTION_EVIDENCE"
                    if agg is not None
                    and agg.cost_model_completeness_status not in {"COMPLETE", "COST_MODEL_COMPLETE"}
                    else ("OK" if agg is not None else "SOURCE_UNAVAILABLE")
                ),
                realized_cost=agg.realized_cost_mean if agg is not None else None,
                realized_cost_status=(
                    "PARTIAL_EXECUTION_EVIDENCE"
                    if agg is not None
                    and agg.cost_model_completeness_status not in {"COMPLETE", "COST_MODEL_COMPLETE"}
                    else ("OK" if agg is not None else "SOURCE_UNAVAILABLE")
                ),
                cost_model_completeness_status=(
                    agg.cost_model_completeness_status if agg is not None else "UNKNOWN"
                ),
                promotion_readiness_status=promotion_readiness_status,
                missing_promotion_evidence=missing_promotion_evidence,
                executed_only_return_status=executed_only_return_status,
                true_drawdown_status=true_drawdown_status,
                shadow_confirmation_status=shadow_confirmation_status,
                sample_warning=sample_warning,
            )
        )
    return EngineWhySnapshot(
        source_status=worst_status(replay_stamp["source_status"], feature_bridge.source_status),
        source_file=str(replay_stamp["source_file"]) if replay_stamp["source_file"] else replay.source_path or feature_bridge.source_path or None,
        last_modified_at=replay_stamp["last_modified_at"],
        age_seconds=replay_stamp["age_seconds"],
        reason_codes=replay_stamp["reason_codes"],
        engines=tuple(rows),
        active_count=active_count,
        dormant_count=dormant_count,
        suspended_count=suspended_count,
    )


__all__ = ["EngineWhyRow", "EngineWhySnapshot", "read_engine_why_state"]
