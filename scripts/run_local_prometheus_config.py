#!/usr/bin/env python3
"""Generate a checked local-PC Prometheus config from the aggregated V5.3 file_sd bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text  # noqa: E402
from monitoring import (  # noqa: E402
    build_local_prometheus_config_summary,
    build_local_prometheus_config_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a checked local-PC Prometheus config from the aggregated Shadow VPS file_sd bundle."
        ),
    )
    parser.add_argument(
        "--vps-file-sd-path",
        type=Path,
        required=True,
        help="Path to shadow_vps_prometheus_file_sd.json generated on the local PC.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_prometheus_config",
        help="Directory where the generated Prometheus config bundle will be written.",
    )
    parser.add_argument(
        "--local-node-exporter-target",
        default="",
        help="Optional local PC node_exporter target for Unix-like hosts; omit on Windows.",
    )
    parser.add_argument(
        "--local-windows-exporter-target",
        default="",
        help="Optional local PC windows_exporter target; for example 127.0.0.1:9182.",
    )
    parser.add_argument(
        "--local-lab-target",
        default="",
        help="Optional local Local-IA-Lab Prometheus bridge target; for example 127.0.0.1:9200.",
    )
    parser.add_argument(
        "--scrape-interval",
        default="15s",
        help="Global Prometheus scrape_interval for the generated config.",
    )
    parser.add_argument(
        "--evaluation-interval",
        default="15s",
        help="Global Prometheus evaluation_interval for the generated config.",
    )
    parser.add_argument(
        "--file-sd-refresh-interval",
        default="30s",
        help="Refresh interval used for the file_sd source in the generated config.",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    config_path = args.output_dir / "prometheus.local.generated.yml"
    summary_path = args.output_dir / "prometheus.local.config.summary.json"
    config_text = build_local_prometheus_config_text(
        vps_file_sd_path=args.vps_file_sd_path,
        scrape_interval=args.scrape_interval,
        evaluation_interval=args.evaluation_interval,
        file_sd_refresh_interval=args.file_sd_refresh_interval,
        local_node_exporter_target=args.local_node_exporter_target,
        local_windows_exporter_target=args.local_windows_exporter_target,
        local_lab_target=args.local_lab_target,
    )
    summary = build_local_prometheus_config_summary(
        vps_file_sd_path=args.vps_file_sd_path,
        output_path=config_path,
        scrape_interval=args.scrape_interval,
        evaluation_interval=args.evaluation_interval,
        local_node_exporter_target=args.local_node_exporter_target,
        local_windows_exporter_target=args.local_windows_exporter_target,
        local_lab_target=args.local_lab_target,
    )
    atomic_write_text(config_path, config_text)
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    print(f"Local Prometheus config YAML: {config_path}")
    print(f"Local Prometheus config summary JSON: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
