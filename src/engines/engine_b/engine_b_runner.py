"""
Build-7 / engine_b / engine_b_runner
Canonical orchestrator for Engine B — Mean Reversion Intraday.

Single entry point. Produces EngineBOutput: a complete, audit-ready
object consumed by scoring_backbone, portfolio, and meta modules.

Pipeline:
0. Long-only guard (spot-halal)
1. Local mean estimation + z-score
2. Excess detection
3. Anti-breakout filter
4. Cost feasibility (stricter than A)
5. Conviction building (Tier 1-2 max)
6. Invalidation mapping (mean-reversion specific)
7. Assemble canonical output + structured logs
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from engines.engine_b.local_mean_estimator_b import (
    LocalMeanInput,
    estimate_local_mean,
)
from engines.engine_b.excess_detector_b import (
    ExcessInput,
    ExcessVerdict,
    detect_excess,
)
from engines.engine_b.anti_breakout_filter_b import (
    BreakoutInput,
    BreakoutVerdict,
    evaluate_breakout_risk,
)
from engines.engine_b.cost_feasibility_b import (
    CostInputB,
    CostVerdictB,
    check_cost_feasibility_b,
)
from engines.engine_b.conviction_builder_b import (
    ConvictionInputB,
    ConvictionLevelB,
    ENGINE_B_CONVICTION_CALIBRATION_STATUS,
    ENGINE_B_CONVICTION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    TierSuggestionB,
    build_conviction_b,
)
from engines.engine_b.invalidation_mapper_b import (
    InvalidationMapB,
    build_invalidation_b,
)
from engines.engine_b.signal_reporter_b import (
    SignalDecisionB,
    NoTradeReasonB,
)


class EngineBDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class EngineBLogEntry(BaseModel, frozen=True):
    """Structured log entry for Engine B — spec section 21."""
    event: str
    pair: str
    regime: str = ""
    local_mean: float = 0.0
    local_std: float = 0.0
    z_score: float = 0.0
    raw_score: float = 0.0
    penalized_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    expected_cost: float = 0.0
    expected_duration: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    conviction: str = ""
    tier: str = ""
    invalidation: str = ""
    holding_hours: float = 0.0
    reasons: tuple[str, ...] = ()
    scoring_version: str = ""
    calibration_profile_id: str = ENGINE_B_CONVICTION_PROFILE_ID
    calibration_status: str = ENGINE_B_CONVICTION_CALIBRATION_STATUS
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS


class EngineBOutput(BaseModel, frozen=True):
    """Complete canonical Engine B output — consumed by scoring/portfolio/meta.

    Note: correlation/risk budget (exposure, beta, cluster) is NOT checked here.
    It is enforced downstream by risk_backbone and scoring_backbone/ranking_router
    (portfolio_compatibility_checker). Engine B produces a candidate; the portfolio
    layer decides whether to accept it given current budget constraints.
    """
    pair: str
    engine_id: str = "engine_b"
    decision: EngineBDecision
    raw_score: float = 0.0
    penalized_score: float = 0.0  # raw_score - breakout_warning_penalty
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevelB = ConvictionLevelB.NONE
    tier_suggestion: TierSuggestionB = TierSuggestionB.NO_TRADE
    z_score: float = 0.0
    excess_score: float = 0.0
    breakout_score: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    expected_holding_hours: float = 0.0
    invalidation: InvalidationMapB | None = None
    scoring_version: str = ""
    calibration_profile_id: str = ENGINE_B_CONVICTION_PROFILE_ID
    calibration_status: str = ENGINE_B_CONVICTION_CALIBRATION_STATUS
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS
    no_trade_reasons: tuple[NoTradeReasonB, ...] = ()
    excess_verdict: ExcessVerdict = ExcessVerdict.NO_EXCESS
    breakout_verdict: BreakoutVerdict = BreakoutVerdict.CLEAR
    cost_verdict: CostVerdictB = CostVerdictB.INFEASIBLE
    log_entries: tuple[EngineBLogEntry, ...] = ()


class EngineBInput(BaseModel, frozen=True):
    """All inputs needed for a single Engine B evaluation."""
    # Price / mean inputs
    pair: str
    current_price: float
    local_mean: float  # μ_t^loc
    local_std: float  # σ_t^loc
    # Excess context
    structure_is_range: float = 0.5
    recent_expansion: float = 0.0
    # Anti-breakout inputs
    regime: str = ""
    regime_trend_strength: float = 0.0
    volume_anomaly: float = 0.0
    structural_break: float = 0.0
    continuation_momentum: float = 0.0
    microstructure_breakout_confirmation: float = 0.0
    sweep_score: float = 0.5
    absorption_score: float = 0.5
    poc_reversion_score: float = 0.5
    false_breakout_score: float = 0.5
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    # Context scores (for conviction)
    regime_favorability: float = 0.5
    pair_health: float = 0.5
    data_freshness: float = 0.5
    flow_coherence: float = 0.5
    # Cost inputs
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    candidate_size: float = 0.0
    holding_period: float = 2.0
    delta_safe: float = 0.0008
    ce_min: float = 0.0002
    # Meta
    scoring_version: str = ""


ENGINE_B_RUNNER_INPUT_DEFAULTS: dict[str, float | str] = {
    "structure_is_range": 0.5,
    "recent_expansion": 0.0,
    "regime": "",
    "regime_trend_strength": 0.0,
    "volume_anomaly": 0.0,
    "structural_break": 0.0,
    "continuation_momentum": 0.0,
    "microstructure_breakout_confirmation": 0.0,
    "sweep_score": 0.5,
    "absorption_score": 0.5,
    "poc_reversion_score": 0.5,
    "false_breakout_score": 0.5,
    "execution_fragility": 0.0,
    "market_toxicity": 0.0,
    "spread_regime_penalty": 0.0,
    "regime_favorability": 0.5,
    "pair_health": 0.5,
    "data_freshness": 0.5,
    "flow_coherence": 0.5,
    "expected_gain": 0.0,
    "expected_cost": 0.0,
    "candidate_size": 0.0,
    "holding_period": 2.0,
    "delta_safe": 0.0008,
    "ce_min": 0.0002,
    "scoring_version": "",
}
ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT = 4.0
ENGINE_B_RUNNER_COST_RATIO_EPSILON = 1e-9
ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT = 0.30

EngineBInput.model_fields["structure_is_range"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["structure_is_range"]
EngineBInput.model_fields["recent_expansion"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["recent_expansion"]
EngineBInput.model_fields["regime"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["regime"]
EngineBInput.model_fields["regime_trend_strength"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["regime_trend_strength"]
EngineBInput.model_fields["volume_anomaly"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["volume_anomaly"]
EngineBInput.model_fields["structural_break"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["structural_break"]
EngineBInput.model_fields["continuation_momentum"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["continuation_momentum"]
EngineBInput.model_fields["microstructure_breakout_confirmation"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["microstructure_breakout_confirmation"]
EngineBInput.model_fields["sweep_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["sweep_score"]
EngineBInput.model_fields["absorption_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["absorption_score"]
EngineBInput.model_fields["poc_reversion_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["poc_reversion_score"]
EngineBInput.model_fields["false_breakout_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["false_breakout_score"]
EngineBInput.model_fields["execution_fragility"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["execution_fragility"]
EngineBInput.model_fields["market_toxicity"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["market_toxicity"]
EngineBInput.model_fields["spread_regime_penalty"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["spread_regime_penalty"]
EngineBInput.model_fields["regime_favorability"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["regime_favorability"]
EngineBInput.model_fields["pair_health"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["pair_health"]
EngineBInput.model_fields["data_freshness"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["data_freshness"]
EngineBInput.model_fields["flow_coherence"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["flow_coherence"]
EngineBInput.model_fields["expected_gain"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["expected_gain"]
EngineBInput.model_fields["expected_cost"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["expected_cost"]
EngineBInput.model_fields["candidate_size"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["candidate_size"]
EngineBInput.model_fields["holding_period"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["holding_period"]
EngineBInput.model_fields["delta_safe"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["delta_safe"]
EngineBInput.model_fields["ce_min"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["ce_min"]
EngineBInput.model_fields["scoring_version"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["scoring_version"]


def run_engine_b(inputs: EngineBInput) -> EngineBOutput:
    """Execute the full Engine B pipeline and produce canonical output.

    Pipeline:
    0. Long-only guard — z_score must be negative (price below mean = buy dip)
    1. Local mean estimation
    2. Excess detection
    3. Anti-breakout filter
    4. Cost feasibility
    5. Conviction building
    6. Invalidation mapping
    7. Assemble output + logs
    """
    logs: list[EngineBLogEntry] = []
    no_trade_reasons: list[NoTradeReasonB] = []

    # ── 1. Local mean estimation ──
    mean_result = estimate_local_mean(LocalMeanInput(
        pair=inputs.pair,
        current_price=inputs.current_price,
        local_mean=inputs.local_mean,
        local_std=inputs.local_std,
    ))
    logs.append(EngineBLogEntry(
        event="engine_b_mean_estimated",
        pair=inputs.pair,
        regime=inputs.regime,
        local_mean=mean_result.local_mean,
        local_std=mean_result.local_std,
        z_score=mean_result.z_score,
    ))

    if not mean_result.valid:
        no_trade_reasons.append(NoTradeReasonB.INVALID_DISPERSION)
        logs.append(EngineBLogEntry(
            event="engine_b_no_trade",
            pair=inputs.pair,
            reasons=("invalid dispersion",),
        ))
        return EngineBOutput(
            pair=inputs.pair,
            decision=EngineBDecision.NO_TRADE,
            z_score=mean_result.z_score,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 0. Long-only guard ──
    # For mean reversion long-only: z_score must be negative (price below mean)
    # Positive z_score means price above mean — would require short to revert
    if mean_result.z_score > 0:
        no_trade_reasons.append(NoTradeReasonB.NON_LONG_DIRECTION)
        logs.append(EngineBLogEntry(
            event="engine_b_no_trade",
            pair=inputs.pair,
            z_score=mean_result.z_score,
            reasons=(f"z_score={mean_result.z_score:.3f} > 0 — long-only, cannot short",),
        ))
        return EngineBOutput(
            pair=inputs.pair,
            decision=EngineBDecision.NO_TRADE,
            z_score=mean_result.z_score,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 2. Excess detection ── (use abs z for detection)
    excess = detect_excess(ExcessInput(
        pair=inputs.pair,
        z_score=mean_result.z_score,
        z_score_valid=mean_result.valid,
        structure_is_range=inputs.structure_is_range,
        recent_expansion=inputs.recent_expansion,
    ))
    logs.append(EngineBLogEntry(
        event="engine_b_excess_evaluated",
        pair=inputs.pair,
        z_score=mean_result.z_score,
        raw_score=excess.excess_score,
        reasons=(excess.reason,) if excess.reason else (),
    ))

    if excess.verdict in (ExcessVerdict.NO_EXCESS, ExcessVerdict.INVALID):
        no_trade_reasons.append(NoTradeReasonB.NO_EXCESS)
        logs.append(EngineBLogEntry(
            event="engine_b_no_trade",
            pair=inputs.pair,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineBOutput(
            pair=inputs.pair,
            decision=EngineBDecision.NO_TRADE,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            excess_verdict=excess.verdict,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 3. Anti-breakout filter ──
    breakout = evaluate_breakout_risk(BreakoutInput(
        pair=inputs.pair,
        regime_trend_strength=inputs.regime_trend_strength,
        volume_anomaly=inputs.volume_anomaly,
        structural_break=inputs.structural_break,
        continuation_momentum=inputs.continuation_momentum,
        microstructure_breakout_confirmation=inputs.microstructure_breakout_confirmation,
    ))
    logs.append(EngineBLogEntry(
        event="engine_b_breakout_evaluated",
        pair=inputs.pair,
        raw_score=breakout.breakout_score,
        reasons=(breakout.reason,) if breakout.reason else (),
    ))

    if breakout.verdict == BreakoutVerdict.BLOCKED:
        no_trade_reasons.append(NoTradeReasonB.BREAKOUT_BLOCKED)
        logs.append(EngineBLogEntry(
            event="engine_b_no_trade",
            pair=inputs.pair,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineBOutput(
            pair=inputs.pair,
            decision=EngineBDecision.NO_TRADE,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            breakout_score=breakout.breakout_score,
            excess_verdict=excess.verdict,
            breakout_verdict=breakout.verdict,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 4. Cost feasibility ──
    cost = check_cost_feasibility_b(CostInputB(
        pair=inputs.pair,
        expected_gain=inputs.expected_gain,
        expected_cost=inputs.expected_cost,
        candidate_size=inputs.candidate_size,
        holding_period=inputs.holding_period,
        delta_safe=inputs.delta_safe,
        ce_min=inputs.ce_min,
    ))
    logs.append(EngineBLogEntry(
        event="engine_b_cost_checked",
        pair=inputs.pair,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        reasons=(cost.reason,) if cost.reason else (),
    ))

    if cost.verdict == CostVerdictB.INFEASIBLE:
        no_trade_reasons.append(NoTradeReasonB.COST_INFEASIBLE)
        logs.append(EngineBLogEntry(
            event="engine_b_no_trade",
            pair=inputs.pair,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineBOutput(
            pair=inputs.pair,
            decision=EngineBDecision.NO_TRADE,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            breakout_score=breakout.breakout_score,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
            excess_verdict=excess.verdict,
            breakout_verdict=breakout.verdict,
            cost_verdict=cost.verdict,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 5. Conviction building ──
    # Context score: regime, health, freshness, and flow coherence all matter for B.
    context_score = (
        inputs.regime_favorability
        + inputs.pair_health
        + inputs.data_freshness
        + inputs.flow_coherence
    ) / ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT

    conviction = build_conviction_b(ConvictionInputB(
        pair=inputs.pair,
        excess_score=excess.excess_score,
        structure_score=inputs.structure_is_range,
        context_score=context_score,
        cost_preference_score=1.0 - min(
            inputs.expected_cost / max(inputs.expected_gain, ENGINE_B_RUNNER_COST_RATIO_EPSILON),
            1.0,
        ),
        sweep_score=inputs.sweep_score,
        absorption_score=inputs.absorption_score,
        poc_reversion_score=inputs.poc_reversion_score,
        false_breakout_score=inputs.false_breakout_score,
        execution_fragility=inputs.execution_fragility,
        market_toxicity=inputs.market_toxicity,
        spread_regime_penalty=inputs.spread_regime_penalty,
        scoring_version=inputs.scoring_version,
    ))
    logs.append(EngineBLogEntry(
        event="engine_b_conviction_built",
        pair=inputs.pair,
        raw_score=conviction.raw_score,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
    ))

    if conviction.conviction == ConvictionLevelB.NONE:
        no_trade_reasons.append(NoTradeReasonB.CONVICTION_NONE)
        logs.append(EngineBLogEntry(
            event="engine_b_no_trade",
            pair=inputs.pair,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineBOutput(
            pair=inputs.pair,
            decision=EngineBDecision.NO_TRADE,
            raw_score=conviction.raw_score,
            block_scores=conviction.block_scores,
            conviction=conviction.conviction,
            tier_suggestion=conviction.tier_suggestion,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            breakout_score=breakout.breakout_score,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
            excess_verdict=excess.verdict,
            breakout_verdict=breakout.verdict,
            cost_verdict=cost.verdict,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 5b. Breakout WARNING penalty ──
    # WARNING doesn't block, but must penalize the score explicitly.
    # Penalty proportional to breakout_score (already in [0, 1]).
    breakout_penalty = 0.0
    if breakout.verdict == BreakoutVerdict.WARNING:
        breakout_penalty = ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT * breakout.breakout_score
        logs.append(EngineBLogEntry(
            event="engine_b_breakout_penalty",
            pair=inputs.pair,
            raw_score=conviction.raw_score,
            penalized_score=conviction.raw_score - breakout_penalty,
            reasons=(
                f"WARNING penalty: -{breakout_penalty:.4f} "
                f"(weight={ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT} x score={breakout.breakout_score:.3f})",
            ),
        ))

    penalized = conviction.raw_score - breakout_penalty

    # ── 6. Invalidation mapping ──
    inv = build_invalidation_b(
        pair=inputs.pair,
        entry_price=inputs.current_price,
        local_mean=inputs.local_mean,
        local_std=inputs.local_std,
        holding_hours=inputs.holding_period,
    )
    logs.append(EngineBLogEntry(
        event="engine_b_invalidation_built",
        pair=inputs.pair,
        invalidation=inv.primary_invalidation,
        holding_hours=inv.max_holding_hours,
    ))

    # ── 7. EMIT ──
    logs.append(EngineBLogEntry(
        event="engine_b_signal_emitted",
        pair=inputs.pair,
        regime=inputs.regime,
        local_mean=mean_result.local_mean,
        local_std=mean_result.local_std,
        z_score=mean_result.z_score,
        raw_score=conviction.raw_score,
        penalized_score=penalized,
        block_scores=conviction.block_scores,
        expected_cost=cost.expected_cost,
        expected_duration=inputs.holding_period,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
        invalidation=inv.primary_invalidation,
        holding_hours=inv.max_holding_hours,
        scoring_version=inputs.scoring_version,
    ))

    return EngineBOutput(
        pair=inputs.pair,
        decision=EngineBDecision.EMIT,
        raw_score=conviction.raw_score,
        penalized_score=penalized,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction,
        tier_suggestion=conviction.tier_suggestion,
        z_score=mean_result.z_score,
        excess_score=excess.excess_score,
        breakout_score=breakout.breakout_score,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        expected_holding_hours=inv.max_holding_hours,
        invalidation=inv,
        excess_verdict=excess.verdict,
        breakout_verdict=breakout.verdict,
        cost_verdict=cost.verdict,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )
