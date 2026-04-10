from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from sharia_compliance import AccountFeaturesAuditConfig
from venue_adapters.binance_spot import BinanceAccountFeatureAuditProvider


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-account-feature-provider-fixtures") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _payload(*, threshold_id: str, value: int | float) -> dict[str, object]:
    return {
        "artifact_id": f"{threshold_id.lower()}-artifact",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-10T10:15:00Z",
        "thresholds": (
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/sharia_compliance/account_features_audit.py",
                "calibration_artifact": "config/calibration/v1/account_audit.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-10T12:00:00Z",
        },
    }


def _write_signed_yaml(path: Path, *, threshold_id: str, value: int | float) -> None:
    payload = _payload(threshold_id=threshold_id, value=value)
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


class _FakeClient:
    def __init__(self) -> None:
        self.paths: list[str] = []

    async def get_account_feature_payload(
        self,
        *,
        path: str,
        recv_window_ms: int,
        params: dict[str, str] | None = None,
    ) -> dict[str, object] | list[object]:
        assert recv_window_ms == 5000
        self.paths.append(path)
        if path == "/sapi/v1/margin/account":
            return {"userAssets": [{"asset": "USDT", "borrowed": "12.5", "interest": "0.5"}]}
        if path == "/sapi/v1/savings/account":
            return {"totalAmountInBTC": "0"}
        if path == "/sapi/v1/lending/project/position/list":
            return {"rows": []}
        if path == "/sapi/v1/staking/position":
            return []
        if path == "/sapi/v1/futures/transfer":
            return []
        raise AssertionError(f"unexpected path {path}")


def test_account_feature_provider_builds_audit_report(calibration_tmpdir: Path) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(version_dir / "account_audit.yml", threshold_id="THR-H02", value=604800)
    client = _FakeClient()

    async def run() -> None:
        provider = BinanceAccountFeatureAuditProvider(
            client,
            recv_window_ms=5000,
            audit_config=AccountFeaturesAuditConfig(calibration_root=calibration_tmpdir),
            now=lambda: datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        )
        report = await provider.run_audit()
        assert report.clean is False
        assert report.audit_interval_s == 604800
        assert report.findings[0].reason_code == "FORBIDDEN_ACCOUNT_FEATURE_BALANCE"

    asyncio.run(run())
    assert client.paths == [
        "/sapi/v1/margin/account",
        "/sapi/v1/savings/account",
        "/sapi/v1/lending/project/position/list",
        "/sapi/v1/staking/position",
        "/sapi/v1/futures/transfer",
    ]
