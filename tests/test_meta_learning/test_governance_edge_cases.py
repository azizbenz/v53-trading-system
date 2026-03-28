"""Governance validator edge cases for Build-9X contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    EngineId,
    ProfileId,
    PromotionState,
    RuntimeMode,
    StrategyClassification,
)
from meta_learning import (
    CandidateKind,
    ImprovementCandidate,
    LearningChecklist,
    LearningHypothesis,
    LearningMemoryRecord,
    LearningMemoryStore,
    TradeLearningInput,
)


def _valid_input(**overrides) -> dict:
    defaults = dict(
        correlation_id="corr-gov",
        dtr_ids=("dtr-1",),
        pair="BTCUSDT",
        engine_id=EngineId.A,
        profile=ProfileId.LIGHT,
        source_runtime_mode=RuntimeMode.SHADOW,
        strategy_classification=StrategyClassification.A_VARIANT,
        source_version="v5.3.0",
    )
    defaults.update(overrides)
    return defaults


class TestTradeLearningInputGovernance:
    def test_live_mutation_forbidden(self):
        with pytest.raises(ValidationError, match="live path"):
            TradeLearningInput(**_valid_input(live_mutation_requested=True))

    def test_implicit_promotion_forbidden(self):
        with pytest.raises(ValidationError, match="implicit promotion"):
            TradeLearningInput(**_valid_input(implicit_promotion_requested=True))

    def test_valid_input_passes(self):
        inp = TradeLearningInput(**_valid_input())
        assert inp.backtest_profile is None
        assert inp.live_mutation_requested is False
        assert inp.implicit_promotion_requested is False

    def test_empty_correlation_id_rejected(self):
        with pytest.raises(ValidationError):
            TradeLearningInput(**_valid_input(correlation_id=""))

    def test_empty_pair_rejected(self):
        with pytest.raises(ValidationError):
            TradeLearningInput(**_valid_input(pair=""))

    def test_empty_source_version_rejected(self):
        with pytest.raises(ValidationError):
            TradeLearningInput(**_valid_input(source_version=""))


class TestHypothesisGovernance:
    def _hyp(self, **overrides):
        defaults = dict(
            hypothesis_id="hyp-1",
            correlation_id="corr-gov",
            title="Investigate issue",
            rationale="Something observed",
        )
        defaults.update(overrides)
        return defaults

    def test_micro_live_target_forbidden(self):
        with pytest.raises(ValidationError, match="LOCAL_REPLAY"):
            LearningHypothesis(**self._hyp(target_runtime_mode=RuntimeMode.MICRO_LIVE))

    def test_live_target_forbidden(self):
        with pytest.raises(ValidationError, match="LOCAL_REPLAY"):
            LearningHypothesis(**self._hyp(target_runtime_mode=RuntimeMode.LIVE))

    def test_local_replay_target_passes(self):
        h = LearningHypothesis(**self._hyp(target_runtime_mode=RuntimeMode.LOCAL_REPLAY))
        assert h.target_runtime_mode == RuntimeMode.LOCAL_REPLAY

    def test_default_target_is_local_replay(self):
        h = LearningHypothesis(**self._hyp())
        assert h.target_runtime_mode == RuntimeMode.LOCAL_REPLAY


class TestCandidateGovernance:
    def _cand(self, **overrides):
        defaults = dict(
            candidate_id="cand-1",
            correlation_id="corr-gov",
            classification=StrategyClassification.A_VARIANT,
            kind=CandidateKind.PARAMETER_TUNING,
            summary="Validate guard tightening",
        )
        defaults.update(overrides)
        return defaults

    def test_auto_promotion_forbidden(self):
        with pytest.raises(ValidationError, match="auto-promote"):
            ImprovementCandidate(**self._cand(auto_promotion_enabled=True))

    def test_micro_live_candidate_forbidden(self):
        with pytest.raises(ValidationError, match="replay/shadow"):
            ImprovementCandidate(**self._cand(promotion_state=PromotionState.MICRO_LIVE_CANDIDATE))

    def test_shadow_candidate_allowed(self):
        c = ImprovementCandidate(**self._cand(promotion_state=PromotionState.SHADOW_CANDIDATE))
        assert c.promotion_state == PromotionState.SHADOW_CANDIDATE

    def test_replay_only_default(self):
        c = ImprovementCandidate(**self._cand())
        assert c.promotion_state == PromotionState.REPLAY_ONLY
        assert c.auto_promotion_enabled is False


class TestChecklistGovernance:
    def test_both_ready_flags_true_allowed(self):
        cl = LearningChecklist(
            checklist_id="chk-1",
            correlation_id="corr-gov",
            items=("item1",),
            ready_for_local_replay=True,
            ready_for_shadow=True,
        )
        assert cl.ready_for_shadow is True

    def test_both_ready_flags_false_allowed(self):
        cl = LearningChecklist(
            checklist_id="chk-1",
            correlation_id="corr-gov",
            items=("item1",),
            ready_for_local_replay=False,
            ready_for_shadow=False,
        )
        assert cl.ready_for_shadow is False

    def test_replay_only_without_shadow_allowed(self):
        cl = LearningChecklist(
            checklist_id="chk-1",
            correlation_id="corr-gov",
            items=("item1",),
            ready_for_local_replay=True,
            ready_for_shadow=False,
        )
        assert cl.ready_for_local_replay is True


class TestMemoryStore:
    def test_empty_store_latest_is_none(self):
        store = LearningMemoryStore()
        assert store.latest() is None

    def test_append_returns_new_store(self):
        store = LearningMemoryStore()
        record = LearningMemoryRecord(
            correlation_id="corr-1", diagnostics_count=1,
            hypothesis_count=0, candidate_count=0, summary="test",
        )
        new_store = store.append(record)
        assert new_store is not store
        assert len(new_store.records) == 1
        assert store.latest() is None  # original unchanged

    def test_append_multiple_records(self):
        store = LearningMemoryStore()
        r1 = LearningMemoryRecord(
            correlation_id="corr-1", diagnostics_count=1,
            hypothesis_count=0, candidate_count=0, summary="first",
        )
        r2 = LearningMemoryRecord(
            correlation_id="corr-2", diagnostics_count=2,
            hypothesis_count=1, candidate_count=0, summary="second",
        )
        store = store.append(r1).append(r2)
        assert store.latest() == r2
        assert len(store.records) == 2

    def test_negative_counts_rejected(self):
        with pytest.raises(ValidationError):
            LearningMemoryRecord(
                correlation_id="corr-1", diagnostics_count=-1,
                hypothesis_count=0, candidate_count=0, summary="bad",
            )
