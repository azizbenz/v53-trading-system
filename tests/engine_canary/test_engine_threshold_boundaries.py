from __future__ import annotations

from local_replay_runtime.engine_math_canary_audit import (
    build_engine_threshold_boundary_report,
)


def test_engine_threshold_boundary_report_is_green() -> None:
    report = build_engine_threshold_boundary_report()
    rows = {(row["engine_id"], row["threshold_name"]): row for row in report["rows"]}

    assert report["row_count"] == len(rows)
    assert all(row["pass"] is True for row in rows.values())
    assert all("tested_input_values" in row for row in rows.values())
    assert all("derived_metric_values" in row for row in rows.values())
    assert all("comparison_expression" in row for row in rows.values())
    assert all("threshold_unit" in row for row in rows.values())

    assert ("engine_a", "min_direction") in rows
    assert ("engine_a", "marginal") in rows
    assert ("engine_a", "favorable") in rows
    assert ("engine_b", "z_marginal") in rows
    assert ("engine_b", "z_star") in rows
    assert ("engine_b", "delta_safe") in rows
    assert ("engine_b", "ce_min") in rows
    assert ("engine_c", "breakout_score_min") in rows
    assert ("engine_c", "breakout_strength_min") in rows
    assert ("engine_c", "range_quality_min") in rows
    assert ("engine_c", "fake_breakout_risk_max") in rows
    assert ("engine_d", "history_min") in rows
    assert ("engine_d", "reformation_min") in rows
    assert ("engine_d", "concentration_max") in rows

    assert rows[("engine_a", "marginal")]["threshold_value"] == 0.30
    assert rows[("engine_a", "marginal")]["tested_input_values"][1] == 0.9
    assert rows[("engine_a", "marginal")]["derived_metric_name"] == "structure_score"

    assert rows[("engine_a", "favorable")]["threshold_value"] == 0.60
    assert rows[("engine_b", "delta_safe")]["threshold_value"] == 0.0008
    assert rows[("engine_b", "ce_min")]["threshold_value"] == 0.0002
    assert rows[("engine_c", "breakout_score_min")]["threshold_value"] == 0.62
    assert rows[("engine_d", "history_min")]["threshold_value"] == 0.55
