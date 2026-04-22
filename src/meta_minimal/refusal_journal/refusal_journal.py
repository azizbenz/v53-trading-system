"""Append-only refusal journal with JSONL + manifest persistence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from interface_contracts.refusal_records import RefusalCategory, RefusalRecord


class RefusalJournalManifest(BaseModel, frozen=True):
    """Audit manifest for a flushed refusal journal snapshot."""

    schema_version: str = "1.0"
    record_count: int = Field(..., ge=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    flushed_at_ms: int = Field(..., ge=1_000_000_000_000, le=9_999_999_999_999)
    last_refusal_ms: int | None = Field(default=None, ge=1_000_000_000_000, le=9_999_999_999_999)


class RefusalJournal:
    """Append-only refusal journal with deterministic snapshot persistence."""

    def __init__(self, flush_dir: Path | None = None) -> None:
        self._records: list[RefusalRecord] = []
        self._serialized_lines: list[str] = []
        self._records_by_pair: dict[str, list[RefusalRecord]] = {}
        self._records_by_engine: dict[str, list[RefusalRecord]] = {}
        self._records_by_category: dict[RefusalCategory, list[RefusalRecord]] = {}
        self._flush_dir = Path(flush_dir) if flush_dir is not None else None
        self._last_flush_index = 0

    def append(self, record: RefusalRecord) -> RefusalRecord:
        serialized = record.model_dump_json()
        self._records.append(record)
        self._serialized_lines.append(serialized)
        self._records_by_pair.setdefault(record.pair, []).append(record)
        if record.engine_id is not None:
            self._records_by_engine.setdefault(record.engine_id.value, []).append(record)
        self._records_by_category.setdefault(record.category, []).append(record)
        return record

    def append_batch(self, records: tuple[RefusalRecord, ...]) -> int:
        for record in records:
            self.append(record)
        return len(records)

    def read(self) -> tuple[RefusalRecord, ...]:
        return tuple(self._records)

    def get_by_pair(self, pair: str) -> tuple[RefusalRecord, ...]:
        return tuple(self._records_by_pair.get(pair.upper().strip(), ()))

    def get_by_engine(self, engine_id: str) -> tuple[RefusalRecord, ...]:
        return tuple(self._records_by_engine.get(engine_id, ()))

    def get_by_category(self, category: RefusalCategory) -> tuple[RefusalRecord, ...]:
        return tuple(self._records_by_category.get(category, ()))

    def count_by_category(self) -> dict[RefusalCategory, int]:
        return {
            category: len(records)
            for category, records in self._records_by_category.items()
        }

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def pending_flush_count(self) -> int:
        return len(self._records) - self._last_flush_index

    def flush_to_disk(self, flush_dir: Path | None = None, *, flushed_at_ms: int | None = None) -> RefusalJournalManifest | None:
        target_dir = Path(flush_dir) if flush_dir is not None else self._flush_dir
        if target_dir is None:
            return None

        jsonl_text = self._build_jsonl_text()
        jsonl_path = target_dir / "refusal_records.jsonl"
        manifest_path = target_dir / "refusal_manifest.json"
        atomic_write_text(jsonl_path, jsonl_text)

        manifest = RefusalJournalManifest(
            record_count=len(self._records),
            sha256=self._compute_sha256(jsonl_text),
            flushed_at_ms=flushed_at_ms or self._infer_flush_timestamp_ms(),
            last_refusal_ms=self._records[-1].timestamp_ms if self._records else None,
        )
        atomic_write_json(manifest_path, manifest.model_dump(mode="json"))
        self._last_flush_index = len(self._records)
        return manifest

    @classmethod
    def load_from_disk(cls, flush_dir: Path) -> "RefusalJournal":
        target_dir = Path(flush_dir)
        jsonl_path = target_dir / "refusal_records.jsonl"
        manifest_path = target_dir / "refusal_manifest.json"

        journal = cls(flush_dir=target_dir)
        if not jsonl_path.exists():
            return journal

        jsonl_text = jsonl_path.read_text(encoding="utf-8")
        if manifest_path.exists():
            manifest = RefusalJournalManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            actual_sha = cls._compute_sha256(jsonl_text)
            if manifest.sha256 != actual_sha:
                raise ValueError("refusal journal manifest hash mismatch")

        for line in jsonl_text.splitlines():
            if not line.strip():
                continue
            journal.append(RefusalRecord.model_validate_json(line))

        journal._last_flush_index = len(journal._records)
        return journal

    def _build_jsonl_text(self) -> str:
        if not self._serialized_lines:
            return ""
        return "\n".join(self._serialized_lines) + "\n"

    def _infer_flush_timestamp_ms(self) -> int:
        if self._records:
            return self._records[-1].timestamp_ms
        return 1_700_000_000_000

    @staticmethod
    def _compute_sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RefusalJournalSink:
    """Minimal adapter exposing the execution refusal sink protocol."""

    def __init__(self, journal: RefusalJournal) -> None:
        self._journal = journal

    def record_refusal(self, record: RefusalRecord) -> None:
        self._journal.append(record)


__all__ = ["RefusalJournal", "RefusalJournalManifest", "RefusalJournalSink"]
