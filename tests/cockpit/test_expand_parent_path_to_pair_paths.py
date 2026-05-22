"""Tests Patch P4 (2026-05-22) — pattern parent + scan helper for multi-pair backtest.

Covers the `expand_parent_path_to_pair_paths` helper that lets the admin point
at a parent directory (e.g. `L:\\ordre book part 1`) and resolves it to one
Path per selected pair via filesystem scan.
"""

from __future__ import annotations

from pathlib import Path

from cockpit.backtest_preflight import expand_parent_path_to_pair_paths


def test_expand_empty_raw_path_returns_empty_tuple() -> None:
    """Empty input → empty tuple (no exception)."""
    assert expand_parent_path_to_pair_paths("") == ()
    assert expand_parent_path_to_pair_paths("   ") == ()


def test_expand_nonexistent_path_returns_empty_tuple(tmp_path: Path) -> None:
    """Path that does not exist → empty tuple."""
    missing = tmp_path / "does_not_exist"
    assert expand_parent_path_to_pair_paths(str(missing)) == ()


def test_expand_pair_dir_preserves_mono_behaviour(tmp_path: Path) -> None:
    """If raw_path is already a pair dir → returns (Path(raw_path),) unchanged."""
    pair_dir = tmp_path / "BTCUSDT"
    pair_dir.mkdir()
    result = expand_parent_path_to_pair_paths(str(pair_dir))
    assert result == (pair_dir,)


def test_expand_parent_dir_with_pair_universe_filter(tmp_path: Path) -> None:
    """Parent dir + pair_universe filter → resolves to only the requested pairs."""
    (tmp_path / "BTCUSDT").mkdir()
    (tmp_path / "ETHUSDT").mkdir()
    (tmp_path / "SOLUSDT").mkdir()
    (tmp_path / "not_a_pair_dir").mkdir()  # ignored (doesn't look like pair)

    result = expand_parent_path_to_pair_paths(
        str(tmp_path),
        pair_universe=("BTCUSDT", "ETHUSDT"),
    )

    assert len(result) == 2
    assert tmp_path / "BTCUSDT" in result
    assert tmp_path / "ETHUSDT" in result
    assert tmp_path / "SOLUSDT" not in result


def test_expand_parent_dir_without_filter_returns_all_pair_subdirs(tmp_path: Path) -> None:
    """Parent dir + empty pair_universe → returns ALL pair-like subdirs sorted."""
    (tmp_path / "BTCUSDT").mkdir()
    (tmp_path / "ETHUSDT").mkdir()
    (tmp_path / "SOLUSDT").mkdir()
    (tmp_path / "not_a_pair").mkdir()  # ignored

    result = expand_parent_path_to_pair_paths(str(tmp_path))

    # Sorted alphabetical
    assert len(result) == 3
    assert result[0] == tmp_path / "BTCUSDT"
    assert result[1] == tmp_path / "ETHUSDT"
    assert result[2] == tmp_path / "SOLUSDT"


def test_expand_parent_dir_filter_ignores_missing_pairs(tmp_path: Path) -> None:
    """If admin asks for paire not on filesystem → silently skipped (no exception)."""
    (tmp_path / "BTCUSDT").mkdir()

    result = expand_parent_path_to_pair_paths(
        str(tmp_path),
        pair_universe=("BTCUSDT", "FUTURE_PAIR_NOT_ON_DISK"),
    )

    assert len(result) == 1
    assert result[0] == tmp_path / "BTCUSDT"


def test_expand_parent_dir_with_arbitrary_pair_names(tmp_path: Path) -> None:
    """ZERO hardcoded pair names — works with arbitrary symbols (MMXX, FUTURE_42)."""
    (tmp_path / "MMXXUSDT").mkdir()
    (tmp_path / "FUTUREUSDC").mkdir()

    result = expand_parent_path_to_pair_paths(
        str(tmp_path),
        pair_universe=("MMXXUSDT", "FUTUREUSDC"),
    )

    assert len(result) == 2
    assert tmp_path / "MMXXUSDT" in result
    assert tmp_path / "FUTUREUSDC" in result


def test_expand_parent_dir_preserves_pair_universe_order(tmp_path: Path) -> None:
    """Result order follows pair_universe order (deterministic for admin UX)."""
    (tmp_path / "BTCUSDT").mkdir()
    (tmp_path / "ETHUSDT").mkdir()
    (tmp_path / "SOLUSDT").mkdir()

    result = expand_parent_path_to_pair_paths(
        str(tmp_path),
        pair_universe=("SOLUSDT", "BTCUSDT", "ETHUSDT"),
    )

    # Order should match pair_universe, not alphabetical
    assert result[0] == tmp_path / "SOLUSDT"
    assert result[1] == tmp_path / "BTCUSDT"
    assert result[2] == tmp_path / "ETHUSDT"
