from __future__ import annotations

import pytest

from engines.engine_c.output_payload_builder_c import build_engine_c_output_payload


def _structure() -> dict[str, float | str | bool]:
    return {
        "range_low": 97.5,
        "range_high": 101.0,
        "range_width_pct": 0.03,
        "breakout_type": "range_expansion",
        "continuation_context": "fresh_breakout",
        "distance_to_breakout_pct": 0.01,
        "duplication_possible_with_engine_a": False,
        "duplication_overlap_with_engine_a": 0.2,
        "local_duplication_policy_triggered": False,
        "duplication_blocked": False,
        "marginal_portfolio_gain": 2.0,
        "covered_share_by_engine_a": 0.2,
        "keff_contribution": 0.3,
    }


def test_payload_contains_required_structure_keys() -> None:
    payload = build_engine_c_output_payload(
        structure=_structure(),
        scoring_version="engine_c.v1",
        log_entries=(),
    )

    assert payload["range_low"] == pytest.approx(97.5)
    assert payload["breakout_type"] == "range_expansion"
    assert payload["local_duplication_policy_triggered"] is False
    assert payload["duplication_blocked"] is False


def test_overrides_win() -> None:
    payload = build_engine_c_output_payload(
        structure=_structure(),
        scoring_version="engine_c.v1",
        log_entries=(),
        marginal_portfolio_gain=9.0,
    )

    assert payload["marginal_portfolio_gain"] == 9.0


def test_incomplete_structure_fails_explicitly_or_is_documented() -> None:
    broken = _structure()
    broken.pop("local_duplication_policy_triggered")

    with pytest.raises(ValueError, match="requires complete structure keys"):
        build_engine_c_output_payload(
            structure=broken,
            scoring_version="engine_c.v1",
            log_entries=(),
        )
