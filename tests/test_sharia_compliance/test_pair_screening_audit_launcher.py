from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4

from sharia_compliance import FilePairScreeningProvider, load_sharia_policy


def _test_dir() -> Path:
    path = Path("build/test_pair_screening_audit_launcher") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_run_sharia_pair_screening_audit_writes_json_report() -> None:
    script_path = Path("scripts/run_sharia_pair_screening_audit.py")
    spec = importlib.util.spec_from_file_location("run_sharia_pair_screening_audit", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    registry_path = _test_dir() / "pair_screening_registry.yml"
    registry_path.write_text(
        """
schema_version: sharia.pair_screening_registry.v1
registry_version: registry_v1
source_reference: manual_review
snapshots:
  - pair: BTCUSDT
    screening_provider: fixture
    provider_version: v1
    reviewed_at: 2026-04-10T12:00:00Z
    debt_to_total_assets: "0.20"
    cash_and_interest_bearing_to_total_assets: "0.10"
    interest_income_to_total_revenue: "0.01"
""".strip(),
        encoding="utf-8",
    )

    output_path = _test_dir() / "sharia_pair_screening" / "latest_report.json"
    alerts_output_path = _test_dir() / "sharia_pair_screening" / "latest_alerts.json"
    exit_code = module.run_sharia_pair_screening_audit(
        FilePairScreeningProvider(registry_path),
        traded_pairs=("BTCUSDT",),
        policy=load_sharia_policy("config/sharia/policy_v1.yml"),
        output_path=output_path,
        alerts_output_path=alerts_output_path,
        correlation_id="corr-1",
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["registry_version"] == "registry_v1"
    assert payload["findings"] == []
    assert json.loads(alerts_output_path.read_text(encoding="utf-8")) == []
