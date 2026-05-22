from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from engines.engine_a.engine_a_runner import run_engine_a
from engines.engine_b.engine_b_runner import run_engine_b
from engines.engine_c.engine_c_runner import run_engine_c
from engines.engine_d.engine_d_runner import run_engine_d
from local_replay_runtime.strategy_ladder_economic_provenance import EconomicProvenance
from local_replay_runtime.strategy_ladder_engine_synthetic_viability import (
    _engine_a_emit_inputs,
    _engine_b_emit_inputs,
    _engine_c_emit_inputs,
    _engine_d_emit_inputs,
    _enum_value,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)
from local_replay_runtime.strategy_ladder_runner import _run_native_engine_candidate


@dataclass(frozen=True)
class SyntheticB2ParityCaseResult:
    engine_id: str
    case_id: str
    viability_direct_decision: str
    builder_direct_decision: str
    builder_path_decision: str
    viability_vs_builder_status: str
    builder_vs_runner_status: str
    builder_status: str
    input_provenance: str
    runner_status: str
    records_built: int
    builder_reason_codes: tuple[str, ...]
    builder_no_trade_reasons: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticB2ParityReport:
    schema_version: str
    generated_at: str
    diagnostic_only: bool
    asset_root: str
    cases: tuple[SyntheticB2ParityCaseResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "diagnostic_only": self.diagnostic_only,
            "asset_root": self.asset_root,
            "cases": [asdict(case) for case in self.cases],
        }


@dataclass(frozen=True)
class _ParityFixture:
    engine_id: str
    case_id: str
    direct_runner: Callable[[object], object]
    direct_input: object
    candidate: StrategyLadderCandidateEvent
    window: StrategyLadderRawWindowManifest
    notes: tuple[str, ...] = ()


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _bar(
    *,
    pair: str,
    timeframe: str,
    ts_ms: int,
    o: float,
    h: float,
    l: float,
    c: float,
    v: float,
) -> dict[str, object]:
    return {
        "timestamp_ms": ts_ms,
        "pair": pair,
        "timeframe": timeframe,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def _trade(
    *,
    pair: str,
    ts_ms: int,
    price: float,
    qty: float,
    side: str,
) -> dict[str, object]:
    return {
        "timestamp_ms": ts_ms,
        "pair": pair,
        "trade_id": str(ts_ms),
        "price": str(price),
        "qty": str(qty),
        "side": side,
    }


def _candidate(
    *,
    engine_id: str,
    case_id: str,
    pair: str,
    timeframe: str,
    ts_ms: int,
    planned_notional: float,
    compatibility_payload: dict[str, object] | None = None,
) -> StrategyLadderCandidateEvent:
    payload = {
        "planned_notional": planned_notional,
        "book_depth_levels": 20,
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        **(compatibility_payload or {}),
    }
    return StrategyLadderCandidateEvent(
        candidate_id=case_id,
        pair=pair,
        timeframe=timeframe,
        engine_id=engine_id,
        strategy_id=engine_id,
        timestamp_ms=ts_ms,
        compatibility_payload=payload,
        candidate_source="SYNTHETIC_B2_PARITY",
        candidate_data_source_label="SYNTHETIC_B2_PARITY",
    )


def _window(
    *,
    case_id: str,
    engine_id: str,
    pair: str,
    ts_ms: int,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | None = None,
    raw_book_path: Path | None = None,
    raw_book_delta_path: Path | None = None,
    raw_ohlcv_path: Path | None = None,
) -> StrategyLadderRawWindowManifest:
    raw_sources_used = tuple(
        source
        for source, path in (
            ("trades", raw_trade_path),
            ("orderbook", raw_book_path),
            ("klines", raw_ohlcv_path),
        )
        if path is not None
    )
    return StrategyLadderRawWindowManifest(
        candidate_id=case_id,
        pair=pair,
        engine_id=engine_id,
        timestamp_ms=ts_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=str(raw_trade_path) if raw_trade_path is not None else None,
        raw_book_path=str(raw_book_path) if raw_book_path is not None else None,
        raw_book_delta_path=(
            str(raw_book_delta_path) if raw_book_delta_path is not None else None
        ),
        raw_ohlcv_path=str(raw_ohlcv_path) if raw_ohlcv_path is not None else None,
        book_depth_levels_available=20 if raw_book_path is not None else None,
        book_depth_source_status=(
            "BOOK_DEPTH20_AVAILABLE"
            if raw_book_path is not None
            else "BOOK_DEPTH_NOT_PROVEN"
        ),
        window_extraction_status="RAW_WINDOW_READY",
        raw_sources_used=raw_sources_used,
        source_coverage_status="RAW_WINDOW_SOURCE_READY",
    )


def _economic_provenance(
    *,
    expected_gain: float,
    expected_cost: float,
) -> EconomicProvenance:
    cost_bps = expected_cost * 10_000.0
    spread_bps = round(cost_bps * 0.5, 6)
    slippage_bps = round((cost_bps * 0.4) / 1.15, 6)
    latency_penalty_bps = round(max(cost_bps - spread_bps - slippage_bps * 1.15, 0.0), 6)
    return EconomicProvenance(
        expected_edge_bps=expected_gain * 10_000.0,
        expected_edge_provenance="GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
        spread_bps=spread_bps,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=slippage_bps,
        slippage_provenance="MEASURED_FROM_KYLE_LAMBDA",
        latency_penalty_bps=latency_penalty_bps,
        latency_provenance="STATIC_CONSERVATIVE_VENUE_MODEL",
        fee_bps=0.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
        measurement_warnings=(),
        expected_edge_model_status="GOVERNED_EDGE_MODEL_READY",
        expected_edge_model_artifact_hash="SYNTHETIC_B2_PARITY",
        expected_edge_model_feature_hash="SYNTHETIC_B2_PARITY",
    )


def _build_engine_a_fixture(asset_root: Path) -> _ParityFixture:
    pair = "BTCUSDT"
    timeframe = "5m"
    direct_input = _engine_a_emit_inputs()
    window_start_ms = 1_700_000_000_000
    window_end_ms = window_start_ms + 6 * 300_000
    ohlcv_rows: list[dict[str, object]] = []
    for i in range(12):
        ts = window_start_ms - (12 - i) * 300_000
        base_price = 100.0 + i * (2.0 / 12.0)
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.15,
                l=base_price - 0.05,
                c=base_price + 0.10,
                v=15.0,
            )
        )
    for i in range(6):
        ts = window_start_ms + i * 300_000
        base_price = 102.0 + i * 0.2
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.2,
                l=base_price - 0.05,
                c=base_price + 0.15,
                v=20.0,
            )
        )
    trade_rows = [
        _trade(
            pair=pair,
            ts_ms=window_start_ms + i * 60_000,
            price=102.0 + i * 0.05,
            qty=1.0,
            side="buy",
        )
        for i in range(40)
    ]
    ohlcv_path = asset_root / "engine_a" / "ohlcv_5m.jsonl"
    trade_path = asset_root / "engine_a" / "trades.jsonl"
    _write_jsonl(ohlcv_path, ohlcv_rows)
    _write_jsonl(trade_path, trade_rows)
    candidate = _candidate(
        engine_id="engine_a",
        case_id="engine_a_emit_parity",
        pair=pair,
        timeframe=timeframe,
        ts_ms=window_end_ms,
        planned_notional=100.0,
    )
    window = _window(
        case_id=candidate.candidate_id,
        engine_id="engine_a",
        pair=pair,
        ts_ms=window_end_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
    )
    return _ParityFixture(
        engine_id="engine_a",
        case_id="emit_viable_candidate",
        direct_runner=run_engine_a,
        direct_input=direct_input,
        candidate=candidate,
        window=window,
    )


