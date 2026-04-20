"""Shared signal-aware idle entrypoints for governed protocol runtimes."""

from __future__ import annotations

import argparse
import logging
import signal
import time
from dataclasses import dataclass
from types import FrameType
from typing import Sequence


@dataclass
class ShutdownSignal:
    requested: bool = False

    def request(self) -> None:
        self.requested = True


def install_signal_handlers(shutdown: ShutdownSignal, *, logger: logging.Logger) -> None:
    """Install cooperative SIGTERM/SIGINT handlers."""

    def handler(signum: int, _frame: FrameType | None) -> None:
        logger.warning("signal_received", extra={"signal": signum})
        shutdown.request()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def run_idle_runtime(runtime_name: str, *, sleep_seconds: float = 0.1) -> int:
    """Run a cooperative idle loop until SIGTERM/SIGINT is received."""

    logger = logging.getLogger(runtime_name)
    shutdown = ShutdownSignal()
    install_signal_handlers(shutdown, logger=logger)
    while not shutdown.requested:
        time.sleep(max(sleep_seconds, 0.0))
    logger.info("graceful_shutdown_complete")
    return 0


def runtime_cli_main(runtime_name: str, argv: Sequence[str] | None = None) -> int:
    """Parse a minimal runtime CLI and block until cooperative shutdown."""

    parser = argparse.ArgumentParser(prog=runtime_name.rsplit(".", maxsplit=1)[-1])
    parser.add_argument("--config")
    parser.add_argument("--fake-config")
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    args = parser.parse_args(list(argv) if argv is not None else None)
    _ = args.config, args.fake_config
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    return run_idle_runtime(runtime_name, sleep_seconds=args.sleep_seconds)


__all__ = [
    "ShutdownSignal",
    "install_signal_handlers",
    "run_idle_runtime",
    "runtime_cli_main",
]
