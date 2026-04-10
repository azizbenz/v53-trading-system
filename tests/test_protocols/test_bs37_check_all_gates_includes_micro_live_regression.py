"""
BS-37 regression — check_all_gates was missing check_complete_to_micro_live.

Blind spot: check_all_gates returned only 2 results (light→micro_live, complete→live).
The COMPLETE shadow→micro-live gate was not surfaced as a standalone result,
making it invisible to callers that iterate over all gate results.

Fix: check_all_gates now returns 3 results:
  (check_complete_to_micro_live, check_complete_to_live, check_light_to_micro_live)
"""

from __future__ import annotations

import pytest

from protocols.promotion_gates import (
    check_all_gates,
    check_complete_to_micro_live,
)
from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile


pytestmark = pytest.mark.build1


_BASE_TS = 1_700_000_000.0
_ONE_DAY = 86_400.0


def _fill_complete_days(state_dir, n: int) -> None:
    counter = ShadowDayCounter(state_dir=state_dir, profile=ShadowProfile.COMPLETE)
    for i in range(n):
        counter.record_shadow_day(
            passed_all_gates=True,
            now=_BASE_TS + i * _ONE_DAY * 0.5,
        )


class TestCheckAllGatesIncludesMicroLive:
    def test_returns_three_results(self, repo_tmp_path):
        """BS-37: check_all_gates must return 3 results (was 2 before fix)."""
        results = check_all_gates(repo_tmp_path)
        assert len(results) == 3

    def test_complete_to_micro_live_gate_is_present(self, repo_tmp_path):
        """check_complete_to_micro_live result must appear in check_all_gates output."""
        results = check_all_gates(repo_tmp_path)
        gate_names = {r.gate_name for r in results}
        assert "complete_shadow_30j_for_micro_live" in gate_names

    def test_complete_to_live_gate_is_present(self, repo_tmp_path):
        """check_complete_to_live result must appear in check_all_gates output."""
        results = check_all_gates(repo_tmp_path)
        gate_names = {r.gate_name for r in results}
        assert "complete_shadow_30j" in gate_names

    def test_light_to_micro_live_gate_is_present(self, repo_tmp_path):
        """Legacy light gate must still appear for backwards compatibility."""
        results = check_all_gates(repo_tmp_path)
        profiles = {r.profile for r in results}
        assert "light" in profiles

    def test_complete_to_micro_live_first_in_order(self, repo_tmp_path):
        """Production gate (complete_to_micro_live) comes before legacy light gate."""
        results = check_all_gates(repo_tmp_path)
        complete_micro_live_idx = next(
            i for i, r in enumerate(results)
            if r.gate_name == "complete_shadow_30j_for_micro_live"
        )
        light_idx = next(
            i for i, r in enumerate(results)
            if r.profile == "light"
        )
        assert complete_micro_live_idx < light_idx

    def test_complete_micro_live_result_matches_standalone_check(self, repo_tmp_path):
        """Result in check_all_gates matches check_complete_to_micro_live() directly."""
        _fill_complete_days(repo_tmp_path, 15)
        results = check_all_gates(repo_tmp_path)
        standalone = check_complete_to_micro_live(repo_tmp_path)

        aggregated = next(
            r for r in results if r.gate_name == "complete_shadow_30j_for_micro_live"
        )
        assert aggregated.passed == standalone.passed
        assert aggregated.consecutive_days == standalone.consecutive_days
        assert aggregated.remaining_days == standalone.remaining_days
