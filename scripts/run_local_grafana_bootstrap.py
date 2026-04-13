#!/usr/bin/env python3
"""Bootstrap local Grafana with the Prometheus datasource and generated V5.3 dashboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from monitoring import bootstrap_local_grafana  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap local Grafana with the Prometheus datasource and generated V5.3 dashboard.",
    )
    parser.add_argument(
        "--grafana-url",
        default="http://127.0.0.1:3000",
        help="Base URL of the local Grafana instance.",
    )
    parser.add_argument(
        "--grafana-user",
        default="admin",
        help="Grafana basic-auth username.",
    )
    parser.add_argument(
        "--grafana-password",
        required=True,
        help="Grafana basic-auth password.",
    )
    parser.add_argument(
        "--dashboard-json-path",
        type=Path,
        required=True,
        help="Path to the generated Grafana dashboard import JSON.",
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://127.0.0.1:9090",
        help="Prometheus URL used by the datasource bootstrap.",
    )
    parser.add_argument(
        "--datasource-name",
        default="Prometheus",
        help="Datasource display name to create/update in Grafana.",
    )
    parser.add_argument(
        "--datasource-uid",
        default="prometheus",
        help="Datasource UID to create/update in Grafana.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_grafana_bootstrap",
        help="Directory where the Grafana bootstrap summary JSON will be written.",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "local_grafana_bootstrap.summary.json"
    summary = bootstrap_local_grafana(
        grafana_url=args.grafana_url,
        username=args.grafana_user,
        password=args.grafana_password,
        dashboard_payload_path=args.dashboard_json_path,
        datasource_name=args.datasource_name,
        datasource_uid=args.datasource_uid,
        prometheus_url=args.prometheus_url,
        output_path=summary_path,
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    print(f"Local Grafana bootstrap summary JSON: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
