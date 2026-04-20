from __future__ import annotations

import pytest
from pydantic import ValidationError

from engines.engine_a.engine_a_runner import EngineAInput, EngineADecision, run_engine_a
from engines.engine_a.signal_reporter_a import (
    ENGINE_A_SIGNAL_REPORTER_STATUS,
    ENGINE_A_SIGNAL_REPORTER_STATUS_DETAIL,
    NoTradeReason,
)


def _good_inputs(**overrides: object) -> EngineAInput:
    payload: dict[str, object] = {
        "pair": "BTCUSDT",
        "direction_score": 0.8,
        "continuation_score": 0.8,
        "structure_quality": 0.8,
        "zone_proximity": 0.7,
        "trend_stability": 0.8,
        "regime": "trending_up",
        "regime_favorability": 0.8,
        "regime_confidence": 0.8,
        "pair_health": 0.8,
        "data_freshness": 0.9,
        "flow_coherence": 0.8,
        "flow_score": 0.8,
        "ofi_flow_score": None,
        "cost_preference_score": 0.8,
        "delta_confirmation": 0.9,
        "competition_density": 0.2,
        "expected_gain": 0.01,
        "expected_cost": 0.001,
        "kyle_lambda_cost_uplift": 0.0,
        "candidate_size": 100.0,
        "holding_period": 4.0,
        "delta_safe": 0.0005,
        "ce_min": 0.0001,
        "entry_price": 100.0,
        "realized_vol_current": 0.02,
        "atr": 2.0,
        "scoring_version": "A_v1",
    }
    payload.update(overrides)
    return EngineAInput(**payload)


def test_emit_path_valid_case() -> None:
    output = run_engine_a(_good_inputs())

    assert output.decision == EngineADecision.EMIT
    assert output.no_trade_reasons == ()
    assert "engine_a.emit.valid" in output.reason_codes
    assert "engine_internal.engine_a.structure.favorable" in output.reason_codes
    assert "engine_a.structure.favorable" in output.reason_codes
    assert "engine_internal.engine_a.context.confirming" in output.reason_codes
    assert "engine_a.context.confirming" in output.reason_codes
    assert "economics.engine_a.cost.feasible" in output.reason_codes
    assert "engine_a.cost.feasible" in output.reason_codes
    assert "scoring.engine_a.conviction.high" in output.reason_codes
    assert "engine_a.conviction.high" in output.reason_codes
    assert output.invalidation is not None
    assert output.invalidation.has_invalidation is True
    assert output.log_entries[-1].event == "engine_a_signal_emitted"


def test_non_long_direction_branch() -> None:
    output = run_engine_a(_good_inputs(direction_score=0.0))

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.NON_LONG_DIRECTION,)
    assert output.reason_codes == (
        "engine_internal.engine_a.direction.non_long",
        "engine_a.input.non_long_direction",
    )
    assert output.log_entries[-1].event == "engine_a_no_trade"
    assert "direction_score=0.000 <= 0 - long-only" in output.log_entries[-1].reasons


def test_structure_unfavorable_branch() -> None:
    output = run_engine_a(_good_inputs(direction_score=0.1))

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.STRUCTURE_UNFAVORABLE,)
    assert output.reason_codes == (
        "engine_internal.engine_a.structure.unfavorable",
        "engine_a.structure.unfavorable",
    )
    assert output.structure_verdict.value == "unfavorable"
    assert output.log_entries[-1].event == "engine_a_no_trade"


def test_context_fatal_branch() -> None:
    output = run_engine_a(
        _good_inputs(
            regime_favorability=0.0,
            regime_confidence=0.0,
            pair_health=0.0,
            data_freshness=0.0,
            flow_coherence=0.0,
        )
    )

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.CONTEXT_FATAL,)
    assert output.reason_codes == (
        "engine_internal.engine_a.context.fatal",
        "engine_a.context.fatal",
    )
    assert output.context_verdict.value == "fatal"


def test_cost_infeasible_branch() -> None:
    output = run_engine_a(_good_inputs(expected_gain=0.001, expected_cost=0.001))

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.COST_INFEASIBLE,)
    assert "economics.engine_a.cost.infeasible" in output.reason_codes
    assert "engine_a.cost.infeasible" in output.reason_codes
    assert "engine_a.cost.break_even_not_cleared" in output.reason_codes
    assert output.cost_verdict.value == "infeasible"


