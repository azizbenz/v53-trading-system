from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Callable

from engines.engine_a.engine_a_runner import EngineADecision, EngineAInput, run_engine_a
from engines.engine_b.engine_b_runner import EngineBDecision, EngineBInput, run_engine_b
from engines.engine_c.engine_c_runner import EngineCDecision, EngineCInput, run_engine_c
from engines.engine_d.engine_d_runner import EngineDDecision, EngineDInput, run_engine_d


def _enum_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


@dataclass(frozen=True)
class SyntheticEngineCaseResult:
    engine_id: str
    case_id: str
    objective: str
    expected_decision: str
    actual_decision: str
    ok: bool
    no_trade_reasons: tuple[str, ...]
    reason_codes: tuple[str, ...]
    invalidation_present: bool


@dataclass(frozen=True)
class SyntheticEngineViabilityReport:
    schema_version: str
    generated_at: str
    diagnostic_only: bool
    overall_ok: bool
    cases: tuple[SyntheticEngineCaseResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "diagnostic_only": self.diagnostic_only,
            "overall_ok": self.overall_ok,
            "cases": [asdict(item) for item in self.cases],
        }


@dataclass(frozen=True)
class _SyntheticCase:
    engine_id: str
    case_id: str
    objective: str
    expected_decision: str
    runner: Callable[[object], object]
    build_input: Callable[[], object]


def _engine_a_emit_inputs() -> EngineAInput:
    return EngineAInput(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.8,
        structure_quality=0.8,
        zone_proximity=0.7,
        trend_stability=0.8,
        regime="trending_up",
        regime_favorability=0.8,
        regime_confidence=0.8,
        pair_health=0.8,
        data_freshness=0.9,
        flow_coherence=0.8,
        flow_score=0.8,
        ofi_flow_score=None,
        cost_preference_score=0.8,
        delta_confirmation=0.9,
        competition_density=0.2,
        expected_gain=0.01,
        expected_cost=0.001,
        kyle_lambda_cost_uplift=0.0,
        candidate_size=100.0,
        holding_period=4.0,
        delta_safe=0.0005,
        ce_min=0.0001,
        entry_price=100.0,
        realized_vol_current=0.02,
        atr=2.0,
        scoring_version="A_v1",
    )


def _engine_a_non_long_inputs() -> EngineAInput:
    return _engine_a_emit_inputs().model_copy(update={"direction_score": 0.0})


def _engine_b_emit_inputs() -> EngineBInput:
    return EngineBInput(
        pair="BTCUSDT",
        current_price=97.0,
        local_mean=100.0,
        local_std=1.5,
        structure_is_range=0.7,
        recent_expansion=0.1,
        regime="range",
        regime_trend_strength=0.1,
        volume_anomaly=0.1,
        structural_break=0.0,
        continuation_momentum=0.1,
        microstructure_breakout_confirmation=0.0,
        regime_favorability=0.7,
        pair_health=0.8,
        data_freshness=0.9,
        flow_coherence=0.8,
        expected_gain=0.003,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=2.0,
        scoring_version="B_v1",
    )


def _engine_b_non_long_inputs() -> EngineBInput:
    return _engine_b_emit_inputs().model_copy(update={"current_price": 103.0})


def _engine_c_emit_inputs() -> EngineCInput:
    return EngineCInput(
        pair="BTCUSDT",
        breakout_strength=0.88,
        range_quality=0.78,
        compression_quality=0.74,
        volume_confirmation=0.81,
        followthrough_room=0.76,
        extension_pct=0.24,
        retrace_risk=0.18,
        rejection_wick_ratio=0.12,
        regime="breakout",
        regime_favorability=0.80,
        pair_health=0.92,
        data_freshness=0.95,
        flow_coherence=0.79,
        cumulative_ofi=24.0,
        queue_pressure=0.36,
        vpin=0.22,
        kyle_lambda=0.0012,
        continuation_ofi_min=0.0,
        continuation_queue_min=0.0,
        continuation_vpin_max=0.35,
        continuation_kyle_lambda_max=0.01,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        range_low=97.5,
        range_high=101.0,
        realized_vol_current=2.0 / 105.0,
        realized_vol_at_break=2.0 / 105.0,
        atr=2.0,
        engine_a_overlap_ratio=0.28,
        marginal_portfolio_gain=9.2,
        covered_share_by_engine_a=0.22,
        keff_contribution=0.31,
        scoring_version="engine_c.v1",
    )


def _engine_c_unconfirmed_micro_inputs() -> EngineCInput:
    return _engine_c_emit_inputs().model_copy(
        update={"cumulative_ofi": None, "continuation_ofi_min": 5.0}
    )


