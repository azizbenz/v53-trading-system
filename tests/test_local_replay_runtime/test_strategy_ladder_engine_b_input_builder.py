"""Tests pour strategy_ladder_engine_b_input_builder (Audit 2026-05-07).

Prouve que le builder construit un EngineBInput.model_validate-compatible
depuis raw_window trades et que run_engine_b() peut etre invoque.

Doctrine engine_b : mean reversion (cote LONG seulement, z_score < 0).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from engines.engine_b.engine_b_runner import EngineBInput, run_engine_b
from local_replay_runtime.strategy_ladder_engine_b_input_builder import (
    EngineBInputBuilderResult,
    build_engine_b_input_from_window,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _trade(*, ts_ms: int, price: float, qty: float = 1.0, side: str = "buy") -> dict[str, object]:
    return {
        "timestamp_ms": ts_ms,
        "pair": "TESTPAIR",
        "trade_id": str(ts_ms),
        "price": str(price),
        "qty": str(qty),
        "side": side,
    }


def test_build_engine_b_input_with_z_negative_long_signal(tmp_path: Path) -> None:
    """Trades avec dernier prix sous le mean → z_score < 0 → signal long valide.

    Doctrine engine_b : long si z_score < 0 (prix sous mean local).
    """
    base_ts = 1_700_000_000_000
    trades: list[dict[str, object]] = []
    # 100 trades autour de 100.0, puis le dernier descend a 99.0
    for i in range(99):
        trades.append(_trade(ts_ms=base_ts + i * 600, price=100.0 + (i % 5) * 0.05))
    trades.append(_trade(ts_ms=base_ts + 99 * 600, price=99.0))  # last << mean

    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, trades)

    result = build_engine_b_input_from_window(
        candidate_id="b-z-neg",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
        candidate_size=100.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )

    assert isinstance(result, EngineBInputBuilderResult)
    assert result.builder_status == "ENGINE_B_INPUT_BUILDER_READY"
    assert (
        result.engine_b_input_provenance == "BUILDER_FROM_BRIDGE_HEURISTIC_TO_CALIBRATE"
    )

    inp = EngineBInput.model_validate(result.engine_b_input_payload)
    assert inp.current_price == 99.0
    z_score = (inp.current_price - inp.local_mean) / inp.local_std
    assert z_score < 0, f"current_price < local_mean expected → z<0; got {z_score}"

    out = run_engine_b(inp)
    # Avec z_score < 0, engine_b ne peut plus etre bloque par NON_LONG_DIRECTION
    # (mais peut bloquer ailleurs : breakout, excess, dispersion etc.)
    assert out.engine_id == "engine_b"
    assert out.decision in {"emit", "no_trade"}


def test_build_engine_b_input_with_z_positive_blocks_non_long(tmp_path: Path) -> None:
    """Trades avec dernier prix au-dessus du mean → z_score > 0 →
    engine_b doit refuser avec NON_LONG_DIRECTION."""
    base_ts = 1_700_000_000_000
    trades: list[dict[str, object]] = []
    for i in range(99):
        trades.append(_trade(ts_ms=base_ts + i * 600, price=100.0 + (i % 5) * 0.05))
    trades.append(_trade(ts_ms=base_ts + 99 * 600, price=101.5))  # last >> mean

    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, trades)

    result = build_engine_b_input_from_window(
        candidate_id="b-z-pos",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
        candidate_size=100.0,
    )

    inp = EngineBInput.model_validate(result.engine_b_input_payload)
    z_score = (inp.current_price - inp.local_mean) / inp.local_std
    assert z_score > 0, f"current_price > local_mean expected; got z={z_score}"

    out = run_engine_b(inp)
    assert out.decision == "no_trade"
    # NON_LONG_DIRECTION attendu (doctrine engine_b)
    reason_codes_str = " ".join(r.value if hasattr(r, "value") else str(r) for r in out.no_trade_reasons)
    assert "non_long_direction" in reason_codes_str, (
        f"NON_LONG_DIRECTION attendu vu z_score>0; got reasons={out.no_trade_reasons}"
    )


def test_build_engine_b_input_handles_insufficient_trades(tmp_path: Path) -> None:
    """Avec 0 ou 1 trade, le builder retourne FAILED_BRIDGE."""
    base_ts = 1_700_000_000_000
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, [_trade(ts_ms=base_ts + 1000, price=100.0)])

    result = build_engine_b_input_from_window(
        candidate_id="b-empty",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
    )

    assert result.builder_status == "ENGINE_B_INPUT_BUILDER_FAILED_BRIDGE"
    assert any(
        w.startswith("BRIDGE_INSUFFICIENT_REQUIRED")
        for w in result.builder_warnings
    )


def test_build_engine_b_input_handles_missing_trade_path() -> None:
    """Sans trade path, le builder retourne FAILED."""
    result = build_engine_b_input_from_window(
        candidate_id="b-no-path",
        pair="TESTPAIR",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 60_000,
        raw_trade_path=None,
    )
    assert result.builder_status == "ENGINE_B_INPUT_BUILDER_FAILED_BRIDGE"


def test_build_engine_b_input_caller_can_override_payload(tmp_path: Path) -> None:
    """Le caller peut forcer des champs via base_payload (ex: regime, scoring_version)."""
    base_ts = 1_700_000_000_000
    trades = [_trade(ts_ms=base_ts + i * 600, price=100.0 + (i % 5) * 0.05) for i in range(50)]
    trades.append(_trade(ts_ms=base_ts + 50 * 600, price=99.5))
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, trades)

    result = build_engine_b_input_from_window(
        candidate_id="b-override",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
        base_payload={"regime": "range", "regime_favorability": 0.85},
    )
    payload = result.engine_b_input_payload
    assert payload["regime"] == "range"
    assert payload["regime_favorability"] == 0.85
    EngineBInput.model_validate(payload)


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_b_input_builder_real_run_dossier_chains_to_run_engine_b() -> None:
    """Test integration sur run dossier reel : run_engine_b() invoque."""
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    result = build_engine_b_input_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        candidate_size=100.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    assert result.builder_status == "ENGINE_B_INPUT_BUILDER_READY"
    assert result.bridge_result is not None
    assert result.bridge_result.current_price is not None
    assert result.bridge_result.current_price > 0.0

    inp = EngineBInput.model_validate(result.engine_b_input_payload)
    assert inp.pair == "BNBUSDT"
    out = run_engine_b(inp)
    assert out.engine_id == "engine_b"
    assert out.decision in {"emit", "no_trade"}
