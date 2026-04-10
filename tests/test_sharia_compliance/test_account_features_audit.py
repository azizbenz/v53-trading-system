from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from sharia_compliance import AccountFeaturesAuditConfig, audit_account_features


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-account-features-audit-fixtures") / uuid4().hex
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
        "generated_at": "2026-04-09T10:15:00Z",
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
            "signed_at": "2026-04-09T12:00:00Z",
        },
    }


def _write_signed_yaml(path: Path, *, threshold_id: str, value: int | float) -> None:
    payload = _payload(threshold_id=threshold_id, value=value)
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_account_features_audit_detects_forbidden_endpoint(calibration_tmpdir: Path) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(version_dir / "account_audit.yml", threshold_id="THR-H02", value=604800)

    report = audit_account_features(
        observed_endpoint_paths=("https://api.binance.com/sapi/v1/savings/account",),
        config=AccountFeaturesAuditConfig(calibration_root=calibration_tmpdir),
        scanned_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
    )

    assert report.clean is False
    assert report.audit_interval_s == 604800
    assert report.findings[0].reason_code == "FORBIDDEN_ACCOUNT_FEATURE_ENDPOINT"


def test_account_features_audit_detects_non_zero_feature_balance(calibration_tmpdir: Path) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(version_dir / "account_audit.yml", threshold_id="THR-H02", value=604800)

    report = audit_account_features(
        feature_balances={"simple_earn_usdt": "12.50", "spot_free_usdt": "1000"},
        config=AccountFeaturesAuditConfig(calibration_root=calibration_tmpdir),
        scanned_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
    )

    assert report.clean is False
    assert report.findings[0].reason_code == "FORBIDDEN_ACCOUNT_FEATURE_BALANCE"


def test_account_features_audit_reports_clean_snapshot(calibration_tmpdir: Path) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(version_dir / "account_audit.yml", threshold_id="THR-H02", value=604800)

    report = audit_account_features(
        observed_endpoint_paths=("/api/v3/account",),
        feature_balances={"spot_free_usdt": "1000"},
        config=AccountFeaturesAuditConfig(calibration_root=calibration_tmpdir),
        scanned_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
    )

    assert report.clean is True
    assert report.findings == ()
