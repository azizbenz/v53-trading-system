#!/usr/bin/env python3
"""Engine-scoped Shadow demo evaluation helpers for the governed LOCAL_REPLAY runner."""

from __future__ import annotations

from pathlib import Path

from engines.engine_a import EngineAInput, EngineARuntime, EngineARuntimeInput, EngineARuntimeStatus
from engines.engine_b import EngineBInput, EngineBRuntime, EngineBRuntimeInput, EngineBRuntimeStatus
from engines.engine_c import EngineCInput, EngineCRuntime, EngineCRuntimeInput, EngineCRuntimeStatus
from engines.engine_d import EngineDInput, EngineDRuntime, EngineDRuntimeInput, EngineDRuntimeStatus
from local_replay_shadow_models import ShadowEngineRuntimeEvidence
from protocols import ShadowComponentVerdict
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringRuntime

REPO_ROOT = Path(__file__).resolve().parent.parent

def _shadow_penalty_registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(
        PenaltyDefinition(
            penalty_id="shadow_context_soft",
            name="Shadow context soft",
            penalty_type=PenaltyType.SCORE,
        )
    )
    registry.register(
        PenaltyDefinition(
            penalty_id="breakout_warning",
            name="Breakout warning",
            penalty_type=PenaltyType.SCORE,
        )
    )
    return registry


def _shadow_scoring_runtime() -> ScoringRuntime:
    return ScoringRuntime(_shadow_penalty_registry())


def _shadow_risk_runtime() -> RiskRuntime:
    return RiskRuntime(
        RiskLimits(
            gross_cap=10_000.0,
            position_cap=4_000.0,
            loss_cap=1_000.0,
            beta_cap=10_000.0,
            cluster_cap=10_000.0,
        )
    )


def _shadow_portfolio_state() -> PortfolioState:
    return PortfolioState(
        remaining_gross_capacity=10_000.0,
        remaining_loss_capacity=1_000.0,
        remaining_beta_capacity=10_000.0,
        remaining_cluster_capacity={
            "btc_majors": 10_000.0,
            "eth_majors": 10_000.0,
        },
    )


def _expected_edge_bps(*, expected_cost: float, ce_expected: float, holding_hours: float) -> float:
    return round((expected_cost + ce_expected * holding_hours) * 10_000, 3)


def _scoring_reason_codes(engine_result: object) -> tuple[str, ...]:
    scoring_audit = getattr(engine_result, "scoring_audit", None)
    if scoring_audit is None:
        return ()
    explainability = getattr(scoring_audit, "explainability", None)
    if explainability is None:
        return ()
    codes = list(getattr(explainability, "hard_block_codes", ()))
    codes.extend(
        f"PEN_{penalty_id.upper()}"
        for penalty_id in getattr(explainability, "dominant_score_penalty_ids", ())
    )
    codes.extend(
        f"SIZE_{penalty_id.upper()}"
        for penalty_id in getattr(explainability, "dominant_size_penalty_ids", ())
    )
    portfolio_verdict = getattr(explainability, "portfolio_verdict_code", "")
    if portfolio_verdict:
        codes.append(f"PORTFOLIO_{portfolio_verdict.upper()}")
    selection_outcome = getattr(explainability, "selection_outcome_code", "")
    if selection_outcome:
        codes.append(f"SELECTION_{selection_outcome.upper()}")
    return tuple(dict.fromkeys(codes))


def _risk_reason_codes(engine_result: object) -> tuple[str, ...]:
    risk_evaluation = getattr(engine_result, "risk_evaluation", None)
    if risk_evaluation is None:
        return ()
    reason_details = getattr(risk_evaluation, "reason_details", ())
    return tuple(dict.fromkeys(detail.code for detail in reason_details))


def _scoring_summary(engine_result: object) -> str:
    scoring_audit = getattr(engine_result, "scoring_audit", None)
    if scoring_audit is None:
        return ""
    explainability = getattr(scoring_audit, "explainability", None)
    if explainability is None:
        return ""
    return getattr(explainability, "summary", "")


def _risk_summary(engine_result: object) -> str:
    risk_evaluation = getattr(engine_result, "risk_evaluation", None)
    if risk_evaluation is None:
        return ""
    return getattr(risk_evaluation, "explain_summary", "")


def _shadow_circuit_breaker(engine_id: str) -> EmergencyCircuitBreaker:
    state_dir = REPO_ROOT / "build" / "local_replay_shadow_breakers" / engine_id
    state_dir.mkdir(parents=True, exist_ok=True)
    return EmergencyCircuitBreaker(state_dir=state_dir)


