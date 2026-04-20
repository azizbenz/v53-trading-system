from __future__ import annotations

from pathlib import Path

from interface_contracts import RefusalCategory, Side
from meta_minimal.refusal_journal import RefusalJournal, RefusalJournalSink
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime, RiskRuntimeAction
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.scoring_runtime import ScoringCandidateInput

from engines.engine_c import EngineCRuntimeStatus

from tests.test_engines.test_engine_c.test_engine_c_runtime import (
    _base_risk_evaluation,
    _coordination_input_c,
    _FixedRiskRuntime,
    _portfolio_state,
    _runtime,
    _runtime_input,
)


def test_runtime_hard_blocked_forecast_is_downstream_truthful(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_hard_blocked_downstream")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True),
        ),
        now=20.0,
    )

    assert result.status == EngineCRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is not None
    assert result.signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate is not None
    assert "engine_c.runtime.hard_blocked" in result.forecast_signal_candidate.reason_codes
    assert "hard_block.engine_c.runtime.hard_blocked" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK


def test_runtime_rejected_by_ranking_is_downstream_truthful(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_rejected_ranking_downstream")
    peer = ScoringCandidateInput(
        engine_id="engine_a",
        pair="ETHUSDT",
        raw_features={"structure": 0.98},
        allowed_features=frozenset({"structure"}),
        weights={"structure": 1.0},
        scoring_version="engine_a.v1",
        expected_cost=0.0005,
        expected_ce=0.003,
        projected_size=500.0,
        projected_loss=20.0,
        projected_beta_impact=0.0,
        cluster_id="eth_ecosystem",
    )

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            peer_candidates=(peer,),
            max_selections=1,
            portfolio=_portfolio_state(
                remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0},
            ),
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
            size_penalties=(SizePenaltyItem(penalty_id="size_soft", multiplier=0.9, reason="size soft"),),
        ),
        now=30.0,
    )

    assert result.status == EngineCRuntimeStatus.REJECTED_RANKING
    assert result.signal_candidate is not None
    assert result.signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate is not None
    assert "engine_c.runtime.rejected_ranking" in result.forecast_signal_candidate.reason_codes
    assert "scoring.engine_c.runtime.rejected_ranking" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.NO_TRADE


def test_runtime_rejected_by_portfolio_is_downstream_truthful(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_c_portfolio_downstream")
    runtime = _runtime(
        repo_tmp_path,
        "engine_c_rejected_portfolio_downstream",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineCRuntimeStatus.REJECTED_PORTFOLIO
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert "engine_c.runtime.rejected_portfolio" in result.forecast_signal_candidate.reason_codes
    assert "portfolio.engine_c.runtime.rejected_portfolio" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.PORTFOLIO_REJECTED
    assert journal.read() == (result.refusal_record,)


def test_runtime_risk_rejected_is_downstream_truthful(repo_tmp_path: Path) -> None:
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_c_risk_rejected_downstream", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(projected_size=1000.0, strategy_id="strategy-c-breakout"),
        now=50.0,
    )

    assert result.status == EngineCRuntimeStatus.RISK_REJECTED
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert "engine_c.runtime.risk_rejected" in result.forecast_signal_candidate.reason_codes
    assert "hard_block.engine_c.runtime.risk_rejected" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert any(entry.event == "engine_c_risk_rejected" for entry in result.log_entries)


def test_runtime_risk_reduced_is_governed_but_not_refusal(repo_tmp_path: Path) -> None:
    base = _base_risk_evaluation()
    risk_runtime = _FixedRiskRuntime(
        base.model_copy(
            update={
                "action": RiskRuntimeAction.REDUCE_EXPOSURE,
                "accepted": False,
                "reasons": ("reduce exposure",),
            }
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_c_risk_reduced_downstream", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-c-breakout"), now=70.0)

    assert result.status == EngineCRuntimeStatus.RISK_REDUCED
    assert result.refusal_record is None
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert "engine_c.runtime.risk_reduced" in result.forecast_signal_candidate.reason_codes
    assert "engine_internal.engine_c.runtime.risk_reduced" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert any(entry.event == "engine_c_risk_reduced" for entry in result.log_entries)
    assert not any(entry.event == "engine_c_risk_rejected" for entry in result.log_entries)


def test_runtime_risk_observe_only_is_governed_but_not_refusal(repo_tmp_path: Path) -> None:
    base = _base_risk_evaluation()
    risk_runtime = _FixedRiskRuntime(
        base.model_copy(
            update={
                "action": RiskRuntimeAction.OBSERVE_ONLY,
                "accepted": False,
                "reasons": ("observe only",),
            }
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_c_risk_observe_downstream", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-c-breakout"), now=80.0)

    assert result.status == EngineCRuntimeStatus.RISK_OBSERVE_ONLY
    assert result.refusal_record is None
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert "engine_c.runtime.risk_observe_only" in result.forecast_signal_candidate.reason_codes
    assert "engine_internal.engine_c.runtime.risk_observe_only" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert any(entry.event == "engine_c_risk_observe_only" for entry in result.log_entries)
    assert not any(entry.event == "engine_c_risk_rejected" for entry in result.log_entries)


def test_runtime_coordination_block_keeps_no_fake_blocked_trade(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_c_coordination_downstream")
    runtime = _runtime(
        repo_tmp_path,
        "engine_c_coordination_no_fake_trade",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            coordination_input=_coordination_input_c(a_holding_block_active=True),
        ),
        now=13.0,
    )

    assert result.status == EngineCRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is None
    assert result.forecast_signal_candidate is None
    assert result.refusal_record is not None
    assert "hard_block.ac_mutual_exclusion.a_holding" in result.refusal_record.reason_codes
    assert "engine_c.runtime.coordination_blocked" in result.refusal_record.reason_codes
    assert journal.read() == (result.refusal_record,)
