"""Governed audit-evidence index builders for Strategy Ladder and related replay outputs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from interface_contracts import (
    GovernedAuditEvidenceClass,
    GovernedAuditEvidenceEntry,
    GovernedAuditEvidenceIndex,
)

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


def build_governed_audit_evidence_entry(
    *,
    rail_id: str,
    artifact_kind: str,
    artifact_ref: str,
    audited_historical: bool = False,
    promotion_grade: bool = False,
) -> GovernedAuditEvidenceEntry:
    """Classify one evidence ref without over-reading scratch outputs as audited proof."""

    resolved = Path(artifact_ref).resolve()
    reasons: list[str] = []
    if not resolved.exists():
        reasons.append("EVIDENCE_PATH_MISSING")
    path_parts = {part.casefold() for part in resolved.parts}
    if ".test_tmp" in path_parts:
        evidence_class = GovernedAuditEvidenceClass.SCRATCH_ONLY
        reasons.append("EVIDENCE_UNDER_TEST_TMP")
    elif promotion_grade and audited_historical:
        evidence_class = GovernedAuditEvidenceClass.PROMOTION_GRADE_EVIDENCE
    elif audited_historical:
        evidence_class = GovernedAuditEvidenceClass.AUDITED_HISTORICAL_EVIDENCE
    else:
        evidence_class = GovernedAuditEvidenceClass.SCRATCH_ONLY
        reasons.append("EVIDENCE_AUDIT_NOT_CONFIRMED")
    return GovernedAuditEvidenceEntry(
        rail_id=rail_id,
        artifact_kind=artifact_kind,
        artifact_ref=str(resolved),
        evidence_class=evidence_class,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def build_governed_audit_evidence_index(
    *,
    run_id: str | None,
    source_root: str | Path | None,
    entries: tuple[GovernedAuditEvidenceEntry, ...],
    created_at: datetime | None = None,
) -> GovernedAuditEvidenceIndex:
    """Materialize the canonical evidence index with deterministic self-hash."""

    return GovernedAuditEvidenceIndex.create(
        run_id=run_id,
        source_root=None if source_root is None else str(Path(source_root).resolve()),
        entries=entries,
        created_at=created_at or datetime.now(tz=UTC),
    )


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
    "build_governed_audit_evidence_entry",
    "build_governed_audit_evidence_index",
    "build_governed_audit_evidence_projection",
    "load_governed_audit_evidence_index",
]
