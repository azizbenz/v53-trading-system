from __future__ import annotations

from decimal import Decimal
from itertools import permutations
from pathlib import Path
from uuid import UUID

import pytest

from interface_contracts import BetStructure, EngineId, ForecastHorizonClass, ForecastTargetClass, Side
from protocols import ClosedEpisodeJournal, EpisodeCloseReason, EpisodeRef


NOW_NS = 1_700_000_000_000_000_000


def _episode(
    suffix: int,
    *,
    pair: str = "BTCUSDT",
    side: Side = Side.BUY,
    engine_id: EngineId = EngineId.A,
    closed_at_ns: int | None = None,
    close_reason: EpisodeCloseReason = EpisodeCloseReason.TAKE_PROFIT,
) -> EpisodeRef:
    return EpisodeRef(
        episode_id=UUID(f"00000000-0000-0000-0000-{suffix:012d}"),
        engine_id_of_origin=engine_id,
        pair=pair,
        side=side,
        entry_level=Decimal("100.0"),
        exit_level=Decimal("103.0"),
        bet_structure=BetStructure.BREAKOUT,
        forecast_horizon_class=ForecastHorizonClass.SHORT,
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        closed_at_ns=closed_at_ns or NOW_NS + suffix,
        close_reason=close_reason,
        realized_pnl_decimal=Decimal("3.0"),
    )


def test_episode_ref_rejects_non_ac_origin_engine() -> None:
    with pytest.raises(ValueError, match="engine_a or engine_c"):
        _episode(1, engine_id=EngineId.D)


def test_closed_episode_journal_is_append_only_and_returns_immutable_snapshots() -> None:
    journal = ClosedEpisodeJournal()
    first = _episode(1)
    second = _episode(2)

    journal.append(first)
    snapshot = journal.read()
    journal.append(second)

    assert snapshot == (first,)
    assert journal.read() == (first, second)
    assert journal.size == 2


def test_closed_episode_journal_filters_stop_out_for_engine_d_without_hiding_evidence() -> None:
    journal = ClosedEpisodeJournal()
    stop_out = _episode(1, close_reason=EpisodeCloseReason.STOP_OUT, closed_at_ns=NOW_NS + 10)
    valid = _episode(2, close_reason=EpisodeCloseReason.TIME_STOP, closed_at_ns=NOW_NS + 20)
    journal.append(stop_out)
    journal.append(valid)

    assert journal.read() == (stop_out, valid)
    assert journal.eligible_for_engine_d(pair="BTCUSDT", side=Side.BUY) == (valid,)


def test_most_recent_eligible_episode_resolution_is_order_independent() -> None:
    episodes = (
        _episode(1, closed_at_ns=NOW_NS + 10),
        _episode(2, closed_at_ns=NOW_NS + 30),
        _episode(3, closed_at_ns=NOW_NS + 20),
    )

    for ordering in permutations(episodes):
        journal = ClosedEpisodeJournal()
        journal.append_batch(ordering)
        selected = journal.most_recent_eligible_for_engine_d(pair="BTCUSDT", side=Side.BUY)
        assert selected is not None
        assert selected.episode_id == episodes[1].episode_id


def test_closed_episode_journal_round_trips_records_and_manifest(repo_tmp_path: Path) -> None:
    journal = ClosedEpisodeJournal(flush_dir=repo_tmp_path)
    journal.append(_episode(1))
    journal.append(_episode(2, engine_id=EngineId.C, pair="ETHUSDT", side=Side.SELL))

    manifest = journal.flush_to_disk()
    loaded = ClosedEpisodeJournal.load_from_disk(repo_tmp_path)

    assert manifest is not None
    assert manifest.record_count == 2
    assert loaded.read() == journal.read()
    assert loaded.pending_flush_count == 0


def test_closed_episode_journal_rejects_manifest_mismatch(repo_tmp_path: Path) -> None:
    journal = ClosedEpisodeJournal(flush_dir=repo_tmp_path)
    journal.append(_episode(1))
    journal.flush_to_disk()

    (repo_tmp_path / "closed_episodes.jsonl").write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="manifest hash mismatch"):
        ClosedEpisodeJournal.load_from_disk(repo_tmp_path)
