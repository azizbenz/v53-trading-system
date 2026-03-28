"""
V5.3 — TESTS INTERFACE_CONTRACTS
57 tests validés — Build-1, Module 1
"""
import pytest
from pydantic import ValidationError

from interface_contracts.domain_types import (
    ALL_PAIRS, COMPLETE_ADDITIONAL_PAIRS, ENGINE_PAIR_MAP, LIGHT_PAIRS,
    PAIR_TIER_MAP, DeploymentState, EngineId, ModuleLayer, ModuleStatus,
    PairId, ProfileId, PromotionState, RegimeId, ReviewState, RuntimeMode,
    Side, StrategyClassification, Tier, Timeframe, TimestampedModel,
)
from interface_contracts.market_event_contracts import (
    DepthEvent, DepthLevel, HeartbeatEvent, KlineEvent, SnapshotEvent, TradeEvent,
)
from interface_contracts.decision_contracts import (
    BlockReason, ExecutionIntent, ExecutionStatus, PenaltyDetail, PortfolioAction,
    PortfolioDecision, RiskDecision, RiskVerdict, ScorePayload, SignalCandidate,
    SignalType,
)
from interface_contracts.meta_contracts import (
    AlertCategory, AlertRecord, AlertSeverity, CostRecord, DTROutcome,
    DTRRecord, EdgeEstimate, PairHealthLevel, PairHealthStatus,
)
from interface_contracts.error_contracts import (
    BootstrapError, ContractViolationError, DataStaleError,
    DependencyViolationError, EngineNotAllowedError,
    InvalidProfileActivationError, PairSuspendedError, ReconciliationError,
    RiskBudgetExceededError, V53BaseError,
)


NOW_MS = 1_700_000_000_000


class TestEnums:
    def test_engine_ids(self):
        assert set(EngineId) == {EngineId.A, EngineId.B, EngineId.C, EngineId.D}

    def test_profile_ids(self):
        assert set(ProfileId) == {ProfileId.LIGHT, ProfileId.COMPLETE}

    def test_runtime_modes(self):
        assert {mode.value for mode in RuntimeMode} == {
            "local_replay",
            "shadow",
            "micro_live",
            "live",
        }

    def test_strategy_classifications(self):
        assert {classification.value for classification in StrategyClassification} == {
            "a_variant",
            "b_variant",
            "build14_enabler",
            "c_candidate",
            "d_candidate",
            "out_of_scope_for_v5_3",
        }

    def test_review_and_promotion_states(self):
        assert ReviewState.PENDING.value == "pending"
        assert PromotionState.REPLAY_ONLY.value == "replay_only"

    def test_deployment_states_completeness(self):
        expected = {"offline", "bootstrap", "shadow", "micro_live", "live_light",
                    "live_complete", "degraded", "halted", "rollback"}
        assert {s.value for s in DeploymentState} == expected

    def test_tiers(self):
        assert Tier.TIER_1.value == 1
        assert Tier.TIER_2.value == 2
        assert Tier.TIER_3.value == 3

    def test_sides(self):
        assert set(Side) == {Side.BUY, Side.SELL}

    def test_module_layers_order(self):
        layers = {l.value for l in ModuleLayer}
        for expected in ["contracts", "data", "execution", "risk", "scoring", "engine"]:
            assert expected in layers


class TestPairConstants:
    def test_light_pairs_count(self):
        assert len(LIGHT_PAIRS) == 6

    def test_complete_additional_count(self):
        assert len(COMPLETE_ADDITIONAL_PAIRS) == 6

    def test_all_pairs_count(self):
        assert len(ALL_PAIRS) == 12

    def test_all_pairs_union(self):
        assert ALL_PAIRS == LIGHT_PAIRS | COMPLETE_ADDITIONAL_PAIRS

    def test_no_overlap(self):
        assert len(LIGHT_PAIRS & COMPLETE_ADDITIONAL_PAIRS) == 0

    def test_tier_map_covers_all_pairs(self):
        assert set(PAIR_TIER_MAP.keys()) == ALL_PAIRS

    def test_btc_eth_tier1(self):
        assert PAIR_TIER_MAP["BTCUSDT"] == Tier.TIER_1
        assert PAIR_TIER_MAP["ETHUSDT"] == Tier.TIER_1

    def test_engine_pair_map_complete(self):
        assert set(ENGINE_PAIR_MAP.keys()) == set(EngineId)


