"""Cockpit reader for the persisted Shadow VPS model-risk snapshot.

The live source of truth is the service-owned file
``service_dir/model_risk_register.snapshot.json``. When the file is absent,
the cockpit renders a neutral placeholder instead of crashing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error", "not_yet_persisted"]


class ArtefactReference(BaseModel, frozen=True):
    kind: str
    profile_id: str = ""
    version: str = ""
    sha256: str = ""
    last_validated_at: str = ""
    drift_score: float | None = None
    review_state: str = ""


class ModelRiskRegisterSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "not_yet_persisted"
    source_path: str = ""
    active_ml: ArtefactReference | None = None
    active_regime_detector: ArtefactReference | None = None
    shadow_ml_challenger: ArtefactReference | None = None
    shadow_regime_detector_challenger: ArtefactReference | None = None
    promotion_eligible: bool = False
    info_message: str = (
        "Model Risk Register snapshot has not been emitted by the current Shadow "
        "service cycle yet."
    )


def read_model_risk_register(service_dir: Path) -> ModelRiskRegisterSnapshot:
    path = service_dir / "model_risk_register.snapshot.json"
    if not path.is_file():
        return ModelRiskRegisterSnapshot(source_status="not_yet_persisted")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse model risk register %s: %s", path, exc)
        return ModelRiskRegisterSnapshot(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return ModelRiskRegisterSnapshot(source_status="parse_error", source_path=str(path))
    return ModelRiskRegisterSnapshot(
        source_status="ok",
        source_path=str(path),
        active_ml=_parse_ref(payload.get("active_ml")),
        active_regime_detector=_parse_ref(payload.get("active_regime_detector")),
        shadow_ml_challenger=_parse_ref(payload.get("shadow_ml_challenger")),
        shadow_regime_detector_challenger=_parse_ref(payload.get("shadow_regime_detector_challenger")),
        promotion_eligible=bool(payload.get("promotion_eligible", False)),
    )


def _parse_ref(payload: object) -> ArtefactReference | None:
    if not isinstance(payload, dict):
        return None
    return ArtefactReference(
        kind=str(payload.get("kind", "")),
        profile_id=str(payload.get("profile_id", "")),
        version=str(payload.get("version", "")),
        sha256=str(payload.get("sha256", "")),
        last_validated_at=str(payload.get("last_validated_at", "")),
        drift_score=_optional_float(payload.get("drift_score")),
        review_state=str(payload.get("review_state", "")),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ArtefactReference",
    "ModelRiskRegisterSnapshot",
    "read_model_risk_register",
]
