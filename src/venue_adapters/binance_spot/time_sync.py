"""Clock synchronization helpers for Binance Spot."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping

import yaml
from pydantic import BaseModel, Field, ValidationError

from calibration_loader.loader import CalibrationArtifactValidationError, CalibrationLoader
from interface_contracts.binance_contracts import BinanceServerTime, BinanceTimeSyncResult


class BinanceAdapterConfig(BaseModel, frozen=True):
    """Runtime config template for the Binance Spot adapter."""

    schema_version: str = Field(default="binance_adapter.v1", min_length=1)
    rest_base_url: str = Field(default="https://api.binance.com", min_length=1)
    timeout_s: float = Field(default=5.0, gt=0.0)
    recv_window_ms: int = Field(default=5000, ge=1)
    calibration_root: str = Field(default="config/calibration", min_length=1)
    calibration_version: str = Field(default="v1", min_length=1)
    fee_aware_edge_gate_enabled: bool = False
    time_sync_drift_threshold_id: str = Field(default="THR-X01", min_length=1)
    websocket_endpoint: str = Field(default="wss://stream.binance.com:9443/ws", min_length=1)
    websocket_gap_threshold_id: str = Field(default="THR-X02", min_length=1)
    websocket_silence_threshold_s: float = Field(default=30.0, ge=0.0)
    websocket_snapshot_limit: int = Field(default=1000, ge=1, le=5000)
    user_data_websocket_endpoint: str = Field(default="wss://ws-api.binance.com:443/ws-api/v3", min_length=1)
    user_data_connect_timeout_s: float = Field(default=5.0, gt=0.0)
    user_data_recv_timeout_s: float = Field(default=0.2, gt=0.0)
    user_data_max_messages_per_poll: int = Field(default=32, ge=1)


class BinanceTimeSync:
    """Read-only drift check against Binance server time."""

    def __init__(
        self,
        server_time_reader: Callable[[], Awaitable[BinanceServerTime]],
        *,
        threshold_ms: int,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        if threshold_ms < 0:
            raise ValueError("threshold_ms must be >= 0")
        self._server_time_reader = server_time_reader
        self._threshold_ms = threshold_ms
        self._clock_ms = clock_ms or _default_clock_ms

    async def sync(self) -> BinanceTimeSyncResult:
        server_time = await self._server_time_reader()
        local_time_ms = self._clock_ms()
        drift_ms = local_time_ms - server_time.server_time_ms
        return BinanceTimeSyncResult(
            server_time_ms=server_time.server_time_ms,
            local_time_ms=local_time_ms,
            drift_ms=drift_ms,
            threshold_ms=self._threshold_ms,
            alert_triggered=abs(drift_ms) > self._threshold_ms,
        )


def _default_clock_ms() -> int:
    return time.time_ns() // 1_000_000


def load_binance_adapter_config(path: Path | str) -> BinanceAdapterConfig:
    """Load and validate the Binance adapter YAML config."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Binance adapter config {config_path} does not exist")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise CalibrationArtifactValidationError(
            f"Binance adapter config {config_path} must deserialize to a mapping"
        )
    try:
        return BinanceAdapterConfig.model_validate(payload)
    except ValidationError as exc:
        raise CalibrationArtifactValidationError(
            f"Binance adapter config {config_path} failed validation: {exc}"
        ) from exc


def resolve_time_sync_threshold_ms(
    config: BinanceAdapterConfig,
    *,
    calibration_root: Path | str | None = None,
) -> int:
    """Resolve THR-X01 through the shared calibration loader."""

    loader = CalibrationLoader(calibration_root or config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    value = loader.get_value(collection, config.time_sync_drift_threshold_id)
    if not isinstance(value, int | float):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.time_sync_drift_threshold_id!r} must be numeric"
        )
    threshold_ms = int(value)
    if threshold_ms < 0:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.time_sync_drift_threshold_id!r} must be >= 0"
        )
    return threshold_ms


def resolve_websocket_gap_threshold_s(
    config: BinanceAdapterConfig,
    *,
    calibration_root: Path | str | None = None,
) -> float:
    """Resolve THR-X02 through the shared calibration loader."""

    loader = CalibrationLoader(calibration_root or config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    value = loader.get_value(collection, config.websocket_gap_threshold_id)
    if not isinstance(value, int | float):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.websocket_gap_threshold_id!r} must be numeric"
        )
    threshold_s = float(value)
    if threshold_s < 0.0:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {config.websocket_gap_threshold_id!r} must be >= 0"
        )
    return threshold_s


__all__ = [
    "BinanceAdapterConfig",
    "BinanceTimeSync",
    "load_binance_adapter_config",
    "resolve_time_sync_threshold_ms",
    "resolve_websocket_gap_threshold_s",
]
