"""Export helpers for governed LOCAL_REPLAY DTR artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


def export_replay_dtr_records(
    records: tuple[DTRRecord, ...],
) -> tuple[dict[str, Any], ...]:
    """Convert typed DTR records into stable JSON-exportable dictionaries."""

    return tuple(record.model_dump(mode="json") for record in records)


def load_replay_dtr_records(path: Path | str) -> tuple[DTRRecord, ...]:
    """Load governed replay DTR records from `.json` or `.jsonl`."""

    candidate = Path(path)
    suffix = candidate.suffix.lower()
    if suffix == ".json":
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Replay DTR JSON exports must contain a list of objects")
        return tuple(DTRRecord.model_validate(item) for item in payload)
    if suffix == ".jsonl":
        records: list[DTRRecord] = []
        for line in candidate.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            records.append(DTRRecord.model_validate(json.loads(stripped)))
        return tuple(records)
    raise ValueError("Replay DTR exports must use .json or .jsonl")


__all__ = ["export_replay_dtr_records", "load_replay_dtr_records"]
