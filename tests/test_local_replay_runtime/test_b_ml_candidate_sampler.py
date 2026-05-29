from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from local_replay_runtime.strategy_ladder_b_ml_label_factory import (
    BmlLabelFactoryRequest,
    run_bml_label_factory,
)


def _ts(raw_value: str) -> int:
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.astimezone(UTC).timestamp() * 1000)


def _row(pair: str, timestamp_ms: int, close_price: float) -> dict[str, object]:
    return {
        "timestamp_ms": timestamp_ms,
        "pair": pair,
        "timeframe": "5m",
        "available_at_timestamp_ms": timestamp_ms,
        "close_price": close_price,
        "feature_values": {
            "close_return": 0.001,
            "high_low_range": 0.002,
            "volume": 10.0,
        },
        "spread_bps": 1.0,
        "spread_provenance": "MEASURED_FROM_BOOK_SNAPSHOT",
        "slippage_bps": 0.4,
        "slippage_provenance": "MEASURED_FROM_DEPTH20_BOOK_WALK",
        "latency_penalty_bps": 0.1,
        "taker_fee_rate": 0.001,
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        "feature_sources_used": ["klines", "orderbook", "trades", "metadata"],
    }


def _write_pair(root: Path, pair: str, rows: list[dict[str, object]]) -> None:
    path = root / "gold" / "features_5m" / pair / "2025" / "04" / "features.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_b_ml_sampler_cap_is_applied_per_pair_timeframe_day(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    for pair in ("BTCUSDT", "BNBUSDT"):
        _write_pair(
            a2_root,
            pair,
            [
                _row(pair, _ts("2025-04-01T00:00:00Z"), 100.0),
                _row(pair, _ts("2025-04-01T00:05:00Z"), 101.0),
                _row(pair, _ts("2025-04-01T00:10:00Z"), 102.0),
            ],
        )

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-sampler",
            a2_run_root=a2_root,
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT", "BNBUSDT"),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=1,
        )
    )

    assert result.row_count == 2
    candidate_events = (
        tmp_path / "b_ml" / "candidates" / "b_ml_candidate_events.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert len(candidate_events) == 2
    assert {json.loads(line)["pair"] for line in candidate_events} == {"BTCUSDT", "BNBUSDT"}


def test_b_ml_sampler_zero_cap_means_uncapped_background_grid(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    _write_pair(
        a2_root,
        "BTCUSDT",
        [
            _row("BTCUSDT", _ts("2025-04-01T00:00:00Z"), 100.0),
            _row("BTCUSDT", _ts("2025-04-01T00:05:00Z"), 101.0),
            _row("BTCUSDT", _ts("2025-04-01T00:10:00Z"), 102.0),
        ],
    )

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-sampler",
            a2_run_root=a2_root,
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=0,
        )
    )

    assert result.row_count == 3


def test_b_ml_reuses_b1_fast_candidates_when_explicitly_requested(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    decision_ts = _ts("2025-04-01T00:00:00Z")
    _write_pair(
        a2_root,
        "BTCUSDT",
        [
            _row("BTCUSDT", decision_ts, 100.0),
            _row("BTCUSDT", _ts("2025-04-01T00:05:00Z"), 101.0),
        ],
    )
    b1_path = tmp_path / "b1" / "candidate_events.jsonl"
    b1_path.parent.mkdir(parents=True, exist_ok=True)
    b1_path.write_text(
        json.dumps(
            {
                "candidate_id": "b1-candidate-1",
                "timestamp_ms": decision_ts,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_a",
                "strategy_id": "engine_a",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
                "preliminary_reason_codes": ["ENGINE_NATIVE_DRY_EVAL"],
                "compatibility_payload": {"side": "buy"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-reuse-b1",
            a2_run_root=a2_root,
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            candidate_sampler_mode="REUSE_B1_FAST_CANDIDATES",
            b1_candidate_events_path=b1_path,
        )
    )

    assert result.row_count == 1
    payload = json.loads(Path(result.label_store_path).read_text(encoding="utf-8").splitlines()[0])
    assert payload["candidate_id"] == "b1-candidate-1"
    assert payload["candidate_source"] == "REUSED_B1_DISCOVERY"
    assert payload["engine_id"] == "engine_a"