def _build_engine_b_fixture(asset_root: Path) -> _ParityFixture:
    pair = "BTCUSDT"
    timeframe = "5m"
    direct_input = _engine_b_emit_inputs()
    window_start_ms = 1_700_100_000_000
    window_end_ms = window_start_ms + 600_000
    trade_rows = [
        _trade(
            pair=pair,
            ts_ms=window_start_ms + i * 20_000,
            price=100.0,
            qty=1.0,
            side="buy" if i % 2 == 0 else "sell",
        )
        for i in range(20)
    ]
    trade_rows.extend(
        [
            _trade(
                pair=pair,
                ts_ms=window_end_ms - 40_000,
                price=99.0,
                qty=1.0,
                side="sell",
            ),
            _trade(
                pair=pair,
                ts_ms=window_end_ms - 20_000,
                price=98.0,
                qty=1.0,
                side="sell",
            ),
            _trade(
                pair=pair,
                ts_ms=window_end_ms,
                price=97.0,
                qty=1.0,
                side="sell",
            ),
        ]
    )
    trade_path = asset_root / "engine_b" / "trades.jsonl"
    _write_jsonl(trade_path, trade_rows)
    candidate = _candidate(
        engine_id="engine_b",
        case_id="engine_b_emit_parity",
        pair=pair,
        timeframe=timeframe,
        ts_ms=window_end_ms,
        planned_notional=100.0,
    )
    window = _window(
        case_id=candidate.candidate_id,
        engine_id="engine_b",
        pair=pair,
        ts_ms=window_end_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=trade_path,
    )
    return _ParityFixture(
        engine_id="engine_b",
        case_id="emit_viable_candidate",
        direct_runner=run_engine_b,
        direct_input=direct_input,
        candidate=candidate,
        window=window,
    )


