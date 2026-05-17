"""Tests pour strategy_ladder_engine_c_input_builder (Audit 2026-05-07 P3a-fix).

Ces tests prouvent que le builder construit un EngineCInput.model_validate-
compatible depuis raw_window selon la spec doc 21 §3 Stage 1, et que
run_engine_c() peut etre invoque sur le payload.

Tests d'integration sur le run dossier reel sont opt-in via env var
STRATEGY_LADDER_REAL_RUN_DOSSIER.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from engines.engine_c.engine_c_runner import EngineCInput, run_engine_c
from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
    BreakoutReference,
    EngineCInputBuilderResult,
    build_engine_c_input_from_window,
    detect_breakout_reference_doc21,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _ohlcv_5m_bar(*, ts_ms: int, o: float, h: float, l: float, c: float, v: float) -> dict[str, object]:
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


def _trade_row(*, ts_ms: int, price: float, qty: float, side: str = "buy") -> dict[str, object]:
    return {
        "timestamp_ms": ts_ms,
        "pair": "TESTPAIR",
        "trade_id": str(ts_ms),
        "price": str(price),
        "qty": str(qty),
        "side": side,
    }


def _build_synthetic_long_breakout_dataset(
    tmp_path: Path,
    *,
    base_ts_ms: int,
    range_high: float = 100.0,
    range_low: float = 99.5,
    break_close: float = 110.0,
) -> tuple[Path, Path, int, int]:
    """Construit un dataset OHLCV+trades synthetique avec un long breakout massif.

    Lookback = 12 bars 5m (1h) consolidant entre range_low et range_high
    avec prix tres uniformes (vol pre-break tres faible).
    In-window = 2 bars 5m, le premier ferme >> range_high (breakout long).
    Le break est volontairement massif (>> 1 sigma) pour detection fiable.
    """
    bars: list[dict[str, object]] = []
    # 12 bars lookback avec prix tres uniformes (compression)
    for i in range(12):
        ts = base_ts_ms - (12 - i) * 300_000
        bars.append(
            _ohlcv_5m_bar(
                ts_ms=ts,
                o=99.7,
                h=range_high,
                l=range_low,
                c=99.7 + (i % 2) * 0.05,  # tres faible amplitude
                v=10.0,
            )
        )
    # 2 bars in-window : premier = breakout massif, second = continuation
    bars.append(
        _ohlcv_5m_bar(
            ts_ms=base_ts_ms,
            o=99.8,
            h=break_close + 0.5,
            l=99.8,
            c=break_close,
            v=50.0,
        )
    )
    bars.append(
        _ohlcv_5m_bar(
            ts_ms=base_ts_ms + 300_000,
            o=break_close,
            h=break_close + 0.3,
            l=break_close - 0.2,
            c=break_close + 0.2,
            v=15.0,
        )
    )
    ohlcv_path = tmp_path / "ohlcv_5m.jsonl"
    _write_jsonl(ohlcv_path, bars)

    # Trades : tres uniformes pre-break (vol kernel proche de zero), puis spike
    trades: list[dict[str, object]] = []
    total_duration = 13 * 300_000 + 600_000
    start_ts = base_ts_ms - 12 * 300_000
    for i in range(200):
        ts = start_ts + (i * total_duration) // 200
        if ts < base_ts_ms:
            # Prix quasi constant pre-break
            price = 99.7 + (i % 3) * 0.01
        else:
            price = break_close + (i % 5) * 0.1
        trades.append(_trade_row(ts_ms=ts, price=price, qty=1.0))
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, trades)

    window_start_ms = base_ts_ms
    window_end_ms = base_ts_ms + 600_000
    return ohlcv_path, trade_path, window_start_ms, window_end_ms


def test_detect_breakout_reference_doc21_finds_long_breakout(tmp_path: Path) -> None:
    """Stage 1 doc 21 : breakout long detecte sur dataset synthetique."""
    ohlcv_path, trade_path, window_start, window_end = (
        _build_synthetic_long_breakout_dataset(
            tmp_path, base_ts_ms=1_700_000_000_000
        )
    )
    # Charger les rows OHLCV pour le test direct
    rows = []
    with ohlcv_path.open("r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    breakout = detect_breakout_reference_doc21(
        pair="TESTPAIR",
        ohlcv_rows=rows,
        raw_trade_path=trade_path,
        window_start_ms=window_start,
        window_end_ms=window_end,
        k_vol_multiplier=1.0,
    )

    assert breakout.detector_status in {
        "DETECTED",
        "DETECTED_FALLBACK_INWINDOW_RANGE",
    }, f"detector_status={breakout.detector_status}"
    assert breakout.direction == "long"
    assert breakout.level == 100.0  # range_high
    assert breakout.range_high_lookback == 100.0
    assert breakout.range_low_lookback == 99.5  # default fixture
    assert breakout.range_size == 0.5
    assert breakout.realized_vol_at_break > 0.0
    assert breakout.t_break_ms == window_start  # premier bar in-window


def test_build_engine_c_input_produces_validatable_payload(tmp_path: Path) -> None:
    """Le builder doit produire un payload qui passe EngineCInput.model_validate()."""
    ohlcv_path, trade_path, window_start, window_end = (
        _build_synthetic_long_breakout_dataset(
            tmp_path, base_ts_ms=1_700_000_000_000
        )
    )
    result = build_engine_c_input_from_window(
        candidate_id="synth-c1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
    )

    assert isinstance(result, EngineCInputBuilderResult)
    assert result.builder_status in {
        "ENGINE_C_INPUT_BUILDER_READY",
        "ENGINE_C_INPUT_BUILDER_READY_FALLBACK_INWINDOW_RANGE",
    }, f"builder_status={result.builder_status}"
    assert result.engine_c_input_provenance == "BUILDER_DOC21_HEURISTIC_TO_CALIBRATE"

    # Le payload doit avoir tous les champs requis avec des valeurs valides
    payload = result.engine_c_input_payload
    for required_field in (
        "pair",
        "breakout_strength",
        "range_quality",
        "compression_quality",
        "volume_confirmation",
        "followthrough_room",
        "extension_pct",
    ):
        assert required_field in payload, f"missing required field: {required_field}"

    # breakout_strength doit etre > 0 vu qu'on a un break clair
    assert payload["breakout_strength"] > 0.0, (
        f"break_close=102 vs range_high=100, breakout_strength={payload['breakout_strength']}"
    )

    # Pydantic validation doit passer
    inp = EngineCInput.model_validate(payload)
    assert inp.pair == "TESTPAIR"
    assert inp.breakout_strength > 0.0
    assert inp.range_high == 100.0


def test_run_engine_c_invocable_on_builder_payload(tmp_path: Path) -> None:
    """Le payload du builder doit permettre run_engine_c() sans crash."""
    ohlcv_path, trade_path, window_start, window_end = (
        _build_synthetic_long_breakout_dataset(
            tmp_path, base_ts_ms=1_700_000_000_000
        )
    )
    result = build_engine_c_input_from_window(
        candidate_id="synth-c1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
    )

    inp = EngineCInput.model_validate(result.engine_c_input_payload)
    output = run_engine_c(inp)

    # On exige que engine_c retourne un EngineCOutput valide (decision peut
    # etre no_trade — le builder ne pretend pas trouver des trades viables).
    assert output.engine_id == "engine_c"
    assert output.decision in {"emit", "no_trade"}
    # Pas de plantage Pydantic ni d'exception, c'est l'objectif principal.


def test_build_engine_c_input_handles_missing_ohlcv(tmp_path: Path) -> None:
    """Sans OHLCV, le builder retourne un statut FAILED explicite."""
    result = build_engine_c_input_from_window(
        candidate_id="empty-c1",
        pair="TESTPAIR",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 600_000,
        raw_trade_path=None,
        raw_ohlcv_path=None,
    )
    assert result.builder_status == "ENGINE_C_INPUT_BUILDER_FAILED_NO_OHLCV"
    assert result.breakout_reference is None
    assert "OHLCV_PATH_MISSING" in result.builder_warnings


def test_build_engine_c_input_merges_microstructure_seam(tmp_path: Path) -> None:
    """Le seam microstructure additif doit s'integrer dans le payload final."""
    ohlcv_path, trade_path, window_start, window_end = (
        _build_synthetic_long_breakout_dataset(
            tmp_path, base_ts_ms=1_700_000_000_000
        )
    )
    micro_payload = {
        "pair": "TESTPAIR",
        "cumulative_ofi": 42.5,
        "queue_pressure": 0.15,
        "vpin": 0.30,
    }
    result = build_engine_c_input_from_window(
        candidate_id="synth-c1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
        microstructure_partial_payload=micro_payload,
    )

    payload = result.engine_c_input_payload
    assert payload["cumulative_ofi"] == 42.5
    assert payload["queue_pressure"] == 0.15
    assert payload["vpin"] == 0.30
    # Pydantic validation OK avec microstructure
    EngineCInput.model_validate(payload)


