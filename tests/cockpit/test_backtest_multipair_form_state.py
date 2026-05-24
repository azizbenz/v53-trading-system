"""Tests Patch P3 (2026-05-22) — Backtest UI multi-select + expected_edge_artifact_mode.

Covers : form state pydantic backward-compat for mode, multi-pair discovery
wrapper on BacktestFormState paths, and command builder propagation of
`--expected-edge-artifact-mode` to the strategy ladder runner CLI.
"""

from __future__ import annotations

from pathlib import Path

from cockpit import action_support as action_support_module
from cockpit.action_support import CockpitBacktestJobKind
from cockpit.form_state_support import BacktestFormState
from cockpit.strategy_ladder_ml_handoff_support import discover_backtest_pair_capabilities


def test_backtest_form_state_expected_edge_artifact_mode_default() -> None:
    """Default mode = MONO_PAIR_LEGACY (backward-compat with existing form state files)."""
    state = BacktestFormState()
    assert state.expected_edge_artifact_mode == "MONO_PAIR_LEGACY"


def test_backtest_form_state_expected_edge_artifact_mode_multi() -> None:
    """Mode MULTI_PAIR_C1 accepted as explicit value."""
    state = BacktestFormState(expected_edge_artifact_mode="MULTI_PAIR_C1")
    assert state.expected_edge_artifact_mode == "MULTI_PAIR_C1"


def test_backtest_form_state_mode_persists_through_model_copy() -> None:
    """model_copy on BacktestFormState preserves the mode (used by sync ops)."""
    base = BacktestFormState(expected_edge_artifact_mode="MULTI_PAIR_C1")
    copied = base.model_copy(update={"pairs": ("BTCUSDT",)})
    assert copied.expected_edge_artifact_mode == "MULTI_PAIR_C1"
    assert copied.pairs == ("BTCUSDT",)


def test_discover_backtest_pair_capabilities_empty_form_returns_empty() -> None:
    """No klines_path → no discovery (template fallback CSV input)."""
    state = BacktestFormState()
    capabilities = discover_backtest_pair_capabilities(state)
    assert capabilities == ()


def test_discover_backtest_pair_capabilities_scans_paths(tmp_path: Path) -> None:
    """tmp filesystem with klines+trades+orderbook for 2 pairs → discovery returns capabilities."""
    (tmp_path / "klines" / "BTCUSDT").mkdir(parents=True)
    (tmp_path / "klines" / "ETHUSDT").mkdir(parents=True)
    (tmp_path / "trades" / "BTCUSDT").mkdir(parents=True)
    (tmp_path / "orderbook" / "BTCUSDT").mkdir(parents=True)

    state = BacktestFormState(
        klines_path=str(tmp_path / "klines"),
        trades_path=str(tmp_path / "trades"),
        orderbook_path=str(tmp_path / "orderbook"),
    )
    capabilities = discover_backtest_pair_capabilities(state)

    assert len(capabilities) == 2
    pair_names = tuple(cap.pair for cap in capabilities)
    assert pair_names == ("BTCUSDT", "ETHUSDT")

    btc = next(cap for cap in capabilities if cap.pair == "BTCUSDT")
    eth = next(cap for cap in capabilities if cap.pair == "ETHUSDT")
    assert btc.has_klines is True
    assert btc.has_trades is True
    assert btc.has_orderbook is True
    assert btc.microstructure_capable is True  # all 3 present
    # ETH has klines but no trades or orderbook in the fake fs
    assert eth.has_klines is True
    assert eth.has_trades is False
    assert eth.has_orderbook is False
    assert eth.microstructure_capable is False


def test_build_backtest_command_emits_expected_edge_artifact_mode_default(tmp_path: Path) -> None:
    """STRATEGY_LADDER_RUNNER + ML_MODE_OVERLAY_FROZEN → `--expected-edge-artifact-mode MONO_PAIR_LEGACY` (default)."""
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text("{}", encoding="utf-8")
    command = action_support_module._build_backtest_command(
        job_id="job-x",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
        export_dir=tmp_path / "export",
        output_root=tmp_path / "out",
        baseline_export_dir=None,
        signed_by="tester",
        python_executable="python",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        raw_source_manifest_path=None,
        raw_roots=(),
        pairs=("BTCUSDT",),
        start="2025-01-01",
        end="2025-01-31",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OVERLAY_FROZEN",
        frozen_ml_artifact_path=artifact_path,
        frozen_ml_artifact_hash="a" * 64,
        rolling_ml_window_plan_path=None,
        ml_artifact_freshness_days=30,
        engine_native_mode=True,
        engine_native_sample_size=10,
    )
    assert "--expected-edge-artifact-mode" in command
    idx = command.index("--expected-edge-artifact-mode")
    assert command[idx + 1] == "MONO_PAIR_LEGACY"


def test_build_backtest_command_propagates_multi_pair_c1_mode(tmp_path: Path) -> None:
    """STRATEGY_LADDER_RUNNER + ML_MODE_OVERLAY_FROZEN + MULTI_PAIR_C1 → mode propagé."""
    artifact_path = tmp_path / "multipair_manifest.json"
    artifact_path.write_text("{}", encoding="utf-8")
    command = action_support_module._build_backtest_command(
        job_id="job-y",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
        export_dir=tmp_path / "export",
        output_root=tmp_path / "out",
        baseline_export_dir=None,
        signed_by="tester",
        python_executable="python",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        raw_source_manifest_path=None,
        raw_roots=(),
        pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        start="2025-01-01",
        end="2025-01-31",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OVERLAY_FROZEN",
        frozen_ml_artifact_path=artifact_path,
        frozen_ml_artifact_hash="b" * 64,
        expected_edge_artifact_mode="MULTI_PAIR_C1",
        rolling_ml_window_plan_path=None,
        ml_artifact_freshness_days=30,
        engine_native_mode=True,
        engine_native_sample_size=10,
    )
    assert "--expected-edge-artifact-mode" in command
    idx = command.index("--expected-edge-artifact-mode")
    assert command[idx + 1] == "MULTI_PAIR_C1"
    # And the multi-pair tuple is propagated as CSV
    assert "--pairs" in command
    pairs_idx = command.index("--pairs")
    assert command[pairs_idx + 1] == "BTCUSDT,ETHUSDT,SOLUSDT"


def test_build_backtest_command_propagates_replay_timeframes(tmp_path: Path) -> None:
    """Backtest multiframe scope is passed to B1/B2 runner only."""
    command = action_support_module._build_backtest_command(
        job_id="job-tf",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
        export_dir=tmp_path / "export",
        output_root=tmp_path / "out",
        baseline_export_dir=None,
        signed_by="tester",
        python_executable="python",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        raw_source_manifest_path=None,
        raw_roots=(),
        pairs=("BTCUSDT",),
        start="2025-04-29",
        end="2025-05-01",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OFF",
        engine_native_mode=True,
        engine_native_sample_size=10,
        backtest_timeframes=("5m", "15m"),
    )
    assert "--timeframes" in command
    idx = command.index("--timeframes")
    assert command[idx + 1] == "5m,15m"
