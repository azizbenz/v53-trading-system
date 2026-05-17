"""IA Lab adapter over the governed gold feature store."""

from __future__ import annotations

from datetime import UTC, datetime
import gzip
import io
import json
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.gold_microstructure_feature_builder import (
    build_gold_microstructure_feature_manifest,
)
from local_replay_runtime.raw_data_processing_contracts import (
    ExpectedEdgeFeatureManifest,
    GoldMicrostructureFeatureManifest,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_feature_store import (
    load_strategy_ladder_feature_store,
    parse_time_boundary_to_ms,
)
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


EXPECTED_EDGE_TRAINING_FEATURE_ROWS_FILENAME = "expected_edge_training_feature_rows.jsonl.gz"
EXPECTED_EDGE_FEATURE_MANIFEST_FILENAME = "expected_edge_feature_manifest.json"


def _boundary_ms(raw_value: str, *, end_of_day: bool) -> int | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    parsed = parse_time_boundary_to_ms(value)
    if parsed is None:
        return None
    if end_of_day and len(value) == 10 and "T" not in value and " " not in value:
        return parsed + 86_399_999
    return parsed


def _write_jsonl_gz(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    payload = "\n".join(
        json.dumps(row, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        for row in rows
    )
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz:
        gz.write(payload.encode("utf-8"))
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(buffer.getvalue())
    tmp_path.replace(path)


def _dataset_rows(rows, *, selected_feature_names: tuple[str, ...]) -> tuple[dict[str, object], ...]:  # noqa: ANN001
    feature_name_filter = set(selected_feature_names)
    records: list[dict[str, object]] = []
    for row in rows:
        feature_values = {
            key: value
            for key, value in row.feature_values.items()
            if not feature_name_filter or key in feature_name_filter
        }
        records.append(
            {
                "schema_version": "v1",
                "decision_timestamp_ms": row.resolved_timestamp_ms,
                "feature_timestamp_ms": row.available_at_timestamp_ms or row.resolved_timestamp_ms,
                "pair": row.pair,
                "timeframe": row.timeframe,
                "engine_scope": row.resolved_engine_ids,
                "feature_values": feature_values,
                "source_ref": row.source_ref,
                "feature_sources_used": row.feature_sources_used,
                "trade_feature_status": row.trade_feature_status,
                "kline_feature_status": row.kline_feature_status,
                "orderbook_feature_status": row.orderbook_feature_status,
                "spread_bps": row.spread_bps,
                "slippage_bps": row.slippage_bps,
                "latency_penalty_bps": row.latency_penalty_bps,
                "input_data_hash": row.input_data_hash,
                "method_version_hash": row.method_version_hash,
            }
        )
    return tuple(records)


def build_expected_edge_feature_dataset(
    *,
    gold_root: Path,
    output_dir: Path,
    dataset_id: str = "expected_edge_training_dataset",
    pairs: tuple[str, ...] = (),
    timeframes: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
    feature_names: tuple[str, ...] = (),
    purge_window_minutes: int = 0,
    embargo_window_minutes: int = 0,
    source_silver_index_ref: str = "",
    gold_manifest: GoldMicrostructureFeatureManifest | None = None,
) -> ExpectedEdgeFeatureManifest:
    """Build the IA Lab expected-edge dataset without training any model."""

    resolved_gold_manifest = gold_manifest or build_gold_microstructure_feature_manifest(
        gold_root=gold_root,
        pairs=pairs,
        timeframes=timeframes,
        start=start,
        end=end,
    )
    result = load_strategy_ladder_feature_store(
        gold_root,
        pairs=pairs,
        timeframes=timeframes,
        start_ms=_boundary_ms(start, end_of_day=False),
        end_ms=_boundary_ms(end, end_of_day=True),
    )
    rows = result.rows
    dataset_rows = _dataset_rows(rows, selected_feature_names=feature_names)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / EXPECTED_EDGE_TRAINING_FEATURE_ROWS_FILENAME
    if dataset_rows:
        _write_jsonl_gz(dataset_path, dataset_rows)
    feature_hash = resolved_gold_manifest.feature_hash
    dataset_hash = deterministic_payload_hash(dataset_rows) if dataset_rows else None
    source_refs = {str(item.get("source_ref") or "").strip() for item in dataset_rows}
    source_refs.discard("")
    status = "EXPECTED_EDGE_FEATURE_DATASET_BLOCKED"
    blockers = list(result.blocker_codes)
    if not dataset_rows:
        blockers.append("EXPECTED_EDGE_FEATURE_ROWS_EMPTY")
    elif not source_refs:
        blockers.append("EXPECTED_EDGE_SOURCE_REFS_EMPTY")
        status = "EXPECTED_EDGE_FEATURE_DATASET_BLOCKED"
    else:
        status = "EXPECTED_EDGE_FEATURE_DATASET_READY"
        if resolved_gold_manifest.feature_groups_missing:
            status = "EXPECTED_EDGE_FEATURE_DATASET_PARTIAL"
    manifest = finalize_hashed_model(
        ExpectedEdgeFeatureManifest(
            dataset_id=dataset_id,
            status=status,
            row_count=len(dataset_rows),
            pair_scope=resolved_gold_manifest.symbol_scope,
            timeframe_scope=resolved_gold_manifest.timeframe_scope,
            feature_names=feature_names or resolved_gold_manifest.feature_names,
            feature_groups_generated=resolved_gold_manifest.feature_groups_generated,
            feature_groups_missing=resolved_gold_manifest.feature_groups_missing,
            feature_hash=feature_hash,
            dataset_hash=dataset_hash,
            feature_timestamp_policy=resolved_gold_manifest.feature_timestamp_policy,
            purge_window_minutes=purge_window_minutes,
            embargo_window_minutes=embargo_window_minutes,
            source_refs_count=len(source_refs),
            output_path=str(dataset_path.resolve()),
            source_gold_feature_refs=resolved_gold_manifest.output_paths,
            source_silver_index_ref=source_silver_index_ref,
            modules_used=(
                *resolved_gold_manifest.modules_used,
                "local_replay_runtime.ia_lab_feature_dataset_adapter",
            ),
            quant_equation_refs=resolved_gold_manifest.quant_equation_refs,
            blocker_codes=tuple(dict.fromkeys(blockers)),
        )
    )
    atomic_write_json(
        output_dir / EXPECTED_EDGE_FEATURE_MANIFEST_FILENAME,
        manifest.model_dump(mode="json"),
        indent=2,
    )
    return manifest


__all__ = [
    "EXPECTED_EDGE_FEATURE_MANIFEST_FILENAME",
    "EXPECTED_EDGE_TRAINING_FEATURE_ROWS_FILENAME",
    "build_expected_edge_feature_dataset",
]
