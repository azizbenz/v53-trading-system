from __future__ import annotations

import logging
import signal

import pytest

from protocols import live_light_runtime, micro_live_runtime, shadow_runtime
from protocols import runtime_signal_support


@pytest.mark.parametrize(
    ("runtime_module", "runtime_name"),
    (
        (shadow_runtime, "protocols.shadow_runtime"),
        (live_light_runtime, "protocols.live_light_runtime"),
        (micro_live_runtime, "protocols.micro_live_runtime"),
    ),
)
def test_runtime_entrypoint_installs_sigterm_and_sigint_handlers(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    runtime_module: object,
    runtime_name: str,
) -> None:
    handlers: dict[int, object] = {}
    fired = {"value": False}

    def fake_signal(signum: int, handler: object) -> None:
        handlers[signum] = handler

    def fake_sleep(_seconds: float) -> None:
        if fired["value"]:
            return
        fired["value"] = True
        handler = handlers[signal.SIGTERM]
        handler(signal.SIGTERM, None)

    monkeypatch.setattr(runtime_signal_support.signal, "signal", fake_signal)
    monkeypatch.setattr(runtime_signal_support.time, "sleep", fake_sleep)
    caplog.set_level(logging.INFO)

    result = runtime_module.run(sleep_seconds=0.0)

    assert result == 0
    assert signal.SIGTERM in handlers
    assert signal.SIGINT in handlers
    assert "graceful_shutdown_complete" in caplog.text
    assert runtime_name in caplog.text


@pytest.mark.parametrize(
    ("runtime_module", "fake_config"),
    (
        (shadow_runtime, "shadow.yaml"),
        (live_light_runtime, "live_light.yaml"),
        (micro_live_runtime, "micro_live.yaml"),
    ),
)
def test_runtime_main_accepts_fake_config_and_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    runtime_module: object,
    fake_config: str,
) -> None:
    monkeypatch.setattr(runtime_module, "runtime_cli_main", lambda _name, argv=None: 0)

    result = runtime_module.main(["--fake-config", fake_config, "--sleep-seconds", "0.0"])

    assert result == 0
