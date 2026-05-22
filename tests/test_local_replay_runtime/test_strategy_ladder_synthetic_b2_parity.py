from __future__ import annotations

from pathlib import Path

from local_replay_runtime.strategy_ladder_synthetic_b2_parity import (
    run_synthetic_b2_parity_report,
)


def test_synthetic_b2_parity_report_exposes_unbiased_direct_vs_builder_truth(
    tmp_path: Path,
) -> None:
    report = run_synthetic_b2_parity_report(asset_root=tmp_path / "synthetic_b2_assets")
    cases = {(case.engine_id, case.case_id): case for case in report.cases}

    assert set(cases) == {
        ("engine_a", "emit_viable_candidate"),
        ("engine_b", "emit_viable_candidate"),
        ("engine_c", "emit_viable_candidate"),
        ("engine_c", "emit_builder_aligned_candidate"),
        ("engine_d", "emit_viable_candidate"),
        ("engine_d", "emit_builder_aligned_candidate"),
    }

    assert cases[("engine_a", "emit_viable_candidate")].viability_vs_builder_status == "PARITY_OK"
    assert cases[("engine_a", "emit_viable_candidate")].builder_vs_runner_status == "PARITY_OK"
    assert cases[("engine_a", "emit_viable_candidate")].builder_path_decision == "emit"

    assert cases[("engine_b", "emit_viable_candidate")].viability_vs_builder_status == "PARITY_OK"
    assert cases[("engine_b", "emit_viable_candidate")].builder_vs_runner_status == "PARITY_OK"
    assert cases[("engine_b", "emit_viable_candidate")].builder_path_decision == "emit"

    assert cases[("engine_c", "emit_viable_candidate")].viability_vs_builder_status == "PARITY_MISMATCH"
    assert cases[("engine_c", "emit_viable_candidate")].builder_vs_runner_status == "PARITY_OK"
    assert "continuation_not_viable" in cases[("engine_c", "emit_viable_candidate")].builder_no_trade_reasons
    assert (
        "ENGINE_C_VIABILITY_INPUT_GEOMETRY_INCONSISTENT_WITH_BUILDER_FORMULA"
        in cases[("engine_c", "emit_viable_candidate")].notes
    )
    assert cases[("engine_c", "emit_builder_aligned_candidate")].viability_vs_builder_status == "PARITY_OK"
    assert cases[("engine_c", "emit_builder_aligned_candidate")].builder_vs_runner_status == "PARITY_OK"
    assert cases[("engine_c", "emit_builder_aligned_candidate")].builder_path_decision == "emit"
    assert (
        "DIRECT_INPUT_DERIVED_FROM_BUILDER_PAYLOAD_FOR_PARITY_ALIGNMENT"
        in cases[("engine_c", "emit_builder_aligned_candidate")].notes
    )

    assert cases[("engine_d", "emit_viable_candidate")].viability_vs_builder_status == "PARITY_MISMATCH"
    assert cases[("engine_d", "emit_viable_candidate")].builder_vs_runner_status == "PARITY_OK"
    assert "reformation_weak" in cases[("engine_d", "emit_viable_candidate")].builder_no_trade_reasons
    assert "ENGINE_D_FIRST_EPISODE_CONTEXT_CONSUMED" in cases[("engine_d", "emit_viable_candidate")].notes
    assert cases[("engine_d", "emit_builder_aligned_candidate")].viability_vs_builder_status == "PARITY_OK"
    assert cases[("engine_d", "emit_builder_aligned_candidate")].builder_vs_runner_status == "PARITY_OK"
    assert cases[("engine_d", "emit_builder_aligned_candidate")].builder_path_decision == "emit"
    assert (
        "DIRECT_INPUT_DERIVED_FROM_BUILDER_PAYLOAD_FOR_PARITY_ALIGNMENT"
        in cases[("engine_d", "emit_builder_aligned_candidate")].notes
    )
