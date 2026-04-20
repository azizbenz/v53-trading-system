from __future__ import annotations

import pytest

from engines.engine_d.output_payload_builder_d import build_engine_d_output_payload


def _context() -> dict[str, float | str | bool | int | None]:
    return {
        "origin_context_id": "ctx-1",
        "origin_trade_id": "trade-1",
        "link_type": "prior_trade",
        "structure_reformed_detected": True,
        "first_episode_id": "episode-1",
        "first_episode_engine_id": "engine_a",
        "first_episode_close_reason": "stop_out",
        "consecutive_stop_count": 1,
        "last_stop_at_ns": 1_700_000_000_000_000_000,
        "last_fresh_a_detection_at_ns": 1_700_000_100_000_000_000,
        "anti_revenge_state": "reset_required",
        "anti_revenge_blocked": False,
        "concentration_risk": 0.4,
        "marginal_concentration": 0.4,
        "duplication_possible_with_engine_a": False,
        "duplication_overlap_with_engine_a": 0.2,
        "duplication_blocked": False,
        "marginal_portfolio_gain": 2.0,
        "covered_share_by_engine_a": 0.2,
    }


def test_payload_contains_required_context_keys() -> None:
    payload = build_engine_d_output_payload(
        context=_context(),
        scoring_version="engine_d.v1",
        log_entries=(),
    )

    assert payload["origin_context_id"] == "ctx-1"
    assert payload["anti_revenge_blocked"] is False
    assert payload["duplication_blocked"] is False
    assert payload["concentration_risk"] == pytest.approx(0.4)


def test_overrides_win() -> None:
    payload = build_engine_d_output_payload(
        context=_context(),
        scoring_version="engine_d.v1",
        log_entries=(),
        marginal_portfolio_gain=9.0,
    )

    assert payload["marginal_portfolio_gain"] == 9.0


def test_incomplete_context_fails_explicitly_or_is_documented() -> None:
    broken = _context()
    broken.pop("anti_revenge_blocked")

    with pytest.raises(ValueError, match="requires complete context keys"):
        build_engine_d_output_payload(
            context=broken,
            scoring_version="engine_d.v1",
            log_entries=(),
        )
