"""Tests for scoring_backbone.raw_score_builder — Build-5."""
import pytest

from scoring_backbone.raw_score_builder.feature_selector import (
    FeatureSelection,
    select_features,
)
from scoring_backbone.raw_score_builder.weight_registry import (
    WeightSet,
    WeightRegistry,
)
from scoring_backbone.raw_score_builder.raw_score_calculator import (
    RawScoreResult,
    calculate_raw_score,
)
from scoring_backbone.raw_score_builder.score_component_breakdown import (
    ScoreBreakdown,
    decompose_score,
    BLOCK_STRUCTURE,
    BLOCK_CONTEXT,
    BLOCK_FLOW,
)
from scoring_backbone.raw_score_builder.score_reporter import (
    ScorePayload,
    ScoreReporter,
)


# ── feature_selector ──


class TestFeatureSelector:
    def test_select_allowed(self):
        result = select_features(
            engine_id="eng1",
            raw_features={"momentum": 0.5, "volume": 1.2, "rsi": 0.3},
            allowed_features=frozenset({"momentum", "volume"}),
        )
        assert set(result.selected.keys()) == {"momentum", "volume"}
        assert "rsi" in result.rejected

    def test_missing_features_tracked(self):
        result = select_features(
            engine_id="eng1",
            raw_features={"momentum": 0.5},
            allowed_features=frozenset({"momentum", "volume"}),
        )
        assert "volume" in result.missing
        assert result.selected["momentum"] == 0.5

    def test_no_unauthorised_feature_passes(self):
        result = select_features(
            engine_id="eng1",
            raw_features={"forbidden": 9.9, "momentum": 0.5},
            allowed_features=frozenset({"momentum"}),
        )
        assert "forbidden" not in result.selected
        assert "forbidden" in result.rejected

    def test_empty_features(self):
        result = select_features(
            engine_id="eng1",
            raw_features={},
            allowed_features=frozenset({"momentum"}),
        )
        assert result.selected == {}
        assert "momentum" in result.missing

    def test_result_frozen(self):
        result = select_features("eng1", {"a": 1.0}, frozenset({"a"}))
        with pytest.raises(Exception):
            result.engine_id = "x"


# ── weight_registry ──


class TestWeightRegistry:
    def test_register_and_get(self):
        reg = WeightRegistry()
        ws = WeightSet(engine_id="eng1", version="1.0", weights={"momentum": 0.8})
        reg.register(ws)
        assert reg.get_weights("eng1") == ws

    def test_version_tracking(self):
        reg = WeightRegistry()
        reg.register(WeightSet(engine_id="eng1", version="1.0", weights={}))
        assert reg.get_version("eng1") == "1.0"

    def test_unknown_engine(self):
        reg = WeightRegistry()
        assert reg.get_weights("unknown") is None
        assert reg.get_version("unknown") == ""

    def test_history(self):
        reg = WeightRegistry()
        ws1 = WeightSet(engine_id="eng1", version="1.0", weights={})
        ws2 = WeightSet(engine_id="eng1", version="2.0", weights={"a": 1.0})
        reg.register(ws1)
        reg.register(ws2)
        assert len(reg.get_history()) == 2

    def test_engine_count(self):
        reg = WeightRegistry()
        reg.register(WeightSet(engine_id="eng1", version="1.0", weights={}))
        reg.register(WeightSet(engine_id="eng2", version="1.0", weights={}))
        assert reg.engine_count == 2


# ── raw_score_calculator ──


class TestRawScoreCalculator:
    def test_basic_score(self):
        """S_i^raw = Σ α_m · F_{i,m}."""
        result = calculate_raw_score(
            engine_id="eng1",
            pair="BTCUSDT",
            features={"momentum": 0.5, "volume": 1.0},
            weights={"momentum": 2.0, "volume": 0.5},
            scoring_version="v1",
        )
        assert result.raw_score == pytest.approx(1.5)

    def test_decomposed_contributions(self):
        result = calculate_raw_score(
            engine_id="eng1",
            pair="BTCUSDT",
            features={"momentum": 0.5, "volume": 1.0},
            weights={"momentum": 2.0, "volume": 0.5},
            scoring_version="v1",
        )
        assert result.weighted_contributions["momentum"] == pytest.approx(1.0)
        assert result.weighted_contributions["volume"] == pytest.approx(0.5)

    def test_missing_weight_ignored(self):
        result = calculate_raw_score(
            engine_id="eng1",
            pair="BTCUSDT",
            features={"momentum": 0.5, "extra": 9.0},
            weights={"momentum": 2.0},
            scoring_version="v1",
        )
        assert result.raw_score == pytest.approx(1.0)
        assert "extra" not in result.weighted_contributions

    def test_reproducibility(self):
        """Same input → same score."""
        kwargs = dict(
            engine_id="eng1", pair="BTCUSDT",
            features={"a": 1.0, "b": 2.0}, weights={"a": 0.5, "b": 0.3}, scoring_version="v1",
        )
        r1 = calculate_raw_score(**kwargs)
        r2 = calculate_raw_score(**kwargs)
        assert r1.raw_score == r2.raw_score

    def test_version_stored(self):
        result = calculate_raw_score(
            engine_id="eng1", pair="BTCUSDT",
            features={"a": 1.0}, weights={"a": 1.0}, scoring_version="v2.1",
        )
        assert result.scoring_version == "v2.1"

    def test_features_used_sorted(self):
        result = calculate_raw_score(
            engine_id="eng1", pair="BTCUSDT",
            features={"z_feat": 1.0, "a_feat": 2.0},
            weights={"z_feat": 1.0, "a_feat": 1.0},
            scoring_version="v1",
        )
        assert result.features_used == ("a_feat", "z_feat")

    def test_result_frozen(self):
        result = calculate_raw_score("eng1", "BTC", {"a": 1.0}, {"a": 1.0}, scoring_version="v1")
        with pytest.raises(Exception):
            result.raw_score = 999.0

    def test_rejects_blank_scoring_version(self):
        with pytest.raises(ValueError, match="requires non-empty scoring_version"):
            calculate_raw_score(
                engine_id="eng1",
                pair="BTCUSDT",
                features={"a": 1.0},
                weights={"a": 1.0},
                scoring_version="   ",
            )


