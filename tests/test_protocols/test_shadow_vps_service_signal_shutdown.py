from __future__ import annotations

from collections.abc import Callable
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest


def _load_service_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_shadow_vps_service.py"
    module_name = f"test_run_shadow_vps_service_signal_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".codex_tmp_shadow_vps_service_signal_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_install_shadow_vps_signal_handlers_sets_stop_flag_and_restores_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    controller = service._ShadowVpsSignalController()
    installed_handlers: dict[object, object] = {}
    restored_handlers: dict[object, object] = {}

    def _fake_getsignal(stop_signal: object) -> object:
        return f"previous:{stop_signal}"

    def _fake_signal(stop_signal: object, handler: object) -> None:
        if stop_signal not in installed_handlers:
            installed_handlers[stop_signal] = handler
            return
        restored_handlers[stop_signal] = handler

    monkeypatch.setattr(service.signal, "getsignal", _fake_getsignal)
    monkeypatch.setattr(service.signal, "signal", _fake_signal)

    restore_signal_handlers = service._install_shadow_vps_signal_handlers(controller)

    assert installed_handlers
    first_signal, first_handler = next(iter(installed_handlers.items()))
    first_handler(first_signal, None)
    assert controller.stop_requested() is True
    assert controller.stop_reason().startswith("signal ")

    restore_signal_handlers()

    assert restored_handlers[first_signal] == f"previous:{first_signal}"


def test_shadow_vps_service_main_loop_stops_cleanly_when_stop_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    runtime_context = SimpleNamespace(
        store=SimpleNamespace(
            state=SimpleNamespace(last_completed_session_date="2026-04-01"),
            persist=lambda: None,
        ),
        telegram_alerter=None,
    )
    stop_state = {"requested": False}
    event_types: list[str] = []
    monitoring_markers: list[str] = []
    cycle_calls: list[str] = []

    def _run_cycle(
        _context: object,
        *,
        continue_on_error: bool,
    ) -> str:
        assert continue_on_error is True
        cycle_calls.append("cycle")
        stop_state["requested"] = True
        return "sleep"

    def _append_event(
        *,
        store: object,
        telegram_alerter: object,
        event: object,
    ) -> None:
        assert store is runtime_context.store
        assert telegram_alerter is None
        event_types.append(event.event_type)

    monkeypatch.setattr(
        service.time,
        "sleep",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("sleep must not be reached after a stop request")
        ),
    )

    service._run_shadow_vps_service_main_loop(
        runtime_context,
        poll_interval_s=60.0,
        max_cycles=None,
        continue_on_error=True,
        run_shadow_vps_service_cycle=_run_cycle,
        should_stop=lambda: stop_state["requested"],
        resolve_stop_reason=lambda: "signal SIGTERM",
        write_service_monitoring=lambda _context: monitoring_markers.append("monitoring"),
        append_service_event=_append_event,
    )

    assert cycle_calls == ["cycle"]
    assert event_types == ["service_stop_requested"]
    assert monitoring_markers == ["monitoring"]


def test_run_shadow_vps_service_finalizes_cleanly_when_signal_is_pre_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    output_dir = _scratch_dir("pre_requested_signal")

    def _fake_install_signal_handlers(controller: object) -> Callable[[], None]:
        controller.request_stop("SIGTERM")
        return lambda: None

    monkeypatch.setattr(
        service,
        "_install_shadow_vps_signal_handlers",
        _fake_install_signal_handlers,
    )

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            poll_interval_s=0.0,
            max_cycles=None,
        )

        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )

        assert exit_code == 0
        assert state["service_status"] == "stopped"
        assert state["loop_count"] == 0
        assert state["last_error"] == ""
        assert [event["event_type"] for event in events][-2:] == [
            "service_stop_requested",
            "service_stopped",
        ]
        assert "SIGTERM" in events[-2]["message"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
