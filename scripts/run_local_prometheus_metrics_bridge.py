#!/usr/bin/env python3
"""Serve a local `.prom` payload over HTTP for dual-role Windows/dev Prometheus scrapes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from monitoring import (  # noqa: E402
    build_local_prometheus_metrics_bridge_server,
    build_local_prometheus_metrics_bridge_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Serve a local `.prom` payload over HTTP for dual-role dev Prometheus scrapes."
        ),
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--prom-text-path",
        type=Path,
        help="Path to the `.prom` file that should be served over HTTP.",
    )
    source_group.add_argument(
        "--observability-export-path",
        type=Path,
        help=(
            "Path to an observability export JSON carrying a `text_payload` field to "
            "serve over HTTP."
        ),
    )
    parser.add_argument(
        "--listen-host",
        default="127.0.0.1",
        help="Host interface to bind for the local dev metrics bridge.",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9100,
        help="Port to bind for the local dev metrics bridge.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_prometheus_metrics_bridge",
        help="Directory where the typed bridge summary JSON will be written.",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=0,
        help="Optional bounded request count before clean exit; 0 means serve forever.",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    server = build_local_prometheus_metrics_bridge_server(
        source_prom_path=args.prom_text_path,
        observability_export_path=args.observability_export_path,
        listen_host=args.listen_host,
        listen_port=args.listen_port,
    )
    actual_host, actual_port = server.server_address
    summary_path = args.output_dir / "local_prometheus_metrics_bridge.summary.json"
    summary = build_local_prometheus_metrics_bridge_summary(
        source_prom_path=args.prom_text_path,
        observability_export_path=args.observability_export_path,
        listen_host=str(actual_host),
        listen_port=int(actual_port),
        output_path=summary_path,
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    print(f"Local Prometheus metrics bridge summary JSON: {summary_path}")
    print(f"Local Prometheus metrics bridge target: http://{actual_host}:{actual_port}/metrics")

    try:
        if args.max_requests > 0:
            handled = 0
            while handled < args.max_requests:
                server.handle_request()
                handled += 1
        else:
            server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
