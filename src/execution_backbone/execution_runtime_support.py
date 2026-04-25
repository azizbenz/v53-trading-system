"""Internal support mixin for the canonical Build-3 execution runtime."""

from __future__ import annotations

import logging
import math

from sharia_compliance.contracts import ShariaPermit, ShariaRejection, ShariaTradeRequest

from interface_contracts import (
    decimal_to_canonical_str,
    decimal_to_float64,
    execution_decimal,
    multiply_exact,
    quantize_down_to_step,
    quantize_up_to_step,
    RefusalCategory,
    RefusalRecord,
)

from .fee_aware_edge_gate import FeeAwareEdgeDecision, evaluate_fee_aware_edge
from .execution_cost_meter.adverse_selection_meter import resolve_adverse_selection_delay_s
from .fill_tracker.order_state_tracker import TERMINAL_STATES
from .gatekeeper import (
    ExecutionGateName,
    ExecutionPermit,
    ExecutionGateRefusalDisposition,
    ExecutionRefusal,
    ExecutionVenueNormalizationResult,
)
from .order_decider.intent_builder import OrderType, VenueConstraintSnapshot
from .rate_limiter import ExecutionRateLimitDecision, evaluate_execution_rate_limit
from .spread_guard import ExecutionSpreadGuardDecision, evaluate_execution_spread_guard
from .slippage_model import ExecutionSlippageEstimate, predict_execution_slippage
from .execution_runtime_models import (
    ExecutionNoTradeFilterInput,
    ExecutionNoTradeFilterOutcome,
    ExecutionOpportunity,
    _TerminalOrderSnapshot,
)


logger = logging.getLogger("execution_backbone.execution_runtime")

_KNOWN_QUOTE_SUFFIXES = (
    "USDT",
    "FDUSD",
    "USDC",
    "BUSD",
    "TUSD",
    "EUR",
    "USD",
    "BTC",
    "ETH",
    "BNB",
)


