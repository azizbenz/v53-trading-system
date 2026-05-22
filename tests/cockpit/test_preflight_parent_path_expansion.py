"""Tests Patch P4b (2026-05-22) — preflight exposes parent_path_expansion via VM.

Verifies that `build_patch6_preflight_preview` calls `expand_parent_path_to_pair_paths`
and surfaces the per-source-kind sub-path resolution in the preflight VM.
"""

from __future__ import annotations

from pathlib import Path

from cockpit.backtest_preflight import build_patch6_preflight_preview
from cockpit.form_state_support import BacktestFormState


def _make_form(tmp_path: Path, *, orderbook_path: str, pairs: tuple[str, ...]) -> BacktestFormState:
    """Minimal valid BacktestFormState with explicit orderbook path + pair tuple."""
    export_dir = tmp_path / "export"
    export_dir.mkdir(exist_ok=True)
    return BacktestFormState(
        job_kind="strategy_ladder_data_factory",
        action_name="PHASE_A2_DATA_FACTORY",
        phase_id="PHASE_A2",
        workflow_phase="PHASE_A2",
        export_dir=str(export_dir),
        orderbook_path=orderbook_path,
        pairs=pairs,
        start="2025-01-01",
        end="2025-01-31",
    )


def test_preflight_parent_path_expansion_empty_for_mono_pair_dir(tmp_path: Path) -> None:
    """If admin points at a pair-dir directly → no expansion surfaced (single path)."""
    (tmp_path / "orderbook" / "BTCUSDT").mkdir(parents=True)

    form = _make_form(
        tmp_path,
        orderbook_path=str(tmp_path / "orderbook" / "BTCUSDT"),
        pairs=("BTCUSDT",),
    )
    preflight = build_patch6_preflight_preview(selected_form=form, jobs_root=None)

    # Mono pair-dir → no entry (we only surface multi-path expansion)
    assert "orderbook" not in preflight.parent_path_expansion


def test_preflight_parent_path_expansion_populated_for_parent_dir_multi(tmp_path: Path) -> None:
    """If admin points at parent + ≥2 pairs requested → expansion surfaced per source."""
    parent = tmp_path / "orderbook_root"
    (parent / "BTCUSDT").mkdir(parents=True)
    (parent / "ETHUSDT").mkdir(parents=True)
    (parent / "SOLUSDT").mkdir(parents=True)

    form = _make_form(
        tmp_path,
        orderbook_path=str(parent),
        pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
    )
    preflight = build_patch6_preflight_preview(selected_form=form, jobs_root=None)

    assert "orderbook" in preflight.parent_path_expansion
    expanded = preflight.parent_path_expansion["orderbook"]
    assert len(expanded) == 3
    assert any("BTCUSDT" in path for path in expanded)
    assert any("ETHUSDT" in path for path in expanded)
    assert any("SOLUSDT" in path for path in expanded)


def test_preflight_parent_path_expansion_filtered_by_requested_pairs(tmp_path: Path) -> None:
    """Parent dir with 3 pair subdirs but admin only requests 2 → only 2 expanded."""
    parent = tmp_path / "ob_root"
    (parent / "BTCUSDT").mkdir(parents=True)
    (parent / "ETHUSDT").mkdir(parents=True)
    (parent / "SOLUSDT").mkdir(parents=True)

    form = _make_form(
        tmp_path,
        orderbook_path=str(parent),
        pairs=("BTCUSDT", "ETHUSDT"),  # SOL not requested
    )
    preflight = build_patch6_preflight_preview(selected_form=form, jobs_root=None)

    expanded = preflight.parent_path_expansion.get("orderbook", ())
    assert len(expanded) == 2
    assert any("BTCUSDT" in path for path in expanded)
    assert any("ETHUSDT" in path for path in expanded)
    assert not any("SOLUSDT" in path for path in expanded)


def test_preflight_parent_path_expansion_empty_when_no_pairs_requested(tmp_path: Path) -> None:
    """If admin doesn't request pairs → no expansion (filter requires pair_universe)."""
    parent = tmp_path / "ob_root"
    (parent / "BTCUSDT").mkdir(parents=True)
    (parent / "ETHUSDT").mkdir(parents=True)

    form = _make_form(
        tmp_path,
        orderbook_path=str(parent),
        pairs=(),  # no pairs requested
    )
    preflight = build_patch6_preflight_preview(selected_form=form, jobs_root=None)

    # No requested pairs → expansion not computed
    assert preflight.parent_path_expansion == {}
