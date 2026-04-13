#!/usr/bin/env python3
"""Generate an importable local Grafana dashboard JSON for current V5.3 Shadow VPS metrics."""

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
    build_local_shadow_vps_grafana_dashboard,
    build_local_shadow_vps_grafana_dashboard_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an importable local Grafana dashboard JSON for current V5.3 Shadow VPS metrics.",
    )
    parser.add_argument(
        "--prom-text-path",
        type=Path,
        required=True,
        help="Path to the current Shadow VPS `.prom` payload used to summarize observed metrics.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_grafana_dashboard",
        help="Directory where the dashboard JSON and summary JSON will be written.",
    )
    parser.add_argument(
        "--datasource-uid",
        default="prometheus",
        help="Grafana datasource UID expected by the generated dashboard.",
    )
    parser.add_argument(
        "--datasource-name",
        default="Prometheus",
        help="Grafana datasource display name expected by the generated dashboard.",
    )
    parser.add_argument(
        "--title",
        default="V5.3 Shadow VPS - Local Dev Observability",
        help="Dashboard title.",
    )
    parser.add_argument(
        "--uid",
        default="v53-shadow-vps-local",
        help="Stable Grafana dashboard UID.",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = args.output_dir / "v53_shadow_vps_local_grafana.dashboard.json"
    summary_path = args.output_dir / "v53_shadow_vps_local_grafana.summary.json"

    payload = build_local_shadow_vps_grafana_dashboard(
        datasource_uid=args.datasource_uid,
        datasource_name=args.datasource_name,
        title=args.title,
        uid=args.uid,
    )
    summary = build_local_shadow_vps_grafana_dashboard_summary(
        source_prom_path=args.prom_text_path,
        output_path=dashboard_path,
        datasource_uid=args.datasource_uid,
        datasource_name=args.datasource_name,
        title=args.title,
        uid=args.uid,
    )

    atomic_write_json(dashboard_path, payload, indent=2)
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    print(f"Local Grafana dashboard JSON: {dashboard_path}")
    print(f"Local Grafana dashboard summary JSON: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
