"""Lightweight real process metrics sampling for VPS observability."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

from monitoring.contracts import ProcessMetricsSample


def _read_linux_total_memory_bytes() -> int | None:
    meminfo_path = Path("/proc/meminfo")
    if not meminfo_path.is_file():
        return None
    try:
        for line in meminfo_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def _read_linux_status() -> tuple[int | None, int | None]:
    status_path = Path("/proc/self/status")
    if not status_path.is_file():
        return None, None
    rss_bytes: int | None = None
    thread_count: int | None = None
    try:
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2:
                    rss_bytes = int(parts[1]) * 1024
            elif line.startswith("Threads:"):
                parts = line.split()
                if len(parts) >= 2:
                    thread_count = int(parts[1])
    except (OSError, ValueError):
        return None, None
    return rss_bytes, thread_count


def _read_windows_rss_bytes() -> int | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        process = kernel32.GetCurrentProcess()
        success = psapi.GetProcessMemoryInfo(
            process,
            ctypes.byref(counters),
            counters.cb,
        )
        if success:
            return int(counters.WorkingSetSize)
    except Exception:
        return None
    return None


def _read_windows_total_memory_bytes() -> int | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
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
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except Exception:
        return None
    return None


def _read_posix_rusage_rss_bytes() -> int | None:
    try:
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return int(rss)
        return int(rss) * 1024
    except Exception:
        return None


def _read_process_memory_snapshot() -> tuple[int, int, str]:
    linux_rss, linux_threads = _read_linux_status()
    if linux_rss is not None:
        return linux_rss, linux_threads or threading.active_count(), "linux_procfs"

    windows_rss = _read_windows_rss_bytes()
    if windows_rss is not None:
        return windows_rss, threading.active_count(), "windows_ctypes"

    rss = _read_posix_rusage_rss_bytes() or 0
    return rss, threading.active_count(), "fallback"


def _read_total_memory_bytes(mode: str) -> int:
    if mode == "linux_procfs":
        return _read_linux_total_memory_bytes() or 0
    if mode == "windows_ctypes":
        return _read_windows_total_memory_bytes() or 0
    return 0


class ProcessMetricsSampler:
    """Stateful sampler that derives bounded real process CPU and memory metrics."""

    def __init__(self) -> None:
        self._last_cpu_seconds: float | None = None
        self._last_monotonic_s: float | None = None

    def sample(self) -> ProcessMetricsSample:
        now_monotonic_s = time.monotonic()
        cpu_seconds = time.process_time()
        cpu_count = max(1, os.cpu_count() or 1)
        cpu_pct = 0.0
        if self._last_cpu_seconds is not None and self._last_monotonic_s is not None:
            delta_cpu = max(0.0, cpu_seconds - self._last_cpu_seconds)
            delta_wall = max(0.0, now_monotonic_s - self._last_monotonic_s)
            if delta_wall > 0.0:
                cpu_pct = min(100.0, max(0.0, delta_cpu / (delta_wall * cpu_count) * 100.0))

        self._last_cpu_seconds = cpu_seconds
        self._last_monotonic_s = now_monotonic_s

        rss_bytes, thread_count, mode = _read_process_memory_snapshot()
        total_memory_bytes = _read_total_memory_bytes(mode)
        ram_pct = (
            min(100.0, max(0.0, rss_bytes / total_memory_bytes * 100.0))
            if total_memory_bytes > 0
            else 0.0
        )

        return ProcessMetricsSample(
            pid=os.getpid(),
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            rss_mb=rss_bytes / (1024.0 * 1024.0),
            thread_count=thread_count,
            sampling_mode=mode,
        )


__all__ = ["ProcessMetricsSampler"]
