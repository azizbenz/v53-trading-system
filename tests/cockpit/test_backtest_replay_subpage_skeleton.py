"""A (2026-05-30) — smoke test backtest_replay sub-page skeleton.

Verifies that the new `/backtest/replay` route returns 200 + renders the
runtime_feature_parity_card partial (backend B wired). The remaining cards
(decision_report, backbone_parity_detail, backbone_metrics, runner_coverage,
prod_safety_contract, loss_analysis_ledger) are queued for Codex extraction
per `2026-05-30_A_BACKTEST_REPLAY_SUBPAGE_SPLIT_SPEC.md`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cockpit.server import create_app

from ._operational_helpers import (
    build_paths,
    scratch_dir,
)


def test_backtest_replay_route_returns_200_and_renders_skeleton() -> None:
    scratch = scratch_dir("backtest_replay_skeleton")
    paths = build_paths(scratch)
    client = TestClient(create_app(paths=paths))

    response = client.get("/backtest/replay")

    assert response.status_code == 200
    body = response.text
    # Welcome banner heading
    assert "Backtest Replay" in body
    # Pinned run ID placeholder
    assert 'id="backtest-replay-pinned-run"' in body
    # Runtime feature parity card partial rendered (backend B → None → fallback shown)
    assert 'id="backtest-runtime-feature-parity-card"' in body


def test_backtest_replay_route_with_pinned_run_id_query_param() -> None:
    scratch = scratch_dir("backtest_replay_pinned")
    paths = build_paths(scratch)
    client = TestClient(create_app(paths=paths))

    response = client.get("/backtest/replay?pinned_run_id=strategy_ladder_workflow-test")

    assert response.status_code == 200
    # Page renders even when pinned_run_id has no matching record (None card)
    assert "Runtime Feature Parity" in response.text


def test_backtest_replay_link_back_to_backtest_present() -> None:
    """Operator should be able to navigate back to /backtest from replay."""
    scratch = scratch_dir("backtest_replay_navigation")
    paths = build_paths(scratch)
    client = TestClient(create_app(paths=paths))

    response = client.get("/backtest/replay")
    assert response.status_code == 200
    assert 'href="/backtest"' in response.text


def test_backtest_main_route_still_renders_after_replay_added() -> None:
    """Adding /backtest/replay must not regress /backtest main."""
    scratch = scratch_dir("backtest_main_after_replay")
    paths = build_paths(scratch)
    client = TestClient(create_app(paths=paths))

    response = client.get("/backtest")
    assert response.status_code == 200
    assert "Backtest / Replay" in response.text  # main page title