def _build_engine_c_fixture(asset_root: Path) -> _ParityFixture:
    pair = "BTCUSDT"
    timeframe = "5m"
    direct_input = _engine_c_emit_inputs()
    window_start_ms = 1_700_200_000_000
    window_end_ms = window_start_ms + 600_000
    ohlcv_rows: list[dict[str, object]] = []
    for i in range(12):
        ts = window_start_ms - (12 - i) * 300_000
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=99.7,
                h=100.0,
                l=99.5,
                c=99.7 + (i % 2) * 0.05,
                v=10.0,
            )
        )
    ohlcv_rows.append(
        _bar(
            pair=pair,
            timeframe=timeframe,
            ts_ms=window_start_ms,
            o=99.8,
            h=110.5,
            l=99.8,
            c=110.0,
            v=50.0,
        )
    )
    ohlcv_rows.append(
        _bar(
            pair=pair,
            timeframe=timeframe,
            ts_ms=window_start_ms + 300_000,
            o=110.0,
            h=110.3,
            l=109.8,
            c=110.2,
            v=15.0,
        )
    )
    ohlcv_path = asset_root / "engine_c" / "ohlcv_5m.jsonl"
    _write_jsonl(ohlcv_path, ohlcv_rows)
    total_duration = 13 * 300_000 + 600_000
    trade_start_ms = window_start_ms - 12 * 300_000
    trade_rows: list[dict[str, object]] = []
    for i in range(240):
        ts = trade_start_ms + (i * total_duration) // 240
        price = 99.7 + (i % 3) * 0.01 if ts < window_start_ms else 110.0 + (i % 5) * 0.1
        trade_rows.append(
            _trade(
                pair=pair,
                ts_ms=ts,
                price=price,
                qty=1.0,
                side="buy",
            )
        )
    trade_path = asset_root / "engine_c" / "trades.jsonl"
    _write_jsonl(trade_path, trade_rows)
    book_path = asset_root / "engine_c" / "orderbook_snapshot.jsonl"
    _write_jsonl(
        book_path,
        [
            {
                "timestamp_ms": window_start_ms - 1_000,
                "update_id": 1,
                "bids": [["109.8", "80"], ["109.7", "60"]],
                "asks": [["110.0", "20"], ["110.1", "25"]],
            }
        ],
    )
    book_delta_path = asset_root / "engine_c" / "orderbook_delta.jsonl"
    _write_jsonl(
        book_delta_path,
        [
            {
                "timestamp_ms": window_start_ms + 1_000,
                "update_id": 2,
                "bids": [["109.9", "120"]],
                "asks": [["110.0", "15"]],
            },
            {
                "timestamp_ms": window_start_ms + 120_000,
                "update_id": 3,
                "bids": [["110.0", "140"]],
                "asks": [["110.1", "10"]],
            },
            {
                "timestamp_ms": window_start_ms + 240_000,
                "update_id": 4,
                "bids": [["110.1", "160"]],
                "asks": [["110.2", "8"]],
            },
        ],
    )
    candidate = _candidate(
        engine_id="engine_c",
        case_id="engine_c_emit_parity",
        pair=pair,
        timeframe=timeframe,
        ts_ms=window_end_ms,
        planned_notional=1000.0,
        compatibility_payload={
            "feature_values": {
                "book_depth_levels": 20,
                "queue_pressure": 0.36,
                "fragility_score": 0.1,
                "false_breakout_context": 0.1,
            }
        },
    )
    window = _window(
        case_id=candidate.candidate_id,
        engine_id="engine_c",
        pair=pair,
        ts_ms=window_end_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=trade_path,
        raw_book_path=book_path,
        raw_book_delta_path=book_delta_path,
        raw_ohlcv_path=ohlcv_path,
    )
    return _ParityFixture(
        engine_id="engine_c",
        case_id="emit_viable_candidate",
        direct_runner=run_engine_c,
        direct_input=direct_input,
        candidate=candidate,
        window=window,
    )


