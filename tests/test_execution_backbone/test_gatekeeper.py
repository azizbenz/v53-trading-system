"""Direct tests for the canonical execution gatekeeper wrapper."""

import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from execution_backbone.execution_runtime import ExecutionOpportunity
from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeDecision
from execution_backbone.gatekeeper import (
    ExecutionGateName,
    ExecutionGateRefusalDisposition,
    ExecutionGateTraceVerdict,
    ExecutionGatekeeper,
    GatekeeperAuditLogger,
    ExecutionVenueNormalizationResult,
)
from execution_backbone.gatekeeper.gatekeeper import ExecutionPermit, ExecutionRefusal
from execution_backbone.order_decider.intent_builder import OrderType, VenueConstraintSnapshot
from execution_backbone.rate_limiter import ExecutionRateLimitDecision
from execution_backbone.spread_guard import ExecutionSpreadGuardDecision


pytestmark = pytest.mark.build3


def _audit_dir(label: str) -> Path:
    root = Path("build/pytest-gatekeeper-audit") / f"{label}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def _opportunity(**updates: object) -> ExecutionOpportunity:
    base = ExecutionOpportunity(
        intent_id="intent-1",
        pair="BTCUSDT",
        engine_id="engine_a",
        side="buy",
        quantity=0.25,
        expected_gain=0.0100,
        expected_cost=0.0015,
        score=0.82,
        justification="validated execution path",
        spread_bps=2.0,
        reference_price=50_000.0,
    )
    return base.model_copy(update=updates)


def _build_gatekeeper(
    *,
    spread_guard=None,
    fee_aware_edge=None,
    sharia=None,
    rate_limit=None,
    venue_constraints=None,
    normalization=None,
    max_spread_for_market: float = 10.0,
    execution_no_trade_filter=None,
) -> ExecutionGatekeeper:
    return ExecutionGatekeeper(
        resolve_spread_guard=(
            spread_guard if spread_guard is not None else (lambda opportunity: None)
        ),
        resolve_fee_aware_edge=(
            fee_aware_edge if fee_aware_edge is not None else (lambda opportunity: None)
        ),
        authorize_sharia=sharia if sharia is not None else (lambda opportunity: None),
        resolve_rate_limit=(
            rate_limit if rate_limit is not None else (lambda opportunity: None)
        ),
        resolve_venue_constraints=(
            venue_constraints
            if venue_constraints is not None
            else (lambda opportunity: opportunity.venue_constraints)
        ),
        normalize_venue_order_fields=(
            normalization
            if normalization is not None
            else (
                lambda **kwargs: (_ for _ in ()).throw(
                    AssertionError("normalization callback should not run in this test")
                )
            )
        ),
        resolve_max_spread_for_market=lambda opportunity: max_spread_for_market,
        evaluate_execution_no_trade_filter=(
            execution_no_trade_filter
            if execution_no_trade_filter is not None
            else (lambda opportunity: None)
        ),
    )


def test_gatekeeper_refusal_preserves_pair_and_engine_id():
    gatekeeper = _build_gatekeeper(
        spread_guard=lambda opportunity: ExecutionSpreadGuardDecision(
            blocked=True,
            reason_code="SPREAD_GUARD_THRESHOLD_EXCEEDED",
            detail="spread too wide",
            current_spread_bps=15.0,
            max_spread_bps=12.0,
        ),
    )

    outcome = gatekeeper.authorize(_opportunity(spread_bps=15.0))

    assert isinstance(outcome, ExecutionRefusal)
    assert outcome.disposition == ExecutionGateRefusalDisposition.NO_TRADE
    assert outcome.gate_name == ExecutionGateName.SPREAD_GUARD
    assert outcome.no_trade.pair == "BTCUSDT"
    assert outcome.no_trade.engine_id == "engine_a"
    assert outcome.no_trade.context["gate"] == "spread_guard"
    assert len(outcome.trace) == 1
    assert outcome.trace[0].gate_name == ExecutionGateName.SPREAD_GUARD
    assert outcome.trace[0].verdict == ExecutionGateTraceVerdict.REFUSED


