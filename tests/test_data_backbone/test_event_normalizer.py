"""Tests for data_backbone.event_normalizer — Build-2."""
import pytest

from data_backbone.event_normalizer.schema_mapper import (
    EventType,
    MappingError,
    TradeEvent,
    DepthEvent,
    KlineEvent,
    HeartbeatEvent,
    map_raw_to_event,
)
from data_backbone.event_normalizer.timestamp_enricher import (
    compute_latency,
    compute_drift,
    enrich_timestamp,
    monotonic_now,
)
from data_backbone.event_normalizer.message_classifier import (
    MessageClass,
    classify_message,
)
from data_backbone.event_normalizer.invalid_message_guard import (
    RejectionReason,
    validate_raw_message,
)
from data_backbone.event_normalizer.normalization_reporter import (
    NormalizationReporter,
)


pytestmark = pytest.mark.build2


# --- Schema Mapper ---

class TestSchemaMapper:
    def test_map_trade(self):
        result = map_raw_to_event(
            {"price": "50000", "quantity": "1.5", "side": "buy"},
            "trade", "BTCUSDT", "binance", 100.0,
        )
        assert isinstance(result, TradeEvent)
        assert result.event_type == EventType.TRADE
        assert result.price == 50000.0
        assert result.pair == "BTCUSDT"

    def test_map_depth(self):
        result = map_raw_to_event(
            {"bids": [[50000, 1]], "asks": [[50001, 2]]},
            "depth", "BTCUSDT", "binance", 100.0,
        )
        assert isinstance(result, DepthEvent)
        assert len(result.bids) == 1

    def test_map_kline(self):
        result = map_raw_to_event(
            {"open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
            "kline", "BTCUSDT", "binance", 100.0,
        )
        assert isinstance(result, KlineEvent)
        assert result.close == 105.0

    def test_map_heartbeat(self):
        result = map_raw_to_event({}, "heartbeat", "BTCUSDT", "binance", 100.0)
        assert isinstance(result, HeartbeatEvent)

    def test_unknown_type_returns_error(self):
        result = map_raw_to_event({}, "unknown_type", "BTCUSDT", "binance", 100.0)
        assert isinstance(result, MappingError)

    def test_recv_time_always_set(self):
        result = map_raw_to_event({"price": "1", "qty": "1"}, "trade", "BTC", "ex", 42.0)
        assert result.recv_time == 42.0


# --- Timestamp Enricher ---

class TestTimestampEnricher:
    def test_drift_computed(self):
        drift = compute_drift(100.5, 100.0)
        assert drift == pytest.approx(0.5)

    def test_drift_none_without_exchange_time(self):
        assert compute_drift(100.0, None) is None

    def test_enrich(self):
        event = TradeEvent(
            pair="BTC", source="ex", recv_time=100.5, exchange_time=100.0,
            data={}, price=1.0, quantity=1.0,
        )
        enrichment = enrich_timestamp(event, now=101.0)
        assert enrichment.drift_s == pytest.approx(0.5)
        assert enrichment.latency_s == pytest.approx(0.5)

    def test_monotonic_helper_is_monotonic(self):
        t1 = monotonic_now()
        t2 = monotonic_now()
        assert t2 >= t1

    def test_negative_latency_filtered(self):
        assert compute_latency(105.0, 100.0) is None

    def test_aberrant_latency_filtered(self):
        assert compute_latency(1.0, 1000.0, max_latency_s=10.0) is None


# --- Message Classifier ---

class TestMessageClassifier:
    def test_classify_by_hint(self):
        result = classify_message({}, stream_type_hint="trade")
        assert result.message_class == MessageClass.TRADE
        assert result.confidence == 1.0

    def test_classify_trade_by_payload(self):
        result = classify_message({"price": 100, "qty": 1})
        assert result.message_class == MessageClass.TRADE

    def test_classify_depth_by_payload(self):
        result = classify_message({"bids": [], "asks": []})
        assert result.message_class == MessageClass.DEPTH

    def test_classify_kline_by_payload(self):
        result = classify_message({"open": 1, "close": 2, "high": 3})
        assert result.message_class == MessageClass.KLINE

    def test_classify_unknown(self):
        result = classify_message({"foo": "bar"})
        assert result.message_class == MessageClass.UNKNOWN


# --- Invalid Message Guard ---

class TestInvalidMessageGuard:
    def test_valid_message(self):
        result = validate_raw_message(
            {"price": 100}, "BTCUSDT", "binance", 100.0, "trade",
        )
        assert result.valid is True
        assert len(result.rejections) == 0

    def test_missing_pair(self):
        result = validate_raw_message({"data": 1}, None, "binance", 100.0, "trade")
        assert result.valid is False
        assert any(r.reason == RejectionReason.MISSING_PAIR for r in result.rejections)

    def test_missing_recv_time(self):
        result = validate_raw_message({"data": 1}, "BTC", "ex", None, "trade")
        assert result.valid is False

    def test_empty_payload(self):
        result = validate_raw_message({}, "BTC", "ex", 100.0, "trade")
        assert result.valid is False

    def test_invalid_stream_type(self):
        result = validate_raw_message({"x": 1}, "BTC", "ex", 100.0, "invalid_stream")
        assert result.valid is False
        assert any(r.reason == RejectionReason.INVALID_TYPE for r in result.rejections)

    def test_multiple_rejections(self):
        result = validate_raw_message({}, None, None, None, "bad")
        assert result.valid is False
        assert len(result.rejections) >= 3


# --- Normalization Reporter ---

class TestNormalizationReporter:
    def test_stats(self):
        reporter = NormalizationReporter()
        reporter.record_normalized("trade")
        reporter.record_normalized("trade")
        reporter.record_normalized("depth")
        reporter.record_rejected("missing_field")
        stats = reporter.get_stats()
        assert stats.total_raw == 4
        assert stats.total_normalized == 3
        assert stats.total_rejected == 1
        assert stats.reject_rate == 0.25

    def test_reject_rate(self):
        reporter = NormalizationReporter()
        assert reporter.reject_rate == 0.0
        reporter.record_rejected("test")
        assert reporter.reject_rate == 1.0