def _build_engine_c_aligned_fixture(asset_root: Path) -> _ParityFixture:
    from engines.engine_c.engine_c_runner import EngineCInput
    from local_replay_runtime.strategy_ladder_complete_enabler_support import (
        apply_build14_shadow_context,
    )
    from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
        build_engine_c_input_from_window,
    )
    from local_replay_runtime.strategy_ladder_engine_native_adapter import (
        build_engine_c_microstructure_inputs_from_window,
    )

    pair = "BTCUSDT"
    timeframe = "5m"
    window_start_ms = 1_700_210_000_000
    window_end_ms = window_start_ms + 300_000
    ohlcv_rows: list[dict[str, object]] = []
    for i in range(6):
        ts = window_start_ms - (12 - i) * 300_000
        base = 99.82 + (i % 2) * 0.01
        low = 99.0 if i == 0 else base - 0.06
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=base,
                h=base + 0.12,
                l=low,
                c=base,
                v=8.0,
            )
        )
    for i in range(6, 12):
        ts = window_start_ms - (12 - i) * 300_000
        base = 99.87 + ((i - 6) % 2) * 0.005
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=base,
                h=base + 0.04,
                l=base - 0.04,
                c=base,
                v=8.0,
            )
        )
    break_close = 100.08
    ext_close = 100.16
    ohlcv_rows.append(
        _bar(
            pair=pair,
            timeframe=timeframe,
            ts_ms=window_start_ms,
            o=99.95,
            h=100.12,
            l=99.95,
            c=break_close,
            v=60.0,
        )
    )
    ohlcv_rows.append(
        _bar(
            pair=pair,
            timeframe=timeframe,
            ts_ms=window_end_ms,
            o=break_close,
            h=ext_close + 0.02,
            l=break_close - 0.02,
            c=ext_close,
            v=16.0,
        )
    )
    total_duration = 14 * 300_000
    trade_start_ms = window_start_ms - 12 * 300_000
    trade_rows: list[dict[str, object]] = []
    for i in range(260):
        ts = trade_start_ms + (i * total_duration) // 260
        price = 99.88 if ts < window_start_ms else (break_close if ts < window_end_ms else ext_close)
        trade_rows.append(
            _trade(
                pair=pair,
                ts_ms=ts,
                price=price,
                qty=1.0,
                side="buy",
            )
        )
    ohlcv_path = asset_root / "engine_c_aligned" / "ohlcv_5m.jsonl"
    trade_path = asset_root / "engine_c_aligned" / "trades.jsonl"
    book_path = asset_root / "engine_c_aligned" / "orderbook_snapshot.jsonl"
    book_delta_path = asset_root / "engine_c_aligned" / "orderbook_delta.jsonl"
    _write_jsonl(ohlcv_path, ohlcv_rows)
    _write_jsonl(trade_path, trade_rows)
    _write_jsonl(
        book_path,
        [
            {
                "timestamp_ms": window_start_ms - 1_000,
                "update_id": 1,
                "bids": [["100.0", "120"], ["99.99", "90"]],
                "asks": [["100.02", "15"], ["100.03", "18"]],
            }
        ],
    )
    _write_jsonl(
        book_delta_path,
        [
            {
                "timestamp_ms": window_start_ms + 1_000,
                "update_id": 2,
                "bids": [["100.01", "160"]],
                "asks": [["100.02", "8"]],
            },
            {
                "timestamp_ms": window_start_ms + 90_000,
                "update_id": 3,
                "bids": [["100.02", "175"]],
                "asks": [["100.03", "6"]],
            },
        ],
    )
    candidate = _candidate(
        engine_id="engine_c",
        case_id="engine_c_emit_builder_aligned",
        pair=pair,
        timeframe=timeframe,
        ts_ms=window_end_ms,
        planned_notional=1000.0,
        compatibility_payload={
            "feature_values": {
                "book_depth_levels": 20,
                "queue_pressure": 0.36,
                "fragility_score": 0.1,
                "false_breakout_context": 0.1,
            }
        },
    )
    window = _window(
        case_id=candidate.candidate_id,
        engine_id="engine_c",
        pair=pair,
        ts_ms=window_end_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=trade_path,
        raw_book_path=book_path,
        raw_book_delta_path=book_delta_path,
        raw_ohlcv_path=ohlcv_path,
    )
    bridge = build_engine_c_microstructure_inputs_from_window(
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        window_start_ms=window.window_start_ms,
        window_end_ms=window.window_end_ms,
        raw_trade_path=window.raw_trade_path,
        raw_book_path=window.raw_book_path,
        raw_book_delta_path=window.raw_book_delta_path,
    )
    builder = build_engine_c_input_from_window(
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        window_start_ms=window.window_start_ms,
        window_end_ms=window.window_end_ms,
        raw_trade_path=window.raw_trade_path,
        raw_ohlcv_path=window.raw_ohlcv_path,
        microstructure_partial_payload=bridge.engine_c_partial_input_payload,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
    )
    direct_input = EngineCInput.model_validate(
        apply_build14_shadow_context(
            engine_id="engine_c",
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            candidate_payload=dict(candidate.compatibility_payload or {}),
            engine_input_payload=builder.engine_c_input_payload,
        ).adjusted_engine_input_payload
    )
    return _ParityFixture(
        engine_id="engine_c",
        case_id="emit_builder_aligned_candidate",
        direct_runner=run_engine_c,
        direct_input=direct_input,
        candidate=candidate,
        window=window,
        notes=("DIRECT_INPUT_DERIVED_FROM_BUILDER_PAYLOAD_FOR_PARITY_ALIGNMENT",),
    )


