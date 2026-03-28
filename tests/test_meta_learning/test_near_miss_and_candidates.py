"""Near-miss analyzer boundaries and candidate kind selection tests."""

from __future__ import annotations

from interface_contracts import StrategyClassification
from meta_learning import (
    CandidateKind,
    DiagnosticResult,
    LearningHypothesis,
    analyze_near_misses,
    build_improvement_candidates,
    build_learning_hypotheses,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


class TestNearMissBoundaries:
    def _record(self, final_score=0.82, state=DecisionState.HARD_BLOCKED, pair="BTCUSDT"):
        return build_dtr(
            dtr_id="dtr-1", pair=pair, engine_id="engine_a",
            decision_state=state, raw_score=0.90,
            final_score=final_score, timestamp=1000.0,
        )

    def test_score_at_threshold_included(self):
        result = analyze_near_misses("corr-1", (self._record(final_score=0.70),))
        assert len(result) == 1

    def test_score_below_threshold_excluded(self):
        result = analyze_near_misses("corr-1", (self._record(final_score=0.69),))
        assert len(result) == 0

    def test_selected_state_excluded(self):
        result = analyze_near_misses("corr-1", (self._record(state=DecisionState.SELECTED),))
        assert len(result) == 0

    def test_evaluated_state_included(self):
        result = analyze_near_misses("corr-1", (self._record(state=DecisionState.EVALUATED),))
        assert len(result) == 1

    def test_rejected_ranking_included(self):
        result = analyze_near_misses("corr-1", (self._record(state=DecisionState.REJECTED_RANKING),))
        assert len(result) == 1

    def test_empty_records_returns_empty(self):
        result = analyze_near_misses("corr-1", ())
        assert result == ()

    def test_custom_threshold(self):
        result = analyze_near_misses("corr-1", (self._record(final_score=0.50),), final_score_threshold=0.50)
        assert len(result) == 1

    def test_diagnostic_id_format(self):
        result = analyze_near_misses("corr-x", (self._record(),))
        assert result[0].diagnostic_id == "corr-x:near_miss:1"

    def test_pair_in_summary(self):
        result = analyze_near_misses("corr-x", (self._record(pair="ETHUSDT"),))
        assert "ETHUSDT" in result[0].summary


class TestCandidateKindSelection:
    def _hyp(self, category="generic"):
        return LearningHypothesis(
            hypothesis_id="hyp-1", correlation_id="corr-1",
            category=category, title="Test hypothesis",
            rationale="For testing",
        )

    def test_trace_coverage_maps_to_observability(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.A_VARIANT, (self._hyp("trace_coverage"),),
        )
        assert candidates[0].kind == CandidateKind.OBSERVABILITY_ONLY

    def test_build14_enabler_maps_to_read_only(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.BUILD14_ENABLER, (self._hyp("sterilization"),),
        )
        assert candidates[0].kind == CandidateKind.BUILD14_READ_ONLY

    def test_trace_coverage_wins_over_build14(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.BUILD14_ENABLER, (self._hyp("trace_coverage"),),
        )
        assert candidates[0].kind == CandidateKind.OBSERVABILITY_ONLY

    def test_cost_drift_maps_to_guard_tightening(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.A_VARIANT, (self._hyp("cost_drift"),),
        )
        assert candidates[0].kind == CandidateKind.GUARD_TIGHTENING

    def test_sterilization_maps_to_guard_tightening(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.A_VARIANT, (self._hyp("sterilization"),),
        )
        assert candidates[0].kind == CandidateKind.GUARD_TIGHTENING

    def test_unknown_category_maps_to_parameter_tuning(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.A_VARIANT, (self._hyp("edge_degraded"),),
        )
        assert candidates[0].kind == CandidateKind.PARAMETER_TUNING

    def test_empty_hypotheses_returns_empty(self):
        candidates = build_improvement_candidates(
            "corr-1", StrategyClassification.A_VARIANT, (),
        )
        assert candidates == ()

    def test_candidate_id_format(self):
        candidates = build_improvement_candidates(
            "corr-x", StrategyClassification.A_VARIANT, (self._hyp(),),
        )
        assert candidates[0].candidate_id == "corr-x:candidate:1"
