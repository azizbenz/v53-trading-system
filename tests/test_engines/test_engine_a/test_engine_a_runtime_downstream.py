"""Downstream runtime truthfulness tests for Engine A additive forecast/refusal wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from engines.engine_a.conviction_builder_a import ENGINE_A_CONVICTION_FEATURE_WEIGHTS
from engines.engine_a.engine_a_runtime_support import _resolve_runtime_risk_reason_codes
from interface_contracts import RefusalCategory, Side
from meta_minimal.refusal_journal import RefusalJournal, RefusalJournalSink
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime, RiskRuntimeAction
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.scoring_runtime import ScoringCandidateInput

from .test_engine_a_runtime import (
    _base_risk_evaluation,
    _detail_only_pre_entry_hook,
    _FixedRiskRuntime,
    _good_engine_inputs,
    _portfolio_state,
    _runtime,
    _runtime_input,
)
from engines.engine_a import EngineARuntimeStatus


def test_runtime_risk_reason_codes_tolerate_blank_or_none_dominant_reason_code() -> None:
    base = _base_risk_evaluation()
    blank = base.model_copy(update={"reason_details": (), "dominant_reason_code": "   "})
    none_value = base.model_copy(update={"reason_details": (), "dominant_reason_code": None})

    assert _resolve_runtime_risk_reason_codes(blank) == ()
    assert _resolve_runtime_risk_reason_codes(none_value) == ()


def test_runtime_hook_blocked_without_structured_codes_uses_stable_runtime_code(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(
        repo_tmp_path,
        "engine_a_hook_blocked_stable_code",
        pre_entry_validation_hook=_detail_only_pre_entry_hook,
    )

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-a-breakout"), now=12.6)

    assert result.status == EngineARuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.forecast_signal_candidate is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_a_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("engine_a.runtime.hook_blocked",)


def test_runtime_writes_stable_refusal_record_for_hook_block_without_structured_codes(
    repo_tmp_path: Path,
) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_a_hook_fallback")
    runtime = _runtime(
        repo_tmp_path,
        "engine_a_hook_fallback_refusal",
        pre_entry_validation_hook=_detail_only_pre_entry_hook,
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-a-breakout"), now=12.7)

    assert result.status == EngineARuntimeStatus.HOOK_BLOCKED
    assert result.refusal_record is not None
    assert result.refusal_record.reason_codes == ("engine_a.runtime.hook_blocked",)
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record


def test_runtime_hard_blocked_logs_explicit_reasons(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_hard_blocked")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-a-breakout",
            blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True),
        ),
        now=20.0,
    )

    assert result.status == EngineARuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is not None
    assert result.signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.side == Side.BUY
    assert "engine_a.runtime.hard_blocked" in result.forecast_signal_candidate.reason_codes
    assert "hard_block.engine_a.runtime.hard_blocked" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.risk_evaluation is None
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_a_hard_blocked"]
    assert len(blocked_logs) == 1
    joined = " ".join(blocked_logs[0].reasons).lower()
    assert "stale" in joined
    assert "suspended" in joined


def test_runtime_rejected_by_ranking_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_rejected_ranking")
    peer = ScoringCandidateInput(
        engine_id="engine_b",
        pair="ETHUSDT",
        raw_features={"structure": 0.95},
        allowed_features=frozenset({"structure"}),
        weights={"structure": 1.0},
        scoring_version="engine_b.v1",
        expected_cost=0.0005,
        expected_ce=0.003,
        projected_size=500.0,
        projected_loss=20.0,
        projected_beta_impact=0.0,
        cluster_id="eth_ecosystem",
    )

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-a-breakout",
            peer_candidates=(peer,),
            max_selections=1,
            portfolio=_portfolio_state(
                remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0},
            ),
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.2, reason="context soft"),),
            size_penalties=(SizePenaltyItem(penalty_id="size_soft", multiplier=0.9, reason="size soft"),),
        ),
        now=30.0,
    )

    assert result.status == EngineARuntimeStatus.REJECTED_RANKING
    assert result.scoring_audit is not None
    assert result.scoring_audit.selection_entry is not None
    assert result.scoring_audit.selection_entry.outcome.value == "rejected_ranking"
    assert result.forecast_signal_candidate is not None
    assert "engine_a.runtime.rejected_ranking" in result.forecast_signal_candidate.reason_codes
    assert "scoring.engine_a.runtime.rejected_ranking" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.NO_TRADE
    ranking_logs = [entry for entry in result.log_entries if entry.event == "engine_a_rejected_by_ranking"]
    assert len(ranking_logs) == 1
    assert "max selections" in ranking_logs[0].reasons[0]


def test_runtime_rejected_by_portfolio_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_rejected_portfolio")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-a-breakout",
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineARuntimeStatus.REJECTED_PORTFOLIO
    assert result.forecast_signal_candidate is not None
    assert "engine_a.runtime.rejected_portfolio" in result.forecast_signal_candidate.reason_codes
    assert "portfolio.engine_a.runtime.rejected_portfolio" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    portfolio_logs = [entry for entry in result.log_entries if entry.event == "engine_a_rejected_by_portfolio"]
    assert len(portfolio_logs) == 1
    assert "remaining gross" in portfolio_logs[0].reasons[0]


def test_runtime_writes_refusal_record_for_portfolio_rejection(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_a_portfolio")
    runtime = _runtime(
        repo_tmp_path,
        "engine_a_portfolio_refusal",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-a-breakout",
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineARuntimeStatus.REJECTED_PORTFOLIO
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.PORTFOLIO_REJECTED
    assert "portfolio.engine_a.runtime.rejected_portfolio" in result.refusal_record.reason_codes
    assert "engine_a.runtime.rejected_portfolio" in result.refusal_record.reason_codes
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record


def test_runtime_cannot_bypass_risk_runtime(repo_tmp_path: Path) -> None:
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_a_risk_runtime", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(projected_size=1000.0, strategy_id="strategy-a-breakout"),
        now=50.0,
    )

    assert result.status == EngineARuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
    assert result.forecast_signal_candidate is not None
    assert "engine_a.runtime.risk_rejected" in result.forecast_signal_candidate.reason_codes
    assert "hard_block.engine_a.runtime.risk_rejected" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    risk_logs = [entry for entry in result.log_entries if entry.event == "engine_a_risk_rejected"]
    assert len(risk_logs) == 1
    assert "gross" in " ".join(risk_logs[0].reasons).lower()


def test_runtime_writes_refusal_record_for_risk_rejection(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_a_risk")
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(
        repo_tmp_path,
        "engine_a_risk_refusal",
        risk_runtime=risk_runtime,
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(projected_size=1000.0, strategy_id="strategy-a-breakout"),
        now=50.0,
    )

    assert result.status == EngineARuntimeStatus.RISK_REJECTED
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert result.refusal_record.reason_codes
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record


def test_runtime_scoring_raw_score_matches_engine_output_with_adjustment_features(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_scoring_parity")

    result = runtime.evaluate(
        _runtime_input(
            engine_inputs=_good_engine_inputs(
                delta_confirmation=0.9,
                competition_density=0.2,
                execution_fragility=0.8,
                market_toxicity=0.7,
                spread_regime_penalty=0.6,
            )
        ),
        now=60.0,
    )

    assert result.status == EngineARuntimeStatus.ACCEPTED
    assert result.scoring_audit is not None
    assert result.scoring_audit.raw_score_result.raw_score == pytest.approx(
        result.engine_output.raw_score
    )
    assert {
        "delta_confirmation_centered",
        "competition_support_centered",
        "fragility_score",
        "toxicity_score",
        "micro_friction_score",
    }.issubset(result.scoring_audit.raw_score_result.features_used)

    block_scores = result.engine_output.block_scores
    legacy_raw = (
        ENGINE_A_CONVICTION_FEATURE_WEIGHTS["structure"] * block_scores["structure"]
        + ENGINE_A_CONVICTION_FEATURE_WEIGHTS["context"] * block_scores["context"]
        + ENGINE_A_CONVICTION_FEATURE_WEIGHTS["flow"] * block_scores["flow"]
        + ENGINE_A_CONVICTION_FEATURE_WEIGHTS["cost_preference"]
        * block_scores["cost_preference"]
    )
    assert result.engine_output.raw_score != pytest.approx(legacy_raw)


def test_runtime_risk_reduced_event_matches_status(repo_tmp_path: Path) -> None:
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
    runtime = _runtime(repo_tmp_path, "engine_a_risk_reduced", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-a-breakout"), now=70.0)

    assert result.status == EngineARuntimeStatus.RISK_REDUCED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.REDUCE_EXPOSURE
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert "engine_a.runtime.risk_reduced" in result.forecast_signal_candidate.reason_codes
    assert "engine_internal.engine_a.runtime.risk_reduced" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is None
    assert any(entry.event == "engine_a_risk_reduced" for entry in result.log_entries)
    assert not any(entry.event == "engine_a_risk_rejected" for entry in result.log_entries)


def test_runtime_risk_observe_only_event_matches_status(repo_tmp_path: Path) -> None:
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
    runtime = _runtime(repo_tmp_path, "engine_a_risk_observe", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-a-breakout"), now=80.0)

    assert result.status == EngineARuntimeStatus.RISK_OBSERVE_ONLY
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert "engine_a.runtime.risk_observe_only" in result.forecast_signal_candidate.reason_codes
    assert "engine_internal.engine_a.runtime.risk_observe_only" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }
    assert result.refusal_record is None
    assert any(entry.event == "engine_a_risk_observe_only" for entry in result.log_entries)
    assert not any(entry.event == "engine_a_risk_rejected" for entry in result.log_entries)
