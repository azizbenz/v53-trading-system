from __future__ import annotations

import pytest

from protocols.shadow_live_plan import (
    build_shadow_live_plan,
    canonical_shadow_pair_universe,
)


def test_canonical_shadow_pair_universe_returns_ordered_governed_pairs() -> None:
    assert canonical_shadow_pair_universe() == (
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "LINKUSDT",
        "BNBUSDT",
        "ADAUSDT",
    )


def test_build_shadow_live_plan_defaults_to_full_canonical_7_pair_surface() -> None:
    plan = build_shadow_live_plan()

    assert plan.pairs == canonical_shadow_pair_universe()
    assert plan.engine_scope == ("engine_a", "engine_b", "engine_c", "engine_d")
    assert set(plan.route_hints_by_pair) == set(plan.pairs)
    for pair in plan.pairs:
        assert {hint.engine_id for hint in plan.route_hints_by_pair[pair]} == {
            "engine_a",
            "engine_b",
            "engine_c",
            "engine_d",
        }


def test_build_shadow_live_plan_preserves_requested_order_and_engine_scope() -> None:
    plan = build_shadow_live_plan(("AVAXUSDT", "ETHUSDT"))

    assert plan.pairs == ("AVAXUSDT", "ETHUSDT")
    assert plan.engine_scope == ("engine_a", "engine_b", "engine_c", "engine_d")
    assert {hint.engine_id for hint in plan.route_hints_by_pair["AVAXUSDT"]} == {
        "engine_c",
        "engine_d",
    }
    assert {hint.engine_id for hint in plan.route_hints_by_pair["ETHUSDT"]} == {
        "engine_a",
        "engine_b",
        "engine_c",
        "engine_d",
    }


def test_build_shadow_live_plan_rejects_out_of_scope_pairs() -> None:
    with pytest.raises(ValueError, match="outside the governed V5.3 pair scope"):
        build_shadow_live_plan(("DOGEUSDT",))
