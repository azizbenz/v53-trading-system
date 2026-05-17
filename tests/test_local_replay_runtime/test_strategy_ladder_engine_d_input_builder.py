"""Tests pour strategy_ladder_engine_d_input_builder (Audit 2026-05-07).

Doctrine engine_d (spec doc 22) : re-entry / second chance.
- Engine D depend d'un first_episode_ref (trade A ou C clos sur meme pair/dir)
- Sans first_episode_ref → HARD_BLOCK avec d.no_first_episode (HISTORY_WEAK)
- Avec first_episode_ref → evaluation reformation + marginal value + cost
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from engines.engine_d.engine_d_models import EngineDInput
from engines.engine_d.engine_d_runner import run_engine_d
from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
    EngineDInputBuilderResult,
    EngineDStructureSummary,
    build_engine_d_input_from_window,
    derive_engine_d_structure_summary,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _bar(*, ts_ms: int, o: float, h: float, l: float, c: float, v: float = 10.0) -> dict[str, object]:
    return {
        "timestamp_ms": ts_ms,
        "pair": "TESTPAIR",
        "timeframe": "5m",
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def _trade(*, ts_ms: int, price: float, qty: float = 1.0, side: str = "buy") -> dict[str, object]:
    return {
        "timestamp_ms": ts_ms,
        "pair": "TESTPAIR",
        "trade_id": str(ts_ms),
        "price": str(price),
        "qty": str(qty),
        "side": side,
    }


def _build_synthetic_dataset_with_pullback(
    tmp_path: Path,
    *,
    base_ts_ms: int,
    n_lookback: int = 12,
    n_in_window: int = 6,
) -> tuple[Path, Path, int, int]:
    """Dataset avec un pullback recent : le prix est monte, puis a retracé.

    Sans first_episode_context, engine_d refusera quand meme (HISTORY_WEAK).
    Le but est de tester que reformation_quality, pullback_quality, etc.
    sont calcules correctement.
    """
    bars: list[dict[str, object]] = []
    for i in range(n_lookback):
        ts = base_ts_ms - (n_lookback - i) * 300_000
        # Phase 1 : montee
        base_price = 100.0 + i * 0.3
        bars.append(_bar(ts_ms=ts, o=base_price, h=base_price + 0.2, l=base_price - 0.05, c=base_price + 0.15))
    # In-window : pullback
    for i in range(n_in_window):
        ts = base_ts_ms + i * 300_000
        # Pullback de ~50% du move precedent
        base_price = 103.6 - i * 0.15
        bars.append(_bar(ts_ms=ts, o=base_price, h=base_price + 0.05, l=base_price - 0.2, c=base_price - 0.10))
    ohlcv_path = tmp_path / "ohlcv_5m.jsonl"
    _write_jsonl(ohlcv_path, bars)

    # Trades
    trades: list[dict[str, object]] = []
    total_dur = (n_lookback + n_in_window) * 300_000
    start_ts = base_ts_ms - n_lookback * 300_000
    for i in range(200):
        ts = start_ts + (i * total_dur) // 200
        if ts < base_ts_ms:
            price = 100.0 + ((ts - start_ts) / total_dur) * 4.0
        else:
            price = 103.6 - ((ts - base_ts_ms) / total_dur) * 1.0
        trades.append(_trade(ts_ms=ts, price=price))
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, trades)
    return ohlcv_path, trade_path, base_ts_ms, base_ts_ms + n_in_window * 300_000


def test_derive_summary_no_first_episode_context() -> None:
    """Sans first_episode_context, prior_trade_quality=0, reentry_lateness=1.

    C'est le comportement attendu en backtest sans trades executes prealables.
    """
    bars = [_bar(ts_ms=1_700_000_000_000 + i * 300_000, o=100.0, h=100.5, l=99.5, c=100.2) for i in range(10)]
    summary = derive_engine_d_structure_summary(
        bars_full=bars,
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 10 * 300_000,
        has_first_episode_context=False,
    )
    assert summary.prior_trade_quality == 0.0
    assert summary.reentry_lateness == 1.0
    # concentration_headroom default 1.0 (pas de concentration en backtest)
    assert summary.concentration_headroom == 1.0


def test_derive_summary_with_first_episode_context() -> None:
    """Avec first_episode_context, prior_trade_quality default 0.5, reentry_lateness 0.5."""
    bars = [_bar(ts_ms=1_700_000_000_000 + i * 300_000, o=100.0, h=100.5, l=99.5, c=100.2) for i in range(10)]
    summary = derive_engine_d_structure_summary(
        bars_full=bars,
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 10 * 300_000,
        has_first_episode_context=True,
    )
    assert summary.prior_trade_quality == 0.5
    assert summary.reentry_lateness == 0.5
    assert summary.has_first_episode_context is True


def test_derive_summary_overrides_apply() -> None:
    """Les overrides du caller doivent etre respectes."""
    bars = [_bar(ts_ms=1_700_000_000_000 + i * 300_000, o=100.0, h=100.5, l=99.5, c=100.2) for i in range(10)]
    summary = derive_engine_d_structure_summary(
        bars_full=bars,
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 10 * 300_000,
        has_first_episode_context=True,
        prior_trade_quality_override=0.85,
        concentration_headroom_override=0.40,
        reentry_lateness_override=0.20,
    )
    assert summary.prior_trade_quality == 0.85
    assert summary.concentration_headroom == 0.40
    assert summary.reentry_lateness == 0.20


def test_build_engine_d_input_no_first_episode_blocks_history_weak(
    tmp_path: Path,
) -> None:
    """Sans first_episode_context, run_engine_d() doit refuser avec HISTORY_WEAK
    (doctrine respectee : D ne peut pas firer sans first_episode_ref)."""
    ohlcv_path, trade_path, ws, we = _build_synthetic_dataset_with_pullback(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    result = build_engine_d_input_from_window(
        candidate_id="d-no-fe",
        pair="TESTPAIR",
        window_start_ms=ws,
        window_end_ms=we,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
        candidate_size=50.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    assert result.engine_d_input_provenance == "BUILDER_NO_FIRST_EPISODE_DEFAULTS"
    inp = EngineDInput.model_validate(result.engine_d_input_payload)
    assert inp.prior_trade_quality == 0.0
    out = run_engine_d(inp)
    assert out.decision == "no_trade"
    reason_codes = " ".join(
        r.value if hasattr(r, "value") else str(r) for r in out.no_trade_reasons
    )
    assert "history_weak" in reason_codes, (
        f"HISTORY_WEAK attendu sans first_episode; got reasons={out.no_trade_reasons}"
    )


def test_build_engine_d_input_with_first_episode_changes_provenance(
    tmp_path: Path,
) -> None:
    """Avec first_episode_context, la provenance bascule vers WITH_FIRST_EPISODE."""
    ohlcv_path, trade_path, ws, we = _build_synthetic_dataset_with_pullback(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    result = build_engine_d_input_from_window(
        candidate_id="d-with-fe",
        pair="TESTPAIR",
        window_start_ms=ws,
        window_end_ms=we,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
        first_episode_context={
            "origin_context_id": "ctx-001",
            "first_episode_id": "ep-A-001",
            "first_episode_engine_id": "engine_a",
            "prior_trade_quality": 0.75,
        },
        candidate_size=50.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    assert (
        result.engine_d_input_provenance
        == "BUILDER_WITH_FIRST_EPISODE_HEURISTIC_TO_CALIBRATE"
    )
    inp = EngineDInput.model_validate(result.engine_d_input_payload)
    assert inp.first_episode_id == "ep-A-001"
    assert inp.first_episode_engine_id == "engine_a"
    assert inp.prior_trade_quality == 0.75
    out = run_engine_d(inp)
    assert out.engine_id == "engine_d"
    assert out.decision in {"emit", "no_trade"}


def test_build_engine_d_input_handles_missing_ohlcv(tmp_path: Path) -> None:
    """Sans OHLCV, le builder retourne FAILED."""
    result = build_engine_d_input_from_window(
        candidate_id="d-no-ohlcv",
        pair="TESTPAIR",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 60_000,
        raw_trade_path=None,
        raw_ohlcv_path=None,
    )
    assert result.builder_status == "ENGINE_D_INPUT_BUILDER_FAILED_NO_OHLCV"
    assert "OHLCV_PATH_MISSING" in result.builder_warnings


def test_build_engine_d_input_pydantic_validatable(tmp_path: Path) -> None:
    """Le payload doit etre EngineDInput.model_validate-compatible."""
    ohlcv_path, trade_path, ws, we = _build_synthetic_dataset_with_pullback(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    result = build_engine_d_input_from_window(
        candidate_id="d-pyd",
        pair="TESTPAIR",
        window_start_ms=ws,
        window_end_ms=we,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
    )
    inp = EngineDInput.model_validate(result.engine_d_input_payload)
    assert inp.pair == "TESTPAIR"
    # Structure_reformed_detected default True
    assert inp.structure_reformed_detected is True


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_d_input_builder_real_run_dossier_chains_to_run_engine_d() -> None:
    """Test integration sur run dossier reel : run_engine_d() invoque, refuse
    proprement avec HISTORY_WEAK (pas de first_episode dans le backtest)."""
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    result = build_engine_d_input_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        raw_ohlcv_path=manifest["raw_ohlcv_path"],
        candidate_size=50.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    inp = EngineDInput.model_validate(result.engine_d_input_payload)
    assert inp.pair == "BNBUSDT"
    out = run_engine_d(inp)
    assert out.engine_id == "engine_d"
    assert out.decision == "no_trade"
    # En backtest sans trades executes, no_first_episode → HISTORY_WEAK
    reason_codes = " ".join(
        r.value if hasattr(r, "value") else str(r) for r in out.no_trade_reasons
    )
    assert "history_weak" in reason_codes
