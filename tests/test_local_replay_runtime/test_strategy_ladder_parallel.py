"""Phase 3 parallel core — parity + order-preservation + auto-detect tests.

Gate: the parallel path must produce results identical to serial, in the SAME
order (despite affinity reshuffling), and the worker count must auto-resolve from
the CPU at runtime with a safe serial default.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_parallel import (
    ordered_parallel_map,
    resolve_worker_count,
)
from local_replay_runtime.strategy_ladder_resource_guard import (
    StrategyLadderMemoryStatus,
    StrategyLadderResourceGuardError,
    cap_workers_for_ram,
    set_memory_status_provider_for_tests,
)


# module-level workers (must be picklable for Windows spawn)
def _square(x: int) -> int:
    return x * x


def _affinity_mod3(x: int) -> int:
    return x % 3


def test_default_is_serial(monkeypatch) -> None:
    monkeypatch.delenv("V53_MAX_WORKERS", raising=False)
    assert resolve_worker_count() == 1  # safe, legacy-identical default
    assert resolve_worker_count(1) == 1


def test_auto_and_int_capping(monkeypatch) -> None:
    monkeypatch.delenv("V53_MAX_WORKERS", raising=False)
    cpus = os.cpu_count() or 1
    assert resolve_worker_count("auto") == cpus
    assert resolve_worker_count("all") == cpus
    assert resolve_worker_count(2) == min(2, cpus)
    assert resolve_worker_count(9999) == cpus  # capped at detected cores


def test_env_var_opt_in(monkeypatch) -> None:
    cpus = os.cpu_count() or 1
    monkeypatch.setenv("V53_MAX_WORKERS", "2")
    assert resolve_worker_count() == min(2, cpus)
    monkeypatch.setenv("V53_MAX_WORKERS", "auto")
    assert resolve_worker_count() == cpus
    monkeypatch.setenv("V53_MAX_WORKERS", "garbage")
    assert resolve_worker_count() == 1  # unparseable -> safe serial


def test_resource_guard_caps_auto_workers_at_soft_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V53_RAM_GUARD_ENABLED", "1")
    monkeypatch.setenv("V53_MAX_RAM_FRACTION", "0.75")
    monkeypatch.setenv("V53_HARD_RAM_FRACTION", "0.80")
    monkeypatch.setenv("V53_RAM_GUARD_MAX_WAIT_SECONDS", "0")
    monkeypatch.setenv("V53_RAM_GUARD_RECLAIM_ENABLED", "0")
    set_memory_status_provider_for_tests(
        lambda: StrategyLadderMemoryStatus(
            total_physical_bytes=100,
            available_physical_bytes=24,
        )
    )
    try:
        assert resolve_worker_count("auto") == 1
    finally:
        set_memory_status_provider_for_tests(None)


def test_resource_guard_caps_workers_by_soft_headroom_reserve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gib = 1024 * 1024 * 1024
    monkeypatch.setenv("V53_RAM_GUARD_ENABLED", "1")
    monkeypatch.setenv("V53_MAX_RAM_FRACTION", "0.75")
    monkeypatch.setenv("V53_HARD_RAM_FRACTION", "0.80")
    monkeypatch.setenv("V53_RAM_GUARD_WORKER_RESERVE_MB", "6144")
    set_memory_status_provider_for_tests(
        lambda: StrategyLadderMemoryStatus(
            total_physical_bytes=32 * gib,
            available_physical_bytes=20 * gib,
        )
    )
    try:
        assert cap_workers_for_ram(32, phase_name="test") == 2
    finally:
        set_memory_status_provider_for_tests(None)


def test_resource_guard_blocks_parallel_map_at_hard_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V53_RAM_GUARD_ENABLED", "1")
    monkeypatch.setenv("V53_MAX_RAM_FRACTION", "0.75")
    monkeypatch.setenv("V53_HARD_RAM_FRACTION", "0.80")
    monkeypatch.setenv("V53_RAM_GUARD_MAX_WAIT_SECONDS", "0")
    monkeypatch.setenv("V53_RAM_GUARD_RECLAIM_ENABLED", "0")
    set_memory_status_provider_for_tests(
        lambda: StrategyLadderMemoryStatus(
            total_physical_bytes=100,
            available_physical_bytes=19,
        )
    )
    try:
        try:
            ordered_parallel_map(_square, [1, 2, 3], max_workers=2)
        except StrategyLadderResourceGuardError as exc:
            assert "RESOURCE_GUARD_RAM_LIMIT_EXCEEDED_AFTER_WAIT" in str(exc)
        else:
            raise AssertionError("resource guard did not block hard RAM limit")
    finally:
        set_memory_status_provider_for_tests(None)


def test_serial_map_input_order() -> None:
    tasks = list(range(20))
    assert ordered_parallel_map(_square, tasks, max_workers=1) == [t * t for t in tasks]


def test_parallel_preserves_order_and_results() -> None:
    tasks = list(range(64))
    serial = ordered_parallel_map(_square, tasks, max_workers=1)
    parallel = ordered_parallel_map(
        _square, tasks, max_workers=2, affinity_key=_affinity_mod3
    )
    assert parallel == serial, "parallel diverged from serial"
    # order preserved despite the affinity reshuffle inside the pool
    assert parallel == [t * t for t in tasks]


def test_empty_tasks() -> None:
    assert ordered_parallel_map(_square, [], max_workers=4) == []


# ---------------------------------------------------------------------------
# Integration: the real runner materialization serial == parallel (on spawn).
# Exercises pickling of real candidate/window models + the spawned worker calling
# the real economic provenance, + accumulation parity.
# ---------------------------------------------------------------------------

BASE_MS = 1_700_000_000_000


def _mk_candidate(i: int):
    from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent

    return StrategyLadderCandidateEvent(
        candidate_id=f"cand{i:03d}",
        pair="BTCUSDT",
        timeframe="15m",
        engine_id=("engine_a", "engine_b", "engine_c", "engine_d")[i % 4],
        strategy_id=("engine_a", "engine_b", "engine_c", "engine_d")[i % 4],
        timestamp_ms=BASE_MS + i * 900_000,
        compatibility_payload={"planned_notional": 100.0, "pair": "BTCUSDT"},
        candidate_source="TEST",
        candidate_data_source_label="TEST",
    )


def _mk_window(i: int):
    from local_replay_runtime.strategy_ladder_models import StrategyLadderRawWindowManifest

    ts = BASE_MS + i * 900_000
    return StrategyLadderRawWindowManifest(
        candidate_id=f"cand{i:03d}",
        pair="BTCUSDT",
        engine_id=("engine_a", "engine_b", "engine_c", "engine_d")[i % 4],
        timestamp_ms=ts,
        window_start_ms=ts - 900_000,
        window_end_ms=ts,
        raw_trade_path=f"/nonexistent/{i}/trades.jsonl",
        raw_book_path=f"/nonexistent/{i}/orderbook_snapshot.jsonl",
        raw_book_delta_path=f"/nonexistent/{i}/orderbook_delta.jsonl",
        raw_ohlcv_path=f"/nonexistent/{i}/klines.jsonl",
        book_depth_levels_available=20,
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        window_extraction_status="RAW_WINDOW_READY",
        raw_sources_used=("trades", "orderbook", "klines"),
        source_coverage_status="RAW_WINDOW_SOURCE_READY",
    )


def test_native_materialization_serial_equals_parallel(monkeypatch) -> None:
    from local_replay_runtime.strategy_ladder_runner import (
        _materialize_engine_native_candidates,
    )

    cands = tuple(_mk_candidate(i) for i in range(6))
    windows = tuple(_mk_window(i) for i in range(6))

    monkeypatch.delenv("V53_MAX_WORKERS", raising=False)
    serial = _materialize_engine_native_candidates(
        candidate_events=cands,
        raw_window_manifests=windows,
        expected_edge_model=None,
        ml_mode="ML_MODE_OFF",
    )

    monkeypatch.setenv("V53_MAX_WORKERS", "2")
    parallel = _materialize_engine_native_candidates(
        candidate_events=cands,
        raw_window_manifests=windows,
        expected_edge_model=None,
        ml_mode="ML_MODE_OFF",
    )

    # counters + statuses identical
    assert serial.engine_native_records_built == parallel.engine_native_records_built
    assert (
        serial.engine_native_runner_invocation_count
        == parallel.engine_native_runner_invocation_count
    )
    assert serial.candidate_discovery_status == parallel.candidate_discovery_status
    assert serial.engine_native_status == parallel.engine_native_status
    assert serial.expected_edge_proxy_count == parallel.expected_edge_proxy_count
    assert serial.expected_edge_governed_count == parallel.expected_edge_governed_count
    assert serial.blocker_codes == parallel.blocker_codes
    # native event order + identity preserved
    assert [c.candidate_id for c in serial.candidate_events] == [
        c.candidate_id for c in parallel.candidate_events
    ]


def test_detailed_replay_serial_equals_parallel(tmp_path, monkeypatch) -> None:
    """Chunk-parallel detailed replay == serial: same status, same per-candidate
    artifact order/identity/status, same bucket counts, same deterministic cache
    counters (timing seconds excluded — wall-clock differs by construction)."""
    from local_replay_runtime.strategy_ladder_detailed_replay import (
        run_strategy_ladder_detailed_replay,
        run_strategy_ladder_detailed_replay_parallel,
    )

    cands = tuple(_mk_candidate(i) for i in range(6))
    windows = tuple(_mk_window(i) for i in range(6))
    buckets = (400, 1500)

    monkeypatch.delenv("V53_MAX_WORKERS", raising=False)
    serial = run_strategy_ladder_detailed_replay(
        tmp_path / "serial",
        candidate_events=cands,
        raw_window_manifests=windows,
        capital_buckets=buckets,
    )

    monkeypatch.setenv("V53_MAX_WORKERS", "2")
    parallel = run_strategy_ladder_detailed_replay_parallel(
        tmp_path / "parallel",
        candidate_events=cands,
        raw_window_manifests=windows,
        capital_buckets=buckets,
    )

    assert serial.detailed_replay_status == parallel.detailed_replay_status
    assert [a.candidate_id for a in serial.candidate_artifacts] == [
        a.candidate_id for a in parallel.candidate_artifacts
    ]
    assert [a.detailed_replay_status for a in serial.candidate_artifacts] == [
        a.detailed_replay_status for a in parallel.candidate_artifacts
    ]
    for b in buckets:
        assert len(serial.bucket_results_by_bucket[b]) == len(
            parallel.bucket_results_by_bucket[b]
        )
        assert len(serial.bucket_dtr_records[b]) == len(
            parallel.bucket_dtr_records[b]
        )
    assert (
        serial.performance_metrics.cache_misses_book_state
        == parallel.performance_metrics.cache_misses_book_state
    )
    assert serial.performance_metrics.replay_workers_used == 0
    assert parallel.performance_metrics.replay_workers_used == 2


def test_detailed_replay_parallel_duplicate_ids_fallback_to_serial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from local_replay_runtime.strategy_ladder_detailed_replay import (
        run_strategy_ladder_detailed_replay_parallel,
    )

    cands = (_mk_candidate(0), _mk_candidate(1), _mk_candidate(1))
    windows = (_mk_window(0), _mk_window(1))

    monkeypatch.setenv("V53_MAX_WORKERS", "2")
    result = run_strategy_ladder_detailed_replay_parallel(
        tmp_path / "duplicate_ids",
        candidate_events=cands,
        raw_window_manifests=windows,
        capital_buckets=(400,),
    )

    assert result.detailed_replay_status == "DETAILED_REPLAY_READY"
    assert len(result.candidate_artifacts) == 3
    assert result.performance_metrics.replay_workers_used == 0


def test_detailed_replay_chunks_keep_duplicate_ids_together() -> None:
    from local_replay_runtime.strategy_ladder_detailed_replay import (
        _split_write_disjoint_candidate_chunks,
    )

    cands = (
        _mk_candidate(0),
        _mk_candidate(1),
        _mk_candidate(0),
        _mk_candidate(2),
        _mk_candidate(3),
        _mk_candidate(2),
    )

    chunks = _split_write_disjoint_candidate_chunks(cands, 4)

    assert [c.candidate_id for chunk in chunks for c in chunk] == [
        c.candidate_id for c in cands
    ]
    owners: dict[str, int] = {}
    for chunk_index, chunk in enumerate(chunks):
        for candidate in chunk:
            previous = owners.setdefault(candidate.candidate_id, chunk_index)
            assert previous == chunk_index
