#!/usr/bin/env python3
"""Build a local-PC Prometheus scrape bundle from discovered Shadow VPS manifests."""

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
    build_shadow_vps_prometheus_file_sd_from_root,
    discover_shadow_vps_service_scrape_manifests,
)


def _emit_output_line(message: str) -> None:
    """Emit a launcher path line without using print()."""
    sys.stdout.write(f"{message}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local-PC Prometheus file_sd bundle from Shadow VPS scrape manifests."
        ),
    )
    parser.add_argument(
        "--scrape-root",
        type=Path,
        required=True,
        help="Root directory containing one or more pulled/copied Shadow VPS service dirs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_prometheus_scrape_bundle",
        help="Directory where the aggregated discovery and file_sd artifacts will be written.",
    )
    args = parser.parse_args(argv)

    discovery = discover_shadow_vps_service_scrape_manifests(args.scrape_root)
    file_sd_entries = build_shadow_vps_prometheus_file_sd_from_root(args.scrape_root)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    discovery_path = args.output_dir / "shadow_vps_scrape_discovery.json"
    file_sd_path = args.output_dir / "shadow_vps_prometheus_file_sd.json"
    atomic_write_json(discovery_path, discovery.model_dump(mode="json"), indent=2)
    atomic_write_json(
        file_sd_path,
        [entry.model_dump(mode="json") for entry in file_sd_entries],
        indent=2,
    )

    _emit_output_line(f"Shadow VPS scrape discovery JSON: {discovery_path}")
    _emit_output_line(f"Shadow VPS Prometheus file_sd JSON: {file_sd_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
