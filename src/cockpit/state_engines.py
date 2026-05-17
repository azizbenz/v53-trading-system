"""Phase 2 adapter — Engine A/B/C/D status grid.

Composes ``state_replay_metrics`` (per-engine aggregates) and
``state_feature_bridge`` (engines actually fed in current cycle) plus
``shadow_vps_service.state.json`` (suspended/active state) into a 4-engine
view-model.

V5.3 doctrine status taxonomy:
- ``active`` — engine present in feature bridge AND not in suspended list.
- ``dormant`` — engine defined in code (A/B/C/D) but not in current cycle.
  Engine B is dormant in Phase 0 by design.
- ``suspended`` — present in ``suspended_engines[]`` of state store.
- ``unknown`` — adapter could not determine the state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cockpit.state_feature_bridge import FeatureBridgeSnapshot
from cockpit.state_replay_metrics import EngineAggregate, ReplayMetricsSnapshot


_logger = logging.getLogger(__name__)

CANONICAL_ENGINES: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d")
EngineStatus = Literal["active", "dormant", "suspended", "unknown"]


class EngineRuntimeStatus(BaseModel, frozen=True):
    engine_id: str
    status: EngineStatus = "unknown"
    record_count: int = 0
    selected_count: int = 0
    hard_blocked_count: int = 0
    ce_net: float = 0.0
    gross_return_mean: float = 0.0
    expected_cost_mean: float = 0.0
    realized_cost_mean: float = 0.0
    in_feature_bridge: bool = False
    suspended_reason: str = ""

    @property
    def select_rate(self) -> float:
        if self.record_count == 0:
            return 0.0
        return self.selected_count / self.record_count


class EnginesGridSnapshot(BaseModel, frozen=True):
    engines: tuple[EngineRuntimeStatus, ...]


def _read_suspended_engines(state_path: Path) -> dict[str, str]:
    """Return ``{engine_id: reason}`` from the shadow service state store."""

    if not state_path.is_file():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse service state %s: %s", state_path, exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    raw = payload.get("suspended_engines") or payload.get("suspended_engine_ids") or ()
    suspended: dict[str, str] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                suspended[item] = ""
            elif isinstance(item, dict):
                eid = str(item.get("engine_id", ""))
                if eid:
                    suspended[eid] = str(item.get("reason", ""))
    return suspended


def build_engines_grid(
    *,
    replay: ReplayMetricsSnapshot,
    feature_bridge: FeatureBridgeSnapshot,
    service_state_path: Path,
) -> EnginesGridSnapshot:
    aggregates: dict[str, EngineAggregate] = {
        agg.engine_id: agg for agg in replay.engine_aggregates
    }
    bridge_engines = set(feature_bridge.engines)
    suspended = _read_suspended_engines(service_state_path)

    rows: list[EngineRuntimeStatus] = []
    for engine_id in CANONICAL_ENGINES:
        agg = aggregates.get(engine_id)
        in_bridge = engine_id in bridge_engines
        if engine_id in suspended:
            status: EngineStatus = "suspended"
            reason = suspended[engine_id] or "suspended via governed command"
        elif in_bridge:
            status = "active"
            reason = ""
        elif replay.source_status != "ok" and feature_bridge.source_status != "ok":
            status = "unknown"
            reason = "no recent runtime artefacts"
        else:
            status = "dormant"
            reason = ""
        rows.append(
            EngineRuntimeStatus(
                engine_id=engine_id,
                status=status,
                record_count=agg.record_count if agg else 0,
                selected_count=agg.selected_count if agg else 0,
                hard_blocked_count=agg.hard_blocked_count if agg else 0,
                ce_net=agg.ce_net if agg else 0.0,
                gross_return_mean=agg.gross_return_mean if agg else 0.0,
                expected_cost_mean=agg.expected_cost_mean if agg else 0.0,
                realized_cost_mean=agg.realized_cost_mean if agg else 0.0,
                in_feature_bridge=in_bridge,
                suspended_reason=reason,
            )
        )
    return EnginesGridSnapshot(engines=tuple(rows))


__all__ = [
    "CANONICAL_ENGINES",
    "EngineRuntimeStatus",
    "EnginesGridSnapshot",
    "build_engines_grid",
]
