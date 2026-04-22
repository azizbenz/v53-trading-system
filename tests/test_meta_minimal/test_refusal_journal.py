"""Build-9 tests for meta_minimal refusal_journal."""

from __future__ import annotations

from pathlib import Path

import pytest

from interface_contracts import EngineId, RefusalCategory, RefusalRecord
from meta_minimal.refusal_journal import RefusalJournal


NOW_MS = 1_700_000_000_000


def _record(
    *,
    pair: str = "BTCUSDT",
    engine_id: EngineId | None = EngineId.A,
    category: RefusalCategory = RefusalCategory.NO_TRADE,
    reason_codes: tuple[str, ...] = ("engine.cost_too_high",),
    timestamp_ms: int = NOW_MS,
) -> RefusalRecord:
    return RefusalRecord(
        timestamp_ms=timestamp_ms,
        pair=pair,
        engine_id=engine_id,
        category=category,
        reason_codes=reason_codes,
    )


class TestRefusalJournal:
    def test_append_and_read(self) -> None:
        journal = RefusalJournal()
        journal.append(_record())
        assert journal.size == 1
        assert journal.read()[0].pair == "BTCUSDT"

    def test_getters_by_pair_engine_and_category(self) -> None:
        journal = RefusalJournal()
        journal.append(_record(pair="BTCUSDT", engine_id=EngineId.A, category=RefusalCategory.NO_TRADE))
        journal.append(_record(pair="ETHUSDT", engine_id=EngineId.B, category=RefusalCategory.HARD_BLOCK))
        assert len(journal.get_by_pair("btcusdt")) == 1
        assert len(journal.get_by_engine(EngineId.B.value)) == 1
        assert len(journal.get_by_category(RefusalCategory.HARD_BLOCK)) == 1

    def test_count_by_category_returns_append_only_counts(self) -> None:
        journal = RefusalJournal()
        journal.append(_record(category=RefusalCategory.NO_TRADE))
        journal.append(_record(pair="ETHUSDT", category=RefusalCategory.NO_TRADE))
        journal.append(_record(pair="SOLUSDT", category=RefusalCategory.HARD_BLOCK))

        assert journal.count_by_category() == {
            RefusalCategory.NO_TRADE: 2,
            RefusalCategory.HARD_BLOCK: 1,
        }

    def test_flush_to_disk_writes_jsonl_and_manifest(self, repo_tmp_path: Path) -> None:
        journal = RefusalJournal(flush_dir=repo_tmp_path)
        journal.append(_record())
        manifest = journal.flush_to_disk()
        assert manifest is not None
        assert manifest.record_count == 1
        assert (repo_tmp_path / "refusal_records.jsonl").exists()
        assert (repo_tmp_path / "refusal_manifest.json").exists()
        assert journal.pending_flush_count == 0

    def test_load_from_disk_round_trips_records(self, repo_tmp_path: Path) -> None:
        journal = RefusalJournal(flush_dir=repo_tmp_path)
        journal.append(_record())
        journal.append(_record(pair="ETHUSDT", engine_id=EngineId.C, category=RefusalCategory.PHANTOM))
        journal.flush_to_disk()

        loaded = RefusalJournal.load_from_disk(repo_tmp_path)
        assert loaded.size == 2
        assert loaded.read()[1].category == RefusalCategory.PHANTOM
        assert loaded.pending_flush_count == 0

    def test_load_from_disk_rejects_manifest_mismatch(self, repo_tmp_path: Path) -> None:
        journal = RefusalJournal(flush_dir=repo_tmp_path)
        journal.append(_record())
        journal.flush_to_disk()

        (repo_tmp_path / "refusal_records.jsonl").write_text('{"tampered": true}\n', encoding="utf-8")

        with pytest.raises(ValueError, match="manifest hash mismatch"):
            RefusalJournal.load_from_disk(repo_tmp_path)
