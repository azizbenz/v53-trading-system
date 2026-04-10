import asyncio
from pathlib import Path
import shutil

from venue_adapters.binance_spot.time_sync import (
    BinanceTimeSync,
    load_binance_adapter_config,
    resolve_time_sync_threshold_ms,
)
from interface_contracts.binance_contracts import BinanceServerTime


def _write_calibration_artifact(root: Path, *, threshold_ms: int) -> None:
    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = version_dir / "execution_thresholds.json"
    artifact_path.write_text(
        """
{
  "schema_version": "calibration.v1",
  "artifact_id": "exec-thresholds",
  "version": "v1",
  "produced_by": "pytest",
  "generated_at": "2026-04-09T10:00:00+00:00",
  "thresholds": [
    {
      "threshold_id": "THR-X01",
      "value": %d,
      "description": "Drift max horloge locale vs Binance avant alerte",
      "source_module": "src/venue_adapters/binance_spot/time_sync.py",
      "calibration_artifact": "execution_thresholds.json",
      "notes": ""
    }
  ],
  "signature": {
    "mode": "human_attestation",
    "signed_by": "pytest",
    "signed_at": "2026-04-09T10:05:00+00:00"
  }
}
"""
        % threshold_ms,
        encoding="utf-8",
    )


def test_load_binance_adapter_config_and_resolve_time_sync_threshold():
    build_root = Path("build/test_venue_adapters_binance_time_sync")
    shutil.rmtree(build_root, ignore_errors=True)
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        calibration_root = build_root / "calibration"
        _write_calibration_artifact(calibration_root, threshold_ms=500)
        config_path = build_root / "binance_adapter.yml"
        config_path.write_text(
            f"""
schema_version: binance_adapter.v1
rest_base_url: https://testnet.binance.vision
timeout_s: 5.0
recv_window_ms: 5000
calibration_root: {calibration_root.as_posix()}
calibration_version: v1
time_sync_drift_threshold_id: THR-X01
""",
            encoding="utf-8",
        )

        config = load_binance_adapter_config(config_path)
        threshold_ms = resolve_time_sync_threshold_ms(config)

        assert config.rest_base_url == "https://testnet.binance.vision"
        assert config.fee_aware_edge_gate_enabled is False
        assert threshold_ms == 500
    finally:
        shutil.rmtree(build_root, ignore_errors=True)


def test_binance_time_sync_flags_drift_beyond_threshold():
    async def fake_server_time() -> BinanceServerTime:
        return BinanceServerTime(server_time_ms=1_000)

    sync = BinanceTimeSync(
        fake_server_time,
        threshold_ms=500,
        clock_ms=lambda: 1_600,
    )

    result = asyncio.run(sync.sync())

    assert result.drift_ms == 600
    assert result.alert_triggered is True