class TestPairId:
    def test_valid_pair(self):
        p = PairId.from_symbol("BTCUSDT")
        assert p.symbol == "BTCUSDT"
        assert p.tier == Tier.TIER_1

    def test_case_insensitive(self):
        assert PairId.from_symbol("btcusdt").symbol == "BTCUSDT"

    def test_invalid_pair_rejected(self):
        with pytest.raises(ValueError):
            PairId.from_symbol("DOGEUSDT")

    def test_is_light(self):
        assert PairId.from_symbol("BTCUSDT").is_light() is True
        assert PairId.from_symbol("ADAUSDT").is_light() is False

    def test_frozen(self):
        with pytest.raises(ValidationError):
            PairId.from_symbol("ETHUSDT").symbol = "BTCUSDT"


class TestTimestampedModel:
    def test_valid_timestamp(self):
        assert TimestampedModel(timestamp_ms=NOW_MS).timestamp_ms == NOW_MS

    def test_timestamp_too_low(self):
        with pytest.raises(ValidationError):
            TimestampedModel(timestamp_ms=999_999_999_999)

    def test_timestamp_too_high(self):
        with pytest.raises(ValidationError):
            TimestampedModel(timestamp_ms=10_000_000_000_000)

    def test_timestamp_dt_property(self):
        assert TimestampedModel(timestamp_ms=NOW_MS).timestamp_dt.year >= 2020


class TestTradeEvent:
    def test_valid_trade(self):
        t = TradeEvent(pair="BTCUSDT", price=50000.0, quantity=0.1,
                       side=Side.BUY, trade_id="12345", timestamp_ms=NOW_MS)
        assert t.notional_usdt == 5000.0

    def test_price_zero_rejected(self):
        with pytest.raises(ValidationError):
            TradeEvent(pair="BTCUSDT", price=0, quantity=0.1,
                       side=Side.BUY, trade_id="12345", timestamp_ms=NOW_MS)

    def test_quantity_negative_rejected(self):
        with pytest.raises(ValidationError):
            TradeEvent(pair="BTCUSDT", price=50000.0, quantity=-0.1,
                       side=Side.BUY, trade_id="12345", timestamp_ms=NOW_MS)


class TestDepthEvent:
    def test_valid_depth(self):
        d = DepthEvent(pair="ETHUSDT",
            bids=[DepthLevel(price=3000, quantity=10), DepthLevel(price=2999, quantity=5)],
            asks=[DepthLevel(price=3001, quantity=8), DepthLevel(price=3002, quantity=3)],
            timestamp_ms=NOW_MS)
        assert d.best_bid == 3000.0
        assert d.best_ask == 3001.0
        assert d.spread_bps > 0

    def test_bids_wrong_order_rejected(self):
        with pytest.raises(ValidationError):
            DepthEvent(pair="ETHUSDT",
                bids=[DepthLevel(price=2999, quantity=5), DepthLevel(price=3000, quantity=10)],
                asks=[DepthLevel(price=3001, quantity=8)], timestamp_ms=NOW_MS)


class TestKlineEvent:
    def test_valid_kline(self):
        k = KlineEvent(pair="SOLUSDT", timeframe=Timeframe.H1,
            open_price=100, high_price=105, low_price=98, close_price=103,
            volume=10000, timestamp_ms=NOW_MS)
        assert k.notional_volume_usdt == 10000 * 103
        assert 0 <= k.body_ratio <= 1

    def test_high_less_than_low_rejected(self):
        with pytest.raises(ValidationError):
            KlineEvent(pair="SOLUSDT", timeframe=Timeframe.H1,
                open_price=100, high_price=95, low_price=98, close_price=97,
                volume=10000, timestamp_ms=NOW_MS)

    def test_low_greater_than_open_rejected(self):
        with pytest.raises(ValidationError):
            KlineEvent(pair="SOLUSDT", timeframe=Timeframe.H1,
                open_price=100, high_price=105, low_price=101, close_price=103,
                volume=10000, timestamp_ms=NOW_MS)