# ===========================================================================
# Integration test sur run dossier reel — opt-in
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_c_input_builder_real_run_dossier_chains_to_run_engine_c() -> None:
    """Test integration : sur le run dossier reel, le pont microstructure +
    builder doivent permettre l'invocation de run_engine_c() sans crash.

    Pour le candidat eea9862e... la fenetre est cross-day (window starts 23:55
    du 4 mai, fichier OHLCV 5m commence a 00:00 du 5 mai). On accepte donc
    BUILDER_NO_BREAKOUT comme statut valide pour ce candidat — la chaine
    fonctionne, mais le breakout ne peut etre detecte sans le fichier 04.jsonl.
    """
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    from local_replay_runtime.strategy_ladder_engine_native_adapter import (
        build_engine_c_microstructure_inputs_from_window,
    )

    micro_result = build_engine_c_microstructure_inputs_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        raw_book_path=manifest["raw_book_path"],
        raw_book_delta_path=manifest.get("raw_book_delta_path"),
    )
    builder_result = build_engine_c_input_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        raw_ohlcv_path=manifest["raw_ohlcv_path"],
        microstructure_partial_payload=micro_result.engine_c_partial_input_payload,
    )

    # Le builder doit produire un payload Pydantic-valide meme si pas de breakout
    assert builder_result.builder_status in {
        "ENGINE_C_INPUT_BUILDER_READY",
        "ENGINE_C_INPUT_BUILDER_READY_FALLBACK_INWINDOW_RANGE",
        "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT",
    }, f"unexpected status: {builder_result.builder_status}"

    payload = builder_result.engine_c_input_payload
    assert payload, "payload must not be empty"

    # Pydantic validation doit passer
    inp = EngineCInput.model_validate(payload)
    assert inp.pair == "BNBUSDT"

    # run_engine_c doit pouvoir etre invoque (peut retourner no_trade)
    output = run_engine_c(inp)
    assert output.engine_id == "engine_c"
    assert output.decision in {"emit", "no_trade"}

    # Le seam microstructure doit etre merge dans le payload
    assert payload.get("cumulative_ofi") is not None
    assert payload.get("vpin") is not None
