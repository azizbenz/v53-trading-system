from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest

from monitoring.contracts import ProcessMetricsSample


def _load_script_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = (
        repo_root / "scripts" / "shadow_vps_service_resource_hygiene_support.py"
    )
    module_name = f"test_shadow_vps_service_resource_hygiene_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FixedSampler:
    def sample(self) -> ProcessMetricsSample:
        return ProcessMetricsSample(
            pid=4321,
            cpu_pct=0.0,
            ram_pct=12.5,
            rss_mb=256.0,
            thread_count=9,
            sampling_mode="test_mode",
        )


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        store=SimpleNamespace(
            state=SimpleNamespace(last_completed_session_date="2026-04-25")
        ),
        process_metrics_sampler=_FixedSampler(),
        telegram_alerter=None,
    )


def test_resource_hygiene_controller_emits_ram_heartbeat_and_hourly_gc() -> None:
    module = _load_script_module()
    current_time = {"now": 0.0}
    events: list[object] = []

    controller = module.ShadowVpsServiceResourceHygieneController(
        gc_interval_s=3600.0,
        ram_heartbeat_interval_s=900.0,
        monotonic_clock=lambda: current_time["now"],
        gc_collect=lambda: 7,
    )

    def _append_event(*, store: object, telegram_alerter: object, event: object) -> None:
        _ = store, telegram_alerter
        events.append(event)

    context = _context()
    controller.run_due(context, append_service_event=_append_event)
    assert [event.event_type for event in events] == ["resource_ram_heartbeat"]
    assert "rss_mb=256.00" in events[0].message
    assert "source=process_metrics_sampler" in events[0].message

    current_time["now"] = 899.0
    controller.run_due(context, append_service_event=_append_event)
    assert len(events) == 1

    current_time["now"] = 900.0
    controller.run_due(context, append_service_event=_append_event)
    assert [event.event_type for event in events] == [
        "resource_ram_heartbeat",
        "resource_ram_heartbeat",
    ]

    current_time["now"] = 3601.0
    controller.run_due(context, append_service_event=_append_event)
    assert [event.event_type for event in events] == [
        "resource_ram_heartbeat",
        "resource_ram_heartbeat",
        "resource_ram_heartbeat",
        "resource_gc_collected",
    ]
    assert "collected=7" in events[-1].message


def test_resource_hygiene_controller_prefers_psutil_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()

    class _FakeMemoryInfo:
        rss = 134_217_728

    class _FakeProcess:
        def __init__(self, pid: int) -> None:
            self.pid = pid

        def memory_info(self) -> _FakeMemoryInfo:
            return _FakeMemoryInfo()

        def memory_percent(self) -> float:
            return 6.25

    fake_psutil = SimpleNamespace(Process=_FakeProcess)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    events: list[object] = []

    controller = module.ShadowVpsServiceResourceHygieneController(
        monotonic_clock=lambda: 0.0,
        gc_collect=lambda: 0,
    )

    def _append_event(*, store: object, telegram_alerter: object, event: object) -> None:
        _ = store, telegram_alerter
        events.append(event)

    controller.run_due(_context(), append_service_event=_append_event)

    assert [event.event_type for event in events] == ["resource_ram_heartbeat"]
    assert "rss_mb=128.00" in events[0].message
    assert "ram_pct=6.25" in events[0].message
    assert "source=psutil" in events[0].message
