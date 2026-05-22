from __future__ import annotations

from local_replay_runtime.strategy_ladder_engine_synthetic_viability import (
    run_synthetic_engine_viability_harness,
)


def test_synthetic_engine_viability_harness_reports_all_four_engines() -> None:
    report = run_synthetic_engine_viability_harness()

    assert report.schema_version == "strategy_ladder.synthetic_engine_viability.v1"
    assert report.diagnostic_only is True
    assert report.overall_ok is True

    cases_by_key = {
        (case.engine_id, case.case_id): case
        for case in report.cases
    }

    assert len(cases_by_key) == 8

    assert cases_by_key[("engine_a", "emit_viable_candidate")].actual_decision == "emit"
    assert cases_by_key[("engine_a", "reject_non_long_candidate")].actual_decision == "no_trade"

    assert cases_by_key[("engine_b", "emit_viable_candidate")].actual_decision == "emit"
    assert cases_by_key[("engine_b", "reject_non_long_candidate")].actual_decision == "no_trade"

    assert cases_by_key[("engine_c", "emit_viable_candidate")].actual_decision == "emit"
    assert (
        cases_by_key[("engine_c", "reject_unconfirmed_microstructure")].actual_decision
        == "no_trade"
    )

    assert cases_by_key[("engine_d", "emit_viable_candidate")].actual_decision == "emit"
    assert cases_by_key[("engine_d", "reject_history_weak_candidate")].actual_decision == "no_trade"


def test_synthetic_engine_viability_harness_exposes_reason_codes_for_failures() -> None:
    report = run_synthetic_engine_viability_harness()
    cases_by_key = {
        (case.engine_id, case.case_id): case
        for case in report.cases
    }

    assert "engine_a.input.non_long_direction" in cases_by_key[
        ("engine_a", "reject_non_long_candidate")
    ].reason_codes
    assert "engine_b.direction.non_long" in cases_by_key[
        ("engine_b", "reject_non_long_candidate")
    ].reason_codes
    assert "engine_c.microstructure.missing" in cases_by_key[
        ("engine_c", "reject_unconfirmed_microstructure")
    ].reason_codes
    assert "engine_d.no_trade.history_weak" in cases_by_key[
        ("engine_d", "reject_history_weak_candidate")
    ].reason_codes
