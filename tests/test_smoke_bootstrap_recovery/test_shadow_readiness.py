"""Tests for the Build-11 Shadow readiness preflight."""

from __future__ import annotations

import smoke_bootstrap_recovery
from smoke_bootstrap_recovery import evaluate_shadow_readiness


def test_shadow_readiness_exports_expected_symbols():
    assert {
        "ShadowReadinessReport",
        "evaluate_shadow_readiness",
    }.issubset(set(smoke_bootstrap_recovery.__all__))


def test_shadow_readiness_auto_detects_current_preflight_stack():
    report = evaluate_shadow_readiness(core_green=True)

    assert report.core_green is True
    assert report.build10_supervision_ready is True
    assert report.build9x_governed_ready is True
    assert report.replay_import_ready is True
    assert report.onboarding_ready is True
    assert report.build14_read_only_fenced is True
    assert report.final_verdict == "ready_for_shadow"


def test_shadow_readiness_lists_missing_items_when_gates_are_not_ready():
    report = evaluate_shadow_readiness(
        core_green=False,
        build10_supervision_ready=False,
        build9x_governed_ready=True,
        replay_import_ready=False,
        onboarding_ready=False,
        build14_read_only_fenced=False,
    )

    assert report.final_verdict == "not_ready_for_shadow"
    assert set(report.missing_items) == {
        "core baseline must stay green",
        "Build-10 supervision layer is not ready",
        "LOCAL_REPLAY / import governed MVP is not ready",
        "strategy onboarding governance is not ready",
        "Build-14 read-only fencing is not ready",
    }
