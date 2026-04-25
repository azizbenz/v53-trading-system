from __future__ import annotations

from tests.support_hybrid_router_v2 import build_router, build_snapshot


def test_diagnostics_contains_raw_and_weighted_ev() -> None:
    router, _, _ = build_router()
    decision = router.decide(build_snapshot())

    assert decision.diagnostics.ev_maker_raw_bps != decision.diagnostics.ev_maker_weighted_bps


def test_diagnostics_contains_capital_cost_components() -> None:
    router, _, _ = build_router()
    decision = router.decide(build_snapshot())

    assert decision.diagnostics.capital_opportunity_rate_bps_per_s > 0.0
    assert decision.diagnostics.capital_opportunity_cost_bps >= 0.0


def test_diagnostics_contains_sanitized_fields_with_raw() -> None:
    router, _, _ = build_router()
    decision = router.decide(build_snapshot(market_toxicity_score=2.0))

    assert decision.diagnostics.market_toxicity.raw_value == 2.0
    assert decision.diagnostics.market_toxicity.sanitized_value == 1.0


def test_ev_maker_raw_minus_taker_visible_in_diagnostics() -> None:
    router, _, _ = build_router()
    decision = router.decide(build_snapshot())

    assert (
        decision.diagnostics.ev_maker_raw_minus_taker_bps
        == decision.diagnostics.ev_maker_raw_bps - decision.ev_taker_bps
    )
