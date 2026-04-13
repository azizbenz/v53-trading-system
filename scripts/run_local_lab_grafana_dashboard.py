#!/usr/bin/env python3
"""Generate an importable local Grafana dashboard JSON for current V5.3 Local IA Lab metrics."""

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
    build_local_lab_grafana_dashboard,
    build_local_lab_grafana_dashboard_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an importable local Grafana dashboard JSON for current V5.3 Local IA Lab metrics.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--prom-text-path",
        type=Path,
        help="Path to the current Local IA Lab `.prom` payload used to summarize observed metrics.",
    )
    source_group.add_argument(
        "--observability-export-path",
        type=Path,
        help=(
            "Path to the current Local IA Lab observability export JSON. The script "
            "reads its `text_payload` field to summarize observed metrics."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_lab_grafana_dashboard",
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
        default="V5.3 Local IA Lab - Local Dev Observability",
        help="Dashboard title.",
    )
    parser.add_argument(
        "--uid",
        default="v53-local-lab",
        help="Stable Grafana dashboard UID.",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = args.output_dir / "v53_local_lab_grafana.dashboard.json"
    summary_path = args.output_dir / "v53_local_lab_grafana.summary.json"

    payload = build_local_lab_grafana_dashboard(
        datasource_uid=args.datasource_uid,
        datasource_name=args.datasource_name,
        title=args.title,
        uid=args.uid,
    )
    summary = build_local_lab_grafana_dashboard_summary(
        prom_text_path=args.prom_text_path,
        observability_export_path=args.observability_export_path,
        output_path=dashboard_path,
        datasource_uid=args.datasource_uid,
        datasource_name=args.datasource_name,
        title=args.title,
        uid=args.uid,
    )

    atomic_write_json(dashboard_path, payload, indent=2)
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    print(f"Local IA Lab Grafana dashboard JSON: {dashboard_path}")
    print(f"Local IA Lab Grafana dashboard summary JSON: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
