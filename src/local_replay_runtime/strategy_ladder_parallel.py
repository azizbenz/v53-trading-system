"""Phase 3 — generic ordered parallel map with source affinity + runtime CPU
auto-detection.

Used to parallelize the B2 per-candidate engine-native / detailed-replay work
(``strategy_ladder_runner``) across CPU cores. Design constraints:

* **Auto-scaling**: worker count is resolved at RUNTIME from the CPU (swap the
  CPU / deploy on a bigger server -> it scales itself, zero code change).
* **Opt-in & safe**: the default is **1 worker = serial**, byte-identical to the
  legacy loop. Parallelism is enabled by the ``V53_MAX_WORKERS`` env var (or an
  explicit argument). A trading runtime must not silently change execution mode.
* **Source affinity**: tasks can be sorted by a key (e.g. the silver source file)
  so items sharing a source land in the same worker chunk -> the per-process
  Arrow ``load_silver_table`` cache is reused instead of re-parsed N times. This
  is what lifts efficiency on Windows ``spawn`` (no shared in-RAM cache).
* **Order-preserving**: results are returned in INPUT order regardless of the
  affinity reshuffle, so downstream manifests/hashes stay deterministic.

The worker callable and every task must be picklable (Windows uses ``spawn``).
"""
from __future__ import annotations

import os
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Callable, Sequence, TypeVar

from local_replay_runtime.strategy_ladder_resource_guard import (
    assert_ram_below_hard_limit,
    cap_workers_for_ram,
)

T = TypeVar("T")
R = TypeVar("R")

_AUTO_TOKENS = {"auto", "0", "-1", "all", "max"}


def _detected_cpus() -> int:
    """Cores usable by THIS process, right now (affinity-aware where available)."""
    try:
        return len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except AttributeError:  # Windows / platforms without sched_getaffinity
        return os.cpu_count() or 1


def resolve_worker_count(requested: int | str | None = None) -> int:
    """Resolve the worker count at runtime.

    Priority: explicit ``requested`` > ``V53_MAX_WORKERS`` env > **1 (serial)**.
    A value of ``auto``/``all``/``max``/``0``/``-1`` means "all detected cores".
    Positive integers are capped at the detected core count. Anything else (or
    nothing) yields ``1`` — the safe, legacy-identical serial default.
    """
    val: int | str | None = requested
    if val is None:
        val = os.environ.get("V53_MAX_WORKERS")
    if val is None:
        return 1
    token = str(val).strip().lower()
    if token in _AUTO_TOKENS:
        workers = max(1, _detected_cpus())
        return cap_workers_for_ram(workers, phase_name="resolve_worker_count")
    if token.isdigit() and int(token) > 0:
        workers = max(1, min(int(token), _detected_cpus()))
        return cap_workers_for_ram(workers, phase_name="resolve_worker_count")
    return 1


def ordered_parallel_map(
    worker_fn: Callable[[T], R],
    tasks: Sequence[T],
    *,
    max_workers: int,
    affinity_key: Callable[[T], object] | None = None,
    chunksize: int | None = None,
) -> list[R]:
    """Map ``worker_fn`` over ``tasks`` across processes, results in INPUT order.

    ``max_workers <= 1`` runs serially in-process (no pool, no pickling, no
    behavioural change). Otherwise tasks are optionally grouped by
    ``affinity_key`` so cache-sharing items batch into the same worker, then the
    results are restored to the original task order.
    """
    n = len(tasks)
    if n == 0:
        return []
    if max_workers <= 1:
        assert_ram_below_hard_limit(phase_name="ordered_parallel_map.serial")
        return [worker_fn(task) for task in tasks]

    indexed: list[tuple[int, T]] = list(enumerate(tasks))
    if affinity_key is not None:
        indexed.sort(key=lambda item: affinity_key(item[1]))
    ordered_tasks = [item[1] for item in indexed]
    if chunksize is None:
        chunksize = max(1, n // (max_workers * 4))

    pool_workers = cap_workers_for_ram(
        max_workers,
        phase_name="ordered_parallel_map.parallel",
    )
    ordered_results: list[R] = [None] * n  # type: ignore[list-item]
    if pool_workers <= 1:
        ordered_results = [worker_fn(task) for task in ordered_tasks]
    else:
        executor = ProcessPoolExecutor(max_workers=pool_workers)
        try:
            pending = {}
            next_task_index = 0
            active_cap = cap_workers_for_ram(
                pool_workers,
                phase_name="ordered_parallel_map.submit",
            )
            while next_task_index < min(active_cap, n):
                future = executor.submit(worker_fn, ordered_tasks[next_task_index])
                pending[future] = next_task_index
                next_task_index += 1
            while pending:
                assert_ram_below_hard_limit(phase_name="ordered_parallel_map.parallel")
                done, _not_done = wait(
                    pending,
                    timeout=2.0,
                    return_when=FIRST_COMPLETED,
                )
                if not done:
                    continue
                for future in done:
                    result_index = pending.pop(future)
                    ordered_results[result_index] = future.result()
                    active_cap = cap_workers_for_ram(
                        pool_workers,
                        phase_name="ordered_parallel_map.submit",
                    )
                    if next_task_index < n and len(pending) < active_cap:
                        new_future = executor.submit(
                            worker_fn,
                            ordered_tasks[next_task_index],
                        )
                        pending[new_future] = next_task_index
                        next_task_index += 1
                while next_task_index < n:
                    active_cap = cap_workers_for_ram(
                        pool_workers,
                        phase_name="ordered_parallel_map.submit",
                    )
                    if len(pending) >= active_cap:
                        break
                    new_future = executor.submit(
                        worker_fn,
                        ordered_tasks[next_task_index],
                    )
                    pending[new_future] = next_task_index
                    next_task_index += 1
        except BaseException:
            if hasattr(executor, "terminate_workers"):
                executor.terminate_workers()
            else:
                executor.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            executor.shutdown()

    results: list[R] = [None] * n  # type: ignore[list-item]
    for (original_index, _task), result in zip(indexed, ordered_results):
        results[original_index] = result
    return results


__all__ = ["resolve_worker_count", "ordered_parallel_map"]