def test_gatekeeper_permit_returns_intent_and_trace():
    constraints = VenueConstraintSnapshot(
        tick_size="0.1",
        step_size="0.01",
        min_notional="10",
    )
    gatekeeper = _build_gatekeeper(
        spread_guard=lambda opportunity: ExecutionSpreadGuardDecision(
            blocked=False,
            current_spread_bps=6.0,
            max_spread_bps=10.0,
        ),
        fee_aware_edge=lambda opportunity: FeeAwareEdgeDecision(
            allowed=True,
            expected_edge_bps=30.0,
            expected_cost_fraction=0.0007,
            expected_cost_bps=7.0,
            edge_multiplier=1.2,
            min_absolute_edge_bps=8.0,
            threshold_bps=8.4,
            detail="edge clears fee threshold",
        ),
        rate_limit=lambda opportunity: ExecutionRateLimitDecision(
            blocked=False,
            current_quota_ratio=0.25,
            quota_ratio_ceiling=0.80,
        ),
        venue_constraints=lambda opportunity: constraints,
        normalization=lambda **kwargs: ExecutionVenueNormalizationResult(
            quantity=1.23,
            quantity_exact="1.23",
            price_limit=50_000.0,
            price_limit_exact="50000",
        ),
        max_spread_for_market=10.0,
    )

    outcome = gatekeeper.authorize(
        _opportunity(
            quantity=1.234,
            spread_bps=6.0,
            reference_price=50_000.03,
            venue_constraints=constraints,
        )
    )

    assert isinstance(outcome, ExecutionPermit)
    assert outcome.intent.pair == "BTCUSDT"
    assert outcome.intent.engine_id == "engine_a"
    assert outcome.intent.order_type == OrderType.LIMIT
    assert outcome.intent.quantity == pytest.approx(1.23)
    assert outcome.intent.quantity_exact == "1.23"
    assert outcome.intent.price_limit == pytest.approx(50_000.0)
    assert outcome.intent.price_limit_exact == "50000"
    assert tuple(step.gate_name for step in outcome.trace) == (
        ExecutionGateName.SPREAD_GUARD,
        ExecutionGateName.ORDER_TYPE,
        ExecutionGateName.FEE_AWARE_EDGE,
        ExecutionGateName.RATE_LIMITER,
        ExecutionGateName.EXECUTION_GUARD,
        ExecutionGateName.PRICE_LIMIT,
        ExecutionGateName.VENUE_CONSTRAINTS,
    )
    assert all(step.verdict == ExecutionGateTraceVerdict.PASSED for step in outcome.trace)


def test_gatekeeper_audit_logger_writes_refusal_event():
    gatekeeper = _build_gatekeeper(
        spread_guard=lambda opportunity: ExecutionSpreadGuardDecision(
            blocked=True,
            reason_code="SPREAD_GUARD_THRESHOLD_EXCEEDED",
            detail="spread too wide",
            current_spread_bps=15.0,
            max_spread_bps=12.0,
        ),
    )
    outcome = gatekeeper.authorize(_opportunity(spread_bps=15.0))

    assert isinstance(outcome, ExecutionRefusal)
    root = _audit_dir("refusal")
    try:
        audit_path = root / "artifacts" / "gatekeeper" / "audit.jsonl"
        logger = GatekeeperAuditLogger(audit_path)
        logger.record_refusal(
            opportunity=_opportunity(spread_bps=15.0),
            refusal=outcome,
            timestamp_s=100.0,
        )

        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["decision"] == "no_trade"
        assert payload["gate_name"] == "spread_guard"
        assert payload["pair"] == "BTCUSDT"
        assert payload["engine_id"] == "engine_a"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_gatekeeper_audit_logger_writes_submission_event():
    constraints = VenueConstraintSnapshot(
        tick_size="0.1",
        step_size="0.01",
        min_notional="10",
    )
    gatekeeper = _build_gatekeeper(
        spread_guard=lambda opportunity: ExecutionSpreadGuardDecision(
            blocked=False,
            current_spread_bps=6.0,
            max_spread_bps=10.0,
        ),
        fee_aware_edge=lambda opportunity: FeeAwareEdgeDecision(
            allowed=True,
            expected_edge_bps=30.0,
            expected_cost_fraction=0.0007,
            expected_cost_bps=7.0,
            edge_multiplier=1.2,
            min_absolute_edge_bps=8.0,
            threshold_bps=8.4,
            detail="edge clears fee threshold",
        ),
        rate_limit=lambda opportunity: ExecutionRateLimitDecision(
            blocked=False,
            current_quota_ratio=0.25,
            quota_ratio_ceiling=0.80,
        ),
        venue_constraints=lambda opportunity: constraints,
        normalization=lambda **kwargs: ExecutionVenueNormalizationResult(
            quantity=1.23,
            quantity_exact="1.23",
            price_limit=50_000.0,
            price_limit_exact="50000",
        ),
        max_spread_for_market=10.0,
    )
    opportunity = _opportunity(
        quantity=1.234,
        spread_bps=6.0,
        reference_price=50_000.03,
        venue_constraints=constraints,
    )
    outcome = gatekeeper.authorize(opportunity)

    assert isinstance(outcome, ExecutionPermit)
    root = _audit_dir("submission")
    try:
        audit_path = root / "artifacts" / "gatekeeper" / "audit.jsonl"
        logger = GatekeeperAuditLogger(audit_path)
        logger.record_submission(
            opportunity=opportunity,
            permit=outcome,
            order_id="ord-1",
            timestamp_s=100.0,
        )

        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["decision"] == "submitted"
        assert payload["order_id"] == "ord-1"
        assert payload["order_type"] == "limit"
        assert payload["pair"] == "BTCUSDT"
    finally:
        shutil.rmtree(root, ignore_errors=True)
