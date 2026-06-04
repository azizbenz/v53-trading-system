"""Runtime RAM guardrails for Strategy Ladder long backtests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import ctypes
import gc
import os
from time import monotonic, sleep


_TRUE_TOKENS = {"1", "true", "yes", "on", "enabled"}
_FALSE_TOKENS = {"0", "false", "no", "off", "disabled"}


class StrategyLadderResourceGuardError(RuntimeError):
    """Raised when a run would exceed the configured resource guard."""


@dataclass(frozen=True)
class StrategyLadderMemoryStatus:
    total_physical_bytes: int
    available_physical_bytes: int

    @property
    def used_fraction(self) -> float:
        if self.total_physical_bytes <= 0:
            return 0.0
        used = max(self.total_physical_bytes - self.available_physical_bytes, 0)
        return min(max(used / float(self.total_physical_bytes), 0.0), 1.0)


@dataclass(frozen=True)
class StrategyLadderResourceGuardSettings:
    enabled: bool
    soft_ram_fraction: float
    hard_ram_fraction: float
    max_wait_seconds: float
    poll_seconds: float
    worker_memory_reserve_bytes: int


_memory_status_override = None


def set_memory_status_provider_for_tests(
    provider: Callable[[], StrategyLadderMemoryStatus] | None,
) -> None:
    global _memory_status_override
    _memory_status_override = provider


def _parse_bool(raw_value: str | None, *, default: bool) -> bool:
    if raw_value is None:
        return default
    token = raw_value.strip().lower()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return default


def _parse_fraction(raw_value: str | None, *, default: float) -> float:
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        return default
    return min(max(value, 0.10), 0.99)


def _parse_seconds(raw_value: str | None, *, default: float) -> float:
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        return default
    return max(value, 0.0)


def _parse_megabytes(raw_value: str | None, *, default_mb: int) -> int:
    if raw_value is None:
        return default_mb * 1024 * 1024
    try:
        value = int(raw_value)
    except ValueError:
        return default_mb * 1024 * 1024
    return max(value, 0) * 1024 * 1024


def resource_guard_settings() -> StrategyLadderResourceGuardSettings:
    explicit_enabled = os.environ.get("V53_RAM_GUARD_ENABLED")
    threshold_present = (
        "V53_MAX_RAM_FRACTION" in os.environ
        or "V53_HARD_RAM_FRACTION" in os.environ
    )
    enabled = _parse_bool(explicit_enabled, default=threshold_present)
    soft = _parse_fraction(os.environ.get("V53_MAX_RAM_FRACTION"), default=0.75)
    hard = _parse_fraction(os.environ.get("V53_HARD_RAM_FRACTION"), default=0.80)
    if hard < soft:
        hard = soft
    max_wait = _parse_seconds(
        os.environ.get("V53_RAM_GUARD_MAX_WAIT_SECONDS"),
        default=1800.0,
    )
    poll = _parse_seconds(
        os.environ.get("V53_RAM_GUARD_POLL_SECONDS"),
        default=5.0,
    )
    worker_reserve = _parse_megabytes(
        os.environ.get("V53_RAM_GUARD_WORKER_RESERVE_MB"),
        default_mb=6144,
    )
    return StrategyLadderResourceGuardSettings(
        enabled=enabled,
        soft_ram_fraction=soft,
        hard_ram_fraction=hard,
        max_wait_seconds=max_wait,
        poll_seconds=max(poll, 0.25),
        worker_memory_reserve_bytes=worker_reserve,
    )


def current_memory_status() -> StrategyLadderMemoryStatus:
    if _memory_status_override is not None:
        return _memory_status_override()
    if os.name == "nt":
        return _windows_memory_status()
    return _posix_memory_status()


def _windows_memory_status() -> StrategyLadderMemoryStatus:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return StrategyLadderMemoryStatus(
        total_physical_bytes=int(status.ullTotalPhys),
        available_physical_bytes=int(status.ullAvailPhys),
    )


def _posix_memory_status() -> StrategyLadderMemoryStatus:
    meminfo = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                value = rest.strip().split()[0]
                meminfo[key] = int(value) * 1024
    except (OSError, ValueError, IndexError):
        page_size = os.sysconf("SC_PAGE_SIZE")
        total_pages = os.sysconf("SC_PHYS_PAGES")
        available_pages = os.sysconf("SC_AVPHYS_PAGES")
        return StrategyLadderMemoryStatus(
            total_physical_bytes=int(page_size * total_pages),
            available_physical_bytes=int(page_size * available_pages),
        )
    total = int(meminfo.get("MemTotal", 0))
    available = int(meminfo.get("MemAvailable", meminfo.get("MemFree", 0)))
    return StrategyLadderMemoryStatus(
        total_physical_bytes=total,
        available_physical_bytes=available,
    )


def reclaim_strategy_ladder_memory(*, phase_name: str) -> dict[str, object]:
    if not _parse_bool(
        os.environ.get("V53_RAM_GUARD_RECLAIM_ENABLED"),
        default=True,
    ):
        return {"phase_name": phase_name, "reclaim_status": "DISABLED"}
    reclaimed: dict[str, object] = {
        "phase_name": phase_name,
        "gc_collected": gc.collect(),
    }
    try:
        from local_replay_runtime.strategy_ladder_engine_native_adapter import (
            evict_microstructure_file_cache,
        )

        reclaimed["microstructure_cache"] = evict_microstructure_file_cache()
    except Exception as exc:  # noqa: BLE001 - best-effort guard path
        reclaimed["microstructure_cache_error"] = type(exc).__name__
    try:
        from local_replay_runtime.strategy_ladder_arrow_window import load_silver_table

        load_silver_table.cache_clear()
        reclaimed["silver_table_cache_cleared"] = True
    except Exception as exc:  # noqa: BLE001 - pyarrow may be unavailable in tests
        reclaimed["silver_table_cache_error"] = type(exc).__name__
    try:
        import pyarrow as pa

        pa.default_memory_pool().release_unused()
        reclaimed["pyarrow_release_unused"] = True
    except Exception as exc:  # noqa: BLE001 - optional runtime dependency
        reclaimed["pyarrow_release_unused_error"] = type(exc).__name__
    gc.collect()
    return reclaimed


def wait_for_ram_below_limit(*, phase_name: str) -> StrategyLadderMemoryStatus:
    settings = resource_guard_settings()
    status = current_memory_status()
    if not settings.enabled:
        return status
    if status.used_fraction < settings.hard_ram_fraction:
        return status
    started = monotonic()
    attempts = 0
    while True:
        attempts += 1
        reclaim_strategy_ladder_memory(phase_name=phase_name)
        status = current_memory_status()
        if status.used_fraction < settings.soft_ram_fraction:
            return status
        elapsed = monotonic() - started
        if settings.max_wait_seconds <= 0 or elapsed >= settings.max_wait_seconds:
            break
        sleep(settings.poll_seconds)
    raise StrategyLadderResourceGuardError(
        "RESOURCE_GUARD_RAM_LIMIT_EXCEEDED_AFTER_WAIT "
        f"phase={phase_name} "
        f"used_fraction={status.used_fraction:.4f} "
        f"soft_fraction={settings.soft_ram_fraction:.4f} "
        f"hard_fraction={settings.hard_ram_fraction:.4f} "
        f"wait_seconds={settings.max_wait_seconds:.1f} "
        f"attempts={attempts} "
        f"available_mb={status.available_physical_bytes / 1048576:.1f} "
        f"total_mb={status.total_physical_bytes / 1048576:.1f}"
    )


def assert_ram_below_hard_limit(*, phase_name: str) -> None:
    wait_for_ram_below_limit(phase_name=phase_name)


def cap_workers_for_ram(max_workers: int, *, phase_name: str) -> int:
    if max_workers <= 1:
        return max(1, max_workers)
    settings = resource_guard_settings()
    if not settings.enabled:
        return max_workers
    status = current_memory_status()
    if status.used_fraction >= settings.hard_ram_fraction:
        status = wait_for_ram_below_limit(phase_name=phase_name)
    if status.used_fraction >= settings.soft_ram_fraction:
        return 1
    near_soft = max(settings.soft_ram_fraction - 0.05, 0.10)
    if status.used_fraction >= near_soft:
        return min(max_workers, 2)
    if settings.worker_memory_reserve_bytes > 0:
        used_bytes = max(
            status.total_physical_bytes - status.available_physical_bytes,
            0,
        )
        soft_limit_bytes = int(
            status.total_physical_bytes * settings.soft_ram_fraction
        )
        headroom_bytes = max(soft_limit_bytes - used_bytes, 0)
        workers_by_headroom = max(
            1,
            headroom_bytes // settings.worker_memory_reserve_bytes,
        )
        return min(max_workers, int(workers_by_headroom))
    return max_workers


__all__ = [
    "StrategyLadderMemoryStatus",
    "StrategyLadderResourceGuardError",
    "assert_ram_below_hard_limit",
    "cap_workers_for_ram",
    "current_memory_status",
    "reclaim_strategy_ladder_memory",
    "resource_guard_settings",
    "set_memory_status_provider_for_tests",
    "wait_for_ram_below_limit",
]
