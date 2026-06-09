"""Phase 3 — proof that the dashboard's chunked launch builds the chunked
orchestrator command.

The /backtest "Run chunked backtest (A1->B2)" button posts to
``POST /backtest/chunked/run`` -> ``launch_backtest_job(job_kind=
STRATEGY_LADDER_CHUNKED)`` -> ``_build_backtest_command`` -> the argv below.
This test pins that the CHUNKED job_kind emits ``run_chunked_backtest.py`` with
the operator's options (not the monolithic phase CLI), so the dashboard rail is
genuinely chunked.
"""

from __future__ import annotations

from pathlib import Path

from cockpit.action_support import CockpitBacktestJobKind, _build_backtest_command


def test_chunked_job_kind_builds_run_chunked_backtest_command(tmp_path: Path) -> None:
    out = tmp_path / "runs" / "chunked-abc123"
    cmd = _build_backtest_command(
        job_id="chunked-abc123",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_CHUNKED,
        export_dir=tmp_path,
        output_root=out,
        baseline_export_dir=None,
        signed_by="cockpit_operator",
        python_executable="python",
        action_name="",
        raw_source_manifest_path=None,
        raw_roots=(Path("L:/ordrebookpart1"), Path("L:/trades")),
        pairs=("BNBUSDT", "BTCUSDT"),
        start="2025-11-16",
        end="2025-11-18",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OFF",
        engine_native_mode=True,
        engine_native_sample_size=50,
        candidate_discovery_mode="TEMPORAL_STRATIFIED",
        b1_5_policy_mode="conservative_hard_only",
        silver_storage_mode="jsonl_gz",
        backtest_timeframes=("5m", "15m"),
        historical_metadata_root=Path("K:/meta"),
    )

    # It is the chunked orchestrator, not a monolithic phase CLI.
    assert any(part.endswith("run_chunked_backtest.py") for part in cmd)
    assert not any(part.endswith("run_backtest_strategy_ladder.py") for part in cmd)

    # Operator options flow through.
    assert "--chunk" in cmd and "1d" in cmd
    assert cmd[cmd.index("--start") + 1] == "2025-11-16"
    assert cmd[cmd.index("--end") + 1] == "2025-11-18"
    assert cmd[cmd.index("--pairs") + 1] == "BNBUSDT,BTCUSDT"
    assert cmd[cmd.index("--timeframes") + 1] == "5m,15m"
    assert cmd[cmd.index("--storage-format") + 1] == "jsonl-gz"
    assert cmd[cmd.index("--engine-native-sample-size") + 1] == "50"
    assert "--max-workers" in cmd
    assert "--historical-metadata-root" in cmd

    # run-id = output_root.name so the run lands at the resolved output_root.
    assert cmd[cmd.index("--run-id") + 1] == "chunked-abc123"
    assert cmd[cmd.index("--output-root") + 1] == str(out.resolve().parent)


def test_chunked_command_includes_each_raw_root(tmp_path: Path) -> None:
    cmd = _build_backtest_command(
        job_id="chunked-xyz",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_CHUNKED,
        export_dir=tmp_path,
        output_root=tmp_path / "runs" / "chunked-xyz",
        baseline_export_dir=None,
        signed_by="cockpit_operator",
        python_executable="python",
        action_name="",
        raw_source_manifest_path=None,
        raw_roots=(Path("L:/ordrebookpart1"), Path("L:/trades"), Path("L:/klines")),
        pairs=("BTCUSDT",),
        start="2025-11-16",
        end="2025-11-16",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OFF",
        engine_native_mode=True,
        engine_native_sample_size=50,
    )
    assert cmd.count("--raw-root") == 3


def test_chunked_command_upgrades_legacy_features_to_governed(tmp_path: Path) -> None:
    """P0-1 (2026-06-08): a legacy-only / default feature selection on the chunked
    rail is upgraded to the governed microstructure set so A2 gold materializes
    vpin / cumulative_ofi / queue_pressure / kyle_lambda / realized_vol_* instead
    of silently degrading to the 3 legacy features.
    """
    cmd = _build_backtest_command(
        job_id="chunked-feat",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_CHUNKED,
        export_dir=tmp_path,
        output_root=tmp_path / "runs" / "chunked-feat",
        baseline_export_dir=None,
        signed_by="cockpit_operator",
        python_executable="python",
        action_name="",
        raw_source_manifest_path=None,
        raw_roots=(Path("L:/trades"),),
        pairs=("BTCUSDT",),
        start="2025-11-16",
        end="2025-11-16",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OFF",
        engine_native_mode=True,
        engine_native_sample_size=50,
        # feature_names_csv left at the 3-legacy default -> must upgrade.
    )
    assert "--feature-names" in cmd
    requested = cmd[cmd.index("--feature-names") + 1].split(",")
    for micro in (
        "vpin",
        "cumulative_ofi",
        "queue_pressure",
        "kyle_lambda",
        "realized_vol_current",
    ):
        assert micro in requested
    assert "close_return" in requested  # governed set is a superset of legacy


def test_chunked_command_honors_explicit_microstructure_selection(
    tmp_path: Path,
) -> None:
    """An explicit microstructure pick is passed through unchanged (no upgrade)."""
    cmd = _build_backtest_command(
        job_id="chunked-explicit",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_CHUNKED,
        export_dir=tmp_path,
        output_root=tmp_path / "runs" / "chunked-explicit",
        baseline_export_dir=None,
        signed_by="cockpit_operator",
        python_executable="python",
        action_name="",
        raw_source_manifest_path=None,
        raw_roots=(Path("L:/trades"),),
        pairs=("BTCUSDT",),
        start="2025-11-16",
        end="2025-11-16",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OFF",
        engine_native_mode=True,
        engine_native_sample_size=50,
        feature_names_csv="close_return,vpin,queue_pressure",
    )
    assert cmd[cmd.index("--feature-names") + 1] == "close_return,vpin,queue_pressure"
