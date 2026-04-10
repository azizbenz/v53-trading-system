"""Deterministic purification estimates for bounded halal compliance."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from calibration_loader.loader import CalibrationArtifactValidationError, CalibrationLoader

from .contracts import PurificationEstimate, PurificationSourceType, ShariaPolicy


class StablecoinPurificationConfig:
    """Shared-core lookup config for the stablecoin purification annual rate."""

    def __init__(
        self,
        *,
        calibration_root: Path | str = "config/calibration",
        calibration_version: str = "v1",
        annual_rate_threshold_id: str = "THR-H03",
    ) -> None:
        self.calibration_root = Path(calibration_root)
        self.calibration_version = calibration_version
        self.annual_rate_threshold_id = annual_rate_threshold_id


def calculate_purification(
    *,
    asset_received: str,
    quantity: Decimal | int | float | str,
    unit_price_quote: Decimal | int | float | str,
    source: PurificationSourceType,
    policy: ShariaPolicy,
) -> PurificationEstimate:
    if source == PurificationSourceType.STABLECOIN_RESERVE:
        raise ValueError("Stablecoin reserve purification must use estimate_stablecoin_purification")
    normalized_quantity = _to_decimal(quantity)
    normalized_price = _to_decimal(unit_price_quote)
    if normalized_quantity < 0 or normalized_price < 0:
        raise ValueError("quantity and unit_price_quote must be >= 0")
    gross_amount_quote = normalized_quantity * normalized_price
    return PurificationEstimate(
        asset_symbol=asset_received.strip().upper(),
        source_type=source,
        policy_version=policy.policy_version,
        gross_amount_quote=gross_amount_quote,
        purification_amount_quote=gross_amount_quote,
        purification_rate=Decimal("1"),
        detail=f"{source.value} revenue is fully marked for purification under {policy.policy_version}",
    )


def estimate_stablecoin_purification(
    *,
    asset_symbol: str,
    average_balance_quote: Decimal | int | float | str,
    holding_days: int,
    policy: ShariaPolicy,
    config: StablecoinPurificationConfig | None = None,
) -> PurificationEstimate:
    if holding_days < 0:
        raise ValueError("holding_days must be >= 0")
    normalized_balance = _to_decimal(average_balance_quote)
    if normalized_balance < 0:
        raise ValueError("average_balance_quote must be >= 0")
    normalized_asset = asset_symbol.strip().upper()
    if not policy.stablecoin_policy.purification_required or holding_days == 0 or normalized_balance == 0:
        return PurificationEstimate(
            asset_symbol=normalized_asset,
            source_type=PurificationSourceType.STABLECOIN_RESERVE,
            policy_version=policy.policy_version,
            gross_amount_quote=normalized_balance,
            purification_amount_quote=Decimal("0"),
            purification_rate=Decimal("0"),
            detail=f"stablecoin purification disabled or not applicable under {policy.policy_version}",
        )
    calibration = config or StablecoinPurificationConfig()
    annual_rate = _resolve_annual_rate(calibration)
    purification_amount = (normalized_balance * annual_rate * Decimal(holding_days)) / Decimal(365)
    purification_rate = Decimal("0") if normalized_balance == 0 else purification_amount / normalized_balance
    return PurificationEstimate(
        asset_symbol=normalized_asset,
        source_type=PurificationSourceType.STABLECOIN_RESERVE,
        policy_version=policy.policy_version,
        gross_amount_quote=normalized_balance,
        purification_amount_quote=purification_amount,
        purification_rate=purification_rate,
        detail=(
            f"stablecoin reserve purification estimated from {calibration.annual_rate_threshold_id} "
            f"over {holding_days} days"
        ),
    )


def _resolve_annual_rate(config: StablecoinPurificationConfig) -> Decimal:
    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    value = loader.get_value(collection, config.annual_rate_threshold_id)
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.annual_rate_threshold_id!r} must be numeric"
        )
    annual_rate = _to_decimal(value)
    if annual_rate < 0 or annual_rate > 1:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.annual_rate_threshold_id!r} must be between 0 and 1"
        )
    return annual_rate


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


__all__ = [
    "StablecoinPurificationConfig",
    "calculate_purification",
    "estimate_stablecoin_purification",
]
