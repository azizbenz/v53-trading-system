"""Build-9 tests for meta_minimal dtr_core."""

from __future__ import annotations

import pytest

from meta_minimal.dtr_core.cause_chain_assembler import assemble_cause_chain
from meta_minimal.dtr_core.decision_state_encoder import (
    DecisionState,
    encode_state,
    state_severity,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord, build_dtr
from meta_minimal.dtr_core.dtr_reporter import build_dtr_summary
from meta_minimal.dtr_core.trace_persistence_layer import DTRStore


class TestDecisionStateEncoder:
    def test_executed_highest_priority(self) -> None:
        state = encode_state(hard_blocked=True, was_executed=True)
        assert state == DecisionState.EXECUTED

    def test_phantom(self) -> None:
        state = encode_state(selected=True, is_phantom=True)
        assert state == DecisionState.PHANTOM

    def test_reduced(self) -> None:
        state = encode_state(selected=True, was_reduced=True)
        assert state == DecisionState.REDUCED

    def test_selected(self) -> None:
        state = encode_state(selected=True)
        assert state == DecisionState.SELECTED

    def test_ranking_rejected(self) -> None:
        state = encode_state(ranking_rejected=True)
        assert state == DecisionState.REJECTED_RANKING

    def test_hard_blocked(self) -> None:
        state = encode_state(hard_blocked=True)
        assert state == DecisionState.HARD_BLOCKED

    def test_default_evaluated(self) -> None:
        state = encode_state()
        assert state == DecisionState.EVALUATED

    def test_severity_ordering(self) -> None:
        assert state_severity(DecisionState.EXECUTED) > state_severity(
            DecisionState.PHANTOM
        )
        assert state_severity(DecisionState.PHANTOM) > state_severity(
            DecisionState.SELECTED
        )


class TestDTRRecordBuilder:
    def test_build_selected_dtr(self) -> None:
        dtr = build_dtr(
            dtr_id="dtr_001",
            pair="BTC/USDT",
            engine_id="engine_a",
            decision_state=DecisionState.SELECTED,
            raw_score=0.8,
            penalized_score=0.7,
            final_score=0.7,
            timestamp=1000.0,
        )
        assert dtr.pair == "BTC/USDT"
        assert dtr.decision_state == DecisionState.SELECTED
        assert dtr.schema_version == "1.0"

    def test_build_blocked_dtr(self) -> None:
        dtr = build_dtr(
            dtr_id="dtr_002",
            pair="ETH/USDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            hard_blocked=True,
            hard_block_reasons=("stale_data", "no_cluster"),
            timestamp=1000.0,
        )
        assert dtr.hard_blocked is True
        assert len(dtr.hard_block_reasons) == 2

    def test_build_phantom_dtr(self) -> None:
        dtr = build_dtr(
            dtr_id="dtr_003",
            pair="X/USDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            candidate_size=100.0,
            final_size=5.0,
            timestamp=1000.0,
        )
        assert dtr.decision_state == DecisionState.PHANTOM
        assert dtr.final_size == 5.0

    def test_timestamp_auto_filled(self) -> None:
        dtr = build_dtr(
            dtr_id="t",
            pair="X",
            engine_id="a",
            decision_state=DecisionState.EVALUATED,
        )
        assert dtr.timestamp > 0.0


class TestCauseChainAssembler:
    def test_full_chain(self) -> None:
        cause_chain = assemble_cause_chain(
            score_step="raw=0.8",
            penalty_steps=("stale:-0.1",),
            penalty_total=0.1,
            ranking_step="rank=3",
            allocation_step="size=50",
        )
        assert len(cause_chain.steps) == 4
        assert cause_chain.penalty_total == 0.1

    def test_blocker_chain(self) -> None:
        cause_chain = assemble_cause_chain(
            blocker_steps=("no_cluster", "stale_data")
        )
        assert cause_chain.blocker_count == 2
        assert cause_chain.primary_reason == "blocked: no_cluster"

    def test_empty_chain(self) -> None:
        cause_chain = assemble_cause_chain()
        assert len(cause_chain.steps) == 0
        assert cause_chain.primary_reason == ""

    def test_reduction_reason(self) -> None:
        cause_chain = assemble_cause_chain(reduction_reason="gross_cap")
        assert cause_chain.was_reduced is True
        assert cause_chain.reduction_reason == "gross_cap"


class TestTracePersistenceLayer:
    def _dtr(
        self,
        dtr_id: str = "d1",
        pair: str = "BTC/USDT",
    ) -> DTRRecord:
        return build_dtr(
            dtr_id=dtr_id,
            pair=pair,
            engine_id="engine_a",
            decision_state=DecisionState.SELECTED,
            timestamp=1000.0,
        )

    def test_persist_and_retrieve(self) -> None:
        store = DTRStore()
        assert store.persist(self._dtr())
        assert store.size == 1

    def test_get_by_pair(self) -> None:
        store = DTRStore()
        store.persist(self._dtr("a", "BTC/USDT"))
        store.persist(self._dtr("b", "ETH/USDT"))
        assert len(store.get_by_pair("BTC/USDT")) == 1

    def test_get_by_engine(self) -> None:
        store = DTRStore()
        store.persist(self._dtr())
        assert len(store.get_by_engine("engine_a")) == 1

    def test_batch_persist(self) -> None:
        store = DTRStore()
        persisted_count = store.persist_batch(
            (self._dtr("a"), self._dtr("b"), self._dtr("c"))
        )
        assert persisted_count == 3
        assert store.size == 3

    def test_stats_no_drops(self) -> None:
        store = DTRStore()
        store.persist(self._dtr())
        stats = store.get_stats()
        assert stats.total_persisted == 1
        assert stats.loss_rate == 0.0


class TestDTRReporter:
    def test_summary_counts(self) -> None:
        records = (
            build_dtr("a", "BTC", "engine_a", DecisionState.SELECTED, timestamp=1.0),
            build_dtr("b", "ETH", "engine_b", DecisionState.HARD_BLOCKED, timestamp=2.0),
            build_dtr("c", "BTC", "engine_a", DecisionState.PHANTOM, timestamp=3.0),
        )
        summary = build_dtr_summary(records, total_opportunities=5)
        assert summary.total_records == 3
        assert summary.by_state["selected"] == 1
        assert summary.by_state["hard_blocked"] == 1
        assert summary.by_state["phantom"] == 1
        assert summary.by_engine["engine_a"] == 2
        assert summary.by_pair["BTC"] == 2
        assert summary.dtr_coverage == pytest.approx(0.6)

    def test_empty_summary(self) -> None:
        summary = build_dtr_summary((), total_opportunities=0)
        assert summary.total_records == 0
        assert summary.dtr_coverage == 0.0
