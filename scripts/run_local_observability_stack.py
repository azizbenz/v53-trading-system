#!/usr/bin/env python3
"""Launch the local Shadow VPS observability stack in one command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from monitoring.local_observability_stack import (  # noqa: E402
    DEFAULT_LOCAL_OBSERVABILITY_OUTPUT_DIR,
    LocalObservabilityStackSummary,
    launch_local_observability_stack,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Launch the local metrics bridge, Prometheus, Grafana, and bootstrap "
            "the V5.3 Shadow VPS dashboard in one command."
        ),
    )
    parser.add_argument(
        "--prom-text-path",
        type=Path,
        default=REPO_ROOT / "build" / "shadow_vps_service" / "shadow_vps_service_observability.prom",
        help="Path to the Shadow VPS Prometheus text payload.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_LOCAL_OBSERVABILITY_OUTPUT_DIR,
        help="Directory where generated configs, logs, and summaries will be written.",
    )
    parser.add_argument(
        "--grafana-url",
        default="http://127.0.0.1:3000",
        help="Grafana URL.",
    )
    parser.add_argument(
        "--grafana-user",
        default="admin",
        help="Grafana username.",
    )
    parser.add_argument(
        "--grafana-password",
        default="admin",
        help="Grafana password used for bootstrap.",
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://127.0.0.1:9090",
        help="Prometheus URL exposed to Grafana.",
    )
    parser.add_argument(
        "--bridge-host",
        default="127.0.0.1",
        help="Host bound by the local metrics bridge.",
    )
    parser.add_argument(
        "--bridge-port",
        type=int,
        default=19100,
        help="Port bound by the local metrics bridge.",
    )
    parser.add_argument(
        "--prometheus-exe",
        type=Path,
        default=None,
        help="Optional explicit Prometheus executable path.",
    )
    parser.add_argument(
        "--grafana-server-exe",
        type=Path,
        default=None,
        help="Optional explicit Grafana server executable path.",
    )
    parser.add_argument(
        "--grafana-home",
        type=Path,
        default=None,
        help="Optional explicit Grafana home directory.",
    )
    parser.add_argument(
        "--scrape-interval",
        default="5s",
        help="Prometheus scrape interval for the generated local bridge config.",
    )
    parser.add_argument(
        "--evaluation-interval",
        default="5s",
        help="Prometheus evaluation interval for the generated local bridge config.",
    )
    parser.add_argument(
        "--readiness-timeout-s",
        type=float,
        default=30.0,
        help="Timeout applied while waiting for bridge/Prometheus/Grafana readiness.",
    )
    return parser


def _emit_summary(summary: LocalObservabilityStackSummary) -> None:
    sys.stdout.write(
        "Local observability stack summary JSON: "
        f"{Path(summary.output_dir) / 'local_observability_stack.summary.json'}\n"
    )
    sys.stdout.write(f"Grafana URL: {summary.grafana_url}\n")
    sys.stdout.write(f"Prometheus URL: {summary.prometheus_url}\n")
    sys.stdout.write(f"Metrics bridge URL: {summary.bridge_url}\n")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        summary = launch_local_observability_stack(
            prom_text_path=args.prom_text_path,
            output_dir=args.output_dir,
            grafana_url=args.grafana_url,
            grafana_user=args.grafana_user,
            grafana_password=args.grafana_password,
            prometheus_url=args.prometheus_url,
            bridge_host=args.bridge_host,
            bridge_port=args.bridge_port,
            prometheus_exe=args.prometheus_exe,
            grafana_server_exe=args.grafana_server_exe,
            grafana_home=args.grafana_home,
            scrape_interval=args.scrape_interval,
            evaluation_interval=args.evaluation_interval,
            readiness_timeout_s=args.readiness_timeout_s,
        )
    except (
        FileNotFoundError,
        HTTPError,
        OSError,
        RuntimeError,
        TimeoutError,
        URLError,
        ValueError,
    ) as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")
    _emit_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
