"""Test microstructure-aware override in build_engine_c_input_from_window.

Per V5.3 doctrine, when microstructure scalars (OFI/queue/vpin/kyle) are
available via microstructure_partial_payload, the builder MUST use the
microstructure-aware resolver instead of the legacy doc21 heuristic
formulas (volume MA, BB squeeze, OHLCV-only pullback).

Validates:
  - Without microstructure → legacy provenance preserved (back-compat)
  - With microstructure → MICROSTRUCTURE_AWARE_RESOLVER_V1 provenance
  - Override does not break EngineCInput.model_validate
"""

from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
    build_engine_c_input_from_window,
)


def _make_ohlcv_window(tmp_path: Path) -> Path:
    """Synthesize a window with detectable breakout for the legacy detector."""
    p = tmp_path / "ohlcv.jsonl"
    rows = []
    base_ts = 1_700_000_000_000
    # 30 lookback bars at price ~100
    for i in range(30):
        rows.append(
            {
                "timestamp_ms": base_ts - (30 - i) * 60_000,
                "open": 100.0,
                "high": 100.2,
                "low": 99.8,
                "close": 100.0,
                "volume": 10.0,
            }
        )
    # 5 in-window bars: breakout above 100.2 → close 101
    for i in range(5):
        rows.append(
            {
                "timestamp_ms": base_ts + i * 60_000,
                "open": 100.5 + i * 0.1,
                "high": 101.0 + i * 0.1,
                "low": 100.3,
                "close": 101.0 + i * 0.1,
                "volume": 50.0,
            }
        )
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def test_builder_uses_legacy_provenance_when_no_microstructure(tmp_path: Path) -> None:
    """Back-compat: no microstructure payload → legacy doc21 heuristic provenance."""
    ohlcv = _make_ohlcv_window(tmp_path)

    result = build_engine_c_input_from_window(
        candidate_id="cand_1",
        pair="BTCUSDT",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_240_000,
        raw_trade_path=None,
        raw_ohlcv_path=ohlcv,
        microstructure_partial_payload=None,
    )

    assert result.engine_c_input_provenance == "BUILDER_DOC21_HEURISTIC_TO_CALIBRATE"
    # Payload has the 7 structural floats from legacy compute
    payload = result.engine_c_input_payload
    if payload:
        for k in (
            "breakout_strength",
            "range_quality",
            "compression_quality",
            "volume_confirmation",
            "followthrough_room",
            "extension_pct",
            "retrace_risk",
        ):
            assert k in payload


def test_builder_uses_microstructure_aware_provenance_when_records_available(
    tmp_path: Path,
) -> None:
    """V5.3 doctrine: microstructure scalars present → resolver V1 provenance."""
    ohlcv = _make_ohlcv_window(tmp_path)

    microstructure = {
        "cumulative_ofi": 0.4,
        "queue_pressure": 0.6,
        "vpin": 0.3,
        "kyle_lambda": 0.02,
        "realized_vol_current": 0.001,
    }

    result = build_engine_c_input_from_window(
        candidate_id="cand_2",
        pair="BTCUSDT",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_240_000,
        raw_trade_path=None,
        raw_ohlcv_path=ohlcv,
        microstructure_partial_payload=microstructure,
    )

    # Provenance starts with MICROSTRUCTURE_AWARE_RESOLVER_V1 (may have _PARTIAL_FALLBACK suffix)
    assert result.engine_c_input_provenance.startswith("MICROSTRUCTURE_AWARE_RESOLVER_V1"), (
        f"unexpected provenance: {result.engine_c_input_provenance}"
    )

    payload = result.engine_c_input_payload
    if payload:
        for k in (
            "breakout_strength",
            "range_quality",
            "compression_quality",
            "volume_confirmation",
            "followthrough_room",
            "extension_pct",
            "retrace_risk",
        ):
            assert k in payload
            assert 0.0 <= payload[k] <= 1.0


def test_builder_falls_back_to_legacy_when_microstructure_keys_all_none(
    tmp_path: Path,
) -> None:
    """Microstructure payload present but all None → legacy preserved."""
    ohlcv = _make_ohlcv_window(tmp_path)

    microstructure = {
        "cumulative_ofi": None,
        "queue_pressure": None,
        "vpin": None,
        "kyle_lambda": None,
    }

    result = build_engine_c_input_from_window(
        candidate_id="cand_3",
        pair="BTCUSDT",
        window_start_ms=1_700_000_000_000,
        window_end_ms=1_700_000_240_000,
        raw_trade_path=None,
        raw_ohlcv_path=ohlcv,
        microstructure_partial_payload=microstructure,
    )

    # All None → no microstructure → legacy provenance
    assert result.engine_c_input_provenance == "BUILDER_DOC21_HEURISTIC_TO_CALIBRATE"
