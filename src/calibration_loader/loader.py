"""Shared loader for signed dynamic-threshold calibration artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from calibration_loader.contracts import (
    CalibrationArtifact,
    CalibrationArtifactCollection,
    CalibrationThresholdEntry,
)


class CalibrationLoaderError(RuntimeError):
    """Base class for explicit calibration-loader failures."""


class CalibrationArtifactNotFoundError(CalibrationLoaderError):
    """Raised when the requested calibration artifact path does not exist."""


class CalibrationArtifactFormatError(CalibrationLoaderError):
    """Raised when an artifact file cannot be parsed as a supported format."""


class CalibrationArtifactValidationError(CalibrationLoaderError):
    """Raised when parsed artifact content violates the typed contract."""


class CalibrationArtifactSignatureError(CalibrationLoaderError):
    """Raised when an artifact exists but is not explicitly signed."""


class CalibrationThresholdNotFoundError(CalibrationLoaderError):
    """Raised when a threshold_id is absent from the loaded collection."""


def _read_supported_payload(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix in {".yml", ".yaml"}:
            return yaml.safe_load(text)
        if suffix == ".json":
            return json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise CalibrationArtifactFormatError(
            f"Calibration artifact {path} could not be parsed: {exc}"
        ) from exc
    raise CalibrationArtifactFormatError(
        f"Calibration artifact {path} has unsupported suffix {path.suffix!r}"
    )


def load_calibration_artifact(path: Path | str) -> CalibrationArtifact:
    """Load and validate a signed calibration artifact from disk."""

    artifact_path = Path(path)
    if not artifact_path.exists():
        raise CalibrationArtifactNotFoundError(
            f"Calibration artifact {artifact_path} does not exist"
        )
    if not artifact_path.is_file():
        raise CalibrationArtifactFormatError(
            f"Calibration artifact {artifact_path} must be a file"
        )

    payload = _read_supported_payload(artifact_path)
    if not isinstance(payload, dict):
        raise CalibrationArtifactFormatError(
            f"Calibration artifact {artifact_path} must deserialize to a mapping"
        )
    if "signature" not in payload:
        raise CalibrationArtifactSignatureError(
            f"Calibration artifact {artifact_path} is missing required signature metadata"
        )
    try:
        return CalibrationArtifact.model_validate(payload)
    except ValidationError as exc:
        raise CalibrationArtifactValidationError(
            f"Calibration artifact {artifact_path} failed validation: {exc}"
        ) from exc


def load_calibration_collection(path: Path | str) -> CalibrationArtifactCollection:
    """Load one signed artifact or a directory of signed artifacts."""

    candidate = Path(path)
    if not candidate.exists():
        raise CalibrationArtifactNotFoundError(
            f"Calibration path {candidate} does not exist"
        )
    if candidate.is_file():
        return CalibrationArtifactCollection(artifacts=(load_calibration_artifact(candidate),))
    if not candidate.is_dir():
        raise CalibrationArtifactFormatError(f"Calibration path {candidate} must be a file or dir")

    artifact_paths = tuple(
        sorted(
            child
            for child in candidate.iterdir()
            if child.is_file() and child.suffix.lower() in {".yml", ".yaml", ".json"}
        )
    )
    if not artifact_paths:
        raise CalibrationArtifactNotFoundError(
            f"Calibration directory {candidate} does not contain supported artifacts"
        )
    try:
        return CalibrationArtifactCollection(
            artifacts=tuple(load_calibration_artifact(path) for path in artifact_paths)
        )
    except ValidationError as exc:
        raise CalibrationArtifactValidationError(
            f"Calibration collection {candidate} failed validation: {exc}"
        ) from exc


class CalibrationLoader:
    """Version-aware neutral shared-core loader for dynamic thresholds."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def load(self, *, version: str) -> CalibrationArtifactCollection:
        if not version:
            raise CalibrationArtifactValidationError("Calibration version must not be empty")
        return load_calibration_collection(self._root / version)

    @staticmethod
    def get_entry(
        collection: CalibrationArtifactCollection,
        threshold_id: str,
    ) -> CalibrationThresholdEntry:
        for entry in collection.threshold_entries:
            if entry.threshold_id == threshold_id:
                return entry
        raise CalibrationThresholdNotFoundError(
            f"Calibration threshold_id {threshold_id!r} is not present in the loaded artifacts"
        )

    @classmethod
    def get_value(
        cls,
        collection: CalibrationArtifactCollection,
        threshold_id: str,
    ) -> bool | int | float | str:
        return cls.get_entry(collection, threshold_id).value
