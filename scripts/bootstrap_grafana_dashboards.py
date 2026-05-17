#!/usr/bin/env python3
"""Bootstrap Grafana datasource + dashboards into an already-running local Grafana.

Use this when ``Run-V53LocalSolution.ps1`` was unable to complete its
``_write_bootstrap_summary`` step (e.g. it timed out in ``_ensure_grafana``
because Grafana was already running and the readiness probe raced the
already-listening detection).
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from monitoring.local_grafana_api import (  # noqa: E402
    bootstrap_local_grafana,
    import_dashboard_payload,
)
from monitoring.local_lab_grafana_dashboard import (  # noqa: E402
    build_local_lab_grafana_dashboard,
)


def main() -> int:
    obs_dir = REPO_ROOT / "build" / "run_v53_local_solution" / "local_observability_stack"
    dashboard_json = obs_dir / "v53_shadow_vps_local_grafana.dashboard.json"
    bootstrap_summary = obs_dir / "local_grafana_bootstrap.summary.json"

    if not dashboard_json.is_file():
        sys.stderr.write(f"Dashboard JSON not found: {dashboard_json}\n")
        return 2

    print(f"→ Importing main Shadow VPS dashboard from {dashboard_json}")
    summary = bootstrap_local_grafana(
        grafana_url="http://127.0.0.1:3000",
        username="admin",
        password="admin",
        dashboard_payload_path=dashboard_json,
        datasource_name="Prometheus",
        datasource_uid="prometheus",
        prometheus_url="http://127.0.0.1:9090",
        output_path=bootstrap_summary,
    )
    print(
        f"  ✓ datasource status={summary.datasource_status_code} "
        f"dashboard status={summary.dashboard_status_code} "
        f"uid={summary.dashboard_uid}"
    )

    print("→ Importing local lab dashboard")
    lab_payload = build_local_lab_grafana_dashboard()
    lab_status, lab_uid = import_dashboard_payload(
        grafana_url="http://127.0.0.1:3000",
        username="admin",
        password="admin",
        dashboard_payload=lab_payload,
    )
    print(f"  ✓ lab dashboard status={lab_status} uid={lab_uid}")

    print("\n✅ Done. Open http://127.0.0.1:3000 → Dashboards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
