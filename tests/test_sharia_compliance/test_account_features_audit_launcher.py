from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

from sharia_compliance.contracts import AccountFeaturesAuditReport


def test_run_sharia_account_audit_writes_json_report(tmp_path: Path) -> None:
    script_path = Path("scripts/run_sharia_account_audit.py")
    spec = importlib.util.spec_from_file_location("run_sharia_account_audit", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class _FakeProvider:
        async def run_audit(self) -> AccountFeaturesAuditReport:
            return AccountFeaturesAuditReport(
                scanned_at="2026-04-10T12:00:00Z",
                audit_interval_s=604800,
                findings=(),
            )

    output_path = tmp_path / "sharia_account_audit" / "latest_report.json"
    alerts_output_path = tmp_path / "sharia_account_audit" / "latest_alerts.json"
    exit_code = asyncio.run(
        module.run_sharia_account_audit(
            _FakeProvider(),
            output_path=output_path,
            alerts_output_path=alerts_output_path,
            correlation_id="corr-1",
        )
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["audit_interval_s"] == 604800
    assert payload["findings"] == []
    assert json.loads(alerts_output_path.read_text(encoding="utf-8")) == []