def _build_engine_d_fixture(asset_root: Path) -> _ParityFixture:
    pair = "BTCUSDT"
    timeframe = "5m"
    direct_input = _engine_d_emit_inputs()
    window_start_ms = 1_700_300_000_000
    window_end_ms = window_start_ms + 6 * 300_000
    ohlcv_rows: list[dict[str, object]] = []
    for i in range(12):
        ts = window_start_ms - (12 - i) * 300_000
        base_price = 100.0 + i * 0.3
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.2,
                l=base_price - 0.05,
                c=base_price + 0.15,
                v=10.0,
            )
        )
    for i in range(6):
        ts = window_start_ms + i * 300_000
        base_price = 103.6 - i * 0.15
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=base_price,
                h=base_price + 0.05,
                l=base_price - 0.2,
                c=base_price - 0.10,
                v=10.0,
            )
        )
    ohlcv_path = asset_root / "engine_d" / "ohlcv_5m.jsonl"
    _write_jsonl(ohlcv_path, ohlcv_rows)
    total_duration = (12 + 6) * 300_000
    trade_start_ms = window_start_ms - 12 * 300_000
    trade_rows: list[dict[str, object]] = []
    for i in range(200):
        ts = trade_start_ms + (i * total_duration) // 200
        price = (
            100.0 + ((ts - trade_start_ms) / total_duration) * 4.0
            if ts < window_start_ms
            else 103.6 - ((ts - window_start_ms) / total_duration) * 1.0
        )
        trade_rows.append(
            _trade(
                pair=pair,
                ts_ms=ts,
                price=price,
                qty=1.0,
                side="buy",
            )
        )
    trade_path = asset_root / "engine_d" / "trades.jsonl"
    _write_jsonl(trade_path, trade_rows)
    candidate = _candidate(
        engine_id="engine_d",
        case_id="engine_d_emit_parity",
        pair=pair,
        timeframe=timeframe,
        ts_ms=window_end_ms,
        planned_notional=800.0,
        compatibility_payload={
            "origin_context_id": "ctx-btc-01",
            "origin_trade_id": "trade-btc-01",
            "link_type": "prior_trade",
            "first_episode_id": "episode-btc-01",
            "first_episode_engine_id": "engine_a",
            "first_episode_close_reason": "time_stop",
            "consecutive_stop_count": 0,
            "last_fresh_a_detection_at_ns": 1_700_000_100_000_000_000,
            "anti_revenge_state": "reset_required",
            "prior_trade_quality": 0.85,
            "duplication_overlap_with_engine_a": 0.24,
            "marginal_portfolio_gain": 6.0,
            "covered_share_by_engine_a": 0.18,
            "concentration_headroom": 0.78,
            "reentry_lateness": 0.18,
            "structure_reformed_detected": True,
            "reentry_anchor_price": 101.5,
            "feature_values": {
                "book_depth_levels": 20,
            },
        },
    )
    window = _window(
        case_id=candidate.candidate_id,
        engine_id="engine_d",
        pair=pair,
        ts_ms=window_end_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
    )
    return _ParityFixture(
        engine_id="engine_d",
        case_id="emit_viable_candidate",
        direct_runner=run_engine_d,
        direct_input=direct_input,
        candidate=candidate,
        window=window,
    )