# ── score_component_breakdown ──


class TestScoreComponentBreakdown:
    def test_basic_decomposition(self):
        contributions = {"momentum": 1.0, "spread": 0.5, "flow_imbalance": 0.3}
        mapping = {
            "momentum": BLOCK_STRUCTURE,
            "spread": BLOCK_CONTEXT,
            "flow_imbalance": BLOCK_FLOW,
        }
        result = decompose_score("eng1", "BTCUSDT", contributions, mapping)
        assert result.block_scores[BLOCK_STRUCTURE] == pytest.approx(1.0)
        assert result.block_scores[BLOCK_CONTEXT] == pytest.approx(0.5)
        assert result.block_scores[BLOCK_FLOW] == pytest.approx(0.3)

    def test_unassigned_features(self):
        contributions = {"momentum": 1.0, "unknown_feat": 0.7}
        mapping = {"momentum": BLOCK_STRUCTURE}
        result = decompose_score("eng1", "BTCUSDT", contributions, mapping)
        assert result.unassigned_contribution == pytest.approx(0.7)

    def test_raw_score_equals_sum(self):
        contributions = {"a": 1.0, "b": 2.0, "c": 0.5}
        mapping = {"a": BLOCK_STRUCTURE, "b": BLOCK_CONTEXT}
        result = decompose_score("eng1", "BTCUSDT", contributions, mapping)
        block_total = sum(result.block_scores.values())
        assert result.raw_score == pytest.approx(block_total + result.unassigned_contribution)

    def test_block_features_tracked(self):
        contributions = {"mom": 1.0, "vol": 0.5}
        mapping = {"mom": BLOCK_STRUCTURE, "vol": BLOCK_STRUCTURE}
        result = decompose_score("eng1", "BTCUSDT", contributions, mapping)
        assert set(result.block_features[BLOCK_STRUCTURE]) == {"mom", "vol"}

    def test_empty_contributions(self):
        result = decompose_score("eng1", "BTCUSDT", {}, {})
        assert result.raw_score == 0.0
        assert result.block_scores == {}


# ── score_reporter ──


class TestScoreReporter:
    def test_normal_score(self):
        reporter = ScoreReporter()
        payload = reporter.evaluate("eng1", "BTCUSDT", 2.5, {}, (), "v1")
        assert payload.is_anomaly is False
        assert payload.raw_score == 2.5

    def test_anomaly_detection_high(self):
        reporter = ScoreReporter(anomaly_high=5.0)
        payload = reporter.evaluate("eng1", "BTCUSDT", 15.0, {}, (), "v1")
        assert payload.is_anomaly is True
        assert "out of range" in payload.anomaly_reason

    def test_anomaly_detection_low(self):
        reporter = ScoreReporter(anomaly_low=-2.0)
        payload = reporter.evaluate("eng1", "BTCUSDT", -5.0, {}, (), "v1")
        assert payload.is_anomaly is True

    def test_stats_tracking(self):
        reporter = ScoreReporter()
        reporter.evaluate("eng1", "BTC", 1.0, {}, (), "v1")
        reporter.evaluate("eng1", "ETH", 3.0, {}, (), "v1")
        stats = reporter.get_stats()
        assert stats.total_scored == 2
        assert stats.mean_score == pytest.approx(2.0)
        assert stats.min_score == pytest.approx(1.0)
        assert stats.max_score == pytest.approx(3.0)

    def test_stats_empty(self):
        reporter = ScoreReporter()
        stats = reporter.get_stats()
        assert stats.total_scored == 0

    def test_payload_frozen(self):
        reporter = ScoreReporter()
        payload = reporter.evaluate("eng1", "BTC", 1.0, {}, (), "v1")
        with pytest.raises(Exception):
            payload.raw_score = 999.0

    def test_rejects_blank_scoring_version(self):
        reporter = ScoreReporter()
        with pytest.raises(ValueError, match="requires non-empty scoring_version"):
            reporter.evaluate("eng1", "BTC", 1.0, {}, (), "   ")
