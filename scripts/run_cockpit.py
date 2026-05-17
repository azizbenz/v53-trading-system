#!/usr/bin/env python3
"""Launch the V5.3 cockpit operator shell."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V5.3 cockpit operator shell.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address. Default 127.0.0.1. On VPS use the Tailscale IP.",
    )
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--service-dir",
        type=Path,
        default=REPO_ROOT / "build" / "build11_live_websocket_campaign" / "service",
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=REPO_ROOT
        / "build"
        / "build11_live_websocket_campaign"
        / "service"
        / "shadow_service.log",
    )
    parser.add_argument(
        "--auto-exports-root",
        type=Path,
        default=REPO_ROOT / "build" / "build11_live_websocket_campaign" / "auto_exports",
    )
    parser.add_argument(
        "--live-websocket-config",
        type=Path,
        default=REPO_ROOT
        / "build"
        / "build11_live_websocket_campaign"
        / "live_websocket_config.json",
    )
    parser.add_argument(
        "--calibration-thresholds",
        type=Path,
        default=REPO_ROOT / "config" / "calibration" / "v1" / "thresholds.yml",
    )
    parser.add_argument(
        "--build-root",
        type=Path,
        default=REPO_ROOT / "build",
        help="Root directory holding local analysis and replay outputs.",
    )
    parser.add_argument(
        "--dashboard-command-queue-root",
        type=Path,
        default=REPO_ROOT / "build" / "dashboard_command_queue",
    )
    parser.add_argument(
        "--observability-output-dir",
        type=Path,
        default=REPO_ROOT / ".local_observability_stack",
    )
    parser.add_argument(
        "--backtest-jobs-root",
        type=Path,
        default=REPO_ROOT / "build" / "cockpit" / "backtest_jobs",
    )
    parser.add_argument(
        "--artifact-ingress-root",
        type=Path,
        default=REPO_ROOT / "build" / "cockpit" / "artifact_ingress",
    )
    parser.add_argument("--welcome-message", default="Welcome Benz Family · AI Bot Trading")
    parser.add_argument("--grafana-url", default="http://127.0.0.1:3000")
    parser.add_argument("--prometheus-url", default="http://127.0.0.1:9090")
    parser.add_argument(
        "--unsafe-bind-all",
        action="store_true",
        help="Allow binding to 0.0.0.0. Use only behind a firewall or Tailscale.",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload.")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = _build_parser().parse_args(argv)
    logger = logging.getLogger("cockpit.launcher")

    host = args.host
    if host == "0.0.0.0" and not args.unsafe_bind_all:
        sys.stderr.write(
            "[cockpit] refusing to bind on 0.0.0.0 without --unsafe-bind-all\n"
            "          On the VPS, bind to the Tailscale IP instead.\n"
            "          For pure dev, use 127.0.0.1 (the default).\n",
        )
        return 2
    if host == "0.0.0.0":
        logger.warning(
            "Binding cockpit on 0.0.0.0 (all interfaces). Ensure the firewall blocks public access."
        )

    try:
        import uvicorn
    except ImportError as exc:
        sys.stderr.write(
            f"[cockpit] missing dependency: {exc}. "
            "Install it with: pip install fastapi uvicorn[standard] jinja2 python-multipart\n"
        )
        return 3

    from cockpit.server import create_app  # noqa: E402
    from cockpit.state import CockpitPaths  # noqa: E402

    pid_file = (
        args.pid_file.expanduser().resolve()
        if args.pid_file is not None
        else (args.service_dir.expanduser().resolve() / "shadow_vps_service.pid")
    )

    paths = CockpitPaths(
        service_dir=args.service_dir.expanduser().resolve(),
        pid_file=pid_file,
        log_file=args.log_file.expanduser().resolve(),
        auto_exports_root=args.auto_exports_root.expanduser().resolve(),
        live_websocket_config=args.live_websocket_config.expanduser().resolve(),
        calibration_thresholds=args.calibration_thresholds.expanduser().resolve(),
        build_root=args.build_root.expanduser().resolve(),
        dashboard_command_queue_root=args.dashboard_command_queue_root.expanduser().resolve(),
        observability_output_dir=args.observability_output_dir.expanduser().resolve(),
        backtest_jobs_root=args.backtest_jobs_root.expanduser().resolve(),
        artifact_ingress_root=args.artifact_ingress_root.expanduser().resolve(),
    )
    for directory in (
        pid_file.parent,
        args.dashboard_command_queue_root,
        args.backtest_jobs_root,
        args.artifact_ingress_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    app = create_app(
        paths=paths,
        welcome_message=args.welcome_message,
        grafana_url=args.grafana_url,
        prometheus_url=args.prometheus_url,
    )
    logger.info("Cockpit listening on http://%s:%s", host, args.port)
    uvicorn.run(
        app,
        host=host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