def _engine_d_emit_inputs() -> EngineDInput:
    return EngineDInput(
        pair="BTCUSDT",
        origin_context_id="ctx-btc-01",
        origin_trade_id="trade-btc-01",
        link_type="prior_trade",
        first_episode_id="episode-btc-01",
        first_episode_engine_id="engine_a",
        first_episode_close_reason="time_stop",
        consecutive_stop_count=0,
        last_fresh_a_detection_at_ns=1_700_000_100_000_000_000,
        anti_revenge_state="reset_required",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        structure_reformed_detected=True,
        regime="trending_up",
        regime_favorability=0.78,
        pair_health=0.90,
        data_freshness=0.94,
        flow_coherence=0.81,
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
        holding_period=2.0,
        entry_price=104.0,
        reentry_anchor_price=101.5,
        realized_vol_current=1.8 / 104.0,
        realized_vol_post_close=1.8 / 104.0,
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
        scoring_version="engine_d.v1",
    )


def _engine_d_history_weak_inputs() -> EngineDInput:
    return _engine_d_emit_inputs().model_copy(update={"prior_trade_quality": 0.2})


def _synthetic_cases() -> tuple[_SyntheticCase, ...]:
    return (
        _SyntheticCase(
            engine_id="engine_a",
            case_id="emit_viable_candidate",
            objective="prove engine_a can emit on a plausible long candidate",
            expected_decision=_enum_value(EngineADecision.EMIT),
            runner=run_engine_a,
            build_input=_engine_a_emit_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_a",
            case_id="reject_non_long_candidate",
            objective="prove engine_a rejects a deterministic non-long candidate",
            expected_decision=_enum_value(EngineADecision.NO_TRADE),
            runner=run_engine_a,
            build_input=_engine_a_non_long_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_b",
            case_id="emit_viable_candidate",
            objective="prove engine_b can emit on a plausible mean-reversion candidate",
            expected_decision=_enum_value(EngineBDecision.EMIT),
            runner=run_engine_b,
            build_input=_engine_b_emit_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_b",
            case_id="reject_non_long_candidate",
            objective="prove engine_b rejects a deterministic non-long candidate",
            expected_decision=_enum_value(EngineBDecision.NO_TRADE),
            runner=run_engine_b,
            build_input=_engine_b_non_long_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_c",
            case_id="emit_viable_candidate",
            objective="prove engine_c can emit when breakout and microstructure align",
            expected_decision=_enum_value(EngineCDecision.EMIT),
            runner=run_engine_c,
            build_input=_engine_c_emit_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_c",
            case_id="reject_unconfirmed_microstructure",
            objective="prove engine_c rejects a breakout candidate when core microstructure proof is missing",
            expected_decision=_enum_value(EngineCDecision.NO_TRADE),
            runner=run_engine_c,
            build_input=_engine_c_unconfirmed_micro_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_d",
            case_id="emit_viable_candidate",
            objective="prove engine_d can emit when prior-trade context and economics are healthy",
            expected_decision=_enum_value(EngineDDecision.EMIT),
            runner=run_engine_d,
            build_input=_engine_d_emit_inputs,
        ),
        _SyntheticCase(
            engine_id="engine_d",
            case_id="reject_history_weak_candidate",
            objective="prove engine_d rejects a candidate with weak prior-trade quality",
            expected_decision=_enum_value(EngineDDecision.NO_TRADE),
            runner=run_engine_d,
            build_input=_engine_d_history_weak_inputs,
        ),
    )


def run_synthetic_engine_viability_harness() -> SyntheticEngineViabilityReport:
    results: list[SyntheticEngineCaseResult] = []
    for case in _synthetic_cases():
        output = case.runner(case.build_input())
        actual_decision = _enum_value(getattr(output, "decision"))
        results.append(
            SyntheticEngineCaseResult(
                engine_id=case.engine_id,
                case_id=case.case_id,
                objective=case.objective,
                expected_decision=case.expected_decision,
                actual_decision=actual_decision,
                ok=actual_decision == case.expected_decision,
                no_trade_reasons=tuple(
                    _enum_value(item) for item in tuple(getattr(output, "no_trade_reasons", ()))
                ),
                reason_codes=tuple(str(item) for item in tuple(getattr(output, "reason_codes", ()))),
                invalidation_present=getattr(output, "invalidation", None) is not None,
            )
        )
    return SyntheticEngineViabilityReport(
        schema_version="strategy_ladder.synthetic_engine_viability.v1",
        generated_at=datetime.now(tz=UTC).isoformat(),
        diagnostic_only=True,
        overall_ok=all(item.ok for item in results),
        cases=tuple(results),
    )


__all__ = [
    "SyntheticEngineCaseResult",
    "SyntheticEngineViabilityReport",
    "run_synthetic_engine_viability_harness",
]