def _build_engine_d_aligned_fixture(asset_root: Path) -> _ParityFixture:
    from engines.engine_d.engine_d_models import EngineDInput
    from local_replay_runtime.strategy_ladder_complete_enabler_support import (
        apply_build14_shadow_context,
    )
    from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
        build_engine_d_input_from_window,
    )

    pair = "BTCUSDT"
    timeframe = "5m"
    window_start_ms = 1_700_310_000_000
    window_end_ms = window_start_ms + 6 * 300_000
    ohlcv_rows: list[dict[str, object]] = []
    vals_pre = [100.0, 100.8, 101.6, 102.4, 103.2, 104.0, 103.5, 103.0, 102.5, 102.0, 101.8, 101.6]
    for i, close in enumerate(vals_pre):
        ts = window_start_ms - (12 - i) * 300_000
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=close,
                h=close + 0.18,
                l=close - 0.18,
                c=close,
                v=10.0,
            )
        )
    in_window_pattern = [102.0, 102.1, 102.0, 102.05, 102.0, 102.0]
    for i, close in enumerate(in_window_pattern):
        ts = window_start_ms + i * 300_000
        ohlcv_rows.append(
            _bar(
                pair=pair,
                timeframe=timeframe,
                ts_ms=ts,
                o=close,
                h=close + 0.08,
                l=close - 0.08,
                c=close,
                v=10.0,
            )
        )
    total_duration = (12 + len(in_window_pattern)) * 300_000
    trade_start_ms = window_start_ms - 12 * 300_000
    trade_rows: list[dict[str, object]] = []
    for i in range(220):
        ts = trade_start_ms + (i * total_duration) // 220
        if ts < window_start_ms:
            price = 101.8
        else:
            idx = min((ts - window_start_ms) // 300_000, len(in_window_pattern) - 1)
            price = float(in_window_pattern[idx])
        trade_rows.append(
            _trade(
                pair=pair,
                ts_ms=ts,
                price=price,
                qty=1.0,
                side="buy",
            )
        )
    ohlcv_path = asset_root / "engine_d_aligned" / "ohlcv_5m.jsonl"
    trade_path = asset_root / "engine_d_aligned" / "trades.jsonl"
    _write_jsonl(ohlcv_path, ohlcv_rows)
    _write_jsonl(trade_path, trade_rows)
    candidate = _candidate(
        engine_id="engine_d",
        case_id="engine_d_emit_builder_aligned",
        pair=pair,
        timeframe=timeframe,
        ts_ms=window_end_ms,
        planned_notional=800.0,
        compatibility_payload={
            "origin_context_id": "ctx-btc-01",
            "origin_trade_id": "trade-btc-01",
            "link_type": "prior_trade",
            "first_episode_id": "episode-btc-01",
            "first_episode_engine_id": "engine_a",
            "first_episode_close_reason": "time_stop",
            "consecutive_stop_count": 0,
            "last_fresh_a_detection_at_ns": 1_700_000_100_000_000_000,
            "anti_revenge_state": "reset_required",
            "prior_trade_quality": 0.85,
            "duplication_overlap_with_engine_a": 0.24,
            "marginal_portfolio_gain": 6.0,
            "covered_share_by_engine_a": 0.18,
            "concentration_headroom": 0.78,
            "reentry_lateness": 0.18,
            "structure_reformed_detected": True,
            "reentry_anchor_price": 101.5,
            "feature_values": {"book_depth_levels": 20},
        },
    )
    window = _window(
        case_id=candidate.candidate_id,
        engine_id="engine_d",
        pair=pair,
        ts_ms=window_end_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=trade_path,
        raw_ohlcv_path=ohlcv_path,
    )
    builder = build_engine_d_input_from_window(
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        window_start_ms=window.window_start_ms,
        window_end_ms=window.window_end_ms,
        raw_trade_path=window.raw_trade_path,
        raw_ohlcv_path=window.raw_ohlcv_path,
        first_episode_context=dict(candidate.compatibility_payload or {}),
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
    )
    direct_input = EngineDInput.model_validate(
        apply_build14_shadow_context(
            engine_id="engine_d",
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            candidate_payload=dict(candidate.compatibility_payload or {}),
            engine_input_payload=builder.engine_d_input_payload,
        ).adjusted_engine_input_payload
    )
    return _ParityFixture(
        engine_id="engine_d",
        case_id="emit_builder_aligned_candidate",
        direct_runner=run_engine_d,
        direct_input=direct_input,
        candidate=candidate,
        window=window,
        notes=("DIRECT_INPUT_DERIVED_FROM_BUILDER_PAYLOAD_FOR_PARITY_ALIGNMENT",),
    )


def _notes_for_case(
    *,
    fixture: _ParityFixture,
    builder_payload: dict[str, object],
) -> tuple[str, ...]:
    notes: list[str] = list(fixture.notes)
    if fixture.engine_id == "engine_c":
        try:
            direct = fixture.direct_input
            range_size = max(
                float(getattr(direct, "range_high")) - float(getattr(direct, "range_low")),
                1e-9,
            )
            geometric_extension = max(
                0.0,
                (float(getattr(direct, "entry_price")) - float(getattr(direct, "breakout_level")))
                / range_size,
            )
            declared_extension = float(getattr(direct, "extension_pct"))
            if abs(geometric_extension - declared_extension) > 0.10:
                notes.append("ENGINE_C_VIABILITY_INPUT_GEOMETRY_INCONSISTENT_WITH_BUILDER_FORMULA")
        except (AttributeError, TypeError, ValueError):
            pass
    if fixture.engine_id == "engine_d":
        if builder_payload.get("first_episode_id"):
            notes.append("ENGINE_D_FIRST_EPISODE_CONTEXT_CONSUMED")
        else:
            notes.append("ENGINE_D_FIRST_EPISODE_CONTEXT_NOT_CONSUMED")
    return tuple(notes)


def _materialize_builder_direct_payload(fixture: _ParityFixture) -> dict[str, object]:
    payload = dict(fixture.candidate.compatibility_payload or {})
    if fixture.engine_id == "engine_a":
        from local_replay_runtime.strategy_ladder_engine_a_input_builder import (
            build_engine_a_input_from_window,
        )
        from local_replay_runtime.strategy_ladder_engine_native_adapter import (
            build_engine_a_microstructure_inputs_from_window,
        )

        bridge = build_engine_a_microstructure_inputs_from_window(
            candidate_id=fixture.candidate.candidate_id,
            pair=fixture.candidate.pair,
            window_start_ms=fixture.window.window_start_ms,
            window_end_ms=fixture.window.window_end_ms,
            raw_trade_path=fixture.window.raw_trade_path,
            raw_book_path=fixture.window.raw_book_path,
            raw_book_delta_path=fixture.window.raw_book_delta_path,
        )
        builder = build_engine_a_input_from_window(
            candidate_id=fixture.candidate.candidate_id,
            pair=fixture.candidate.pair,
            window_start_ms=fixture.window.window_start_ms,
            window_end_ms=fixture.window.window_end_ms,
            raw_ohlcv_path=fixture.window.raw_ohlcv_path,
            microstructure_updates=bridge.engine_a_microstructure_updates,
            expected_gain=float(getattr(fixture.direct_input, "expected_gain")),
            expected_cost=float(getattr(fixture.direct_input, "expected_cost")),
            candidate_size=float(getattr(fixture.direct_input, "candidate_size")),
        )
        return dict(builder.engine_a_input_payload)
    if fixture.engine_id == "engine_b":
        from local_replay_runtime.strategy_ladder_engine_b_input_builder import (
            build_engine_b_input_from_window,
        )

        builder = build_engine_b_input_from_window(
            candidate_id=fixture.candidate.candidate_id,
            pair=fixture.candidate.pair,
            window_start_ms=fixture.window.window_start_ms,
            window_end_ms=fixture.window.window_end_ms,
            raw_trade_path=fixture.window.raw_trade_path,
            expected_gain=float(getattr(fixture.direct_input, "expected_gain")),
            expected_cost=float(getattr(fixture.direct_input, "expected_cost")),
            candidate_size=float(getattr(fixture.direct_input, "candidate_size")),
        )
        return dict(builder.engine_b_input_payload)
    if fixture.engine_id == "engine_c":
        from local_replay_runtime.strategy_ladder_complete_enabler_support import (
            apply_build14_shadow_context,
        )
        from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
            build_engine_c_input_from_window,
        )
        from local_replay_runtime.strategy_ladder_engine_native_adapter import (
            build_engine_c_microstructure_inputs_from_window,
        )

        bridge = build_engine_c_microstructure_inputs_from_window(
            candidate_id=fixture.candidate.candidate_id,
            pair=fixture.candidate.pair,
            window_start_ms=fixture.window.window_start_ms,
            window_end_ms=fixture.window.window_end_ms,
            raw_trade_path=fixture.window.raw_trade_path,
            raw_book_path=fixture.window.raw_book_path,
            raw_book_delta_path=fixture.window.raw_book_delta_path,
        )
        builder = build_engine_c_input_from_window(
            candidate_id=fixture.candidate.candidate_id,
            pair=fixture.candidate.pair,
            window_start_ms=fixture.window.window_start_ms,
            window_end_ms=fixture.window.window_end_ms,
            raw_trade_path=fixture.window.raw_trade_path,
            raw_ohlcv_path=fixture.window.raw_ohlcv_path,
            microstructure_partial_payload=bridge.engine_c_partial_input_payload,
            expected_gain=float(getattr(fixture.direct_input, "expected_gain")),
            expected_cost=float(getattr(fixture.direct_input, "expected_cost")),
            candidate_size=float(getattr(fixture.direct_input, "candidate_size")),
        )
        return dict(
            apply_build14_shadow_context(
                engine_id=fixture.engine_id,
                candidate_id=fixture.candidate.candidate_id,
                pair=fixture.candidate.pair,
                candidate_payload=payload,
                engine_input_payload=builder.engine_c_input_payload,
            ).adjusted_engine_input_payload
        )
    if fixture.engine_id == "engine_d":
        from local_replay_runtime.strategy_ladder_complete_enabler_support import (
            apply_build14_shadow_context,
        )
        from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
            build_engine_d_input_from_window,
        )
        from local_replay_runtime.strategy_ladder_runner import (
            _extract_engine_d_first_episode_context,
        )

        builder = build_engine_d_input_from_window(
            candidate_id=fixture.candidate.candidate_id,
            pair=fixture.candidate.pair,
            window_start_ms=fixture.window.window_start_ms,
            window_end_ms=fixture.window.window_end_ms,
            raw_trade_path=fixture.window.raw_trade_path,
            raw_ohlcv_path=fixture.window.raw_ohlcv_path,
            first_episode_context=_extract_engine_d_first_episode_context(payload),
            expected_gain=float(getattr(fixture.direct_input, "expected_gain")),
            expected_cost=float(getattr(fixture.direct_input, "expected_cost")),
            candidate_size=float(getattr(fixture.direct_input, "candidate_size")),
        )
        return dict(
            apply_build14_shadow_context(
                engine_id=fixture.engine_id,
                candidate_id=fixture.candidate.candidate_id,
                pair=fixture.candidate.pair,
                candidate_payload=payload,
                engine_input_payload=builder.engine_d_input_payload,
            ).adjusted_engine_input_payload
        )
    raise ValueError(f"unsupported engine_id: {fixture.engine_id}")


