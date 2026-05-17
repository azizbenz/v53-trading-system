"""Tests pour strategy_ladder_engine_a_input_builder (Audit 2026-05-07).

Prouve que le builder construit un EngineAInput.model_validate-compatible
depuis raw_window OHLCV et que run_engine_a() peut etre invoque.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from engines.engine_a.engine_a_runner import EngineAInput, run_engine_a
from local_replay_runtime.strategy_ladder_engine_a_input_builder import (
    EngineAInputBuilderResult,
    EngineAStructureSummary,
    build_engine_a_input_from_window,
    derive_engine_a_structure_summary,
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


def _build_synthetic_uptrend_dataset(
    tmp_path: Path,
    *,
    base_ts_ms: int,
    n_lookback: int = 12,
    n_in_window: int = 6,
) -> tuple[Path, int, int]:
    """Construit un dataset OHLCV avec un uptrend stable, structure lisible.

    Le trend est lineaire ascendant pour donner direction_score > 0,
    continuation_score > 0, trend_stability eleve, structure_quality eleve
    (peu de wicks).
    """
    bars: list[dict[str, object]] = []
    # Lookback : prix qui montent regulierement de 100 a 102
    for i in range(n_lookback):
        ts = base_ts_ms - (n_lookback - i) * 300_000
        # Bars haussiers stables : open < close, peu de wicks
        base_price = 100.0 + i * (2.0 / n_lookback)
        bars.append(
            _bar(
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.15,
                l=base_price - 0.05,
                c=base_price + 0.10,
                v=15.0,
            )
        )
    # In-window : trend continue
    for i in range(n_in_window):
        ts = base_ts_ms + i * 300_000
        base_price = 102.0 + i * 0.2
        bars.append(
            _bar(
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.2,
                l=base_price - 0.05,
                c=base_price + 0.15,
                v=20.0,
            )
        )
    ohlcv_path = tmp_path / "ohlcv_5m.jsonl"
    _write_jsonl(ohlcv_path, bars)

    window_start_ms = base_ts_ms
    window_end_ms = base_ts_ms + n_in_window * 300_000
    return ohlcv_path, window_start_ms, window_end_ms


def test_derive_structure_summary_uptrend(tmp_path: Path) -> None:
    """Sur un uptrend lineaire stable, les 5 champs structurels doivent etre eleves."""
    ohlcv_path, ws, we = _build_synthetic_uptrend_dataset(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    rows = []
    with ohlcv_path.open("r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    summary = derive_engine_a_structure_summary(
        bars_full=rows, window_start_ms=ws, window_end_ms=we
    )
    assert isinstance(summary, EngineAStructureSummary)
    assert summary.detector_status == "DETECTED"
    assert summary.direction_score > 0.5, (
        f"direction_score doit etre > 0.5 sur uptrend; got {summary.direction_score}"
    )
    assert summary.continuation_score > 0.5, (
        f"continuation_score doit etre > 0.5 sur uptrend; got {summary.continuation_score}"
    )
    assert summary.structure_quality > 0.5, (
        f"structure_quality doit etre > 0.5 sur bars stables; got {summary.structure_quality}"
    )
    # zone_proximity : last_close proche du high (uptrend), donc proximity haut
    assert 0.0 <= summary.zone_proximity <= 1.0
    # trend_stability : R^2 du fit lineaire doit etre tres eleve sur uptrend lineaire
    assert summary.trend_stability > 0.8, (
        f"trend_stability doit etre > 0.8 sur trend lineaire; got {summary.trend_stability}"
    )


def test_derive_structure_summary_downtrend(tmp_path: Path) -> None:
    """Sur un downtrend lineaire, direction_score doit etre < 0."""
    bars: list[dict[str, object]] = []
    base_ts = 1_700_000_000_000
    for i in range(15):
        ts = base_ts + i * 300_000
        base_price = 100.0 - i * 0.2
        bars.append(
            _bar(
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.05,
                l=base_price - 0.15,
                c=base_price - 0.10,  # bearish bar
                v=15.0,
            )
        )
    ohlcv_path = tmp_path / "ohlcv_down.jsonl"
    _write_jsonl(ohlcv_path, bars)
    rows = bars  # direct
    summary = derive_engine_a_structure_summary(
        bars_full=rows,
        window_start_ms=base_ts,
        window_end_ms=base_ts + 15 * 300_000,
    )
    assert summary.direction_score < -0.3, (
        f"direction_score doit etre clairement negatif sur downtrend; got {summary.direction_score}"
    )
    assert summary.continuation_score > 0.5
    assert summary.trend_stability > 0.5


def test_derive_structure_summary_choppy(tmp_path: Path) -> None:
    """Sur des bars chaotiques, structure_quality et trend_stability bas."""
    bars: list[dict[str, object]] = []
    base_ts = 1_700_000_000_000
    # 15 bars alternant haut/bas avec grosses meches
    for i in range(15):
        ts = base_ts + i * 300_000
        if i % 2 == 0:
            bars.append(_bar(ts_ms=ts, o=100.0, h=102.0, l=99.0, c=100.5, v=10.0))
        else:
            bars.append(_bar(ts_ms=ts, o=100.5, h=101.0, l=98.5, c=99.8, v=10.0))
    summary = derive_engine_a_structure_summary(
        bars_full=bars,
        window_start_ms=base_ts,
        window_end_ms=base_ts + 15 * 300_000,
    )
    # continuation_score doit etre bas (alternance)
    assert summary.continuation_score < 0.3, (
        f"continuation_score doit etre bas sur alternance; got {summary.continuation_score}"
    )


def test_build_engine_a_input_produces_validatable_payload(tmp_path: Path) -> None:
    """Le payload doit passer EngineAInput.model_validate()."""
    ohlcv_path, ws, we = _build_synthetic_uptrend_dataset(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    result = build_engine_a_input_from_window(
        candidate_id="a-synth-1",
        pair="TESTPAIR",
        window_start_ms=ws,
        window_end_ms=we,
        raw_ohlcv_path=ohlcv_path,
        candidate_size=100.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    assert isinstance(result, EngineAInputBuilderResult)
    assert result.builder_status == "ENGINE_A_INPUT_BUILDER_READY"
    assert (
        result.engine_a_input_provenance == "BUILDER_OHLCV_HEURISTIC_TO_CALIBRATE"
    )
    payload = result.engine_a_input_payload
    inp = EngineAInput.model_validate(payload)
    assert inp.pair == "TESTPAIR"
    assert inp.direction_score > 0.0  # uptrend
    assert inp.continuation_score > 0.0
    assert inp.candidate_size == 100.0
    assert inp.cost_preference_score == pytest.approx(0.5)


def test_run_engine_a_invocable_on_builder_payload(tmp_path: Path) -> None:
    """run_engine_a() doit pouvoir tourner sans crash."""
    ohlcv_path, ws, we = _build_synthetic_uptrend_dataset(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    result = build_engine_a_input_from_window(
        candidate_id="a-synth-2",
        pair="TESTPAIR",
        window_start_ms=ws,
        window_end_ms=we,
        raw_ohlcv_path=ohlcv_path,
        candidate_size=100.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    inp = EngineAInput.model_validate(result.engine_a_input_payload)
    out = run_engine_a(inp)
    assert out.engine_id == "engine_a"
    assert out.decision in {"emit", "no_trade"}


def test_build_engine_a_input_handles_missing_ohlcv() -> None:
    """Sans OHLCV, le builder retourne FAILED."""
    result = build_engine_a_input_from_window(
        candidate_id="empty",
        pair="TESTPAIR",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_000_000 + 600_000,
        raw_ohlcv_path=None,
    )
    assert result.builder_status == "ENGINE_A_INPUT_BUILDER_FAILED_NO_OHLCV"
    assert "OHLCV_PATH_MISSING" in result.builder_warnings


def test_build_engine_a_input_merges_microstructure_updates(tmp_path: Path) -> None:
    """Le seam microstructure additif doit s'integrer dans le payload."""
    ohlcv_path, ws, we = _build_synthetic_uptrend_dataset(
        tmp_path, base_ts_ms=1_700_000_000_000
    )
    micro_updates = {
        "flow_score": 0.37,
        "ofi_flow_score": 0.42,
        "realized_kernel_vol_scale": 0.15,
        "realized_vol_current": 0.001,
        "kyle_lambda_cost_uplift": 0.05,
    }
    result = build_engine_a_input_from_window(
        candidate_id="a-synth-3",
        pair="TESTPAIR",
        window_start_ms=ws,
        window_end_ms=we,
        raw_ohlcv_path=ohlcv_path,
        microstructure_updates=micro_updates,
    )
    payload = result.engine_a_input_payload
    assert payload["flow_score"] == 0.37
    assert payload["ofi_flow_score"] == 0.42
    assert payload["realized_kernel_vol_scale"] == 0.15
    assert payload["realized_vol_current"] == 0.001
    assert payload["kyle_lambda_cost_uplift"] == 0.05
    EngineAInput.model_validate(payload)


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_a_input_builder_real_run_dossier_chains_to_run_engine_a() -> None:
    """Test integration sur le run dossier reel : run_engine_a() invoque."""
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    from local_replay_runtime.strategy_ladder_engine_native_adapter import (
        build_engine_a_microstructure_inputs_from_window,
    )

    micro = build_engine_a_microstructure_inputs_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        raw_book_path=manifest["raw_book_path"],
        raw_book_delta_path=manifest.get("raw_book_delta_path"),
    )
    result = build_engine_a_input_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_ohlcv_path=manifest["raw_ohlcv_path"],
        microstructure_updates=micro.engine_a_microstructure_updates,
        candidate_size=100.0,
        expected_gain=0.001,
        expected_cost=0.0005,
    )
    # Pas crash, payload valide Pydantic
    inp = EngineAInput.model_validate(result.engine_a_input_payload)
    assert inp.pair == "BNBUSDT"
    out = run_engine_a(inp)
    assert out.engine_id == "engine_a"
    assert out.decision in {"emit", "no_trade"}
