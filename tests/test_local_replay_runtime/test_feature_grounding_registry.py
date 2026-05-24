from __future__ import annotations

from local_replay_runtime.feature_grounding_registry import (
    FeatureGroundingStatus,
    build_feature_grounding_contract_report,
)


def _row(report, feature_name: str):
    return next(item for item in report.rows if item.feature_name == feature_name)


def test_legacy_only_without_b2_is_allowed() -> None:
    report = build_feature_grounding_contract_report(
        ("close_return", "high_low_range", "volume"),
    )

    assert report.status == "FEATURE_GROUNDING_CONTRACT_OK"
    assert all(
        row.status == FeatureGroundingStatus.FEATURE_GROUNDING_OK
        for row in report.rows
    )


def test_spread_bps_with_a2_orderbook_is_allowed_as_ex_ante_input() -> None:
    report = build_feature_grounding_contract_report(
        ("spread_bps",),
        a2_orderbook_available=True,
    )

    row = _row(report, "spread_bps")
    assert row.status == FeatureGroundingStatus.FEATURE_GROUNDING_OK
    assert row.available_at_decision_time is True
    assert row.allowed_as_runtime_input is True
    assert row.requires_a2_orderbook is True
    assert row.requires_b2 is False


def test_spread_bps_without_orderbook_is_blocked() -> None:
    report = build_feature_grounding_contract_report(("spread_bps",))

    row = _row(report, "spread_bps")
    assert report.status == "FEATURE_GROUNDING_CONTRACT_BLOCKED"
    assert row.status == FeatureGroundingStatus.FEATURE_REQUIRES_A2_ORDERBOOK


def test_mfe_bps_as_input_is_blocked() -> None:
    report = build_feature_grounding_contract_report(("mfe_bps",))

    row = _row(report, "mfe_bps")
    assert row.status == FeatureGroundingStatus.FEATURE_LABEL_NOT_ALLOWED_AS_RUNTIME_INPUT
    assert row.is_label_or_outcome is True


def test_selected_count_as_input_is_blocked() -> None:
    report = build_feature_grounding_contract_report(("selected_count",))

    row = _row(report, "selected_count")
    assert row.status == FeatureGroundingStatus.FEATURE_LABEL_NOT_ALLOWED_AS_RUNTIME_INPUT


def test_slippage_without_execution_replay_requires_b2() -> None:
    report = build_feature_grounding_contract_report(("slippage_bps",))

    row = _row(report, "slippage_bps")
    assert row.status == FeatureGroundingStatus.FEATURE_REQUIRES_B2
