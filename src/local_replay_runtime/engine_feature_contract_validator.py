from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_PROXY_TOKENS = ("PROXY", "DEFAULT", "TO_CALIBRATE", "UNKNOWN")
_MEASURED_TOKENS = ("MEASURED_", "GOVERNED_", "STATIC_CONSERVATIVE_")


@dataclass(frozen=True)
class EngineFeatureExpectation:
    engine_id: str
    feature_name: str
    unit: str
    consumer: str
    required: bool = True
    requires_timestamp: bool = False
    measured_required: bool = False
    proxy_forbidden_in_b2: bool = False
    sanity_min: float | None = None
    sanity_max: float | None = None


@dataclass(frozen=True)
class EngineFeatureContractRow:
    engine_id: str
    candidate_id: str
    feature_name: str
    value: Any
    unit: str
    provenance: str
    source_path: str
    timestamp_ms: int | None
    staleness_ms: int | None
    proxy_or_measured: str
    source_status: str
    truth_status: str
    consumer: str
    expected_min: float | None
    expected_max: float | None
    missing: bool
    status: str
    reason: str


@dataclass(frozen=True)
class EngineFeatureContractAudit:
    schema_version: str
    engine_id: str
    candidate_id: str
    runtime_mode: str
    builder_status: str
    builder_provenance: str
    valid: bool
    invalid_count: int
    rows: tuple[EngineFeatureContractRow, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "engine_id": self.engine_id,
            "candidate_id": self.candidate_id,
            "runtime_mode": self.runtime_mode,
            "builder_status": self.builder_status,
            "builder_provenance": self.builder_provenance,
            "valid": self.valid,
            "invalid_count": self.invalid_count,
            "rows": [asdict(row) for row in self.rows],
        }


def _is_measured(provenance: str) -> bool:
    normalized = str(provenance or "").strip().upper()
    return any(token in normalized for token in _MEASURED_TOKENS)


def _is_proxy(provenance: str) -> bool:
    normalized = str(provenance or "").strip().upper()
    return any(token in normalized for token in _PROXY_TOKENS)


def _classify_provenance(provenance: str) -> str:
    if _is_measured(provenance):
        return "measured"
    if _is_proxy(provenance):
        return "proxy"
    return "unknown"


def _validate_row(
    expectation: EngineFeatureExpectation,
    *,
    candidate_id: str,
    value: Any,
    provenance: str,
    source_path: str,
    timestamp_ms: int | None,
    staleness_ms: int | None,
    runtime_mode: str,
    feature_metadata: dict[str, Any] | None = None,
) -> EngineFeatureContractRow:
    metadata = feature_metadata or {}
    missing = value is None
    provenance_class = str(
        metadata.get("proxy_or_measured_override")
        or _classify_provenance(provenance)
    ).strip() or "unknown"
    source_status = str(metadata.get("source_status") or provenance or "").strip()
    truth_status = str(metadata.get("truth_status") or "").strip()
    status = "valid"
    reason = ""

    if not expectation.unit.strip():
        status = "invalid"
        reason = "unknown_unit"
    elif not provenance.strip():
        status = "invalid"
        reason = "unknown_provenance"
    elif missing and expectation.required:
        status = "invalid"
        reason = "required_feature_missing"
    elif expectation.requires_timestamp and timestamp_ms is None:
        status = "invalid"
        reason = "timestamp_missing"
    elif provenance_class == "unknown":
        status = "invalid"
        reason = str(metadata.get("unclassified_reason") or "provenance_unclassified")
    elif expectation.measured_required and provenance_class != "measured":
        status = "invalid"
        reason = str(
            metadata.get("measured_required_failure_reason")
            or "measured_feature_required"
        )
    elif expectation.proxy_forbidden_in_b2 and runtime_mode.upper() == "B2" and provenance_class == "proxy":
        status = "invalid"
        reason = str(metadata.get("block_reason") or "proxy_used_as_truth_in_b2")
    elif metadata.get("forced_invalid_reason"):
        status = "invalid"
        reason = str(metadata.get("forced_invalid_reason") or "")
    elif isinstance(value, bool):
        status = "valid"
    elif isinstance(value, int | float):
        numeric = float(value)
        if expectation.sanity_min is not None and numeric < expectation.sanity_min:
            status = "invalid"
            reason = f"value_below_sanity_min:{expectation.sanity_min}"
        elif expectation.sanity_max is not None and numeric > expectation.sanity_max:
            status = "invalid"
            reason = f"value_above_sanity_max:{expectation.sanity_max}"

    return EngineFeatureContractRow(
        engine_id=expectation.engine_id,
        candidate_id=candidate_id,
        feature_name=expectation.feature_name,
        value=value,
        unit=expectation.unit,
        provenance=provenance,
        source_path=source_path,
        timestamp_ms=timestamp_ms,
        staleness_ms=staleness_ms,
        proxy_or_measured=provenance_class,
        source_status=source_status,
        truth_status=truth_status,
        consumer=expectation.consumer,
        expected_min=expectation.sanity_min,
        expected_max=expectation.sanity_max,
        missing=missing,
        status=status,
        reason=reason,
    )


def audit_engine_feature_contract(
    *,
    engine_id: str,
    candidate_id: str,
    payload: dict[str, Any],
    expectations: tuple[EngineFeatureExpectation, ...],
    provenance_by_feature: dict[str, str],
    source_path_by_feature: dict[str, str] | None = None,
    timestamp_ms_by_feature: dict[str, int | None] | None = None,
    staleness_ms_by_feature: dict[str, int | None] | None = None,
    feature_metadata_by_feature: dict[str, dict[str, Any]] | None = None,
    runtime_mode: str,
    builder_status: str,
    builder_provenance: str,
) -> EngineFeatureContractAudit:
    source_paths = source_path_by_feature or {}
    timestamps = timestamp_ms_by_feature or {}
    staleness = staleness_ms_by_feature or {}
    metadata_by_feature = feature_metadata_by_feature or {}
    rows = tuple(
        _validate_row(
            expectation,
            candidate_id=candidate_id,
            value=payload.get(expectation.feature_name),
            provenance=provenance_by_feature.get(expectation.feature_name, builder_provenance),
            source_path=source_paths.get(expectation.feature_name, ""),
            timestamp_ms=timestamps.get(expectation.feature_name),
            staleness_ms=staleness.get(expectation.feature_name),
            runtime_mode=runtime_mode,
            feature_metadata=metadata_by_feature.get(expectation.feature_name),
        )
        for expectation in expectations
    )
    invalid_count = sum(1 for row in rows if row.status != "valid")
    return EngineFeatureContractAudit(
        schema_version="v53.engine_feature_contract_audit.v1",
        engine_id=engine_id,
        candidate_id=candidate_id,
        runtime_mode=runtime_mode,
        builder_status=builder_status,
        builder_provenance=builder_provenance,
        valid=invalid_count == 0,
        invalid_count=invalid_count,
        rows=rows,
    )


__all__ = [
    "EngineFeatureContractAudit",
    "EngineFeatureExpectation",
    "EngineFeatureContractRow",
    "audit_engine_feature_contract",
]
