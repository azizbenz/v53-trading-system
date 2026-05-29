from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from local_replay_runtime.strategy_ladder_b_ml_label_factory import (
    BML_SCHEMA_VERSION,
    BML_TARGET_POLICY,
    TRAINING_ROW_ELIGIBLE,
    BmlLabelFactoryRequest,
    BmlLabelStoreRow,
    run_bml_label_factory,
)


def _ts(raw_value: str) -> int:
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.astimezone(UTC).timestamp() * 1000)


def _write_rows(root: Path) -> None:
    path = root / "gold" / "features_1m" / "BTCUSDT" / "2025" / "04" / "features.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for timestamp_ms, close_price in (
        (_ts("2025-04-01T00:00:00Z"), 100.0),
        (_ts("2025-04-01T00:01:00Z"), 100.5),
    ):
        rows.append(
            {
                "timestamp_ms": timestamp_ms,
                "pair": "BTCUSDT",
                "timeframe": "1m",
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
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_b_ml_label_store_rows_have_stable_schema_and_policy(tmp_path: Path) -> None:
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-schema",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("1m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("1m",),
            capital_buckets=(400,),
            max_candidates_per_day=1,
        )
    )

    payload = json.loads(Path(result.label_store_path).read_text(encoding="utf-8").splitlines()[0])
    row = BmlLabelStoreRow.model_validate(payload)
    assert row.schema_version == BML_SCHEMA_VERSION
    assert row.target_policy == BML_TARGET_POLICY
    assert row.training_row_status == TRAINING_ROW_ELIGIBLE
    assert row.raw_window_refs["ohlcv"].endswith("features.jsonl")
    assert row.promotion_allowed is False
