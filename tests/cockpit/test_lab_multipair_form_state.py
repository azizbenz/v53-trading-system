"""Tests Patch P2 (2026-05-22) — IA Lab multi-select paires.

Covers : form state pydantic backward-compat, normalization (dedup/uppercase),
filesystem-driven pair discovery wrapper, and the sync-to-backtest propagation
that picks selected_pairs over the mono `pair` fallback.
"""

from __future__ import annotations

from pathlib import Path

from cockpit import server as server_module
from cockpit.form_state_support import BacktestFormState, LabMlHandoffFormState
from cockpit.strategy_ladder_ml_handoff_support import discover_lab_pair_capabilities
from local_replay_runtime.pair_capability_discovery import PairCapability


def test_lab_form_state_backward_compat_mono_pair() -> None:
    """selected_pairs default vide → équivalent au comportement actuel mono."""
    state = LabMlHandoffFormState(pair="BTCUSDT")
    assert state.pair == "BTCUSDT"
    assert state.selected_pairs == ()


def test_lab_form_state_multi_pair_preserves_explicit_tuple() -> None:
    """Tuple multi-pair fourni explicitement est conservé tel quel."""
    state = LabMlHandoffFormState(
        pair="BTCUSDT",
        selected_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
    )
    assert state.selected_pairs == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_build_lab_handoff_form_state_normalizes_multi_select() -> None:
    """server._build_lab_ml_handoff_form_state strip/upper/dedup le multi-select."""
    built = server_module._build_lab_ml_handoff_form_state(
        kline_root="L:/klines",
        b2_run_root="",
        orderbook_root="",
        trades_root="",
        metadata_root="",
        handoff_export_dir="",
        pair="btcusdt",
        timeframe="1m",
        train_start="2025-01-01",
        train_end="2025-06-30",
        requested_backtest_start="",
        requested_backtest_days=130,
        train_days=180,
        validation_days=30,
        freshness_days=30,
        chunk_days=30,
        calibration_version="strategy_ladder_expected_edge.v1",
        feature_names="close_return,high_low_range,volume",
        sample_stride_minutes=60,
        target_horizon_minutes=1,
        training_seed=5307,
        max_optuna_trials=0,
        min_training_rows=210,
        shap_summary_ref="",
        signed_by="cockpit_operator",
        intent="launch",
        selected_pairs=["btcusdt", "  ethusdt  ", "BTCUSDT", "", "solusdt"],
    )
    # btc seen twice → dedup ; whitespace trimmed ; lowercase upper ; order preserved
    assert built.selected_pairs == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert built.pair == "BTCUSDT"


def test_build_lab_handoff_form_state_empty_multi_select_defaults_to_empty_tuple() -> None:
    """Si l'admin ne coche rien (selected_pairs=[] ou None) → tuple vide."""
    built = server_module._build_lab_ml_handoff_form_state(
        kline_root="L:/klines",
        b2_run_root="",
        orderbook_root="",
        trades_root="",
        metadata_root="",
        handoff_export_dir="",
        pair="BTCUSDT",
        timeframe="1m",
        train_start="2025-01-01",
        train_end="2025-06-30",
        requested_backtest_start="",
        requested_backtest_days=130,
        train_days=180,
        validation_days=30,
        freshness_days=30,
        chunk_days=30,
        calibration_version="strategy_ladder_expected_edge.v1",
        feature_names="close_return,high_low_range,volume",
        sample_stride_minutes=60,
        target_horizon_minutes=1,
        training_seed=5307,
        max_optuna_trials=0,
        min_training_rows=210,
        shap_summary_ref="",
        signed_by="cockpit_operator",
        intent="launch",
        selected_pairs=None,
    )
    assert built.selected_pairs == ()
    assert built.pair == "BTCUSDT"


def test_discover_lab_pair_capabilities_empty_form_state_returns_empty_tuple() -> None:
    """Aucun kline_root → discovery retourne () (template fallback mono)."""
    state = LabMlHandoffFormState()  # all defaults, no kline_root
    capabilities = discover_lab_pair_capabilities(state)
    assert capabilities == ()


def test_discover_lab_pair_capabilities_scans_filesystem(tmp_path: Path) -> None:
    """tmp filesystem avec 2 paires klines + 1 orderbook → discovery retourne 2 capabilities."""
    # Setup : klines avec BTCUSDT + ETHUSDT ; orderbook avec BTCUSDT seulement
    (tmp_path / "klines" / "BTCUSDT").mkdir(parents=True)
    (tmp_path / "klines" / "ETHUSDT").mkdir(parents=True)
    (tmp_path / "orderbook" / "BTCUSDT").mkdir(parents=True)

    state = LabMlHandoffFormState(
        kline_root=str(tmp_path / "klines"),
        orderbook_root=str(tmp_path / "orderbook"),
    )

    capabilities = discover_lab_pair_capabilities(state)

    # Sorted alphabetical (BTCUSDT before ETHUSDT)
    assert len(capabilities) == 2
    pair_names = tuple(cap.pair for cap in capabilities)
    assert pair_names == ("BTCUSDT", "ETHUSDT")

    # Capability matrix per pair
    btc_cap = next(cap for cap in capabilities if cap.pair == "BTCUSDT")
    eth_cap = next(cap for cap in capabilities if cap.pair == "ETHUSDT")

    assert isinstance(btc_cap, PairCapability)
    assert btc_cap.has_klines is True
    assert btc_cap.has_orderbook is True  # has orderbook dir
    assert eth_cap.has_klines is True
    assert eth_cap.has_orderbook is False  # no orderbook dir for ETH


def test_sync_backtest_form_uses_selected_pairs_when_present() -> None:
    """Si lab_form.selected_pairs ≥ 1 → backtest_form.pairs = selected_pairs (priority over mono pair)."""
    current = BacktestFormState()
    lab_form = LabMlHandoffFormState(
        kline_root="L:/klines",
        pair="LEGACY_MONO",
        selected_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        train_start="2025-01-01",
        train_end="2025-06-30",
    )

    synced = server_module._sync_lab_handoff_into_backtest_form(current, lab_form)

    assert synced.pairs == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    # Legacy mono `pair` is NOT used because selected_pairs has priority
    assert "LEGACY_MONO" not in synced.pairs


def test_sync_backtest_form_falls_back_to_mono_pair_when_no_selected() -> None:
    """Si selected_pairs vide → fallback à (lab_form.pair,) pour backward-compat."""
    current = BacktestFormState()
    lab_form = LabMlHandoffFormState(
        kline_root="L:/klines",
        pair="BTCUSDT",
        selected_pairs=(),  # empty multi-select
        train_start="2025-01-01",
        train_end="2025-06-30",
    )

    synced = server_module._sync_lab_handoff_into_backtest_form(current, lab_form)

    assert synced.pairs == ("BTCUSDT",)
