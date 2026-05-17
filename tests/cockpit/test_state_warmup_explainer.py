from __future__ import annotations

from cockpit.state import WarmupCheck, WarmupSummary
from cockpit.state_warmup_explainer import read_warmup_explainer

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir, seed_phase25_files


def test_warmup_explainer_maps_blocked_checks_to_actions() -> None:
    scratch = scratch_dir("warmup_explainer_blocked")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        warmup = WarmupSummary(
            runtime_mode="shadow",
            final_state="blocked",
            eligible_to_trade=False,
            checks=(
                WarmupCheck(
                    check_id="bootstrap_reconciliation",
                    status="blocked",
                    reasons=("shadow.bootstrap.not_ready",),
                ),
            ),
        )
        snapshot = read_warmup_explainer(paths, warmup=warmup)
        assert snapshot.final_state == "blocked"
        assert snapshot.eligible_to_trade is False
        assert snapshot.readiness_status == "blocked"
        assert snapshot.checks[0].required_action == "run bootstrap reconciliation"
        assert "run_shadow_bootstrap.py" in snapshot.checks[0].suggested_command
    finally:
        cleanup_scratch(scratch)


def test_warmup_explainer_leaves_passed_checks_without_actions() -> None:
    scratch = scratch_dir("warmup_explainer_passed")
    try:
        paths = build_paths(scratch)
        warmup = WarmupSummary(
            runtime_mode="shadow",
            final_state="ready",
            eligible_to_trade=True,
            checks=(
                WarmupCheck(check_id="bootstrap_reconciliation", status="passed", reasons=()),
                WarmupCheck(check_id="remote_account_state", status="passed", reasons=()),
                WarmupCheck(check_id="time_sync", status="passed", reasons=()),
                WarmupCheck(check_id="market_data_capture", status="passed", reasons=()),
                WarmupCheck(check_id="binance_credentials", status="passed", reasons=()),
            ),
        )
        snapshot = read_warmup_explainer(paths, warmup=warmup)
        assert snapshot.readiness_status == "passed"
        assert snapshot.required_checks_passed is True
        assert snapshot.checks[0].required_action == ""
    finally:
        cleanup_scratch(scratch)


def test_warmup_explainer_accepts_eligible_to_trade_final_state_as_passed() -> None:
    scratch = scratch_dir("warmup_explainer_eligible_to_trade")
    try:
        paths = build_paths(scratch)
        warmup = WarmupSummary(
            runtime_mode="shadow",
            final_state="eligible_to_trade",
            eligible_to_trade=True,
            checks=(
                WarmupCheck(check_id="bootstrap_reconciliation", status="passed", reasons=()),
                WarmupCheck(check_id="remote_account_state", status="passed", reasons=()),
                WarmupCheck(check_id="time_sync", status="passed", reasons=()),
                WarmupCheck(check_id="market_data_capture", status="passed", reasons=()),
                WarmupCheck(check_id="binance_credentials", status="passed", reasons=()),
                WarmupCheck(check_id="account_user_data", status="passed", reasons=()),
            ),
        )
        snapshot = read_warmup_explainer(paths, warmup=warmup)
        assert snapshot.readiness_status == "passed"
        assert snapshot.required_checks_passed is True
        assert snapshot.review_only_checks == ()
    finally:
        cleanup_scratch(scratch)