def _evaluate_engine_a_shadow() -> ShadowEngineRuntimeEvidence:
    engine_a_runtime = EngineARuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_a"),
    )
    engine_a_result = engine_a_runtime.evaluate(
        EngineARuntimeInput(
            engine_inputs=EngineAInput(
                pair="BTCUSDT",
                direction_score=0.8,
                continuation_score=0.9,
                structure_quality=0.85,
                zone_proximity=0.7,
                trend_stability=0.8,
                regime="trending_up",
                regime_favorability=0.9,
                regime_confidence=0.8,
                pair_health=0.9,
                data_freshness=0.95,
                flow_coherence=0.8,
                flow_score=0.4,
                cost_preference_score=0.5,
                expected_gain=0.005,
                expected_cost=0.001,
                candidate_size=1_000.0,
                holding_period=4.0,
                entry_price=50_000.0,
                atr=500.0,
                scoring_version="engine_a.shadow.v1",
            ),
            timestamp_ms=1_700_000_000_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=1_000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.8,
            cluster_id="btc_majors",
        ),
        now=5.0,
    )
    return ShadowEngineRuntimeEvidence(
        component_id="engine_a",
        pair=engine_a_result.engine_output.pair,
        runtime_status=engine_a_result.status.value,
        emitted_signal=engine_a_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_a_result.status == EngineARuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_a_result.status.value} / pair={engine_a_result.engine_output.pair} / "
            f"structure={engine_a_result.engine_output.structure_verdict.value} / "
            f"context={engine_a_result.engine_output.context_verdict.value} / "
            f"conviction={engine_a_result.engine_output.conviction.value}"
        ),
        expected_cost_bps=round(engine_a_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_a_result.engine_output.expected_cost,
            ce_expected=engine_a_result.engine_output.ce_expected,
            holding_hours=engine_a_result.engine_output.holding_hours,
        ),
        ce_expected=engine_a_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_a_result),
        risk_summary=_risk_summary(engine_a_result),
        scoring_reason_codes=_scoring_reason_codes(engine_a_result),
        risk_reason_codes=_risk_reason_codes(engine_a_result),
        details=engine_a_result.model_dump(mode="json"),
    )


def _evaluate_engine_b_shadow() -> ShadowEngineRuntimeEvidence:
    engine_b_runtime = EngineBRuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_b"),
    )
    engine_b_result = engine_b_runtime.evaluate(
        EngineBRuntimeInput(
            engine_inputs=EngineBInput(
                pair="ETHUSDT",
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
                scoring_version="engine_b.shadow.v1",
            ),
            timestamp_ms=1_700_000_030_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=1_000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.7,
            cluster_id="eth_majors",
        ),
        now=10.0,
    )
    return ShadowEngineRuntimeEvidence(
        component_id="engine_b",
        pair=engine_b_result.engine_output.pair,
        runtime_status=engine_b_result.status.value,
        emitted_signal=engine_b_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_b_result.status == EngineBRuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_b_result.status.value} / pair={engine_b_result.engine_output.pair} / "
            f"z_score={engine_b_result.engine_output.z_score:.3f} / "
            f"breakout={engine_b_result.engine_output.breakout_verdict.value} / "
            f"conviction={engine_b_result.engine_output.conviction.value}"
        ),
        expected_cost_bps=round(engine_b_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_b_result.engine_output.expected_cost,
            ce_expected=engine_b_result.engine_output.ce_expected,
            holding_hours=engine_b_result.engine_output.expected_holding_hours,
        ),
        ce_expected=engine_b_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_b_result),
        risk_summary=_risk_summary(engine_b_result),
        scoring_reason_codes=_scoring_reason_codes(engine_b_result),
        risk_reason_codes=_risk_reason_codes(engine_b_result),
        details=engine_b_result.model_dump(mode="json"),
    )


