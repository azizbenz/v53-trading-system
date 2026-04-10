"""Deterministic weekly audit of forbidden Binance account features."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from calibration_loader.loader import CalibrationArtifactValidationError, CalibrationLoader

from .contracts import AccountFeatureAuditFinding, AccountFeaturesAuditReport

_FORBIDDEN_ENDPOINT_PREFIXES = (
    "/sapi/v1/margin/",
    "/sapi/v1/futures/",
    "/sapi/v1/savings/",
    "/sapi/v1/lending/",
    "/sapi/v1/staking/",
)
_FORBIDDEN_BALANCE_MARKERS = (
    "earn",
    "savings",
    "staking",
    "margin",
    "futures",
    "lending",
    "borrow",
    "loan",
)


class AccountFeaturesAuditConfig:
    """Shared-core lookup config for weekly account-feature audits."""

    def __init__(
        self,
        *,
        calibration_root: Path | str = "config/calibration",
        calibration_version: str = "v1",
        audit_interval_threshold_id: str = "THR-H02",
    ) -> None:
        self.calibration_root = Path(calibration_root)
        self.calibration_version = calibration_version
        self.audit_interval_threshold_id = audit_interval_threshold_id


def audit_account_features(
    *,
    observed_endpoint_paths: tuple[str, ...] = (),
    feature_balances: dict[str, Decimal | int | float | str] | None = None,
    config: AccountFeaturesAuditConfig | None = None,
    scanned_at: datetime | None = None,
) -> AccountFeaturesAuditReport:
    calibration = config or AccountFeaturesAuditConfig()
    findings: list[AccountFeatureAuditFinding] = []
    for observed_path in observed_endpoint_paths:
        normalized_path = _normalize_path(observed_path)
        if normalized_path.startswith(_FORBIDDEN_ENDPOINT_PREFIXES):
            findings.append(
                AccountFeatureAuditFinding(
                    reason_code="FORBIDDEN_ACCOUNT_FEATURE_ENDPOINT",
                    detail=f"forbidden account feature endpoint used: {normalized_path}",
                    observation=observed_path,
                )
            )
    for feature_name, raw_amount in (feature_balances or {}).items():
        normalized_name = feature_name.strip().lower()
        amount = _to_decimal(raw_amount)
        if amount <= 0:
            continue
        if any(marker in normalized_name for marker in _FORBIDDEN_BALANCE_MARKERS):
            findings.append(
                AccountFeatureAuditFinding(
                    reason_code="FORBIDDEN_ACCOUNT_FEATURE_BALANCE",
                    detail=f"forbidden account feature balance detected: {feature_name}={amount}",
                    observation=feature_name,
                )
            )
    return AccountFeaturesAuditReport(
        scanned_at=scanned_at or datetime.now(timezone.utc),
        audit_interval_s=resolve_account_features_audit_interval_s(calibration),
        findings=tuple(findings),
    )


def resolve_account_features_audit_interval_s(
    config: AccountFeaturesAuditConfig,
) -> int:
    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    value = loader.get_value(collection, config.audit_interval_threshold_id)
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.audit_interval_threshold_id!r} must be numeric"
        )
    interval_s = int(_to_decimal(value))
    if interval_s < 1:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.audit_interval_threshold_id!r} must be >= 1"
        )
    return interval_s


def _normalize_path(path: str) -> str:
    if not path.strip():
        return ""
    parsed = urlsplit(path)
    target = parsed.path or path
    return target.strip()


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


__all__ = [
    "AccountFeaturesAuditConfig",
    "audit_account_features",
    "resolve_account_features_audit_interval_s",
]
