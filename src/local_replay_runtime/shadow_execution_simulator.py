"""Prudent Shadow-compatible execution simulator for LOCAL_REPLAY."""

from __future__ import annotations

from dataclasses import dataclass

from data_backbone.market_physics_math import round_float64
from execution_backbone.execution_cost_meter.adverse_selection_meter import (
    CANONICAL_ADVERSE_SELECTION_DELAY_POLICY,
    compute_adverse_selection,
    resolve_adverse_selection_delay_s,
)
from execution_backbone.execution_cost_meter.cost_aggregator import compute_trade_cost
from execution_backbone.execution_cost_meter.fee_meter import estimate_fee
from execution_backbone.execution_cost_meter.partial_fill_cost_meter import (
    compute_partial_fill_cost,
)
from execution_backbone.fee_aware_edge_gate import evaluate_fee_aware_edge
from execution_backbone.fill_tracker.fill_aggregator import FillAggregator, FillEvent
from execution_backbone.fill_tracker.fill_reporter import FillReporter
from execution_backbone.fill_tracker.order_state_tracker import (
    OrderState,
    OrderStateTracker,
)
from execution_backbone.fill_tracker.order_terminal_state_resolver import resolve_terminal
from execution_backbone.order_decider.intent_builder import OrderType, VenueConstraintSnapshot
from execution_backbone.order_decider.order_type_selector import select_order_type
from execution_backbone.slippage_model import predict_execution_slippage
from execution_backbone.spread_guard import evaluate_execution_spread_guard
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from local_replay_runtime.replay_execution_contracts import (
    ParityTolerancePolicy,
    ReplayParityDiagnosticsSummary,
    ShadowExecutionSimulatorConfig,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord, build_dtr


@dataclass(frozen=True)
class _RowExecutionProfile:
    expected_cost: float
    realized_cost: float
    component_sources: dict[str, str]
    replay_cost_components: tuple[str, ...]
    order_type: OrderType
    order_reason: str
    venue_constraints: VenueConstraintSnapshot | None
    fee_aware_edge_reason_code: str | None = None


def _resolve_book_depth_contract(
    dataset: HistoricalReplayDataset,
) -> dict[str, object]:
    level_values = tuple(
        row.book_depth_levels for row in dataset.rows if row.book_depth_levels is not None
    )
    snapshot_count = sum(
        row.book_depth_snapshot_count or 0 for row in dataset.rows
    ) or None
    event_count = sum(row.book_depth_event_count or 0 for row in dataset.rows) or None
    missing_count = sum(row.book_depth_missing_count or 0 for row in dataset.rows) or None
    explicit_statuses = {
        row.book_depth_source_status
        for row in dataset.rows
        if row.book_depth_source_status
        and row.book_depth_source_status != "BOOK_DEPTH_NOT_PROVEN"
    }
    stale = any(
        row.book_depth_staleness_status == "BOOK_DEPTH_STALE"
        for row in dataset.rows
    )
    if stale:
        status = "BOOK_DEPTH_STALE"
    else:
        levels = min(level_values) if level_values else None
        if levels is None:
            status = "BOOK_DEPTH_NOT_PROVEN"
        elif levels <= 0:
            status = "BOOK_DEPTH_MISSING"
        elif levels == 1:
            status = "BOOK_TOP_OF_BOOK_ONLY"
        elif levels < 20:
            status = "BOOK_LIMITED_DEPTH_AVAILABLE"
        else:
            status = "BOOK_DEPTH20_AVAILABLE"
        if explicit_statuses:
            if "BOOK_DEPTH_MISSING" in explicit_statuses and status != "BOOK_DEPTH20_AVAILABLE":
                status = "BOOK_DEPTH_MISSING"
            elif "BOOK_TOP_OF_BOOK_ONLY" in explicit_statuses and status != "BOOK_DEPTH20_AVAILABLE":
                status = "BOOK_TOP_OF_BOOK_ONLY"
            elif "BOOK_LIMITED_DEPTH_AVAILABLE" in explicit_statuses and status == "BOOK_DEPTH_NOT_PROVEN":
                status = "BOOK_LIMITED_DEPTH_AVAILABLE"
            elif "BOOK_DEPTH20_AVAILABLE" in explicit_statuses and status == "BOOK_DEPTH_NOT_PROVEN":
                status = "BOOK_DEPTH20_AVAILABLE"
    levels = min(level_values) if level_values else None
    if status == "BOOK_DEPTH20_AVAILABLE":
        return {
            "book_depth_available": True,
            "book_depth_levels": levels,
            "book_depth_source_status": status,
            "book_depth_snapshot_count": snapshot_count,
            "book_depth_event_count": event_count,
            "book_depth_missing_count": missing_count,
            "book_depth_staleness_status": status,
            "impact_depth_level_used": levels,
            "impact_depth_readiness_status": "DEPTH20_AVAILABLE",
            "shadow_extension_required": False,
            "shadow_extension_reason": "SHADOW_STANDARD_30D",
            "minimum_shadow_days_required": 30,
            "shadow_extension_status": "SHADOW_STANDARD_30D",
            "impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
        }
    if status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        minimum_shadow_days_required = 60 if levels is not None and levels <= 5 else 45
        shadow_extension_status = (
            "SHADOW_EXTENDED_60D" if minimum_shadow_days_required == 60 else "SHADOW_EXTENDED_45D"
        )
        return {
            "book_depth_available": True,
            "book_depth_levels": levels,
            "book_depth_source_status": status,
            "book_depth_snapshot_count": snapshot_count,
            "book_depth_event_count": event_count,
            "book_depth_missing_count": missing_count,
            "book_depth_staleness_status": status,
            "impact_depth_level_used": levels,
            "impact_depth_readiness_status": "LIMITED_DEPTH_PARTIAL",
            "shadow_extension_required": True,
            "shadow_extension_reason": "SHADOW_EXTENDED_REQUIRED",
            "minimum_shadow_days_required": minimum_shadow_days_required,
            "shadow_extension_status": shadow_extension_status,
            "impact_source_status": "IMPACT_SOURCE_LIMITED_DEPTH_MODEL",
        }
    if status == "BOOK_TOP_OF_BOOK_ONLY":
        return {
            "book_depth_available": True,
            "book_depth_levels": levels or 1,
            "book_depth_source_status": status,
            "book_depth_snapshot_count": snapshot_count,
            "book_depth_event_count": event_count,
            "book_depth_missing_count": missing_count,
            "book_depth_staleness_status": status,
            "impact_depth_level_used": levels or 1,
            "impact_depth_readiness_status": "TOP_OF_BOOK_PROXY_ONLY",
            "shadow_extension_required": True,
            "shadow_extension_reason": "MICRO_LIVE_BLOCKED_BY_DEPTH",
            "minimum_shadow_days_required": 60,
            "shadow_extension_status": "SHADOW_DIAGNOSTIC_ONLY",
            "impact_source_status": "IMPACT_SOURCE_TOP_OF_BOOK_PROXY",
        }
    if status == "BOOK_DEPTH_STALE":
        return {
            "book_depth_available": True,
            "book_depth_levels": levels,
            "book_depth_source_status": status,
            "book_depth_snapshot_count": snapshot_count,
            "book_depth_event_count": event_count,
            "book_depth_missing_count": missing_count,
            "book_depth_staleness_status": status,
            "impact_depth_level_used": levels,
            "impact_depth_readiness_status": "BOOK_DEPTH_STALE",
            "shadow_extension_required": True,
            "shadow_extension_reason": "BOOK_DEPTH_STALE",
            "minimum_shadow_days_required": None,
            "shadow_extension_status": "MICRO_LIVE_BLOCKED_BY_DEPTH",
            "impact_source_status": "IMPACT_SOURCE_NOT_PROVEN",
        }
    return {
        "book_depth_available": False if status == "BOOK_DEPTH_MISSING" else None,
        "book_depth_levels": levels,
        "book_depth_source_status": status,
        "book_depth_snapshot_count": snapshot_count,
        "book_depth_event_count": event_count,
        "book_depth_missing_count": missing_count,
        "book_depth_staleness_status": status,
        "impact_depth_level_used": levels,
        "impact_depth_readiness_status": status,
        "shadow_extension_required": True,
        "shadow_extension_reason": "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF",
        "minimum_shadow_days_required": None,
        "shadow_extension_status": "MICRO_LIVE_BLOCKED_BY_DEPTH",
        "impact_source_status": (
            "IMPACT_SOURCE_MISSING" if status == "BOOK_DEPTH_MISSING" else "IMPACT_SOURCE_NOT_PROVEN"
        ),
    }


def _resolve_fill_realism_contract(
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
) -> dict[str, object]:
    attempted_states = {DecisionState.EXECUTED, DecisionState.REDUCED, DecisionState.PHANTOM}
    attempted_rows = tuple(
        row for row, record in zip(dataset.rows, dtr_records, strict=False)
        if record.decision_state in attempted_states
    )
    attempted_count = len(attempted_rows)
    if attempted_count == 0:
        return {
            "fill_ratio_source": "UNKNOWN",
            "fill_realism_status": "FILL_REALISM_NOT_PROVEN",
            "fill_source_status": "FILL_SOURCE_NOT_PROVEN",
            "fill_model_name": None,
            "fill_model_version": None,
            "fill_ratio_expected": None,
            "fill_ratio_observed": None,
            "partial_fill_rate_expected": None,
            "partial_fill_rate_observed": None,
            "no_fill_rate_expected": None,
            "no_fill_rate_observed": None,
            "fill_latency_ms_expected": None,
            "fill_latency_ms_observed": None,
            "synthetic_fill_flag": False,
            "measured_fill_flag": False,
            "fill_provenance_ref": None,
            "fill_input_hash": None,
            "fill_policy_version": None,
        }
    tracker = OrderStateTracker()
    reporter = FillReporter()
    aggregator = FillAggregator()
    fill_ratios = tuple(row.fill_ratio for row in attempted_rows)
    no_fill_count = 0
    canonical_tracker_used = False
    for row in attempted_rows:
        order_id = row.opportunity_id
        reporter.record_order_created()
        mid_price = _resolve_mid_price(row)
        ordered_quantity = _resolve_ordered_quantity(row, mid_price=mid_price)
        tracker.register_order(
            order_id=order_id,
            pair=row.pair,
            engine_id=row.engine_id,
            side=row.side,
            order_type="replay_shadow",
            quantity=max(ordered_quantity or 0.0, 1.0),
        )
        tracker.mark_sent(order_id, row.timestamp_ms / 1000.0)
        tracker.mark_acked(order_id, row.timestamp_ms / 1000.0)
        exec_price = _resolve_exec_price(
            row,
            mid_price=mid_price,
            slippage_bps=row.slippage_bps,
        )
        fill_prices, fill_quantities = _resolve_fill_path(
            row,
            ordered_quantity=ordered_quantity,
            exec_price=exec_price,
        )
        if ordered_quantity is not None and mid_price is not None:
            canonical_tracker_used = True
        for index, (price, quantity) in enumerate(zip(fill_prices, fill_quantities, strict=False), start=1):
            fill_id = f"{order_id}:fill:{index}"
            tracker.mark_fill(
                order_id,
                fill_qty=quantity,
                fill_price=price,
                fill_time=row.timestamp_ms / 1000.0,
                fill_id=fill_id,
            )
            aggregator.record_fill(
                FillEvent(
                    fill_id=fill_id,
                    order_id=order_id,
                    pair=row.pair,
                    side=row.side,
                    quantity=quantity,
                    price=price,
                    timestamp=row.timestamp_ms / 1000.0,
                )
            )
        tracked = tracker.get(order_id)
        if tracked is None:
            continue
        if row.fill_ratio >= 1.0:
            terminal_state = OrderState.FILLED
        else:
            terminal_state = OrderState.CANCELLED
            tracker.mark_cancelled(order_id, row.timestamp_ms / 1000.0, reason="replay_fill_ratio")
        if row.fill_ratio <= 0.0:
            no_fill_count += 1
        resolution = resolve_terminal(
            order_id=order_id,
            state=terminal_state,
            ordered_quantity=max(tracked.quantity, 0.0),
            filled_quantity=tracked.filled_quantity,
        )
        reporter.record_terminal(
            resolution.state,
            had_partial_fills=(0.0 < resolution.fill_ratio < 1.0),
        )
    stats = reporter.get_stats()
    return {
        "fill_ratio_source": (
            "CANONICAL_FILL_TRACKER" if canonical_tracker_used else "REPLAY_MODEL"
        ),
        "fill_realism_status": "FILL_REALISM_MODEL_ONLY",
        "fill_source_status": (
            "FILL_SOURCE_CANONICAL_FILL_TRACKER"
            if canonical_tracker_used
            else "FILL_SOURCE_REPLAY_MODEL"
        ),
        "fill_model_name": (
            "execution_backbone.fill_tracker.replay_adapter"
            if canonical_tracker_used
            else "shadow_execution_simulator_prudent_replay"
        ),
        "fill_model_version": (
            "execution_backbone.fill_tracker.v1"
            if canonical_tracker_used
            else "shadow_execution_simulator.v1"
        ),
        "fill_ratio_expected": round_float64(sum(fill_ratios) / attempted_count, 6),
        "fill_ratio_observed": None,
        "partial_fill_rate_expected": round_float64(stats.partial_fill_rate, 6),
        "partial_fill_rate_observed": None,
        "no_fill_rate_expected": round_float64(no_fill_count / attempted_count, 6),
        "no_fill_rate_observed": None,
        "fill_latency_ms_expected": None,
        "fill_latency_ms_observed": None,
        "synthetic_fill_flag": False,
        "measured_fill_flag": False,
        "fill_provenance_ref": "shadow_execution_simulator://prudent_replay_model",
        "fill_input_hash": None,
        "fill_policy_version": "shadow_execution_simulator.v1",
    }


def _base_state(row: HistoricalReplayOpportunity) -> DecisionState:
    if row.target_decision_state is not None:
        return row.target_decision_state
    if row.hard_block_reasons:
        return DecisionState.HARD_BLOCKED
    if row.final_size > 0.0 and row.fill_ratio >= 1.0:
        return DecisionState.EXECUTED
    if row.final_size > 0.0 and row.fill_ratio > 0.0:
        return DecisionState.REDUCED
    if row.ranking_position > 0:
        return DecisionState.REJECTED_RANKING
    return DecisionState.EVALUATED


def _resolve_slippage_size_value(
    row: HistoricalReplayOpportunity,
    *,
    size_proxy: str,
) -> float | None:
    normalized = size_proxy.strip().casefold()
    if normalized == "final_size" and row.final_size > 0.0:
        return row.final_size
    if normalized == "candidate_size" and row.candidate_size > 0.0:
        return row.candidate_size
    if row.final_size > 0.0:
        return row.final_size
    if row.candidate_size > 0.0:
        return row.candidate_size
    return None


def _predict_replay_slippage_bps(
    row: HistoricalReplayOpportunity,
    config: ShadowExecutionSimulatorConfig,
) -> float | None:
    if config.slippage_model is None:
        return None
    size_value = _resolve_slippage_size_value(
        row,
        size_proxy=config.slippage_model.size_proxy,
    )
    if size_value is None:
        return None
    try:
        estimate = predict_execution_slippage(
            config.slippage_model,
            size_value=size_value,
        )
    except ValueError:
        return None
    return estimate.predicted_slippage_bps


def _is_buy_side(side: str) -> bool:
    return str(side or "buy").strip().lower() != "sell"


def _resolve_mid_price(row: HistoricalReplayOpportunity) -> float | None:
    if row.mid_price is not None and row.mid_price > 0.0:
        return row.mid_price
    if row.close_price > 0.0:
        return row.close_price
    return None


def _resolve_ordered_quantity(
    row: HistoricalReplayOpportunity,
    *,
    mid_price: float | None,
) -> float | None:
    if row.fill_quantities and row.fill_ratio > 0.0:
        return sum(row.fill_quantities) / row.fill_ratio
    size_value = row.candidate_size or row.final_size
    if size_value <= 0.0:
        return None
    if mid_price is not None and mid_price > 0.0:
        return size_value / mid_price
    return size_value


def _resolve_exec_price(
    row: HistoricalReplayOpportunity,
    *,
    mid_price: float | None,
    slippage_bps: float,
) -> float | None:
    reference_price = mid_price or (row.close_price if row.close_price > 0.0 else None)
    if reference_price is None or reference_price <= 0.0:
        return None
    spread_fraction = row.spread_bps / 20_000.0
    slippage_fraction = slippage_bps / 10_000.0
    signed_fraction = spread_fraction + slippage_fraction
    if not _is_buy_side(row.side):
        signed_fraction = -signed_fraction
    return max(reference_price * (1.0 + signed_fraction), 0.0)


def _resolve_fill_path(
    row: HistoricalReplayOpportunity,
    *,
    ordered_quantity: float | None,
    exec_price: float | None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if row.fill_prices and row.fill_quantities and len(row.fill_prices) == len(row.fill_quantities):
        return row.fill_prices, row.fill_quantities
    if ordered_quantity is None or ordered_quantity <= 0.0 or exec_price is None or exec_price <= 0.0:
        return (), ()
    executed_quantity = ordered_quantity * max(0.0, min(row.fill_ratio, 1.0))
    if executed_quantity <= 0.0:
        return (), ()
    return (exec_price,), (executed_quantity,)


def _build_venue_constraints(
    row: HistoricalReplayOpportunity,
) -> VenueConstraintSnapshot | None:
    if row.tick_size is None and row.step_size is None and row.min_notional is None:
        return None
    return VenueConstraintSnapshot(
        tick_size=(f"{row.tick_size:.12g}" if row.tick_size is not None else None),
        step_size=(f"{row.step_size:.12g}" if row.step_size is not None else None),
        min_notional=(f"{row.min_notional:.12g}" if row.min_notional is not None else None),
    )


def _violates_min_notional(
    row: HistoricalReplayOpportunity,
    venue_constraints: VenueConstraintSnapshot | None,
) -> bool:
    if venue_constraints is None or venue_constraints.min_notional is None:
        return False
    planned_notional = row.candidate_size or row.final_size
    if planned_notional <= 0.0:
        return False
    return planned_notional < float(venue_constraints.min_notional)


def _select_replay_order_type(
    row: HistoricalReplayOpportunity,
    *,
    config: ShadowExecutionSimulatorConfig,
    expected_cost: float,
) -> object:
    max_spread_for_market = (
        config.spread_guard_model.max_spread_bps
        if config.spread_guard_model is not None
        else 10.0
    )
    limit_threshold = min(5.0, max_spread_for_market)
    return select_order_type(
        expected_gain=row.expected_edge_bps / 10_000.0,
        expected_cost=expected_cost,
        safety_margin=config.economic_absurdity_buffer_bps / 10_000.0,
        spread_bps=row.spread_bps,
        max_spread_for_market=max_spread_for_market,
        use_limit_threshold_bps=limit_threshold,
    )


def _resolve_fee_fraction(
    row: HistoricalReplayOpportunity,
    *,
    order_type: OrderType,
    mid_price: float | None,
    ordered_quantity: float | None,
) -> float | None:
    if mid_price is None or mid_price <= 0.0 or ordered_quantity is None or ordered_quantity <= 0.0:
        return None
    if order_type == OrderType.LIMIT:
        fee_rate = row.maker_fee_rate
    elif order_type == OrderType.MARKET:
        fee_rate = row.taker_fee_rate
    else:
        fee_rate = row.taker_fee_rate if row.taker_fee_rate is not None else row.maker_fee_rate
    if fee_rate is None or fee_rate < 0.0:
        return None
    planned_notional = mid_price * ordered_quantity
    if planned_notional <= 0.0:
        return None
    fee_amount = estimate_fee(mid_price, ordered_quantity, fee_rate)
    return fee_amount / planned_notional


def _classify_adverse_selection_source(
    *,
    adverse_selection_fraction: float | None,
) -> str:
    """Map per-record adverse_selection availability to manifest-level
    `adverse_selection_source`.

    Audit 2026-05-14 P3-C wiring : adverse_selection est une mesure POST-FILL.
    Le meter (`adverse_selection_meter.compute_adverse_selection`) requiert un
    trade execute (exec_price + post_fill_mid_price + fill quantities). Sur un
    run avec `executed_count = 0` (e.g. run B2), aucune mesure n'est possible
    car la dependance amont (executed trade) manque.

    Per directive utilisateur :
    > "If dependency is missing, keep the blocker and emit
    >  ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY."

    Le code `ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY` n'est
    PAS dans `_PURE_CANONICAL_EXECUTION_SOURCES` donc le gate
    `ADVERSE_SELECTION_PROXY` reste actif — pas de false READY.

    Mapping :
      - adverse_selection_fraction is not None → "CANONICAL_ADVERSE_SELECTION_METER"
      - adverse_selection_fraction is None     → "ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY"
    """
    if adverse_selection_fraction is not None:
        return "CANONICAL_ADVERSE_SELECTION_METER"
    return "ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY"


def _classify_slippage_model_source(
    *,
    slippage_provenance: str,
    has_slippage_model: bool,
) -> str:
    """Map per-record `slippage_provenance` (tier-aware) to manifest-level
    `slippage_model_source`.

    Audit 2026-05-14 P3-B wiring : Kyle lambda measurement (microstructure
    canonique) leve le gate `SLIPPAGE_MODEL_PROXY`. L'override caller
    (live API account dynamique) est valide upstream donc canonical aussi.
    Fallback `DEFAULT_TO_CALIBRATE` ou vide retombe sur le mecanisme legacy
    `CANONICAL_EXECUTION_BACKBONE` si `config.slippage_model` present,
    sinon `REPLAY_PROXY`.

    Mapping :
      - "MEASURED_FROM_KYLE_LAMBDA"          → "CANONICAL_KYLE_LAMBDA_METER"
      - "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE" → "CANONICAL_KYLE_LAMBDA_OVERRIDE"
      - "MEASURED_FROM_DEPTH20_BOOK_WALK"    → "CANONICAL_EXECUTION_BACKBONE"
      - "MEASURED_FROM_DEPTH20_BOOK_WALK_STALE" → "MEASURED_STALE_AUDIT_ONLY"
      - "DEFAULT_TO_CALIBRATE" / "" / autre  → "CANONICAL_EXECUTION_BACKBONE"
        si has_slippage_model, sinon "REPLAY_PROXY"
    """
    if slippage_provenance == "MEASURED_FROM_KYLE_LAMBDA":
        return "CANONICAL_KYLE_LAMBDA_METER"
    if slippage_provenance == "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE":
        return "CANONICAL_KYLE_LAMBDA_OVERRIDE"
    if slippage_provenance == "MEASURED_FROM_DEPTH20_BOOK_WALK":
        return "CANONICAL_EXECUTION_BACKBONE"
    if slippage_provenance == "MEASURED_FROM_DEPTH20_BOOK_WALK_STALE":
        return "MEASURED_STALE_AUDIT_ONLY"
    if has_slippage_model:
        return "CANONICAL_EXECUTION_BACKBONE"
    return "REPLAY_PROXY"


def _classify_spread_model_source(
    *,
    spread_provenance: str,
    has_spread_guard: bool,
) -> str:
    """Map per-record `spread_provenance` (tier-aware) to manifest-level
    `spread_model_source`.

    Audit 2026-05-14 P3-A wiring : verrouille la directive utilisateur
    selon laquelle un spread mesure stale (`MEASURED_FROM_BOOK_SNAPSHOT_STALE`)
    NE DOIT PAS lever le gate `SPREAD_MODEL_PROXY`. Seules les mesures
    fresh (`MEASURED_FROM_BOOK_SNAPSHOT` dans la tolerance) ou
    reconstruites causales (`MEASURED_FROM_BOOK_RECONSTRUCTION`) sont
    promues `CANONICAL_BOOK_*`. Le mecanisme existant
    `CANONICAL_SPREAD_GUARD` (config-driven) reste valide en parallele.

    Mapping :
      - "MEASURED_FROM_BOOK_SNAPSHOT"          → "CANONICAL_BOOK_MEASURED"
      - "MEASURED_FROM_BOOK_RECONSTRUCTION"    → "CANONICAL_BOOK_RECONSTRUCTED"
      - "MEASURED_FROM_BOOK_SNAPSHOT_STALE"    → "MEASURED_STALE_AUDIT_ONLY"
        (NE leve PAS le gate ; audit-ready mais pas promotion-grade)
      - "DEFAULT_BY_BOOK_STATUS" / "" / autre  → "CANONICAL_SPREAD_GUARD"
        si has_spread_guard, sinon "REPLAY_PROXY"
    """
    if spread_provenance == "MEASURED_FROM_BOOK_SNAPSHOT":
        return "CANONICAL_BOOK_MEASURED"
    if spread_provenance == "MEASURED_FROM_BOOK_RECONSTRUCTION":
        return "CANONICAL_BOOK_RECONSTRUCTED"
    if spread_provenance == "MEASURED_FROM_BOOK_SNAPSHOT_STALE":
        return "MEASURED_STALE_AUDIT_ONLY"
    if has_spread_guard:
        return "CANONICAL_SPREAD_GUARD"
    return "REPLAY_PROXY"


def _build_row_component_sources(
    *,
    config: ShadowExecutionSimulatorConfig,
    fee_fraction: float | None,
    partial_fill_cost_fraction: float | None,
    adverse_selection_fraction: float | None,
    order_type_source_active: bool,
    venue_constraints: VenueConstraintSnapshot | None,
    spread_provenance: str = "",
    slippage_provenance: str = "",
) -> dict[str, str]:
    return {
        "fee_model_source": (
            "CANONICAL_EXECUTION_COST_METER" if fee_fraction is not None else "REPLAY_PROXY"
        ),
        "spread_model_source": _classify_spread_model_source(
            spread_provenance=spread_provenance,
            has_spread_guard=config.spread_guard_model is not None,
        ),
        "slippage_model_source": _classify_slippage_model_source(
            slippage_provenance=slippage_provenance,
            has_slippage_model=config.slippage_model is not None,
        ),
        "partial_fill_model_source": (
            "CANONICAL_PARTIAL_FILL_COST_METER"
            if partial_fill_cost_fraction is not None
            else "REPLAY_PROXY"
        ),
        "adverse_selection_source": _classify_adverse_selection_source(
            adverse_selection_fraction=adverse_selection_fraction,
        ),
        "order_type_selection_source": (
            "CANONICAL_ORDER_DECIDER" if order_type_source_active else "REPLAY_PROXY"
        ),
        "venue_constraints_source": (
            "CANONICAL_VENUE_CONSTRAINT_SNAPSHOT"
            if venue_constraints is not None
            else "REPLAY_PROXY"
        ),
    }


def _build_row_execution_profile(
    row: HistoricalReplayOpportunity,
    *,
    config: ShadowExecutionSimulatorConfig,
    execution_factor: float,
) -> _RowExecutionProfile:
    slippage_bps = _predict_replay_slippage_bps(row, config)
    if slippage_bps is None:
        slippage_bps = row.slippage_bps * config.slippage_multiplier
    implicit_cost = (
        row.spread_bps
        + slippage_bps
        + row.latency_penalty_bps * config.latency_penalty_multiplier
    ) / 10_000.0
    mid_price = _resolve_mid_price(row)
    ordered_quantity = _resolve_ordered_quantity(row, mid_price=mid_price)
    venue_constraints = _build_venue_constraints(row)
    order_type_decision = _select_replay_order_type(
        row,
        config=config,
        expected_cost=implicit_cost,
    )
    fee_fraction = _resolve_fee_fraction(
        row,
        order_type=order_type_decision.order_type,
        mid_price=mid_price,
        ordered_quantity=ordered_quantity,
    )
    expected_cost = implicit_cost + (fee_fraction or 0.0)
    if fee_fraction is not None:
        order_type_decision = _select_replay_order_type(
            row,
            config=config,
            expected_cost=expected_cost,
        )
        updated_fee_fraction = _resolve_fee_fraction(
            row,
            order_type=order_type_decision.order_type,
            mid_price=mid_price,
            ordered_quantity=ordered_quantity,
        )
        if updated_fee_fraction is not None:
            fee_fraction = updated_fee_fraction
            expected_cost = implicit_cost + fee_fraction
    exec_price = _resolve_exec_price(
        row,
        mid_price=mid_price,
        slippage_bps=slippage_bps,
    )
    fill_prices, fill_quantities = _resolve_fill_path(
        row,
        ordered_quantity=ordered_quantity,
        exec_price=exec_price,
    )
    partial_fill_cost_fraction = None
    if mid_price is not None and mid_price > 0.0 and ordered_quantity is not None and ordered_quantity > 0.0:
        partial_fill_cost = compute_partial_fill_cost(
            order_id=row.opportunity_id,
            pair=row.pair,
            ordered_quantity=ordered_quantity,
            fill_prices=fill_prices,
            fill_quantities=fill_quantities,
            current_mid=mid_price,
        )
        variance_component = (
            partial_fill_cost.price_variance / (mid_price ** 2)
            if mid_price > 0.0
            else 0.0
        )
        partial_fill_cost_fraction = variance_component + (
            partial_fill_cost.unfilled_cost / max(mid_price * ordered_quantity, 1e-12)
        )
    adverse_selection_fraction = None
    if (
        row.post_fill_mid_price is not None
        and row.post_fill_mid_price > 0.0
        and fill_prices
        and fill_quantities
    ):
        filled_quantity = sum(fill_quantities)
        if filled_quantity > 0.0:
            average_fill_price = sum(
                price * quantity
                for price, quantity in zip(fill_prices, fill_quantities, strict=False)
            ) / filled_quantity
            delay_s = resolve_adverse_selection_delay_s(
                pair=row.pair,
                event_delay_s=row.adverse_selection_delay_s,
                policy=CANONICAL_ADVERSE_SELECTION_DELAY_POLICY,
            )
            adverse_measurement = compute_adverse_selection(
                order_id=row.opportunity_id,
                pair=row.pair,
                side=row.side,
                exec_price=average_fill_price,
                mid_after=row.post_fill_mid_price,
                delay_s=delay_s,
            )
            adverse_selection_fraction = max(0.0, -adverse_measurement.adverse_selection) * execution_factor
    realized_cost = expected_cost * execution_factor
    replay_cost_components = ["expected_cost_total", "spread_bps", "latency_penalty_bps"]
    if config.spread_guard_model is not None:
        replay_cost_components.append("canonical_spread_guard")
    if config.slippage_model is not None:
        replay_cost_components.append("canonical_slippage_model")
    if fee_fraction is not None:
        replay_cost_components.append("explicit_fee")
    if partial_fill_cost_fraction is not None:
        replay_cost_components.append("partial_fill_cost")
    if adverse_selection_fraction is not None:
        replay_cost_components.append("adverse_selection")
    if venue_constraints is not None:
        replay_cost_components.append("venue_constraints")
    if fill_prices and fill_quantities and mid_price is not None and ordered_quantity is not None:
        planned_notional = max(mid_price * ordered_quantity, 1e-12)
        executed_quantity = sum(fill_quantities)
        executed_notional = max(mid_price * executed_quantity, 0.0)
        explicit_fee_realized = (fee_fraction or 0.0) * (executed_notional / planned_notional)
        trade_cost = compute_trade_cost(
            order_id=row.opportunity_id,
            pair=row.pair,
            engine_id=row.engine_id,
            explicit_fee=explicit_fee_realized,
            implicit_cost=implicit_cost * execution_factor,
            adverse_selection=adverse_selection_fraction or 0.0,
            partial_fill_cost=partial_fill_cost_fraction or 0.0,
            expected_cost=expected_cost * execution_factor,
        )
        realized_cost = trade_cost.total_cost
    fee_edge_reason_code = None
    if config.fee_aware_edge_gate_config is not None:
        try:
            fee_edge_decision = evaluate_fee_aware_edge(
                expected_edge_bps=row.expected_edge_bps,
                expected_cost=expected_cost,
                config=config.fee_aware_edge_gate_config,
            )
        except ValueError:
            fee_edge_decision = None
        if fee_edge_decision is not None and not fee_edge_decision.allowed:
            fee_edge_reason_code = fee_edge_decision.reason_code
    return _RowExecutionProfile(
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        component_sources=_build_row_component_sources(
            config=config,
            fee_fraction=fee_fraction,
            partial_fill_cost_fraction=partial_fill_cost_fraction,
            adverse_selection_fraction=adverse_selection_fraction,
            order_type_source_active=True,
            venue_constraints=venue_constraints,
            # Audit 2026-05-14 P3-A : passe le tier-aware spread_provenance
            # per-row pour decider spread_model_source au manifest level.
            spread_provenance=getattr(row, "spread_provenance", "") or "",
            # Audit 2026-05-14 P3-B : passe le tier-aware slippage_provenance
            # per-row pour decider slippage_model_source au manifest level.
            slippage_provenance=getattr(row, "slippage_provenance", "") or "",
        ),
        replay_cost_components=tuple(dict.fromkeys(replay_cost_components)),
        order_type=order_type_decision.order_type,
        order_reason=order_type_decision.reason,
        venue_constraints=venue_constraints,
        fee_aware_edge_reason_code=fee_edge_reason_code,
    )


_PURE_CANONICAL_EXECUTION_SOURCES = frozenset(
    {
        "CANONICAL_EXECUTION_COST_METER",
        "CANONICAL_SPREAD_GUARD",
        # Audit 2026-05-14 P3-A wiring : fresh book measurement et
        # reconstruction causale comptent comme canoniques (clearent le
        # gate SPREAD_MODEL_PROXY). En revanche, "MEASURED_STALE_AUDIT_ONLY"
        # N'EST PAS dans cette liste — par directive utilisateur, un spread
        # mesure stale (snapshot @ -N min hors tolerance) reste audit-only
        # et le gate SPREAD_MODEL_PROXY DOIT rester actif.
        "CANONICAL_BOOK_MEASURED",
        "CANONICAL_BOOK_RECONSTRUCTED",
        # Audit 2026-05-14 P3-B wiring : Kyle lambda measurement
        # (microstructure canonique) leve le gate SLIPPAGE_MODEL_PROXY.
        # L'override caller-supplied (live API account dynamique) compte
        # egalement comme canonique car son origine est validee upstream.
        "CANONICAL_KYLE_LAMBDA_METER",
        "CANONICAL_KYLE_LAMBDA_OVERRIDE",
        "CANONICAL_EXECUTION_BACKBONE",
        "CANONICAL_PARTIAL_FILL_COST_METER",
        "CANONICAL_ADVERSE_SELECTION_METER",
        "CANONICAL_ORDER_DECIDER",
        "CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
    }
)


def _reduce_component_source(values: tuple[str, ...]) -> str:
    normalized = tuple(value for value in values if value)
    if not normalized or all(value == "REPLAY_PROXY" for value in normalized):
        return "REPLAY_PROXY"
    unique = tuple(dict.fromkeys(normalized))
    if len(unique) == 1:
        return unique[0]
    return "CANONICAL_OR_PROXY"


def _aggregate_component_sources(
    row_profiles: tuple[_RowExecutionProfile, ...],
) -> dict[str, str]:
    field_names = (
        "fee_model_source",
        "spread_model_source",
        "slippage_model_source",
        "partial_fill_model_source",
        "adverse_selection_source",
        "order_type_selection_source",
        "venue_constraints_source",
    )
    return {
        field_name: _reduce_component_source(
            tuple(
                profile.component_sources.get(field_name, "REPLAY_PROXY")
                for profile in row_profiles
            )
        )
        for field_name in field_names
    }


def _canonical_execution_backbone_status(
    component_sources: dict[str, str],
) -> str:
    component_count = sum(
        1
        for value in component_sources.values()
        if value != "REPLAY_PROXY"
    )
    if component_count == 0:
        return "REPLAY_PROXY_ONLY"
    if component_count < len(component_sources):
        return "CANONICAL_EXECUTION_BACKBONE_PARTIAL"
    return "CANONICAL_EXECUTION_BACKBONE_ACTIVE"


def _canonical_expected_cost_components(
    config: ShadowExecutionSimulatorConfig,
    component_sources: dict[str, str],
) -> tuple[str, ...]:
    return tuple(
        component
        for component in (
            "spread_bps",
            "explicit_fee"
            if component_sources.get("fee_model_source") != "REPLAY_PROXY"
            else "",
            "canonical_slippage_model" if config.slippage_model is not None else "slippage_proxy",
            "latency_penalty_bps",
            "spread_guard_threshold" if config.spread_guard_model is not None else "",
            "partial_fill_cost"
            if component_sources.get("partial_fill_model_source") != "REPLAY_PROXY"
            else "",
            "adverse_selection"
            if component_sources.get("adverse_selection_source") != "REPLAY_PROXY"
            else "",
        )
        if component
    )


def _execution_label_source(component_sources: dict[str, str]) -> str:
    values = tuple(component_sources.values())
    if all(value == "REPLAY_PROXY" for value in values):
        return "REPLAY_PROXY_EXECUTION"
    return "PARTIAL_CANONICAL_EXECUTION"


def _execution_fidelity_gap_codes(
    component_sources: dict[str, str],
) -> tuple[str, ...]:
    return tuple(
        code
        for field_name, code in (
            ("fee_model_source", "FEE_MODEL_PROXY"),
            ("spread_model_source", "SPREAD_MODEL_PROXY"),
            ("slippage_model_source", "SLIPPAGE_MODEL_PROXY"),
            ("partial_fill_model_source", "PARTIAL_FILL_MODEL_PROXY"),
            ("adverse_selection_source", "ADVERSE_SELECTION_PROXY"),
            ("order_type_selection_source", "ORDER_TYPE_SELECTION_PROXY"),
            ("venue_constraints_source", "VENUE_CONSTRAINTS_PROXY"),
        )
        if component_sources.get(field_name) not in _PURE_CANONICAL_EXECUTION_SOURCES
    )


def _state_and_reason(
    row: HistoricalReplayOpportunity,
    *,
    config: ShadowExecutionSimulatorConfig,
    execution_profile: _RowExecutionProfile,
) -> tuple[DecisionState, str]:
    base_state = _base_state(row)
    expected_edge = row.expected_edge_bps / 10_000.0
    selected_states = {
        DecisionState.SELECTED,
        DecisionState.REDUCED,
        DecisionState.EXECUTED,
    }
    if (
        config.spread_guard_model is not None
        and base_state in selected_states
    ):
        try:
            spread_guard = evaluate_execution_spread_guard(
                config.spread_guard_model,
                current_spread_bps=row.spread_bps,
            )
        except ValueError:
            spread_guard = None
        if spread_guard is not None and spread_guard.blocked:
            return DecisionState.HARD_BLOCKED, spread_guard.reason_code
    if (
        base_state in selected_states
        and execution_profile.venue_constraints is not None
        and _violates_min_notional(row, execution_profile.venue_constraints)
    ):
        return DecisionState.HARD_BLOCKED, "VENUE_MIN_NOTIONAL_UNSATISFIED"
    if (
        base_state in selected_states
        and execution_profile.fee_aware_edge_reason_code
    ):
        return DecisionState.PHANTOM, execution_profile.fee_aware_edge_reason_code
    if (
        base_state in selected_states
        and execution_profile.order_type == OrderType.NO_TRADE
    ):
        return DecisionState.PHANTOM, execution_profile.order_reason
    if base_state in selected_states and expected_edge <= (
        execution_profile.expected_cost + config.economic_absurdity_buffer_bps / 10_000.0
    ):
        return DecisionState.PHANTOM, "economically_absurd"
    if base_state in selected_states and row.fill_ratio <= config.phantom_fill_threshold:
        return DecisionState.PHANTOM, row.primary_reason or "no_fill"
    if base_state in selected_states and row.fill_ratio < config.reduced_fill_threshold:
        return DecisionState.REDUCED, row.primary_reason or "partial_fill"
    if base_state == DecisionState.SELECTED:
        return DecisionState.EXECUTED, row.primary_reason or "shadow_compatible_execution"
    if base_state == DecisionState.HARD_BLOCKED:
        return DecisionState.HARD_BLOCKED, row.primary_reason or "hard_blocked"
    if base_state == DecisionState.REJECTED_RANKING:
        return DecisionState.REJECTED_RANKING, row.primary_reason or "rank_cutoff"
    return base_state, row.primary_reason


def _execution_factor(state: DecisionState, row: HistoricalReplayOpportunity) -> float:
    if state in {
        DecisionState.HARD_BLOCKED,
        DecisionState.REJECTED_RANKING,
        DecisionState.EVALUATED,
        DecisionState.NOT_EVALUATED,
    }:
        return 0.0
    if state == DecisionState.PHANTOM:
        return 0.0
    if state == DecisionState.REDUCED:
        return row.fill_ratio
    return 1.0


def simulate_shadow_compatible_dtrs(
    dataset: HistoricalReplayDataset,
    *,
    config: ShadowExecutionSimulatorConfig | None = None,
) -> tuple[DTRRecord, ...]:
    """Replay historical opportunities through a prudent Shadow-style simulator."""

    effective_config = config or ShadowExecutionSimulatorConfig()
    records: list[DTRRecord] = []
    for row in dataset.rows:
        provisional_execution_factor = _execution_factor(_base_state(row), row)
        execution_profile = _build_row_execution_profile(
            row,
            config=effective_config,
            execution_factor=provisional_execution_factor,
        )
        state, primary_reason = _state_and_reason(
            row,
            config=effective_config,
            execution_profile=execution_profile,
        )
        resolved_hard_block_reasons = row.hard_block_reasons
        if state == DecisionState.HARD_BLOCKED and not resolved_hard_block_reasons and primary_reason:
            resolved_hard_block_reasons = (primary_reason,)
        execution_factor = _execution_factor(state, row)
        execution_profile = _build_row_execution_profile(
            row,
            config=effective_config,
            execution_factor=execution_factor,
        )
        gross_return = round((row.gross_return_bps / 10_000.0) * execution_factor, 6)
        records.append(
            build_dtr(
                dtr_id=f"{dataset.dataset_id}:{row.opportunity_id}",
                pair=row.pair,
                engine_id=row.engine_id,
                decision_state=state,
                raw_score=row.raw_score,
                penalized_score=row.penalized_score or row.raw_score,
                final_score=row.final_score or row.raw_score,
                hard_blocked=bool(resolved_hard_block_reasons),
                hard_block_reasons=resolved_hard_block_reasons,
                ranking_position=row.ranking_position,
                candidate_size=row.candidate_size,
                final_size=(
                    row.final_size
                    if execution_factor >= 1.0
                    else round(row.final_size * execution_factor, 6)
                ),
                tier=row.tier,
                expected_cost=round(execution_profile.expected_cost, 6),
                realized_cost=round(execution_profile.realized_cost, 6),
                gross_return=gross_return,
                ce_expected=round(
                    (row.expected_edge_bps / 10_000.0) - execution_profile.expected_cost,
                    6,
                ),
                regime=row.regime,
                runtime_mode="local_replay",
                input_source="historical_data_gateway",
                path_complete=bool(row.feature_values) and row.shared_core_match,
                path_warnings=tuple(
                    warning
                    for warning in (
                        "" if row.feature_values else "missing_feature_values",
                        "" if row.shared_core_match else "shared_core_mismatch",
                    )
                    if warning
                ),
                primary_reason=primary_reason,
                cause_chain=(
                    resolved_hard_block_reasons
                    if resolved_hard_block_reasons
                    else ((primary_reason,) if primary_reason else ())
                ),
                timestamp=row.timestamp_ms / 1000.0,
            )
        )
    return tuple(records)


def build_parity_diagnostics_payload(
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
    *,
    config: ShadowExecutionSimulatorConfig | None = None,
) -> dict[str, object]:
    """Compare simulated replay outputs against optional production baselines."""

    effective_config = config or ShadowExecutionSimulatorConfig()
    row_profiles = tuple(
        _build_row_execution_profile(
            row,
            config=effective_config,
            execution_factor=_execution_factor(record.decision_state, row),
        )
        for row, record in zip(dataset.rows, dtr_records, strict=False)
    )
    component_sources = _aggregate_component_sources(row_profiles)
    parity_policy = effective_config.parity_policy
    decision_compared = 0
    decision_matches = 0
    score_compared = 0
    score_matches = 0
    cost_compared = 0
    cost_diffs: list[float] = []

    for row, record in zip(dataset.rows, dtr_records, strict=False):
        baseline_state = row.production_decision_state or row.target_decision_state
        if baseline_state is not None:
            decision_compared += 1
            if baseline_state == record.decision_state:
                decision_matches += 1

        baseline_score = (
            row.production_final_score
            if row.production_final_score is not None
            else row.final_score
        )
        if baseline_score is not None:
            score_compared += 1
            if (
                abs(float(baseline_score) - record.final_score)
                <= parity_policy.score_tolerance
            ):
                score_matches += 1

        if row.production_expected_cost is not None:
            cost_compared += 1
            cost_diffs.append(abs(row.production_expected_cost - record.expected_cost))

    decision_match_rate = (
        round_float64(decision_matches / decision_compared, 6)
        if decision_compared
        else 0.0
    )
    score_match_rate = (
        round_float64(score_matches / score_compared, 6) if score_compared else 0.0
    )
    mean_cost_gap = (
        round_float64(sum(cost_diffs) / len(cost_diffs), 6) if cost_diffs else 0.0
    )
    baseline_status = (
        "sufficient"
        if decision_compared >= parity_policy.minimum_compared_records
        else "insufficient"
    )
    score_alignment = (
        "within_prudent_tolerance"
        if score_compared and score_match_rate >= parity_policy.score_match_threshold
        else ("missing_baseline" if score_compared == 0 else "diverged")
    )
    cost_alignment = (
        "within_prudent_tolerance"
        if cost_compared and mean_cost_gap <= parity_policy.cost_tolerance
        else ("missing_baseline" if cost_compared == 0 else "diverged")
    )
    depth_contract = _resolve_book_depth_contract(dataset)
    fill_contract = _resolve_fill_realism_contract(dataset, dtr_records)
    replay_cost_component_values = {
        "expected_cost_total",
        *(
            component
            for profile in row_profiles
            for component in profile.replay_cost_components
        ),
    }
    if fill_contract["fill_ratio_expected"] is not None:
        replay_cost_component_values.add("fill_ratio_expected")
    if depth_contract["impact_source_status"] in {
        "IMPACT_SOURCE_DEPTH20_MODEL",
        "IMPACT_SOURCE_LIMITED_DEPTH_MODEL",
        "IMPACT_SOURCE_TOP_OF_BOOK_PROXY",
    }:
        replay_cost_component_values.add("impact_bps")
    replay_cost_components = tuple(sorted(replay_cost_component_values))
    parity_status = (
        "ok"
        if dataset.shared_core_match
        and dataset.missing_feature_rows == 0
        and baseline_status == "sufficient"
        and decision_match_rate >= parity_policy.decision_match_threshold
        and score_alignment == "within_prudent_tolerance"
        and cost_alignment == "within_prudent_tolerance"
        else "warning"
    )
    return ReplayParityDiagnosticsSummary(
        parity_status=parity_status,
        dataset_id=dataset.dataset_id,
        decision_match_rate=decision_match_rate,
        score_match_rate=score_match_rate,
        baseline_status=baseline_status,
        score_alignment=score_alignment,
        cost_alignment=cost_alignment,
        mean_cost_gap=mean_cost_gap,
        compared_records=decision_compared,
        missing_baseline_records=max(dataset.record_count - decision_compared, 0),
        divergence_count=max(decision_compared - decision_matches, 0),
        shared_core_match=dataset.shared_core_match,
        book_depth_available=depth_contract["book_depth_available"],
        book_depth_levels=depth_contract["book_depth_levels"],
        book_depth_source_status=depth_contract["book_depth_source_status"],
        book_depth_snapshot_count=depth_contract["book_depth_snapshot_count"],
        book_depth_event_count=depth_contract["book_depth_event_count"],
        book_depth_missing_count=depth_contract["book_depth_missing_count"],
        book_depth_staleness_status=depth_contract["book_depth_staleness_status"],
        impact_depth_level_used=depth_contract["impact_depth_level_used"],
        impact_depth_readiness_status=depth_contract["impact_depth_readiness_status"],
        shadow_extension_required=depth_contract["shadow_extension_required"],
        shadow_extension_reason=depth_contract["shadow_extension_reason"],
        minimum_shadow_days_required=depth_contract["minimum_shadow_days_required"],
        shadow_extension_status=depth_contract["shadow_extension_status"],
        impact_source_status=depth_contract["impact_source_status"],
        fill_ratio_source=str(fill_contract["fill_ratio_source"]),
        fill_realism_status=str(fill_contract["fill_realism_status"]),
        fill_source_status=str(fill_contract["fill_source_status"]),
        fill_model_name=fill_contract["fill_model_name"],
        fill_model_version=fill_contract["fill_model_version"],
        fill_ratio_expected=fill_contract["fill_ratio_expected"],
        fill_ratio_observed=fill_contract["fill_ratio_observed"],
        partial_fill_rate_expected=fill_contract["partial_fill_rate_expected"],
        partial_fill_rate_observed=fill_contract["partial_fill_rate_observed"],
        no_fill_rate_expected=fill_contract["no_fill_rate_expected"],
        no_fill_rate_observed=fill_contract["no_fill_rate_observed"],
        fill_latency_ms_expected=fill_contract["fill_latency_ms_expected"],
        fill_latency_ms_observed=fill_contract["fill_latency_ms_observed"],
        synthetic_fill_flag=bool(fill_contract["synthetic_fill_flag"]),
        measured_fill_flag=bool(fill_contract["measured_fill_flag"]),
        fill_provenance_ref=fill_contract["fill_provenance_ref"],
        fill_input_hash=fill_contract["fill_input_hash"],
        fill_policy_version=fill_contract["fill_policy_version"],
        realized_slippage_status="NOT_PROVEN",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        replay_cost_components=replay_cost_components,
        shadow_cost_components=(),
        live_cost_components=(),
        replay_fee_bps=None,
        shadow_fee_bps=None,
        live_fee_bps=None,
        replay_impact_bps=None,
        shadow_impact_bps=None,
        live_impact_bps=None,
        replay_slippage_bps=None,
        shadow_slippage_bps=None,
        live_slippage_bps=None,
        replay_fill_ratio=fill_contract["fill_ratio_expected"],
        shadow_fill_ratio=None,
        live_fill_ratio=None,
        cost_drift_bps=None,
        cost_drift_status="NOT_PROVEN",
        parity_sample_count=decision_compared,
        parity_window_start=str(dataset.start_timestamp_ms),
        parity_window_end=str(dataset.end_timestamp_ms),
        parity_input_hash=dataset.dataset_id,
        parity_policy_version="shadow_execution_simulator.v1",
        parity_policy=parity_policy.model_dump(mode="json"),
        canonical_execution_backbone_status=_canonical_execution_backbone_status(
            component_sources
        ),
        execution_label_source=_execution_label_source(component_sources),
        fee_model_source=component_sources["fee_model_source"],
        spread_model_source=component_sources["spread_model_source"],
        slippage_model_source=component_sources["slippage_model_source"],
        partial_fill_model_source=component_sources["partial_fill_model_source"],
        adverse_selection_source=component_sources["adverse_selection_source"],
        order_type_selection_source=component_sources["order_type_selection_source"],
        venue_constraints_source=component_sources["venue_constraints_source"],
        execution_fidelity_gap_codes=_execution_fidelity_gap_codes(component_sources),
        spread_guard_model_loaded=effective_config.spread_guard_model is not None,
        slippage_model_loaded=effective_config.slippage_model is not None,
        execution_runtime_projection_ref=effective_config.execution_runtime_projection_ref,
        canonical_expected_cost_components=_canonical_expected_cost_components(
            effective_config,
            component_sources,
        ),
    ).model_dump(mode="json")


__all__ = [
    "ParityTolerancePolicy",
    "ReplayParityDiagnosticsSummary",
    "ShadowExecutionSimulatorConfig",
    "simulate_shadow_compatible_dtrs",
    "build_parity_diagnostics_payload",
]
