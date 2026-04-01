"""Tests for scoring_backbone.penalty_aggregator — Build-5."""
import pytest
import math

from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyType,
    PenaltyDefinition,
    PenaltyRegistry,
    validate_penalty_ids,
)
from scoring_backbone.penalty_aggregator.score_penalty_builder import (
    ScorePenaltyItem,
    ScorePenaltyResult,
    build_score_penalty,
)
from scoring_backbone.penalty_aggregator.size_penalty_builder import (
    SizePenaltyItem,
    SizePenaltyResult,
    build_size_penalty,
)
from scoring_backbone.penalty_aggregator.penalty_cap_guard import (
    PenaltyCapVerdict,
    PenaltyCapResult,
    evaluate_penalty_cap,
)
from scoring_backbone.penalty_aggregator.penalty_reporter import (
    PenaltyEvent,
    PenaltyReporter,
)


def build_registry() -> PenaltyRegistry:
    reg = PenaltyRegistry()
    reg.register(PenaltyDefinition(penalty_id="stale", name="Staleness", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="spread", name="Spread", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="regime", name="Regime", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="size_stale", name="Staleness sizing", penalty_type=PenaltyType.SIZE))
    reg.register(PenaltyDefinition(penalty_id="size_spread", name="Spread sizing", penalty_type=PenaltyType.SIZE))
    return reg


# ── penalty_registry ──


class TestPenaltyRegistry:
    def test_register_and_get(self):
        reg = PenaltyRegistry()
        p = PenaltyDefinition(penalty_id="stale", name="Staleness", penalty_type=PenaltyType.SCORE)
        reg.register(p)
        assert reg.get("stale") == p

    def test_is_authorised(self):
        reg = PenaltyRegistry()
        reg.register(PenaltyDefinition(penalty_id="stale", name="Staleness", penalty_type=PenaltyType.SCORE))
        assert reg.is_authorised("stale") is True
        assert reg.is_authorised("unknown") is False

    def test_version(self):
        reg = PenaltyRegistry(version="2.0")
        assert reg.version == "2.0"

    def test_get_all(self):
        reg = PenaltyRegistry()
        reg.register(PenaltyDefinition(penalty_id="a", name="A", penalty_type=PenaltyType.SCORE))
        reg.register(PenaltyDefinition(penalty_id="b", name="B", penalty_type=PenaltyType.SIZE))
        assert reg.count == 2
        assert len(reg.get_all()) == 2

    def test_unknown_returns_none(self):
        reg = PenaltyRegistry()
        assert reg.get("nope") is None

    def test_validate_penalty_ids_rejects_duplicates_and_unauthorised(self):
        reg = build_registry()
        with pytest.raises(ValueError, match="unauthorised penalties: rogue; duplicate penalties: stale"):
            validate_penalty_ids(("stale", "stale", "rogue"), reg)


# ── score_penalty_builder ──


class TestScorePenaltyBuilder:
    def test_single_penalty(self):
        reg = build_registry()
        penalties = (ScorePenaltyItem(penalty_id="stale", value=0.5),)
        result = build_score_penalty(raw_score=3.0, penalties=penalties, registry=reg)
        assert result.total_penalty == pytest.approx(0.5)
        assert result.adjusted_score == pytest.approx(2.5)

    def test_multiple_additive(self):
        """Pen_i = Σ pen_{i,ℓ}."""
        reg = build_registry()
        penalties = (
            ScorePenaltyItem(penalty_id="stale", value=0.3),
            ScorePenaltyItem(penalty_id="spread", value=0.2),
            ScorePenaltyItem(penalty_id="regime", value=0.1),
        )
        result = build_score_penalty(raw_score=3.0, penalties=penalties, registry=reg)
        assert result.total_penalty == pytest.approx(0.6)
        assert result.adjusted_score == pytest.approx(2.4)

    def test_penalties_detail_exported(self):
        reg = build_registry()
        penalties = (
            ScorePenaltyItem(penalty_id="stale", value=0.3, reason="data stale"),
            ScorePenaltyItem(penalty_id="spread", value=0.2, reason="wide spread"),
        )
        result = build_score_penalty(raw_score=3.0, penalties=penalties, registry=reg)
        assert len(result.penalties) == 2
        assert result.penalties[0].reason == "data stale"

    def test_no_penalties(self):
        result = build_score_penalty(raw_score=3.0, penalties=(), registry=build_registry())
        assert result.adjusted_score == pytest.approx(3.0)
        assert result.total_penalty == 0.0

    def test_result_frozen(self):
        result = build_score_penalty(3.0, (), registry=build_registry())
        with pytest.raises(Exception):
            result.adjusted_score = 999.0

    def test_rejects_unauthorised_penalty(self):
        with pytest.raises(ValueError, match="unauthorised penalties: rogue"):
            build_score_penalty(
                raw_score=3.0,
                penalties=(ScorePenaltyItem(penalty_id="rogue", value=0.5),),
                registry=build_registry(),
            )

    def test_rejects_duplicate_penalty_ids(self):
        with pytest.raises(ValueError, match="duplicate penalties: stale"):
            build_score_penalty(
                raw_score=3.0,
                penalties=(
                    ScorePenaltyItem(penalty_id="stale", value=0.3),
                    ScorePenaltyItem(penalty_id="stale", value=0.2),
                ),
                registry=build_registry(),
            )


# ── size_penalty_builder ──


