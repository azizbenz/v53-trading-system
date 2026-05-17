"""Typed contracts for governed audit-evidence classification."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator


class GovernedAuditEvidenceClass(StrEnum):
    """Evidence-grade vocabulary for governed audit outputs."""

    SCRATCH_ONLY = "SCRATCH_ONLY"
    AUDITED_HISTORICAL_EVIDENCE = "AUDITED_HISTORICAL_EVIDENCE"
    PROMOTION_GRADE_EVIDENCE = "PROMOTION_GRADE_EVIDENCE"


_EVIDENCE_CLASS_RANK = {
    GovernedAuditEvidenceClass.SCRATCH_ONLY: 0,
    GovernedAuditEvidenceClass.AUDITED_HISTORICAL_EVIDENCE: 1,
    GovernedAuditEvidenceClass.PROMOTION_GRADE_EVIDENCE: 2,
}

_ARTIFACT_GROUP_TO_KINDS = {
    "run_manifest": ("run_manifest",),
    "capital_profiles": ("capital_profile",),
    "engine_promotion": ("engine_promotion",),
    "pair_promotion": ("pair_promotion",),
    "strategy_promotion": ("strategy_promotion",),
    "sample_size_survival": ("sample_size_survival",),
    "trade_detail_ledger": ("trade_detail_ledger",),
    "refusal_ledger": ("refusal_ledger",),
    "loss_analysis_ledger": ("loss_analysis_ledger",),
}


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class GovernedAuditEvidenceEntry(BaseModel, frozen=True):
    """One classified evidence rail entry."""

    rail_id: str = Field(..., min_length=1)
    artifact_kind: str = Field(..., min_length=1)
    artifact_ref: str = Field(..., min_length=1)
    evidence_class: GovernedAuditEvidenceClass
    reasons: tuple[str, ...] = ()


class GovernedAuditEvidenceIndex(BaseModel, frozen=True):
    """Canonical audit-evidence index written alongside governed outputs."""

    schema_version: str = Field(default="governed_audit_evidence_index.v1", min_length=1)
    run_id: str | None = None
    source_root: str | None = None
    entries: tuple[GovernedAuditEvidenceEntry, ...] = ()
    created_at: datetime
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_index(self) -> "GovernedAuditEvidenceIndex":
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("GovernedAuditEvidenceIndex artifact_hash mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "source_root": self.source_root,
            "entries": [entry.model_dump(mode="json") for entry in self.entries],
            "created_at": _normalize_datetime(self.created_at).isoformat(),
        }

    def artifact_hash_sha256(self) -> str:
        return _hash_payload(self.canonical_payload())

    @classmethod
    def create(cls, **payload: Any) -> "GovernedAuditEvidenceIndex":
        canonical_payload = dict(payload)
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


def load_governed_audit_evidence_index(
    path: str | Path | None,
) -> GovernedAuditEvidenceIndex | None:
    """Read a governed evidence index from disk when present and valid."""

    if path is None:
        return None
    resolved = Path(path)
    if not resolved.is_file():
        return None
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return GovernedAuditEvidenceIndex.model_validate(payload)
    except ValidationError:
        return None


def _aggregate_group_evidence_class(
    entries: tuple[GovernedAuditEvidenceEntry, ...],
) -> str:
    if not entries:
        return "EVIDENCE_CLASS_NOT_PROVEN"
    strictest = min(
        entries,
        key=lambda item: _EVIDENCE_CLASS_RANK[item.evidence_class],
    )
    return strictest.evidence_class.value


def build_governed_audit_evidence_projection(
    *,
    index: GovernedAuditEvidenceIndex,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """Project evidence classes and fail-closed counts into summary-friendly fields."""

    counts = {
        GovernedAuditEvidenceClass.SCRATCH_ONLY.value: 0,
        GovernedAuditEvidenceClass.AUDITED_HISTORICAL_EVIDENCE.value: 0,
        GovernedAuditEvidenceClass.PROMOTION_GRADE_EVIDENCE.value: 0,
    }
    for entry in index.entries:
        counts[entry.evidence_class.value] += 1

    grouped: dict[str, tuple[GovernedAuditEvidenceEntry, ...]] = {}
    for group_name, kinds in _ARTIFACT_GROUP_TO_KINDS.items():
        grouped[group_name] = tuple(
            entry for entry in index.entries if entry.artifact_kind in kinds
        )

    blocker_codes: list[str] = []
    if counts[GovernedAuditEvidenceClass.SCRATCH_ONLY.value] > 0:
        blocker_codes.append("EVIDENCE_AUDIT_NOT_CONFIRMED")
    for entry in index.entries:
        blocker_codes.extend(str(reason) for reason in entry.reasons if reason)

    if counts[GovernedAuditEvidenceClass.SCRATCH_ONLY.value] > 0:
        evidence_status = "EVIDENCE_AUDIT_NOT_CONFIRMED"
    elif counts[GovernedAuditEvidenceClass.PROMOTION_GRADE_EVIDENCE.value] > 0 and (
        counts[GovernedAuditEvidenceClass.PROMOTION_GRADE_EVIDENCE.value]
        == len(index.entries)
    ):
        evidence_status = "PROMOTION_GRADE_EVIDENCE_PRESENT"
    elif counts[GovernedAuditEvidenceClass.AUDITED_HISTORICAL_EVIDENCE.value] > 0:
        evidence_status = "AUDITED_HISTORICAL_EVIDENCE_PRESENT"
    else:
        evidence_status = "EVIDENCE_CLASS_NOT_PROVEN"

    resolved_index_path = ""
    if index_path is not None:
        resolved_index_path = str(Path(index_path).resolve())

    return {
        "governed_audit_evidence_index_path": resolved_index_path,
        "governed_evidence_status": evidence_status,
        "audited_evidence_count": counts[
            GovernedAuditEvidenceClass.AUDITED_HISTORICAL_EVIDENCE.value
        ],
        "scratch_only_evidence_count": counts[
            GovernedAuditEvidenceClass.SCRATCH_ONLY.value
        ],
        "promotion_grade_evidence_count": counts[
            GovernedAuditEvidenceClass.PROMOTION_GRADE_EVIDENCE.value
        ],
        "run_manifest_evidence_class": _aggregate_group_evidence_class(
            grouped["run_manifest"]
        ),
        "capital_profiles_evidence_class": _aggregate_group_evidence_class(
            grouped["capital_profiles"]
        ),
        "engine_promotion_evidence_class": _aggregate_group_evidence_class(
            grouped["engine_promotion"]
        ),
        "pair_promotion_evidence_class": _aggregate_group_evidence_class(
            grouped["pair_promotion"]
        ),
        "strategy_promotion_evidence_class": _aggregate_group_evidence_class(
            grouped["strategy_promotion"]
        ),
        "sample_size_survival_evidence_class": _aggregate_group_evidence_class(
            grouped["sample_size_survival"]
        ),
        "trade_detail_ledger_evidence_class": _aggregate_group_evidence_class(
            grouped["trade_detail_ledger"]
        ),
        "refusal_ledger_evidence_class": _aggregate_group_evidence_class(
            grouped["refusal_ledger"]
        ),
        "loss_analysis_ledger_evidence_class": _aggregate_group_evidence_class(
            grouped["loss_analysis_ledger"]
        ),
        "evidence_audit_blocker_codes": tuple(dict.fromkeys(blocker_codes)),
    }


__all__ = [
    "GovernedAuditEvidenceClass",
    "GovernedAuditEvidenceEntry",
    "GovernedAuditEvidenceIndex",
    "build_governed_audit_evidence_projection",
    "load_governed_audit_evidence_index",
]
