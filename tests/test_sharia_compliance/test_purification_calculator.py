from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from sharia_compliance import (
    PurificationSourceType,
    StablecoinPurificationConfig,
    calculate_purification,
    estimate_stablecoin_purification,
    load_sharia_policy,
)


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-sharia-calibration-fixtures") / uuid4().hex
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
                "source_module": "src/sharia_compliance/purification_calculator.py",
                "calibration_artifact": "config/calibration/v1/sharia.yml",
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


def test_calculate_purification_marks_airdrop_as_fully_purifiable() -> None:
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    estimate = calculate_purification(
        asset_received="TOKENX",
        quantity=Decimal("15"),
        unit_price_quote=Decimal("2.50"),
        source=PurificationSourceType.AIRDROP,
        policy=policy,
    )

    assert estimate.asset_symbol == "TOKENX"
    assert estimate.gross_amount_quote == Decimal("37.50")
    assert estimate.purification_amount_quote == Decimal("37.50")
    assert estimate.purification_rate == Decimal("1")


def test_estimate_stablecoin_purification_loads_h03_from_calibration(
    calibration_tmpdir: Path,
) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(version_dir / "sharia.yml", threshold_id="THR-H03", value=0.02)
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    estimate = estimate_stablecoin_purification(
        asset_symbol="USDT",
        average_balance_quote=Decimal("10000"),
        holding_days=30,
        policy=policy,
        config=StablecoinPurificationConfig(calibration_root=calibration_tmpdir),
    )

    assert estimate.asset_symbol == "USDT"
    assert estimate.purification_amount_quote == Decimal("16.43835616438356164383561644")
    assert estimate.purification_rate == Decimal("0.001643835616438356164383561644")


def test_estimate_stablecoin_purification_returns_zero_when_policy_disables_it(
    calibration_tmpdir: Path,
) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(version_dir / "sharia.yml", threshold_id="THR-H03", value=0.02)
    policy = load_sharia_policy("config/sharia/policy_v1.yml")
    disabled_policy = policy.model_copy(
        update={
            "stablecoin_policy": policy.stablecoin_policy.model_copy(
                update={"purification_required": False}
            )
        }
    )

    estimate = estimate_stablecoin_purification(
        asset_symbol="USDT",
        average_balance_quote=Decimal("10000"),
        holding_days=30,
        policy=disabled_policy,
        config=StablecoinPurificationConfig(calibration_root=calibration_tmpdir),
    )

    assert estimate.purification_amount_quote == Decimal("0")
    assert estimate.purification_rate == Decimal("0")