class TestSnapshotEvent:
    def test_valid_snapshot(self):
        s = SnapshotEvent(pair="BTCUSDT", last_price=50000, bid=49999, ask=50001,
                          volume_24h=1000, timestamp_ms=NOW_MS)
        assert s.spread_bps > 0

    def test_ask_less_than_bid_rejected(self):
        with pytest.raises(ValidationError):
            SnapshotEvent(pair="BTCUSDT", last_price=50000, bid=50001, ask=49999,
                          volume_24h=1000, timestamp_ms=NOW_MS)


class TestSignalCandidate:
    def test_valid_signal(self):
        s = SignalCandidate(pair="BTCUSDT", engine_id=EngineId.A, signal_type=SignalType.ENTRY,
            side=Side.BUY, confidence=0.85, regime=RegimeId.TRENDING_UP,
            entry_price=50000, stop_loss=49000, take_profit=52000, timestamp_ms=NOW_MS)
        assert s.expected_risk_reward == 2.0

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            SignalCandidate(pair="BTCUSDT", engine_id=EngineId.A, signal_type=SignalType.ENTRY,
                side=Side.BUY, confidence=1.5, regime=RegimeId.TRENDING_UP,
                entry_price=50000, timestamp_ms=NOW_MS)


class TestRiskDecision:
    def test_approved(self):
        r = RiskDecision(pair="BTCUSDT", engine_id=EngineId.A, verdict=RiskVerdict.APPROVED,
            requested_size=1.0, approved_size=1.0,
            exposure_used_pct=30, loss_budget_used_pct=10, timestamp_ms=NOW_MS)
        assert r.approved_size == 1.0

    def test_hard_blocked_must_have_zero_size(self):
        with pytest.raises(ValidationError):
            RiskDecision(pair="BTCUSDT", engine_id=EngineId.A, verdict=RiskVerdict.HARD_BLOCKED,
                requested_size=1.0, approved_size=0.5,
                exposure_used_pct=100, loss_budget_used_pct=100, timestamp_ms=NOW_MS)

    def test_approved_cannot_exceed_requested(self):
        with pytest.raises(ValidationError):
            RiskDecision(pair="BTCUSDT", engine_id=EngineId.A, verdict=RiskVerdict.APPROVED,
                requested_size=1.0, approved_size=2.0,
                exposure_used_pct=30, loss_budget_used_pct=10, timestamp_ms=NOW_MS)


class TestExecutionIntent:
    def test_valid_intent(self):
        e = ExecutionIntent(pair="ETHUSDT", engine_id=EngineId.B, side=Side.BUY,
            size=10, target_price=3000, order_type="limit",
            status=ExecutionStatus.PENDING, timestamp_ms=NOW_MS)
        assert e.fill_ratio is None

    def test_invalid_order_type_rejected(self):
        with pytest.raises(ValidationError):
            ExecutionIntent(pair="ETHUSDT", engine_id=EngineId.B, side=Side.BUY,
                size=10, target_price=3000, order_type="stop_limit",
                status=ExecutionStatus.PENDING, timestamp_ms=NOW_MS)

    def test_slippage_calculation(self):
        e = ExecutionIntent(pair="ETHUSDT", engine_id=EngineId.B, side=Side.BUY,
            size=10, target_price=3000, order_type="market",
            status=ExecutionStatus.FILLED, filled_price=3003,
            filled_size=10, timestamp_ms=NOW_MS)
        assert e.slippage_bps == pytest.approx(10.0, abs=0.1)
        assert e.fill_ratio == 1.0


class TestCostRecord:
    def test_valid_cost(self):
        c = CostRecord(pair="BTCUSDT", engine_id=EngineId.A,
            fee_bps=5, spread_cost_bps=3, slippage_bps=2,
            total_cost_bps=10, notional_usdt=50000, timestamp_ms=NOW_MS)
        assert c.total_cost_bps == 10

    def test_total_cost_mismatch_rejected(self):
        with pytest.raises(ValidationError):
            CostRecord(pair="BTCUSDT", engine_id=EngineId.A,
                fee_bps=5, spread_cost_bps=3, slippage_bps=2,
                total_cost_bps=20, notional_usdt=50000, timestamp_ms=NOW_MS)