def test_cost_marginal_branch() -> None:
    output = run_engine_a(_good_inputs(holding_period=30.0, expected_gain=0.003, expected_cost=0.001))

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.COST_MARGINAL,)
    assert "economics.engine_a.cost.marginal" in output.reason_codes
    assert "engine_a.cost.marginal" in output.reason_codes
    assert "engine_a.cost.ce_below_min" in output.reason_codes
    assert output.cost_verdict.value == "marginal"


def test_low_conviction_branch() -> None:
    output = run_engine_a(
        _good_inputs(
            continuation_score=0.6,
            structure_quality=0.6,
            zone_proximity=0.6,
            trend_stability=0.6,
            regime_favorability=0.4,
            regime_confidence=0.4,
            pair_health=0.4,
            data_freshness=0.4,
            flow_coherence=0.4,
            flow_score=0.0,
            cost_preference_score=0.0,
            delta_confirmation=0.5,
            competition_density=0.5,
        )
    )

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.LOW_CONVICTION,)
    assert output.reason_codes == (
        "scoring.engine_a.conviction.low_non_emittable",
        "engine_a.conviction.low_non_emittable",
    )
    assert output.conviction.value == "low"
    assert output.tier_suggestion.value == "no_trade"


def test_invalid_invalidation_branch_when_helper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> object:
        raise ValueError("synthetic invalidation failure")

    monkeypatch.setattr("engines.engine_a.engine_a_runner._evaluate_invalidation_stage", _boom)

    output = run_engine_a(_good_inputs())

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.INVALID_INVALIDATION,)
    assert output.reason_codes == (
        "hard_block.engine_a.invalidation.invalid_contract",
        "engine_a.invalidation.invalid_contract",
    )
    assert output.log_entries[-1].event == "engine_a_no_trade"
    assert "synthetic invalidation failure" in output.log_entries[-1].reasons


def test_ofi_flow_score_overrides_legacy_flow_channel() -> None:
    output = run_engine_a(_good_inputs(flow_score=0.1, ofi_flow_score=0.9))

    assert output.decision == EngineADecision.EMIT
    assert output.block_scores["flow"] == pytest.approx(0.9)
    assert output.block_scores["flow_legacy_score"] == pytest.approx(0.1)
    assert output.block_scores["flow_source_is_ofi"] == pytest.approx(1.0)
    assert output.block_scores["ofi_flow_score"] == pytest.approx(0.9)


def test_kyle_lambda_cost_uplift_applied_in_cost_stage() -> None:
    output = run_engine_a(
        _good_inputs(
            expected_gain=0.0017,
            expected_cost=0.0010,
            kyle_lambda_cost_uplift=0.0004,
        )
    )

    assert output.decision == EngineADecision.NO_TRADE
    assert output.no_trade_reasons == (NoTradeReason.COST_INFEASIBLE,)
    assert "engine_a.cost.kyle_lambda_uplift_applied" in output.reason_codes


def test_realized_kernel_vol_scale_overrides_trend_stability() -> None:
    output = run_engine_a(
        _good_inputs(
            trend_stability=0.1,
            realized_kernel_vol_scale=0.9,
        )
    )

    assert output.decision == EngineADecision.EMIT
    structure_logs = [entry for entry in output.log_entries if entry.event == "engine_a_structure_evaluated"]
    assert len(structure_logs) == 1
    assert structure_logs[0].block_scores["trend_stability"] == pytest.approx(0.9)
    assert structure_logs[0].block_scores["trend_stability_legacy_score"] == pytest.approx(0.1)
    assert structure_logs[0].block_scores["trend_stability_source_is_realized_kernel"] == pytest.approx(1.0)
    assert structure_logs[0].block_scores["realized_kernel_vol_scale"] == pytest.approx(0.9)


def test_engine_a_input_rejects_out_of_range_fields() -> None:
    with pytest.raises(ValidationError):
        _good_inputs(flow_score=1.5)
    with pytest.raises(ValidationError):
        _good_inputs(realized_kernel_vol_scale=-0.1)


def test_signal_reporter_status_is_explicit() -> None:
    assert ENGINE_A_SIGNAL_REPORTER_STATUS == "secondary_helper_non_canonical_flow"
    assert "NoTradeReason is canonical" in ENGINE_A_SIGNAL_REPORTER_STATUS_DETAIL