def _run_builder_direct_decision(
    fixture: _ParityFixture,
    builder_direct_payload: dict[str, object],
) -> str:
    if fixture.engine_id == "engine_a":
        from engines.engine_a.engine_a_runner import EngineAInput

        return _enum_value(run_engine_a(EngineAInput.model_validate(builder_direct_payload)).decision)
    if fixture.engine_id == "engine_b":
        from engines.engine_b.engine_b_runner import EngineBInput

        return _enum_value(run_engine_b(EngineBInput.model_validate(builder_direct_payload)).decision)
    if fixture.engine_id == "engine_c":
        from engines.engine_c.engine_c_runner import EngineCInput

        return _enum_value(run_engine_c(EngineCInput.model_validate(builder_direct_payload)).decision)
    if fixture.engine_id == "engine_d":
        from engines.engine_d.engine_d_models import EngineDInput

        return _enum_value(run_engine_d(EngineDInput.model_validate(builder_direct_payload)).decision)
    raise ValueError(f"unsupported engine_id: {fixture.engine_id}")


def _run_fixture(fixture: _ParityFixture) -> SyntheticB2ParityCaseResult:
    direct_output = fixture.direct_runner(fixture.direct_input)
    viability_direct_decision = _enum_value(getattr(direct_output, "decision"))
    builder_direct_payload = _materialize_builder_direct_payload(fixture)
    builder_direct_decision = _run_builder_direct_decision(
        fixture,
        builder_direct_payload,
    )
    economic_provenance = _economic_provenance(
        expected_gain=float(getattr(fixture.direct_input, "expected_gain")),
        expected_cost=float(getattr(fixture.direct_input, "expected_cost")),
    )
    synthetic_event, records_built, _runner_invoked = _run_native_engine_candidate(
        candidate=fixture.candidate,
        window=fixture.window,
        economic_provenance=economic_provenance,
    )
    payload = dict(synthetic_event.compatibility_payload or {})
    builder_path_decision = str(payload.get("engine_native_decision") or "not_invoked")
    return SyntheticB2ParityCaseResult(
        engine_id=fixture.engine_id,
        case_id=fixture.case_id,
        viability_direct_decision=viability_direct_decision,
        builder_direct_decision=builder_direct_decision,
        builder_path_decision=builder_path_decision,
        viability_vs_builder_status=(
            "PARITY_OK"
            if viability_direct_decision == builder_direct_decision
            else "PARITY_MISMATCH"
        ),
        builder_vs_runner_status=(
            "PARITY_OK"
            if builder_direct_decision == builder_path_decision
            else "PARITY_MISMATCH"
        ),
        builder_status=str(payload.get("engine_native_builder_status") or ""),
        input_provenance=str(payload.get("engine_native_input_provenance") or ""),
        runner_status=str(payload.get("engine_native_status") or ""),
        records_built=records_built,
        builder_reason_codes=tuple(
            str(item)
            for item in tuple(payload.get("engine_native_reason_codes") or ())
        ),
        builder_no_trade_reasons=tuple(
            str(item)
            for item in tuple(payload.get("engine_native_no_trade_reasons") or ())
        ),
        notes=_notes_for_case(fixture=fixture, builder_payload=payload),
    )


