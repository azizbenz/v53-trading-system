from __future__ import annotations

import json

from local_replay_runtime import tabular_artifacts
from local_replay_runtime.tabular_artifacts import (
    read_tabular_mirror_rows_if_ready,
    write_tabular_mirror,
)


def test_tabular_mirror_writes_parquet_when_pyarrow_is_available(tmp_path):
    if not tabular_artifacts._pyarrow_available():
        return
    source_path = tmp_path / "rows.jsonl"
    rows = [
        {
            "candidate_id": "c1",
            "pair": "BTCUSDT",
            "timestamp_ms": 1,
            "spread_bps": 1.2,
            "feature_values": {"close_return": 0.1},
        },
        {
            "candidate_id": "c2",
            "pair": "BTCUSDT",
            "timestamp_ms": 2,
            "spread_bps": 1.4,
            "feature_values": {"close_return": 0.2},
        },
    ]
    source_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    manifest = write_tabular_mirror(
        rows=rows,
        artifact_name="rows",
        output_dir=tmp_path,
        source_path=source_path,
    )

    assert manifest["status"] == "TABULAR_MIRROR_PARQUET_READY"
    assert manifest["storage_format"] == "parquet"
    assert manifest["row_count"] == 2
    assert manifest["audit_jsonl_preserved"] is True
    assert (tmp_path / "rows.parquet").is_file()
    assert (tmp_path / "rows.tabular_manifest.json").is_file()

    import pyarrow.parquet as pq

    table = pq.read_table(tmp_path / "rows.parquet")
    payload = table.to_pylist()
    assert len(payload) == 2
    assert payload[0]["candidate_id"] == "c1"
    assert json.loads(payload[0]["feature_values"]) == {"close_return": 0.1}
    mirrored_rows = read_tabular_mirror_rows_if_ready(source_path)
    assert mirrored_rows is not None
    assert len(mirrored_rows) == 2
    assert mirrored_rows[1]["candidate_id"] == "c2"


def test_tabular_mirror_falls_back_to_columnar_json_without_pyarrow(tmp_path, monkeypatch):
    monkeypatch.setattr(tabular_artifacts, "_pyarrow_available", lambda: False)
    source_path = tmp_path / "rows.jsonl"
    rows = [
        {"candidate_id": "c1", "pair": "BTCUSDT", "timestamp_ms": 1},
        {"candidate_id": "c2", "pair": "ETHUSDT", "timestamp_ms": 2},
    ]
    source_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    manifest = write_tabular_mirror(
        rows=rows,
        artifact_name="candidate_events",
        output_dir=tmp_path,
        source_path=source_path,
    )

    assert manifest["status"] == "TABULAR_MIRROR_COLUMNAR_JSON_READY"
    assert manifest["storage_format"] == "columnar_json"
    assert manifest["fallback_reason"] == "PYARROW_NOT_AVAILABLE"
    payload = json.loads((tmp_path / "candidate_events.columns.json").read_text(encoding="utf-8"))
    assert payload["columns"] == ["candidate_id", "pair", "timestamp_ms"]
    assert payload["rows"] == [["c1", "BTCUSDT", 1], ["c2", "ETHUSDT", 2]]
    assert read_tabular_mirror_rows_if_ready(source_path) is None


def test_tabular_mirror_reader_requires_matching_ready_manifest(tmp_path):
    if not tabular_artifacts._pyarrow_available():
        return
    source_path = tmp_path / "rows.jsonl"
    source_path.write_text('{"candidate_id":"c1"}\n', encoding="utf-8")
    manifest = write_tabular_mirror(
        rows=({"candidate_id": "c1"},),
        artifact_name="rows",
        output_dir=tmp_path,
        source_path=source_path,
    )
    manifest_path = tmp_path / "rows.tabular_manifest.json"
    manifest["source_path"] = str((tmp_path / "other.jsonl").resolve())
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    assert read_tabular_mirror_rows_if_ready(source_path) is None