def _evaluate_engine_c_shadow() -> ShadowEngineRuntimeEvidence:
    engine_c_runtime = EngineCRuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_c"),
    )
    engine_c_result = engine_c_runtime.evaluate(
        EngineCRuntimeInput(
            engine_inputs=EngineCInput(
                pair="BTCUSDT",
                breakout_strength=0.88,
                range_quality=0.79,
                compression_quality=0.76,
                volume_confirmation=0.82,
                followthrough_room=0.78,
                extension_pct=0.23,
                retrace_risk=0.16,
                rejection_wick_ratio=0.11,
                regime="breakout",
                regime_favorability=0.81,
                pair_health=0.93,
                data_freshness=0.96,
                flow_coherence=0.84,
                expected_gain=0.0115,
                expected_cost=0.0023,
                candidate_size=1_000.0,
                holding_period=3.0,
                entry_price=105.0,
                breakout_level=101.0,
                range_low=97.5,
                range_high=101.0,
                atr=2.0,
                engine_a_overlap_ratio=0.28,
                marginal_portfolio_gain=9.2,
                covered_share_by_engine_a=0.22,
                keff_contribution=0.31,
                scoring_version="engine_c.v1",
            ),
            timestamp_ms=1_700_000_000_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=1_000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.8,
            cluster_id="btc_majors",
        ),
        now=10.0,
    )
    return ShadowEngineRuntimeEvidence(
        component_id="engine_c",
        pair=engine_c_result.engine_output.pair,
        runtime_status=engine_c_result.status.value,
        emitted_signal=engine_c_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_c_result.status == EngineCRuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_c_result.status.value} / pair={engine_c_result.engine_output.pair} / "
            f"breakout_type={engine_c_result.engine_output.breakout_type} / "
            f"duplication_with_a={engine_c_result.engine_output.duplication_overlap_with_engine_a:.2f} / "
            f"keff={engine_c_result.engine_output.keff_contribution:.2f}"
        ),
        expected_cost_bps=round(engine_c_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_c_result.engine_output.expected_cost,
            ce_expected=engine_c_result.engine_output.ce_expected,
            holding_hours=engine_c_result.engine_output.holding_hours,
        ),
        ce_expected=engine_c_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_c_result),
        risk_summary=_risk_summary(engine_c_result),
        scoring_reason_codes=_scoring_reason_codes(engine_c_result),
        risk_reason_codes=_risk_reason_codes(engine_c_result),
        details=engine_c_result.model_dump(mode="json"),
    )


def _evaluate_engine_d_shadow() -> ShadowEngineRuntimeEvidence:
    engine_d_runtime = EngineDRuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_d"),
    )
    engine_d_result = engine_d_runtime.evaluate(
        EngineDRuntimeInput(
            engine_inputs=EngineDInput(
                pair="ETHUSDT",
                origin_context_id="ctx-eth-breakout-01",
                origin_trade_id="trade-eth-01",
                link_type="prior_trade",
                prior_trade_quality=0.86,
                reformation_quality=0.79,
                pullback_quality=0.75,
                continuation_room=0.71,
                concentration_headroom=0.81,
                marginal_edge=0.74,
                reentry_lateness=0.17,
                structure_reformed_detected=True,
                regime="trending_up",
                regime_favorability=0.79,
                pair_health=0.91,
                data_freshness=0.95,
                flow_coherence=0.82,
                expected_gain=0.0095,
                expected_cost=0.0020,
                candidate_size=800.0,
                holding_period=2.0,
                entry_price=104.0,
                reentry_anchor_price=101.5,
                atr=1.8,
                duplication_overlap_with_engine_a=0.24,
                marginal_portfolio_gain=6.0,
                covered_share_by_engine_a=0.18,
                scoring_version="engine_d.v1",
            ),
            timestamp_ms=1_700_000_060_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=800.0,
            projected_loss=40.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.7,
            cluster_id="eth_majors",
        ),
        now=20.0,
    )
    return ShadowEngineRuntimeEvidence(
        component_id="engine_d",
        pair=engine_d_result.engine_output.pair,
        runtime_status=engine_d_result.status.value,
        emitted_signal=engine_d_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_d_result.status == EngineDRuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_d_result.status.value} / pair={engine_d_result.engine_output.pair} / "
            f"origin={engine_d_result.engine_output.origin_trade_id or engine_d_result.engine_output.origin_context_id} / "
            f"link_type={engine_d_result.engine_output.link_type} / "
            f"duplication_with_a={engine_d_result.engine_output.duplication_overlap_with_engine_a:.2f}"
        ),
        expected_cost_bps=round(engine_d_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_d_result.engine_output.expected_cost,
            ce_expected=engine_d_result.engine_output.ce_expected,
            holding_hours=engine_d_result.engine_output.holding_hours,
        ),
        ce_expected=engine_d_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_d_result),
        risk_summary=_risk_summary(engine_d_result),
        scoring_reason_codes=_scoring_reason_codes(engine_d_result),
        risk_reason_codes=_risk_reason_codes(engine_d_result),
        details=engine_d_result.model_dump(mode="json"),
    )


def _run_engine_shadow_evaluations() -> tuple[ShadowEngineRuntimeEvidence, ...]:
    return (
        _evaluate_engine_a_shadow(),
        _evaluate_engine_b_shadow(),
        _evaluate_engine_c_shadow(),
        _evaluate_engine_d_shadow(),
    )
