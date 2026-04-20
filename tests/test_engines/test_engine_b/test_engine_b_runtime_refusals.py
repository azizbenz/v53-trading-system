"""Refusal-journal tests for Build-7 Engine B runtime."""

from __future__ import annotations

from pathlib import Path

from engines.engine_b import EngineBRuntime, EngineBRuntimeStatus
from interface_contracts import RefusalCategory
from meta_minimal.refusal_journal import RefusalJournal, RefusalJournalSink
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker, KillSwitchReason
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime

from .test_engine_b_runtime import (
    _blocking_sweep_hook,
    _breaker_state_dir,
    _risk_runtime,
    _runtime,
    _runtime_input,
    _scoring_runtime,
    _portfolio_state,
)


def test_runtime_writes_refusal_record_for_circuit_breaker_block(repo_tmp_path: Path) -> None:
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, "engine_b_refusal_breaker"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_b_breaker")
    runtime = EngineBRuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(_runtime_input(), now=11.0)

    assert result.status == EngineBRuntimeStatus.CIRCUIT_BREAKER_BLOCKED
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert result.refusal_record.reason_codes == (
        "engine_b.runtime.circuit_breaker.operator_manual",
    )
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record


def test_runtime_writes_refusal_record_for_hook_block(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_b_hook")
    runtime = _runtime(
        repo_tmp_path,
        "engine_b_hook_refusal",
        sweep_validation_hook=_blocking_sweep_hook,
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(_runtime_input(), now=12.5)

    assert result.status == EngineBRuntimeStatus.HOOK_BLOCKED
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert result.refusal_record.reason_codes == ("ARTIFACT_SWEEP_BLOCK",)
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record


def test_runtime_writes_refusal_record_for_portfolio_rejection(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_b_portfolio")
    runtime = _runtime(
        repo_tmp_path,
        "engine_b_portfolio_refusal",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineBRuntimeStatus.REJECTED_PORTFOLIO
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.PORTFOLIO_REJECTED
    assert "portfolio.engine_b.runtime.rejected_portfolio" in result.refusal_record.reason_codes
    assert "engine_b.runtime.rejected_portfolio" in result.refusal_record.reason_codes
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record


def test_runtime_writes_refusal_record_for_risk_rejection(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_b_risk")
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
        "engine_b_risk_refusal",
        risk_runtime=risk_runtime,
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)

    assert result.status == EngineBRuntimeStatus.RISK_REJECTED
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert result.refusal_record.reason_codes
    records = journal.read()
    assert len(records) == 1
    assert records[0] == result.refusal_record
