"""Phase 2 adapter — EDGE / clock-drift / WS-gap calibration thresholds.

Source: ``config/calibration/v1/thresholds.yml`` produced manually
(human attestation) on 2026-04-26 to unblock the warmup.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error"]


class CalibrationThreshold(BaseModel, frozen=True):
    threshold_id: str
    value: float
    description: str = ""
    source_module: str = ""
    notes: str = ""


class CalibrationThresholdsSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    schema_version: str = ""
    artifact_id: str = ""
    version: str = ""
    produced_by: str = ""
    generated_at: str = ""
    thresholds: tuple[CalibrationThreshold, ...] = ()
    signature_mode: str = ""
    signed_by: str = ""
    signed_at: str = ""
    payload_hash_sha256: str = ""

    @property
    def is_signed(self) -> bool:
        return bool(self.signature_mode)


def read_calibration_thresholds(thresholds_path: Path) -> CalibrationThresholdsSnapshot:
    if not thresholds_path.is_file():
        return CalibrationThresholdsSnapshot(
            source_status="missing", source_path=str(thresholds_path)
        )
    try:
        payload = yaml.safe_load(thresholds_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        _logger.warning("Cannot parse thresholds %s: %s", thresholds_path, exc)
        return CalibrationThresholdsSnapshot(
            source_status="parse_error", source_path=str(thresholds_path)
        )
    if not isinstance(payload, dict):
        return CalibrationThresholdsSnapshot(
            source_status="parse_error", source_path=str(thresholds_path)
        )
    thresholds_raw = payload.get("thresholds") or ()
    thresholds = tuple(
        CalibrationThreshold(
            threshold_id=str(t.get("threshold_id", "")),
            value=float(t.get("value", 0.0) or 0.0),
            description=str(t.get("description", "")),
            source_module=str(t.get("source_module", "")),
            notes=str(t.get("notes", "")),
        )
        for t in thresholds_raw
        if isinstance(t, dict)
    )
    signature = payload.get("signature") or {}
    if not isinstance(signature, dict):
        signature = {}
    return CalibrationThresholdsSnapshot(
        source_status="ok",
        source_path=str(thresholds_path),
        schema_version=str(payload.get("schema_version", "")),
        artifact_id=str(payload.get("artifact_id", "")),
        version=str(payload.get("version", "")),
        produced_by=str(payload.get("produced_by", "")),
        generated_at=str(payload.get("generated_at", "")),
        thresholds=thresholds,
        signature_mode=str(signature.get("mode", "")),
        signed_by=str(signature.get("signed_by", "")),
        signed_at=str(signature.get("signed_at", "")),
        payload_hash_sha256=str(signature.get("payload_hash_sha256", "")),
    )


__all__ = [
    "CalibrationThreshold",
    "CalibrationThresholdsSnapshot",
    "read_calibration_thresholds",
]
