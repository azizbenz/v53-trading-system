"""Export helpers for governed LOCAL_REPLAY DTR artifacts."""

from __future__ import annotations

from typing import Any

from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


def export_replay_dtr_records(
    records: tuple[DTRRecord, ...],
) -> tuple[dict[str, Any], ...]:
    """Convert typed DTR records into stable JSON-exportable dictionaries."""

    return tuple(record.model_dump(mode="json") for record in records)


__all__ = ["export_replay_dtr_records"]