class TestSizePenaltyBuilder:
    def test_single_multiplier(self):
        penalties = (SizePenaltyItem(penalty_id="size_stale", multiplier=0.8),)
        result = build_size_penalty(penalties, registry=build_registry())
        assert result.total_multiplier == pytest.approx(0.8)

    def test_multiple_multipliers(self):
        """m_i = Π m_{i,ℓ}."""
        penalties = (
            SizePenaltyItem(penalty_id="size_stale", multiplier=0.8),
            SizePenaltyItem(penalty_id="size_spread", multiplier=0.9),
        )
        result = build_size_penalty(penalties, registry=build_registry())
        assert result.total_multiplier == pytest.approx(0.72)

    def test_log_multiplier(self):
        reg = build_registry()
        reg.register(PenaltyDefinition(penalty_id="size_a", name="A sizing", penalty_type=PenaltyType.SIZE))
        penalties = (SizePenaltyItem(penalty_id="size_a", multiplier=0.5),)
        result = build_size_penalty(penalties, registry=reg)
        assert result.log_multiplier == pytest.approx(math.log(0.5))

    def test_clamp_to_floor(self):
        """Multiplier clamped to 0.001 minimum."""
        reg = build_registry()
        reg.register(PenaltyDefinition(penalty_id="size_bad", name="Bad sizing", penalty_type=PenaltyType.SIZE))
        penalties = (SizePenaltyItem(penalty_id="size_bad", multiplier=-0.5),)
        result = build_size_penalty(penalties, registry=reg)
        assert result.total_multiplier == pytest.approx(0.001)

    def test_no_penalties(self):
        result = build_size_penalty((), registry=build_registry())
        assert result.total_multiplier == pytest.approx(1.0)

    def test_rejects_unauthorised_penalty(self):
        with pytest.raises(ValueError, match="unauthorised penalties: rogue"):
            build_size_penalty(
                (SizePenaltyItem(penalty_id="rogue", multiplier=0.8),),
                registry=build_registry(),
            )

    def test_rejects_duplicate_penalty_ids(self):
        with pytest.raises(ValueError, match="duplicate penalties: size_stale"):
            build_size_penalty(
                (
                    SizePenaltyItem(penalty_id="size_stale", multiplier=0.9),
                    SizePenaltyItem(penalty_id="size_stale", multiplier=0.8),
                ),
                registry=build_registry(),
            )


# ── penalty_cap_guard ──


class TestPenaltyCapGuard:
    def test_normal(self):
        result = evaluate_penalty_cap(
            score_penalty=0.5, size_multiplier=0.9,
            max_score_penalty=2.0, min_size_multiplier=0.1,
            raw_score=3.0,
        )
        assert result.verdict == PenaltyCapVerdict.NORMAL

    def test_capped(self):
        result = evaluate_penalty_cap(
            score_penalty=5.0, size_multiplier=0.05,
            max_score_penalty=2.0, min_size_multiplier=0.1,
            raw_score=3.0,
        )
        assert result.verdict == PenaltyCapVerdict.CAPPED
        assert result.capped_score_penalty == pytest.approx(2.0)
        assert result.capped_size_multiplier == pytest.approx(0.1)

    def test_phantom_risk(self):
        """Trade non-fatal but economically non-monetizable."""
        result = evaluate_penalty_cap(
            score_penalty=2.8, size_multiplier=0.1,
            max_score_penalty=3.0, min_size_multiplier=0.05,
            raw_score=3.0, expected_cost=0.5,
        )
        # adjusted = 3.0 - 2.8 = 0.2, effective = 0.2 * 0.1 = 0.02 <= 0.5
        assert result.verdict == PenaltyCapVerdict.PHANTOM_RISK

    def test_cap_prevents_veto(self):
        result = evaluate_penalty_cap(
            score_penalty=10.0, size_multiplier=0.001,
            max_score_penalty=1.0, min_size_multiplier=0.5,
            raw_score=3.0,
        )
        assert result.capped_score_penalty == pytest.approx(1.0)
        assert result.capped_size_multiplier == pytest.approx(0.5)

    def test_result_frozen(self):
        result = evaluate_penalty_cap(0.5, 0.9, 2.0, 0.1, 3.0)
        with pytest.raises(Exception):
            result.verdict = "x"


# ── penalty_reporter ──


class TestPenaltyReporter:
    def test_initial_empty(self):
        reporter = PenaltyReporter()
        stats = reporter.get_stats()
        assert stats.total_evaluated == 0

    def test_record_event(self):
        reporter = PenaltyReporter()
        reporter.record(PenaltyEvent(
            engine_id="eng1", pair="BTCUSDT",
            score_penalty=0.5, size_multiplier=0.9,
        ))
        stats = reporter.get_stats()
        assert stats.total_evaluated == 1
        assert stats.mean_score_penalty == pytest.approx(0.5)

    def test_phantom_count(self):
        reporter = PenaltyReporter()
        reporter.record(PenaltyEvent(
            engine_id="eng1", pair="BTC",
            score_penalty=2.0, size_multiplier=0.1, is_phantom=True,
        ))
        reporter.record(PenaltyEvent(
            engine_id="eng1", pair="ETH",
            score_penalty=0.5, size_multiplier=0.9,
        ))
        stats = reporter.get_stats()
        assert stats.phantom_count == 1

    def test_capped_count(self):
        reporter = PenaltyReporter()
        reporter.record(PenaltyEvent(
            engine_id="eng1", pair="BTC",
            score_penalty=2.0, size_multiplier=0.5, is_capped=True,
        ))
        stats = reporter.get_stats()
        assert stats.capped_count == 1

    def test_get_events_by_pair(self):
        reporter = PenaltyReporter()
        reporter.record(PenaltyEvent(engine_id="eng1", pair="BTC", score_penalty=0.5, size_multiplier=0.9))
        reporter.record(PenaltyEvent(engine_id="eng1", pair="ETH", score_penalty=0.3, size_multiplier=0.8))
        assert len(reporter.get_events(pair="BTC")) == 1
        assert len(reporter.get_events()) == 2
