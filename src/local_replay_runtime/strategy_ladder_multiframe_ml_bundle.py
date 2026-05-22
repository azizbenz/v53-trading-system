"""Governed Strategy Ladder multi-timeframe ML bundle contracts.

This bundle keeps the existing single-timeframe ``MlModelArtifact`` untouched.
Each timeframe still trains its own governed artifact; the bundle only adds a
strict routing manifest so the backtest can select the matching frozen model.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


_HASH_PATTERN = r"^[0-9a-f]{64}$"


def normalize_timeframe_scope(raw_value: object) -> tuple[str, ...]:
    """Return a deduplicated ordered timeframe scope from text or sequence."""

    values: list[str] = []
    if raw_value is None:
        return ()
    if isinstance(raw_value, str):
        values = [part.strip() for part in raw_value.split(",")]
    elif isinstance(raw_value, (list, tuple, set)):
        values = [str(part).strip() for part in raw_value]
    else:
        values = [str(raw_value).strip()]
    normalized = tuple(dict.fromkeys(value for value in values if value))
    return normalized


def multiframe_bundle_feature_hash(
    slices: tuple["StrategyLadderMlTimeframeSlice", ...],
) -> str:
    payload = [
        {
            "timeframe": item.timeframe,
            "feature_hash": item.feature_hash,
            "feature_names": list(item.feature_names),
        }
        for item in slices
    ]
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class StrategyLadderMlTimeframeSlice(BaseModel, frozen=True):
    """One governed frozen artifact inside the multi-timeframe bundle."""

    timeframe: str = Field(..., min_length=1)
    artifact_ref: str = Field(..., min_length=1)
    artifact_hash: str = Field(..., pattern=_HASH_PATTERN)
    feature_hash: str = Field(..., pattern=_HASH_PATTERN)
    feature_names: tuple[str, ...]
    training_report_ref: str = ""
    anti_leakage_proof_ref: str = ""
    live_drift_snapshot_ref: str = ""
    artifact_stale_after: datetime | None = None

    @field_validator("timeframe")
    @classmethod
    def _normalize_timeframe(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("timeframe must not be empty")
        return normalized

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not normalized:
            raise ValueError("feature_names must not be empty")
        return normalized


class StrategyLadderMlMultiTimeframeBundle(BaseModel, frozen=True):
    """Local governed bundle used by Strategy Ladder frozen overlay routing."""

    schema_version: str = "strategy_ladder.ml_multiframe_bundle.v1"
    bundle_kind: str = "STRATEGY_LADDER_EXPECTED_EDGE_MULTIFRAME"
    artifact_hash: str = Field(..., pattern=_HASH_PATTERN)
    feature_hash: str = Field(..., pattern=_HASH_PATTERN)
    pair: str = Field(..., min_length=1)
    timeframe_scope: tuple[str, ...]
    feature_names: tuple[str, ...]
    calibration_version: str = Field(..., min_length=1)
    created_at: datetime
    slices: tuple[StrategyLadderMlTimeframeSlice, ...]

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be empty")
        return normalized

    @field_validator("timeframe_scope", mode="before")
    @classmethod
    def _normalize_scope(cls, value: object) -> tuple[str, ...]:
        normalized = normalize_timeframe_scope(value)
        if not normalized:
            raise ValueError("timeframe_scope must not be empty")
        return normalized

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not normalized:
            raise ValueError("feature_names must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_slices(self) -> "StrategyLadderMlMultiTimeframeBundle":
        slice_timeframes = tuple(item.timeframe for item in self.slices)
        if not self.slices:
            raise ValueError("slices must not be empty")
        if tuple(dict.fromkeys(slice_timeframes)) != self.timeframe_scope:
            raise ValueError("timeframe_scope must match ordered slice timeframes")
        expected_feature_hash = multiframe_bundle_feature_hash(self.slices)
        if self.feature_hash != expected_feature_hash:
            raise ValueError("feature_hash does not match slice feature payload")
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("artifact_hash mismatch")
        for item in self.slices:
            if item.feature_names != self.feature_names:
                raise ValueError("all slices must share the same feature_names")
        return self

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "bundle_kind": self.bundle_kind,
            "feature_hash": self.feature_hash,
            "pair": self.pair,
            "timeframe_scope": list(self.timeframe_scope),
            "feature_names": list(self.feature_names),
            "calibration_version": self.calibration_version,
            "created_at": self.created_at.isoformat(),
            "slices": [item.model_dump(mode="json") for item in self.slices],
        }

    def artifact_hash_sha256(self) -> str:
        payload = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def create(cls, **payload: object) -> "StrategyLadderMlMultiTimeframeBundle":
        canonical_payload = dict(payload)
        slices_raw = canonical_payload.get("slices")
        if isinstance(slices_raw, list):
            canonical_payload["slices"] = tuple(
                StrategyLadderMlTimeframeSlice.model_validate(item) for item in slices_raw
            )
        canonical_payload["feature_hash"] = multiframe_bundle_feature_hash(
            canonical_payload["slices"]
        )
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


__all__ = [
    "StrategyLadderMlMultiTimeframeBundle",
    "StrategyLadderMlTimeframeSlice",
    "multiframe_bundle_feature_hash",
    "normalize_timeframe_scope",
]