def run_synthetic_b2_parity_report(
    asset_root: Path | str | None = None,
) -> SyntheticB2ParityReport:
    base_root = (
        Path(asset_root)
        if asset_root is not None
        else Path(
            tempfile.mkdtemp(
                prefix="strategy_ladder_synth_b2_parity_",
                dir=Path.cwd() / ".test_tmp",
            )
        )
    )
    base_root.mkdir(parents=True, exist_ok=True)
    fixtures = (
        _build_engine_a_fixture(base_root),
        _build_engine_b_fixture(base_root),
        _build_engine_c_fixture(base_root),
        _build_engine_c_aligned_fixture(base_root),
        _build_engine_d_fixture(base_root),
        _build_engine_d_aligned_fixture(base_root),
    )
    results = tuple(_run_fixture(fixture) for fixture in fixtures)
    return SyntheticB2ParityReport(
        schema_version="strategy_ladder.synthetic_b2_parity.v1",
        generated_at=datetime.now(tz=UTC).isoformat(),
        diagnostic_only=True,
        asset_root=str(base_root.resolve()),
        cases=results,
    )


def render_synthetic_b2_parity_report(report: SyntheticB2ParityReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


__all__ = [
    "SyntheticB2ParityCaseResult",
    "SyntheticB2ParityReport",
    "run_synthetic_b2_parity_report",
    "render_synthetic_b2_parity_report",
]
