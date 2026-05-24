from __future__ import annotations

from local_replay_runtime.ml_label_leakage_guards import (
    LABEL_FEATURE_AS_INPUT_BLOCKED,
    NO_LABEL_LEAKAGE_DETECTED,
    build_ml_feature_input_label_leakage_report,
)


def test_label_leakage_guard_allows_legacy_inputs() -> None:
    report = build_ml_feature_input_label_leakage_report(
        ("close_return", "high_low_range", "volume")
    )

    assert report.status == NO_LABEL_LEAKAGE_DETECTED
    assert report.blocked_feature_names == ()


def test_label_leakage_guard_blocks_mfe_mae_and_realized_pnl() -> None:
    report = build_ml_feature_input_label_leakage_report(
        ("close_return", "mfe_bps", "mae_bps", "realized_pnl")
    )

    assert report.status == LABEL_FEATURE_AS_INPUT_BLOCKED
    assert report.blocked_feature_names == ("mfe_bps", "mae_bps", "realized_pnl")


def test_label_leakage_guard_blocks_selected_and_executed_counts() -> None:
    report = build_ml_feature_input_label_leakage_report(
        ("selected_count", "executed_count")
    )

    assert report.status == LABEL_FEATURE_AS_INPUT_BLOCKED
    assert report.blocked_feature_names == ("selected_count", "executed_count")
