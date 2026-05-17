"""Canonical pair-universe and route-plan helpers for Shadow live capture."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, Field

from interface_contracts import ALL_PAIRS, ENGINE_PAIR_MAP, V53_MULTIPAIR_7
from interface_contracts.domain_types import EngineId
from interface_contracts.pair_catalog import V53_PAIR_CATALOG


_CANONICAL_PAIR_ORDER = tuple(
    entry.symbol
    for entry in V53_PAIR_CATALOG.entries
    if entry.symbol in V53_MULTIPAIR_7
)
_TIER1_PAIRS = frozenset({"BTCUSDT", "ETHUSDT"})
_ENGINE_TEMPLATE_BY_ID: dict[EngineId, dict[str, object]] = {
    EngineId.A: {
        "raw_score": 0.91,
        "penalized_score": 0.88,
        "final_score": 0.86,
        "expected_edge_bps": 17.0,
        "target_decision_state": "executed",
        "production_decision_state": "executed",
        "production_final_score": 0.86,
        "production_expected_cost": 0.00086,
        "candidate_size": 1.0,
        "final_size": 1.0,
        "gross_return_bps": 21.0,
    },
    EngineId.B: {
        "raw_score": 0.81,
        "penalized_score": 0.79,
        "final_score": 0.76,
        "expected_edge_bps": 7.0,
        "target_decision_state": "rejected_ranking",
        "production_decision_state": "rejected_ranking",
        "production_final_score": 0.76,
        "production_expected_cost": 0.00094,
        "candidate_size": 1.0,
        "final_size": 0.0,
        "gross_return_bps": -4.0,
        "ranking_position": 3,
        "primary_reason": "rank_cutoff",
    },
    EngineId.C: {
        "raw_score": 0.73,
        "penalized_score": 0.71,
        "final_score": 0.69,
        "expected_edge_bps": 9.0,
        "target_decision_state": "rejected_ranking",
        "production_decision_state": "rejected_ranking",
        "production_final_score": 0.69,
        "production_expected_cost": 0.00091,
        "candidate_size": 1.0,
        "final_size": 0.0,
        "gross_return_bps": 6.0,
        "ranking_position": 2,
        "primary_reason": "rank_cutoff",
    },
    EngineId.D: {
        "raw_score": 0.78,
        "penalized_score": 0.72,
        "final_score": 0.68,
        "expected_edge_bps": 11.0,
        "target_decision_state": "executed",
        "production_decision_state": "executed",
        "production_final_score": 0.68,
        "production_expected_cost": 0.00079,
        "candidate_size": 0.8,
        "final_size": 0.8,
        "gross_return_bps": 13.0,
    },
}


class ShadowLiveRouteHint(BaseModel, frozen=True):
    """One synthetic live route hint bound to one pair and one engine."""

    route_id: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    raw_score: float = 0.0
    penalized_score: float = 0.0
    final_score: float = 0.0
    expected_edge_bps: float = 0.0
    target_decision_state: str = ""
    production_decision_state: str = ""
    production_final_score: float = 0.0
    production_expected_cost: float = 0.0
    candidate_size: float = 0.0
    final_size: float = 0.0
    gross_return_bps: float = 0.0
    ranking_position: int | None = None
    primary_reason: str = ""
    feature_values: dict[str, float] = Field(default_factory=dict)


class ShadowLivePlan(BaseModel, frozen=True):
    """Canonical live pair scope plus deterministic route hints."""

    pairs: tuple[str, ...]
    engine_scope: tuple[str, ...]
    route_hints_by_pair: dict[str, tuple[ShadowLiveRouteHint, ...]]


def canonical_shadow_pair_universe() -> tuple[str, ...]:
    """Return the canonical ordered 7-pair Shadow universe."""

    return _CANONICAL_PAIR_ORDER


def resolve_shadow_live_pairs(
    requested_pairs: Iterable[str] | None = None,
) -> tuple[str, ...]:
    """Resolve one valid Shadow live pair scope."""

    if requested_pairs is None:
        return canonical_shadow_pair_universe()
    deduped: list[str] = []
    seen: set[str] = set()
    for raw_pair in requested_pairs:
        pair = str(raw_pair).strip().upper()
        if not pair or pair in seen:
            continue
        if pair not in ALL_PAIRS:
            raise ValueError(
                f"Shadow live pair {pair!r} is outside the governed V5.3 pair scope"
            )
        seen.add(pair)
        deduped.append(pair)
    return tuple(deduped) if deduped else canonical_shadow_pair_universe()


def build_shadow_live_plan(
    requested_pairs: Iterable[str] | None = None,
) -> ShadowLivePlan:
    """Build the deterministic Shadow live plan from the canonical doctrine."""

    pairs = resolve_shadow_live_pairs(requested_pairs)
    route_hints_by_pair = {
        pair: tuple(
            _build_route_hint(pair=pair, pair_index=pair_index, engine_id=engine_id)
            for engine_id in _engines_for_pair(pair)
        )
        for pair_index, pair in enumerate(pairs)
    }
    engine_scope = tuple(
        engine_id.value
        for engine_id in EngineId
        if any(pair in ENGINE_PAIR_MAP[engine_id] for pair in pairs)
    )
    return ShadowLivePlan(
        pairs=pairs,
        engine_scope=engine_scope,
        route_hints_by_pair=route_hints_by_pair,
    )


def _engines_for_pair(pair: str) -> tuple[EngineId, ...]:
    return tuple(engine_id for engine_id in EngineId if pair in ENGINE_PAIR_MAP[engine_id])


def _build_route_hint(
    *,
    pair: str,
    pair_index: int,
    engine_id: EngineId,
) -> ShadowLiveRouteHint:
    template = dict(_ENGINE_TEMPLATE_BY_ID[engine_id])
    pair_label = pair.lower().replace("usdt", "")
    spread_bps = _spread_bps_for_pair(pair=pair, pair_index=pair_index)
    return ShadowLiveRouteHint(
        route_id=f"{pair_label}-live-campaign-{engine_id.value.replace('_', '-')}",
        engine_id=engine_id.value,
        raw_score=float(template["raw_score"]),
        penalized_score=float(template["penalized_score"]),
        final_score=float(template["final_score"]),
        expected_edge_bps=float(template["expected_edge_bps"]),
        target_decision_state=str(template["target_decision_state"]),
        production_decision_state=str(template["production_decision_state"]),
        production_final_score=float(template["production_final_score"]),
        production_expected_cost=float(template["production_expected_cost"]),
        candidate_size=float(template["candidate_size"]),
        final_size=float(template["final_size"]),
        gross_return_bps=float(template["gross_return_bps"]),
        ranking_position=_optional_int(template.get("ranking_position")),
        primary_reason=str(template.get("primary_reason", "")),
        feature_values={"spread_bps": spread_bps},
    )


def _spread_bps_for_pair(*, pair: str, pair_index: int) -> float:
    base = 3.0 if pair in _TIER1_PAIRS else 4.1
    return round(base + (pair_index * 0.15), 2)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


__all__ = [
    "ShadowLivePlan",
    "ShadowLiveRouteHint",
    "build_shadow_live_plan",
    "canonical_shadow_pair_universe",
    "resolve_shadow_live_pairs",
]
