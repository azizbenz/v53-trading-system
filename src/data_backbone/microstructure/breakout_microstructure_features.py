"""Breakout microstructure features — NEUTRAL layer primitives.

Pure microstructure feature computation. Engine-agnostic. Reusable by
engine_a (breakout detection), engine_c (breakout continuation), or any
future engine needing breakout/continuation microstructure scoring.

Doctrine V5.3 — microstructure-only :
  - OFI / aggressive buy-sell pressure
  - queue pressure / book imbalance
  - walls and liquidity gap detection
  - spread freshness / dynamics
  - realized volatility (Yang-Zhang / Garman-Klass class)
  - microprice stability
  - VPIN / PIN toxicity
  - adverse selection risk

Forbidden as primary signal :
  - Fibonacci retrace probability
  - Bollinger squeeze as primary compression signal
  - ATR projection as followthrough proxy
  - slope ratio alone as breakout strength
  - simple volume moving average as confirmation

This module produces 7 normalized scores in [0, 1] with full provenance
envelopes. Engine-specific MAPPING to engine input contracts (e.g.
EngineCInput) lives in the engine package, not here. See:
  - `engines/engine_c/structure_resolver_c.py` :
    `build_engine_c_input_from_breakout_features()`

Layer separation rationale : neutral microstructure scoring + engine-aware
mapping = clean dependency direction (engines can depend on data_backbone
but not vice-versa).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Per-field freshness enum aligned with audit C5 calibration
FRESHNESS_FRESH = "MICROSTRUCTURE_INPUT_FRESH"
FRESHNESS_STALE = "MICROSTRUCTURE_INPUT_STALE_RESEARCH_ONLY"
FRESHNESS_MISSING = "MICROSTRUCTURE_INPUT_MISSING"
FRESHNESS_NOT_PROVEN = "MICROSTRUCTURE_INPUT_NOT_PROVEN"


@dataclass(frozen=True)
class BreakoutMicrostructureField:
    """Audit-ready envelope for a single resolved microstructure score.

    Engine-neutral: emitted by `resolve_breakout_microstructure_features` and
    consumed by engine-specific mappers (e.g. EngineCInput builder).

    Attributes:
      value: normalized score in [0, 1].
      provenance: machine-readable tag identifying the microstructure path
        used (e.g. "MICROSTRUCTURE_OFI_AGG_BUY_VOL_NORMALIZED").
      input_features: tuple of microstructure helper names that contributed.
      freshness_status: per-field temporal proof (FRESH/STALE/MISSING).
      confidence: meta-score in [0, 1] indicating reliability of the value.
      fallback_used: True when a non-canonical fallback was applied.
      research_only_if_legacy_fallback: True when fallback degrades the
        field to research-quality only (blocks promotion via P5 validator).
    """

    value: float
    provenance: str
    input_features: tuple[str, ...]
    freshness_status: str = FRESHNESS_NOT_PROVEN
    confidence: float = 0.0
    fallback_used: bool = False
    research_only_if_legacy_fallback: bool = False


@dataclass(frozen=True)
class BreakoutMicrostructureResolution:
    """Container for the 7 resolved scores + aggregated diagnostics.

    Engine-neutral output. Engine packages map these to their specific input
    contracts (e.g. EngineCInput has matching 7 float field names that an
    engine-specific mapper can project onto).
    """

    breakout_strength: BreakoutMicrostructureField
    range_quality: BreakoutMicrostructureField
    compression_quality: BreakoutMicrostructureField
    volume_confirmation: BreakoutMicrostructureField
    followthrough_room: BreakoutMicrostructureField
    extension_pct: BreakoutMicrostructureField
    retrace_risk: BreakoutMicrostructureField

    @property
    def any_fallback_used(self) -> bool:
        return any(
            getattr(self, name).fallback_used
            for name in (
                "breakout_strength",
                "range_quality",
                "compression_quality",
                "volume_confirmation",
                "followthrough_room",
                "extension_pct",
                "retrace_risk",
            )
        )

    @property
    def any_research_only_fallback(self) -> bool:
        return any(
            getattr(self, name).research_only_if_legacy_fallback
            for name in (
                "breakout_strength",
                "range_quality",
                "compression_quality",
                "volume_confirmation",
                "followthrough_room",
                "extension_pct",
                "retrace_risk",
            )
        )

    def to_score_dict(self) -> dict[str, float]:
        """Neutral projection: 7 named float scores.

        Engine-specific mappers consume this dict and project into their
        engine input contract (e.g. EngineCInput).
        """
        return {
            "breakout_strength": self.breakout_strength.value,
            "range_quality": self.range_quality.value,
            "compression_quality": self.compression_quality.value,
            "volume_confirmation": self.volume_confirmation.value,
            "followthrough_room": self.followthrough_room.value,
            "extension_pct": self.extension_pct.value,
            "retrace_risk": self.retrace_risk.value,
        }


@dataclass(frozen=True)
class BreakoutMicrostructureInputs:
    """Bundle of microstructure scalars consumed by the resolver.

    All inputs are precomputed by upstream microstructure helpers
    (vpin, ofi, queue_pressure, kyle_lambda, realized_kernel_vol,
    walls_and_spoofing, spread_dynamics). None values trigger fallbacks.
    """

    # Price context (from raw OHLCV / book microprice)
    breakout_price: float | None = None
    entry_price: float | None = None
    range_high: float | None = None
    range_low: float | None = None
    recent_range_width: float | None = None

    # Realized volatility (canonical microstructure)
    realized_vol_current: float | None = None
    realized_vol_at_break: float | None = None
    realized_vol_lookback_mean: float | None = None
    realized_vol_lookback_p50: float | None = None

    # Order flow imbalance + aggressive flow
    ofi_normalized: float | None = None
    cumulative_ofi: float | None = None
    aggressive_buy_ratio: float | None = None
    signed_trade_imbalance: float | None = None

    # Queue pressure / book imbalance
    queue_pressure: float | None = None
    queue_pressure_stability: float | None = None

    # Microprice stability
    microprice_stability: float | None = None
    microprice_reversal: float | None = None

    # Walls / liquidity gap
    distance_to_ask_wall_bps: float | None = None
    distance_to_bid_wall_bps: float | None = None
    liquidity_gap_above_bps: float | None = None
    depth_thinning_score: float | None = None

    # Expected slippage to next cluster
    expected_slippage_bps: float | None = None

    # Spread freshness / dynamics
    spread_bps: float | None = None
    spread_stability: float | None = None
    spread_widening_recent: float | None = None

    # Toxicity
    vpin: float | None = None
    vpin_spike: float | None = None

    # Bid support / ask absorption
    bid_support_strength: float | None = None
    ask_absorption_failure: float | None = None

    # Wick / noise ratio (range quality)
    wick_noise_ratio: float | None = None

    # Lookback freshness metadata
    inputs_freshness_status: str = FRESHNESS_NOT_PROVEN


def _clamp(value: float) -> float:
    """Clamp to [0, 1] — score contract."""
    if value is None:
        return 0.0
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if f != f:  # NaN
        return 0.0
    return max(0.0, min(1.0, f))


def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    if den is None or num is None:
        return default
    try:
        if abs(den) < 1e-12:
            return default
        return float(num) / float(den)
    except (TypeError, ValueError):
        return default


def _all_present(*values: float | None) -> bool:
    return all(v is not None for v in values)


def _resolve_breakout_strength(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if _all_present(
        inputs.breakout_price,
        inputs.range_high,
        inputs.realized_vol_current,
    ) and inputs.realized_vol_current > 0:
        price_break = inputs.breakout_price - inputs.range_high
        vol_normalized = _safe_div(price_break, inputs.realized_vol_current * inputs.range_high)
        components.append(_clamp(0.5 + vol_normalized * 0.5))
        used.append("price_break_normalized_by_realized_vol")

    if inputs.cumulative_ofi is not None:
        components.append(_clamp(0.5 + inputs.cumulative_ofi * 0.5))
        used.append("cumulative_ofi")

    if inputs.aggressive_buy_ratio is not None:
        components.append(_clamp(inputs.aggressive_buy_ratio))
        used.append("aggressive_buy_ratio")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="BREAKOUT_STRENGTH_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_OFI_AGGRESSIVE_FLOW_VOL_NORMALIZED",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 3.0),
        fallback_used=False,
    )


def _resolve_range_quality(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if _all_present(inputs.realized_vol_current, inputs.realized_vol_lookback_p50) and inputs.realized_vol_lookback_p50 > 0:
        ratio = _safe_div(inputs.realized_vol_current, inputs.realized_vol_lookback_p50)
        components.append(_clamp(1.0 - min(ratio, 2.0) / 2.0))
        used.append("realized_vol_pct_vs_lookback_p50")

    if inputs.wick_noise_ratio is not None:
        components.append(_clamp(1.0 - inputs.wick_noise_ratio))
        used.append("wick_noise_ratio")

    if inputs.spread_stability is not None:
        components.append(_clamp(inputs.spread_stability))
        used.append("spread_stability")

    if inputs.queue_pressure_stability is not None:
        components.append(_clamp(inputs.queue_pressure_stability))
        used.append("queue_pressure_stability")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="RANGE_QUALITY_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_VOL_PERCENTILE_WICK_SPREAD_QUEUE_STABILITY",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 4.0),
        fallback_used=False,
    )


def _resolve_compression_quality(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if _all_present(inputs.realized_vol_current, inputs.realized_vol_lookback_mean) and inputs.realized_vol_lookback_mean > 0:
        ratio = _safe_div(inputs.realized_vol_current, inputs.realized_vol_lookback_mean)
        components.append(_clamp(1.0 - min(ratio, 2.0) / 2.0))
        used.append("realized_vol_contraction_vs_lookback_mean")

    if inputs.microprice_stability is not None:
        components.append(_clamp(inputs.microprice_stability))
        used.append("microprice_stability")

    if inputs.queue_pressure_stability is not None:
        components.append(_clamp(inputs.queue_pressure_stability))
        used.append("queue_pressure_stability")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="COMPRESSION_QUALITY_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_VOL_CONTRACTION_MICROPRICE_QUEUE_STABILITY",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 3.0),
        fallback_used=False,
    )


def _resolve_volume_confirmation(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if inputs.aggressive_buy_ratio is not None:
        components.append(_clamp(inputs.aggressive_buy_ratio))
        used.append("aggressive_buy_ratio")

    if inputs.signed_trade_imbalance is not None:
        components.append(_clamp(0.5 + inputs.signed_trade_imbalance * 0.5))
        used.append("signed_trade_imbalance")

    if inputs.cumulative_ofi is not None:
        components.append(_clamp(0.5 + inputs.cumulative_ofi * 0.5))
        used.append("cumulative_ofi")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="VOLUME_CONFIRMATION_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_AGGRESSIVE_FLOW_SIGNED_IMBALANCE_CUMOFI",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 3.0),
        fallback_used=False,
    )


def _resolve_followthrough_room(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if inputs.distance_to_ask_wall_bps is not None:
        components.append(_clamp(min(inputs.distance_to_ask_wall_bps / 50.0, 1.0)))
        used.append("distance_to_ask_wall_bps")

    if inputs.liquidity_gap_above_bps is not None:
        components.append(_clamp(min(inputs.liquidity_gap_above_bps / 50.0, 1.0)))
        used.append("liquidity_gap_above_bps")

    if inputs.depth_thinning_score is not None:
        components.append(_clamp(inputs.depth_thinning_score))
        used.append("depth_thinning_score")

    if inputs.expected_slippage_bps is not None:
        components.append(_clamp(1.0 - min(inputs.expected_slippage_bps / 10.0, 1.0)))
        used.append("expected_slippage_bps_inverse")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="FOLLOWTHROUGH_ROOM_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_WALLS_LIQUIDITY_GAP_DEPTH_SLIPPAGE",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 4.0),
        fallback_used=False,
    )


def _resolve_extension_pct(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if _all_present(
        inputs.breakout_price,
        inputs.entry_price,
        inputs.realized_vol_current,
    ) and inputs.realized_vol_current > 0:
        move = abs(inputs.entry_price - inputs.breakout_price)
        ratio = _safe_div(move, inputs.realized_vol_current * inputs.entry_price)
        components.append(_clamp(min(ratio, 1.0)))
        used.append("move_normalized_by_realized_vol")

    if _all_present(
        inputs.breakout_price,
        inputs.entry_price,
        inputs.recent_range_width,
    ) and inputs.recent_range_width > 0:
        move = abs(inputs.entry_price - inputs.breakout_price)
        ratio = _safe_div(move, inputs.recent_range_width)
        components.append(_clamp(min(ratio, 1.0)))
        used.append("move_normalized_by_recent_range_width")

    if inputs.cumulative_ofi is not None:
        components.append(_clamp(0.5 - inputs.cumulative_ofi * 0.5))
        used.append("ofi_overextension_penalty")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="EXTENSION_PCT_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_MOVE_VS_VOL_RANGE_OFI_SUPPORT",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 3.0),
        fallback_used=False,
    )


def _resolve_retrace_risk(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureField:
    used: list[str] = []
    components: list[float] = []

    if inputs.cumulative_ofi is not None:
        components.append(_clamp(0.5 - inputs.cumulative_ofi * 0.5))
        used.append("cumulative_ofi_reversal")

    if inputs.microprice_reversal is not None:
        components.append(_clamp(inputs.microprice_reversal))
        used.append("microprice_reversal")

    if inputs.spread_widening_recent is not None:
        components.append(_clamp(min(max(inputs.spread_widening_recent - 1.0, 0.0), 1.0)))
        used.append("spread_widening_recent")

    if inputs.vpin_spike is not None:
        components.append(_clamp(min(max(inputs.vpin_spike, 0.0), 1.0)))
        used.append("vpin_spike")

    if inputs.bid_support_strength is not None:
        components.append(_clamp(1.0 - inputs.bid_support_strength))
        used.append("bid_support_weakness")

    if inputs.ask_absorption_failure is not None:
        components.append(_clamp(inputs.ask_absorption_failure))
        used.append("ask_absorption_failure")

    if not components:
        return BreakoutMicrostructureField(
            value=0.0,
            provenance="RETRACE_RISK_NO_MICROSTRUCTURE_INPUTS",
            input_features=(),
            freshness_status=FRESHNESS_MISSING,
            confidence=0.0,
            fallback_used=True,
            research_only_if_legacy_fallback=True,
        )

    return BreakoutMicrostructureField(
        value=_clamp(sum(components) / len(components)),
        provenance="MICROSTRUCTURE_OFI_REV_MICROPRICE_REV_SPREAD_VPIN_BID_ASK_ABSORPTION",
        input_features=tuple(used),
        freshness_status=inputs.inputs_freshness_status,
        confidence=min(1.0, len(components) / 6.0),
        fallback_used=False,
    )


def resolve_breakout_microstructure_features(
    inputs: BreakoutMicrostructureInputs,
) -> BreakoutMicrostructureResolution:
    """Top-level resolver — produces 7 neutral breakout microstructure scores.

    Each field is independently resolved with provenance envelope. Engine
    packages map the result to their engine input contract (e.g.
    `engines.engine_c.structure_resolver_c.build_engine_c_input_from_breakout_features`).
    """

    return BreakoutMicrostructureResolution(
        breakout_strength=_resolve_breakout_strength(inputs),
        range_quality=_resolve_range_quality(inputs),
        compression_quality=_resolve_compression_quality(inputs),
        volume_confirmation=_resolve_volume_confirmation(inputs),
        followthrough_room=_resolve_followthrough_room(inputs),
        extension_pct=_resolve_extension_pct(inputs),
        retrace_risk=_resolve_retrace_risk(inputs),
    )


__all__ = [
    "BreakoutMicrostructureField",
    "BreakoutMicrostructureInputs",
    "BreakoutMicrostructureResolution",
    "FRESHNESS_FRESH",
    "FRESHNESS_MISSING",
    "FRESHNESS_NOT_PROVEN",
    "FRESHNESS_STALE",
    "resolve_breakout_microstructure_features",
]