class TestEdgeEstimate:
    def test_valid_edge(self):
        e = EdgeEstimate(pair="BTCUSDT", engine_id=EngineId.A,
            gross_edge_bps=15, cost_drag_bps=10, net_edge_bps=5,
            sample_size=100, confidence_level=0.8, timestamp_ms=NOW_MS)
        assert e.net_edge_bps == 5

    def test_net_edge_mismatch_rejected(self):
        with pytest.raises(ValidationError):
            EdgeEstimate(pair="BTCUSDT", engine_id=EngineId.A,
                gross_edge_bps=15, cost_drag_bps=10, net_edge_bps=10,
                sample_size=100, confidence_level=0.8, timestamp_ms=NOW_MS)


class TestDTRRecord:
    def test_valid_dtr(self):
        d = DTRRecord(dtr_id="dtr_001", pair="BTCUSDT", engine_id=EngineId.A,
            regime=RegimeId.TRENDING_UP, signal_confidence=0.9,
            raw_score=0.85, final_score=0.7, hard_blocked=False,
            risk_verdict="approved", outcome=DTROutcome.PROFIT,
            entry_price=50000, exit_price=51000, pnl_usdt=100,
            cost_total_bps=10, timestamp_ms=NOW_MS)
        assert not d.is_phantom
        assert d.net_pnl_usdt is not None

    def test_phantom_dtr(self):
        d = DTRRecord(dtr_id="dtr_phantom", pair="ETHUSDT", engine_id=EngineId.B,
            regime=RegimeId.RANGE_BOUND, signal_confidence=0.5,
            raw_score=0.4, final_score=0.2, hard_blocked=True,
            risk_verdict="hard_blocked", outcome=DTROutcome.PHANTOM, timestamp_ms=NOW_MS)
        assert d.is_phantom


class TestAlertRecord:
    def test_valid_alert(self):
        a = AlertRecord(alert_id="alert_001", severity=AlertSeverity.CRITICAL,
            category=AlertCategory.DATA, message="WS disconnected",
            pair="BTCUSDT", timestamp_ms=NOW_MS)
        assert a.severity == AlertSeverity.CRITICAL


class TestErrors:
    def test_base_error_serialization(self):
        d = V53BaseError("test", "ERR_TEST", "test_mod", "BTCUSDT").to_dict()
        assert d["code"] == "ERR_TEST"

    def test_data_stale_error(self):
        e = DataStaleError(pair="BTCUSDT", stale_ms=5000, threshold_ms=3000)
        assert e.code == "ERR_DATA_STALE"

    def test_dependency_violation_error(self):
        e = DependencyViolationError(source_module="engine_a", target_module="execution")
        assert e.code == "ERR_DEPENDENCY_VIOLATION"

    def test_risk_budget_exceeded(self):
        e = RiskBudgetExceededError(pair="ETHUSDT", budget_type="exposure",
                                    current_pct=95.0, limit_pct=80.0)
        assert "95.0%" in e.message

    def test_bootstrap_error(self):
        assert BootstrapError(module="ws", phase="init", reason="fail").code == "ERR_BOOTSTRAP"

    def test_all_errors_are_v53_base(self):
        for cls in [DataStaleError, DependencyViolationError, PairSuspendedError,
                    RiskBudgetExceededError, InvalidProfileActivationError,
                    ContractViolationError, EngineNotAllowedError,
                    ReconciliationError, BootstrapError]:
            assert issubclass(cls, V53BaseError)


class TestRetrocompatibility:
    def test_trade_event_roundtrip(self):
        t = TradeEvent(pair="BTCUSDT", price=50000, quantity=0.1,
                       side=Side.BUY, trade_id="12345", timestamp_ms=NOW_MS)
        assert TradeEvent(**t.model_dump()) == t

    def test_signal_candidate_roundtrip(self):
        s = SignalCandidate(pair="BTCUSDT", engine_id=EngineId.A, signal_type=SignalType.ENTRY,
            side=Side.BUY, confidence=0.85, regime=RegimeId.TRENDING_UP,
            entry_price=50000, timestamp_ms=NOW_MS)
        assert SignalCandidate(**s.model_dump()) == s

    def test_json_serialization(self):
        t = TradeEvent(pair="BTCUSDT", price=50000, quantity=0.1,
                       side=Side.BUY, trade_id="12345", timestamp_ms=NOW_MS)
        assert TradeEvent.model_validate_json(t.model_dump_json()) == t
