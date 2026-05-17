#!/usr/bin/env python3
"""Resource-hygiene helpers for the long-running Shadow VPS service."""

from __future__ import annotations

import gc
import os
import time
from dataclasses import dataclass, field
from typing import Callable

from protocols import ShadowVpsServiceEvent
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext

AppendServiceEvent = Callable[..., None]


def _read_process_ram_heartbeat(
    context: ShadowVpsServiceRuntimeContext,
) -> tuple[float, float, str]:
    try:
        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return (
            memory_info.rss / (1024.0 * 1024.0),
            float(process.memory_percent()),
            "psutil",
        )
    except Exception:
        sampler = getattr(context, "process_metrics_sampler", None)
        if sampler is not None:
            sample = sampler.sample()
            return sample.rss_mb, sample.ram_pct, "process_metrics_sampler"
        return 0.0, 0.0, "unavailable"


@dataclass
class ShadowVpsServiceResourceHygieneController:
    """Run low-frequency GC and RAM heartbeat tasks without touching trading logic."""

    gc_interval_s: float = 3600.0
    ram_heartbeat_interval_s: float = 900.0
    monotonic_clock: Callable[[], float] = time.monotonic
    gc_collect: Callable[[], int] = gc.collect
    _next_gc_monotonic_s: float | None = field(default=None, init=False)
    _next_ram_heartbeat_monotonic_s: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.gc_interval_s <= 0.0:
            raise ValueError("gc_interval_s must be > 0")
        if self.ram_heartbeat_interval_s <= 0.0:
            raise ValueError("ram_heartbeat_interval_s must be > 0")

    def run_due(
        self,
        context: ShadowVpsServiceRuntimeContext,
        *,
        append_service_event: AppendServiceEvent,
    ) -> None:
        now_monotonic_s = self.monotonic_clock()
        if self._next_ram_heartbeat_monotonic_s is None:
            self._emit_ram_heartbeat(context, append_service_event=append_service_event)
            self._next_ram_heartbeat_monotonic_s = (
                now_monotonic_s + self.ram_heartbeat_interval_s
            )
        elif now_monotonic_s >= self._next_ram_heartbeat_monotonic_s:
            self._emit_ram_heartbeat(context, append_service_event=append_service_event)
            self._next_ram_heartbeat_monotonic_s = (
                now_monotonic_s + self.ram_heartbeat_interval_s
            )

        if self._next_gc_monotonic_s is None:
            self._next_gc_monotonic_s = now_monotonic_s + self.gc_interval_s
        elif now_monotonic_s >= self._next_gc_monotonic_s:
            collected = max(0, int(self.gc_collect()))
            append_service_event(
                store=context.store,
                telegram_alerter=context.telegram_alerter,
                event=ShadowVpsServiceEvent(
                    event_type="resource_gc_collected",
                    message=(
                        "Shadow VPS explicit GC completed: "
                        f"collected={collected}."
                    ),
                    session_date=context.store.state.last_completed_session_date,
                ),
            )
            self._next_gc_monotonic_s = now_monotonic_s + self.gc_interval_s

    def _emit_ram_heartbeat(
        self,
        context: ShadowVpsServiceRuntimeContext,
        *,
        append_service_event: AppendServiceEvent,
    ) -> None:
        rss_mb, ram_pct, source = _read_process_ram_heartbeat(context)
        append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="resource_ram_heartbeat",
                message=(
                    "Shadow VPS RAM heartbeat: "
                    f"rss_mb={rss_mb:.2f} / ram_pct={ram_pct:.2f} / source={source}."
                ),
                session_date=context.store.state.last_completed_session_date,
            ),
        )


__all__ = ["ShadowVpsServiceResourceHygieneController"]