class ExecutionRuntimeSupportMixin:
    def _run_execution_no_trade_filter(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ExecutionNoTradeFilterOutcome | None:
        if self._execution_no_trade_filter is None:
            return None
        hook_input = ExecutionNoTradeFilterInput(
            intent_id=opportunity.intent_id,
            pair=opportunity.pair,
            engine_id=opportunity.engine_id,
            expected_cost=opportunity.expected_cost,
            expected_gain=opportunity.expected_gain,
            score=opportunity.score,
        )
        return self._execution_no_trade_filter(hook_input)

    def _run_rate_limit_guard(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ExecutionRateLimitDecision | None:
        if self._rate_limit_model is None:
            return None
        raw_value = opportunity.metadata.get("rest_quota_ratio_current")
        if raw_value is None:
            return None
        try:
            current_quota_ratio = float(raw_value)
        except (TypeError, ValueError):
            logger.warning(
                "execution_rate_limit_telemetry_invalid",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                },
            )
            return None
        if not math.isfinite(current_quota_ratio) or current_quota_ratio < 0.0:
            logger.warning(
                "execution_rate_limit_telemetry_invalid",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                },
            )
            return None
        return evaluate_execution_rate_limit(
            self._rate_limit_model,
            current_quota_ratio=current_quota_ratio,
        )

    def _run_spread_guard(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ExecutionSpreadGuardDecision | None:
        if self._spread_guard_model is None:
            return None
        current_spread_bps = opportunity.spread_bps
        if not math.isfinite(current_spread_bps) or current_spread_bps < 0.0:
            logger.warning(
                "execution_spread_guard_telemetry_invalid",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                },
            )
            return None
        return evaluate_execution_spread_guard(
            self._spread_guard_model,
            current_spread_bps=current_spread_bps,
        )

    def _run_fee_aware_edge_gate(
        self,
        opportunity: ExecutionOpportunity,
    ) -> FeeAwareEdgeDecision | None:
        if self._fee_aware_edge_gate_config is None:
            return None
        return evaluate_fee_aware_edge(
            expected_edge_bps=opportunity.expected_gain * 10_000.0,
            expected_cost=opportunity.expected_cost,
            config=self._fee_aware_edge_gate_config,
        )

    def _log_gatekeeper_refusal(
        self,
        refusal: ExecutionRefusal,
        opportunity: ExecutionOpportunity,
        now: float,
    ) -> None:
        extra = {
            "intent_id": opportunity.intent_id,
            "pair": opportunity.pair,
            "engine_id": opportunity.engine_id,
            "gate_trace": tuple(step.model_dump(mode="json") for step in refusal.trace),
            "timestamp": now,
        }
        context = refusal.no_trade.context
        if refusal.gate_name == ExecutionGateName.SPREAD_GUARD:
            logger.warning(
                "execution_submission_spread_guard_blocked",
                extra={
                    **extra,
                    "current_spread_bps": context.get("current_spread_bps"),
                    "max_spread_bps": context.get("max_spread_bps"),
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.ORDER_TYPE:
            logger.warning(
                "execution_submission_no_trade",
                extra={
                    **extra,
                    "reason": refusal.no_trade.reason.value,
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.FEE_AWARE_EDGE:
            logger.warning(
                "execution_submission_fee_aware_edge_blocked",
                extra={
                    **extra,
                    "reason_code": context.get("reason_code", ""),
                    "expected_edge_bps": context.get("expected_edge_bps"),
                    "expected_cost_bps": context.get("expected_cost_bps"),
                    "threshold_bps": context.get("threshold_bps"),
                    "edge_multiplier": context.get("edge_multiplier"),
                    "min_absolute_edge_bps": context.get("min_absolute_edge_bps"),
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.SHARIA:
            logger.warning(
                "execution_submission_sharia_blocked",
                extra={
                    **extra,
                    "reason_code": context.get("reason_code", ""),
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.RATE_LIMITER:
            logger.warning(
                "execution_submission_rate_limited",
                extra={
                    **extra,
                    "current_quota_ratio": context.get("current_quota_ratio"),
                    "quota_ratio_ceiling": context.get("quota_ratio_ceiling"),
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.EXECUTION_GUARD:
            logger.warning(
                "execution_submission_blocked",
                extra={
                    **extra,
                    "blocks": (
                        tuple(block.value for block in refusal.guard.blocks)
                        if refusal.guard is not None
                        else ()
                    ),
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.PRICE_LIMIT:
            logger.warning("execution_submission_invalid_limit", extra=extra)
            return
        if refusal.gate_name == ExecutionGateName.VENUE_CONSTRAINTS:
            logger.warning(
                "execution_submission_venue_constraints",
                extra={
                    **extra,
                    "detail": refusal.detail,
                },
            )
            return
        if refusal.gate_name == ExecutionGateName.EXECUTION_NO_TRADE_FILTER:
            logger.warning(
                "execution_submission_filtered",
                extra={
                    **extra,
                    "block_reason_codes": refusal.reason_codes,
                },
            )
            return
        logger.warning(
            "execution_submission_gatekeeper_refused",
            extra={
                **extra,
                "gate_name": refusal.gate_name.value,
                "detail": refusal.detail,
            },
        )

    def _record_gatekeeper_refusal_audit(
        self,
        *,
        refusal: ExecutionRefusal,
        opportunity: ExecutionOpportunity,
        now: float,
    ) -> None:
        if self._gatekeeper_audit_logger is None:
            return
        self._gatekeeper_audit_logger.record_refusal(
            opportunity=opportunity,
            refusal=refusal,
            timestamp_s=now,
        )

    def _record_runtime_refusal(
        self,
        *,
        refusal: ExecutionRefusal,
        opportunity: ExecutionOpportunity,
        now: float,
    ) -> None:
        if self._refusal_sink is None:
            return
        record = self._build_runtime_refusal_record(
            refusal=refusal,
            opportunity=opportunity,
            now=now,
        )
        if record is None:
            logger.warning(
                "execution_refusal_journal_skipped_invalid_timestamp",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                    "gate_name": refusal.gate_name.value,
                    "timestamp": now,
                },
            )
            return
        self._refusal_sink.record_refusal(record)

    def _build_runtime_refusal_record(
        self,
        *,
        refusal: ExecutionRefusal,
        opportunity: ExecutionOpportunity,
        now: float,
    ) -> RefusalRecord | None:
        timestamp_ms = self._resolve_refusal_timestamp_ms(opportunity=opportunity, now=now)
        if timestamp_ms is None:
            return None
        category = (
            RefusalCategory.HARD_BLOCK
            if refusal.disposition == ExecutionGateRefusalDisposition.BLOCKED
            else RefusalCategory.NO_TRADE
        )
        return RefusalRecord(
            timestamp_ms=timestamp_ms,
            pair=opportunity.pair,
            engine_id=self._resolve_refusal_engine_id(opportunity.engine_id),
            category=category,
            reason_codes=self._resolve_refusal_reason_codes(refusal),
        )

    @staticmethod
    def _resolve_refusal_timestamp_ms(
        *,
        opportunity: ExecutionOpportunity,
        now: float,
    ) -> int | None:
        metadata_timestamp = opportunity.metadata.get("timestamp_ms")
        if isinstance(metadata_timestamp, int):
            if 1_000_000_000_000 <= metadata_timestamp <= 9_999_999_999_999:
                return metadata_timestamp
        elif isinstance(metadata_timestamp, float):
            normalized = int(metadata_timestamp)
            if 1_000_000_000_000 <= normalized <= 9_999_999_999_999:
                return normalized

        now_ms = int(now * 1000.0)
        if 1_000_000_000_000 <= now_ms <= 9_999_999_999_999:
            return now_ms
        return None

    @staticmethod
    def _resolve_refusal_engine_id(engine_id: str) -> str | None:
        if engine_id in {"engine_a", "engine_b", "engine_c", "engine_d"}:
            return engine_id
        return None

    @staticmethod
    def _resolve_refusal_reason_codes(refusal: ExecutionRefusal) -> tuple[str, ...]:
        if refusal.reason_codes:
            return refusal.reason_codes
        if refusal.guard is not None and refusal.guard.blocks:
            return tuple(block.value for block in refusal.guard.blocks)
        context_reason_code = refusal.no_trade.context.get("reason_code")
        if isinstance(context_reason_code, str) and context_reason_code.strip():
            return (context_reason_code.strip(),)
        return (f"execution.{refusal.gate_name.value}.{refusal.no_trade.reason.value}",)

    def _record_gatekeeper_submission_audit(
        self,
        *,
        permit: ExecutionPermit,
        opportunity: ExecutionOpportunity,
        order_id: str,
        now: float,
    ) -> None:
        if self._gatekeeper_audit_logger is None:
            return
        self._gatekeeper_audit_logger.record_submission(
            opportunity=opportunity,
            permit=permit,
            order_id=order_id,
            timestamp_s=now,
        )

    def _run_sharia_trade_authorizer(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ShariaPermit | ShariaRejection | None:
        if self._sharia_trade_authorizer is None:
            return None
        return self._sharia_trade_authorizer.authorize_trade(
            ShariaTradeRequest(
                intent_id=opportunity.intent_id,
                pair=opportunity.pair,
                engine_id=opportunity.engine_id,
                side=opportunity.side,
                profile=opportunity.profile,
                metadata=dict(opportunity.metadata),
            )
        )

    def _apply_runtime_slippage_model(
        self,
        opportunity: ExecutionOpportunity,
    ) -> ExecutionOpportunity:
        if self._slippage_model is None:
            return opportunity
        try:
            estimate = predict_execution_slippage(
                self._slippage_model,
                size_value=opportunity.quantity,
            )
        except ValueError:
            logger.warning(
                "execution_slippage_model_invalid",
                extra={
                    "intent_id": opportunity.intent_id,
                    "pair": opportunity.pair,
                    "engine_id": opportunity.engine_id,
                },
            )
            return opportunity
        updated_metadata = dict(opportunity.metadata)
        updated_metadata["execution_slippage_model"] = self._build_slippage_metadata_payload(
            estimate
        )
        return opportunity.model_copy(
            update={
                "expected_cost": opportunity.expected_cost + estimate.cost_addition,
                "metadata": updated_metadata,
            }
        )

    def _resolve_max_spread_for_market(
        self,
        opportunity: ExecutionOpportunity,
    ) -> float:
        if self._spread_guard_model is None:
            return 10.0
        return self._spread_guard_model.max_spread_bps

    @staticmethod
    def _build_slippage_metadata_payload(
        estimate: ExecutionSlippageEstimate,
    ) -> dict[str, str | float]:
        return {
            "threshold_id": estimate.source_threshold_id,
            "size_proxy": estimate.size_proxy,
            "size_value": estimate.size_value,
            "predicted_slippage_bps": estimate.predicted_slippage_bps,
            "cost_addition": estimate.cost_addition,
        }

    def _resolve_adverse_selection_delay_s(
        self,
        *,
        pair: str,
        event_delay_s: float | None,
    ) -> float:
        return resolve_adverse_selection_delay_s(
            pair=pair,
            event_delay_s=event_delay_s,
            policy=self._adverse_selection_delay_policy,
        )

    def _next_replacement_intent_id(self, *, base_intent_id: str, order_id: str) -> str:
        self._replacement_intent_nonce += 1
        return f"{base_intent_id}:replace:{order_id}:{self._replacement_intent_nonce}"

    def _update_local_position(self, pair: str, side: str, quantity: float) -> None:
        base_asset = self._extract_base_asset(pair)
        signed_quantity = quantity if side.lower() == "buy" else -quantity
        self._local_positions[base_asset] = self._local_positions.get(base_asset, 0.0) + signed_quantity

    def _local_open_order_states(self) -> dict[str, str]:
        return {record.order_id: record.state.value for record in self._state_tracker.get_open_orders()}

    def _remote_open_order_states(self, remote_orders: dict[str, str]) -> dict[str, str]:
        terminal_values = {state.value for state in TERMINAL_STATES}
        return {
            order_id: state
            for order_id, state in remote_orders.items()
            if state not in terminal_values
        }

    def _local_fill_quantities(self) -> dict[str, float]:
        fill_quantities = {
            aggregated.order_id: aggregated.total_filled_qty
            for aggregated in (
                self._fill_aggregator.get_aggregated(order_id)
                for order_id in self._intents
            )
            if aggregated is not None
        }
        for order_id, snapshot in self._terminal_orders.items():
            fill_quantities.setdefault(order_id, snapshot.filled_quantity)
        return fill_quantities

    def _retain_terminal_snapshot(self, order_id: str, *, filled_quantity: float) -> None:
        self._terminal_orders[order_id] = _TerminalOrderSnapshot(
            filled_quantity=filled_quantity
        )
        self._terminal_order_sequence.append(order_id)
        self._prune_terminal_snapshots()

    def _prune_terminal_snapshots(self) -> None:
        while len(self._terminal_order_sequence) > self._terminal_order_retention:
            oldest_order_id = self._terminal_order_sequence.popleft()
            self._terminal_orders.pop(oldest_order_id, None)

    def _release_terminal_order_state(self, order_id: str) -> None:
        self._pending_cancels.discard(order_id)
        self._timeout_by_order_id.pop(order_id, None)
        self._cost_context.pop(order_id, None)
        self._cost_recorded.discard(order_id)
        if hasattr(self, "_hybrid_plans_by_order_id"):
            self._hybrid_plans_by_order_id.pop(order_id, None)
        if hasattr(self, "_hybrid_decisions_by_order_id"):
            self._hybrid_decisions_by_order_id.pop(order_id, None)
        if hasattr(self, "_hybrid_shadow_record_id_by_order_id"):
            self._hybrid_shadow_record_id_by_order_id.pop(order_id, None)
        self._intents.pop(order_id, None)
        self._fill_aggregator.evict_order(order_id)
        self._state_tracker.evict_order(order_id)

    def _extract_base_asset(self, pair: str) -> str:
        for suffix in _KNOWN_QUOTE_SUFFIXES:
            if pair.endswith(suffix) and len(pair) > len(suffix):
                return pair[: -len(suffix)]
        return pair

    def _resolve_venue_constraints(
        self,
        opportunity: ExecutionOpportunity,
    ) -> VenueConstraintSnapshot | None:
        if opportunity.venue_constraints is not None:
            return opportunity.venue_constraints
        adapter_constraints = self._adapter.fetch_venue_constraints(opportunity.pair)
        if adapter_constraints is not None:
            return adapter_constraints
        if self._venue_constraint_provider is None:
            return None
        return self._venue_constraint_provider.fetch_venue_constraints(opportunity.pair)

    def _normalize_venue_order_fields(
        self,
        *,
        quantity: float,
        side: str,
        order_type: OrderType,
        price_limit: float | None,
        reference_price: float | None,
        constraints: VenueConstraintSnapshot,
    ) -> ExecutionVenueNormalizationResult:
        quantity_decimal = execution_decimal(quantity, name="quantity")
        quantity_decimal = (
            quantize_down_to_step(quantity_decimal, constraints.step_size)
            if constraints.step_size is not None
            else quantity_decimal
        )
        if quantity_decimal <= 0:
            return ExecutionVenueNormalizationResult(
                quantity=0.0,
                quantity_exact="0",
                error_detail="venue constraints reduce quantity to zero",
            )

        normalized_price_limit: float | None = price_limit
        price_limit_exact: str | None = None
        price_anchor_decimal = (
            execution_decimal(price_limit, name="price_limit")
            if price_limit is not None
            else (
                execution_decimal(reference_price, name="reference_price")
                if reference_price is not None
                else None
            )
        )

        if price_limit is not None and constraints.tick_size is not None:
            normalized_price_decimal = (
                quantize_down_to_step(price_limit, constraints.tick_size)
                if side.lower() == "buy"
                else quantize_up_to_step(price_limit, constraints.tick_size)
            )
            if normalized_price_decimal <= 0:
                return ExecutionVenueNormalizationResult(
                    quantity=0.0,
                    quantity_exact="0",
                    error_detail="venue constraints reduce price limit to zero",
                )
            normalized_price_limit = decimal_to_float64(
                normalized_price_decimal,
                max_abs_loss=constraints.tick_size,
                name="normalized_price_limit",
            )
            price_limit_exact = decimal_to_canonical_str(normalized_price_decimal)
            price_anchor_decimal = normalized_price_decimal

        if constraints.min_notional is not None:
            if price_anchor_decimal is None:
                return ExecutionVenueNormalizationResult(
                    quantity=0.0,
                    quantity_exact="0",
                    error_detail="min_notional requires a usable price anchor",
                )
            normalized_notional = multiply_exact(quantity_decimal, price_anchor_decimal)
            if normalized_notional < execution_decimal(
                constraints.min_notional, name="min_notional"
            ):
                return ExecutionVenueNormalizationResult(
                    quantity=0.0,
                    quantity_exact="0",
                    error_detail="normalized order violates venue min_notional",
                )

        return ExecutionVenueNormalizationResult(
            quantity=decimal_to_float64(
                quantity_decimal,
                max_abs_loss=constraints.step_size,
                name="normalized_quantity",
            )
            if constraints.step_size is not None
            else decimal_to_float64(quantity_decimal, name="normalized_quantity"),
            quantity_exact=decimal_to_canonical_str(quantity_decimal),
            price_limit=normalized_price_limit,
            price_limit_exact=price_limit_exact,
        )
