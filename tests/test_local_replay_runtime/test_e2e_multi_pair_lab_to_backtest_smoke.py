"""E2E smoke test (2026-05-22) — Lab multi-select → Backtest sync → CLI → C1 manifest → P1 provider.

Verifies that the patches P1+P2+P3+P4+P4b+P2b chain together coherently end-to-end :

  [Lab UI selects 3 pairs]
       ↓ LabMlHandoffFormState.selected_pairs
  [sync to backtest form]
       ↓ BacktestFormState.pairs + expected_edge_artifact_mode=MULTI_PAIR_C1
  [cockpit command builder]
       ↓ CLI : --pairs BTC,ETH,SOL --expected-edge-artifact-mode MULTI_PAIR_C1
  [handoff writer P2b]
       ↓ MULTI_PAIR_C1_EXPECTED_EDGE manifest JSON
  [P1 provider load mode=MULTI_PAIR_C1]
       ↓ StrategyLadderMultiPairC1Manifest validated
  ✅ chain green
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cockpit import server as server_module
from cockpit.action_support import (
    CockpitBacktestJobKind,
    _build_backtest_command,
)
from cockpit.form_state_support import BacktestFormState, LabMlHandoffFormState
from local_replay_runtime.strategy_ladder_edge_model_provider import (
    EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    load_governed_expected_edge_model_artifact,
)
from local_replay_runtime.strategy_ladder_edge_model_provider_multi_pair import (
    StrategyLadderMultiPairC1Manifest,
)
from local_replay_runtime.strategy_ladder_multi_pair_handoff_writer import (
    maybe_emit_multi_pair_c1_handoff_manifest,
)


def test_e2e_chain_lab_to_backtest_to_cli_to_manifest_to_provider(tmp_path: Path) -> None:
    """End-to-end chain : 3 pairs admin choice → CLI command → C1 manifest → P1 validate."""

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1 : Lab UI form state with admin multi-select (3 pairs)
    # ─────────────────────────────────────────────────────────────────────────
    lab_form = LabMlHandoffFormState(
        kline_root=str(tmp_path / "klines"),
        pair="LEGACY_FALLBACK",  # ignored when selected_pairs ≥ 1
        selected_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    assert lab_form.selected_pairs == ("BTCUSDT", "ETHUSDT", "SOLUSDT")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2 : sync vers Backtest form — multi-pair must take priority
    # ─────────────────────────────────────────────────────────────────────────
    current_backtest_form = BacktestFormState(
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    )
    synced = server_module._sync_lab_handoff_into_backtest_form(
        current_backtest_form, lab_form
    )
    assert synced.pairs == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert "LEGACY_FALLBACK" not in synced.pairs
    assert synced.expected_edge_artifact_mode == EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3 : cockpit command builder emits CLI with multi-pair + C1 mode
    # ─────────────────────────────────────────────────────────────────────────
    fake_artifact = tmp_path / "frozen_artifact.json"
    fake_artifact.write_text("{}", encoding="utf-8")
    command = _build_backtest_command(
        job_id="e2e-smoke-job",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
        export_dir=tmp_path / "export",
        output_root=tmp_path / "out",
        baseline_export_dir=None,
        signed_by="e2e-tester",
        python_executable="python",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        raw_source_manifest_path=None,
        raw_roots=(),
        pairs=synced.pairs,
        start="2025-01-01",
        end="2025-01-31",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OVERLAY_FROZEN",
        frozen_ml_artifact_path=fake_artifact,
        frozen_ml_artifact_hash="a" * 64,
        expected_edge_artifact_mode=synced.expected_edge_artifact_mode,
        rolling_ml_window_plan_path=None,
        ml_artifact_freshness_days=30,
        engine_native_mode=True,
        engine_native_sample_size=10,
    )

    assert "--pairs" in command
    pairs_idx = command.index("--pairs")
    assert command[pairs_idx + 1] == "BTCUSDT,ETHUSDT,SOLUSDT"

    assert "--expected-edge-artifact-mode" in command
    mode_idx = command.index("--expected-edge-artifact-mode")
    assert command[mode_idx + 1] == "MULTI_PAIR_C1"

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4 : P2b writer emits the MULTI_PAIR_C1_EXPECTED_EDGE manifest
    # ─────────────────────────────────────────────────────────────────────────
    handoff_export = tmp_path / "handoff_export"
    handoff_export.mkdir()
    # Fake "lgb file" — for this smoke test we only verify the manifest, not load
    fake_lgb_path = handoff_export / "stub_mono_artifact.lgb"
    fake_lgb_path.write_text("FAKE_LIGHTGBM_PLACEHOLDER", encoding="utf-8")

    manifest_path = maybe_emit_multi_pair_c1_handoff_manifest(
        selected_pairs=synced.pairs,
        artifact_id="e2e_multipair_v1_1m",
        calibration_version="v1",
        timeframe="1m",
        feature_names=("close_return", "high_low_range", "volume"),
        model_path_ref=str(fake_lgb_path),
        train_start="2025-01-01",
        train_end="2025-06-30",
        export_dir=handoff_export,
    )
    assert manifest_path is not None
    assert manifest_path.is_file()

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5 : P1 provider validates the manifest via pydantic round-trip
    # ─────────────────────────────────────────────────────────────────────────
    raw_payload = manifest_path.read_text(encoding="utf-8")
    validated = StrategyLadderMultiPairC1Manifest.model_validate_json(raw_payload)
    assert validated.pair_id_encoding == {"BTCUSDT": 0, "ETHUSDT": 1, "SOLUSDT": 2}
    assert "pair_id" in validated.feature_names
    assert validated.timeframe == "1m"

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6 : P1 loader attempts MULTI_PAIR_C1 mode — booster load fails because
    #          fake_lgb is not a real LightGBM file, but the manifest parsing is
    #          confirmed successful (status starts with GOVERNED_EDGE_MODEL_LOAD_FAILED).
    # ─────────────────────────────────────────────────────────────────────────
    result = load_governed_expected_edge_model_artifact(
        manifest_path,
        expected_artifact_hash=validated.artifact_hash,
        expected_edge_artifact_mode=EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1,
    )
    # Manifest itself was valid (no MODE_MISMATCH, no INVALID_ARTIFACT)
    assert "MODE_MISMATCH" not in result.status
    assert "INVALID_ARTIFACT" not in result.status
    # Booster load failed (fake file is not LightGBM) — exact error code OK
    assert result.status.startswith("GOVERNED_EDGE_MODEL_LOAD_FAILED")
    assert result.artifact_hash == validated.artifact_hash


def test_e2e_chain_mono_pair_stays_legacy(tmp_path: Path) -> None:
    """Mono-pair admin choice → sync uses (pair,) and MONO_PAIR_LEGACY mode passes through."""
    lab_form = LabMlHandoffFormState(
        kline_root=str(tmp_path / "klines"),
        pair="BTCUSDT",
        selected_pairs=(),  # explicit mono path
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    current = BacktestFormState()  # default MONO_PAIR_LEGACY mode
    synced = server_module._sync_lab_handoff_into_backtest_form(current, lab_form)
    assert synced.pairs == ("BTCUSDT",)
    assert synced.expected_edge_artifact_mode == "MONO_PAIR_LEGACY"

    # P2b writer does NOT emit a manifest for mono-pair
    handoff_export = tmp_path / "handoff_export_mono"
    handoff_export.mkdir()
    result = maybe_emit_multi_pair_c1_handoff_manifest(
        selected_pairs=synced.pairs,
        artifact_id="mono_v1_1m",
        calibration_version="v1",
        timeframe="1m",
        feature_names=("close_return",),
        model_path_ref="x.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
        export_dir=handoff_export,
    )
    assert result is None
