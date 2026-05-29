"""Backbone/local-replay surface resolution contracts.

The adapter is intentionally decision-neutral: it chooses and labels the source
of a surface payload, but it does not alter engine output, thresholds, trade
selection, or replay records. It exists so B2 can migrate one surface at a time
without keeping silent local-replay truth.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field


CANONICAL_BACKBONE_USED = "CANONICAL_BACKBONE_USED"
LOCAL_REPLAY_FALLBACK_USED = "LOCAL_REPLAY_FALLBACK_USED"
BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT = "BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT"
BACKBONE_CONTRACT_INCOMPLETE = "BACKBONE_CONTRACT_INCOMPLETE"
BACKBONE_RESULT_MISSING = "BACKBONE_RESULT_MISSING"
LOCAL_REPLAY_RESULT_MISSING = "LOCAL_REPLAY_RESULT_MISSING"
NO_SURFACE_RESULT_AVAILABLE = "NO_SURFACE_RESULT_AVAILABLE"


class BackboneParityPolicy(BaseModel, frozen=True):
    """Comparison policy for one surface during migration."""

    compared_fields: tuple[str, ...] = ()
    numeric_tolerance: float = Field(default=1e-9, ge=0.0)
    require_contract_ready: bool = True


class BackboneSurfaceResolution(BaseModel, frozen=True):
    """Source-of-truth status for one migrated surface."""

    surface: str
    status: str
    selected_source: str
    canonical_source: str = "canonical_backbone"
    fallback_source: str = "local_replay_runtime"
    promotion_allowed: bool = False
    reason_codes: tuple[str, ...] = ()
    conflict_fields: tuple[str, ...] = ()
    canonical_payload: dict[str, Any] = Field(default_factory=dict)
    fallback_payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def used_canonical(self) -> bool:
        return self.status == CANONICAL_BACKBONE_USED

    @property
    def used_fallback(self) -> bool:
        return self.status == LOCAL_REPLAY_FALLBACK_USED

    @property
    def has_parity_conflict(self) -> bool:
        return self.status == BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT


def _is_payload_present(payload: dict[str, Any] | None) -> bool:
    return isinstance(payload, dict) and bool(payload)


def _values_match(left: Any, right: Any, *, numeric_tolerance: float) -> bool:
    if left is None and right is None:
        return True
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not math.isfinite(float(left)) or not math.isfinite(float(right)):
            return False
        return abs(float(left) - float(right)) <= numeric_tolerance
    return left == right


def _conflict_fields(
    canonical_payload: dict[str, Any],
    fallback_payload: dict[str, Any],
    *,
    compared_fields: tuple[str, ...],
    numeric_tolerance: float,
) -> tuple[str, ...]:
    conflicts: list[str] = []
    for field in compared_fields:
        if field not in canonical_payload or field not in fallback_payload:
            conflicts.append(field)
            continue
        if not _values_match(
            canonical_payload.get(field),
            fallback_payload.get(field),
            numeric_tolerance=numeric_tolerance,
        ):
            conflicts.append(field)
    return tuple(conflicts)


def resolve_backbone_surface(
    *,
    surface: str,
    canonical_payload: dict[str, Any] | None,
    local_replay_payload: dict[str, Any] | None,
    contract_ready: bool,
    policy: BackboneParityPolicy | None = None,
    canonical_source: str = "canonical_backbone",
    fallback_source: str = "local_replay_runtime",
    fallback_reason: str = "",
) -> BackboneSurfaceResolution:
    """Resolve one surface source with explicit fallback and conflict states."""

    resolved_policy = policy or BackboneParityPolicy()
    canonical = dict(canonical_payload or {})
    fallback = dict(local_replay_payload or {})
    has_canonical = _is_payload_present(canonical_payload)
    has_fallback = _is_payload_present(local_replay_payload)
    reason_codes: list[str] = []

    if not contract_ready and resolved_policy.require_contract_ready:
        reason_codes.append(BACKBONE_CONTRACT_INCOMPLETE)
        if fallback_reason:
            reason_codes.append(fallback_reason)
        if has_fallback:
            reason_codes.append(LOCAL_REPLAY_FALLBACK_USED)
            return BackboneSurfaceResolution(
                surface=surface,
                status=LOCAL_REPLAY_FALLBACK_USED,
                selected_source=fallback_source,
                canonical_source=canonical_source,
                fallback_source=fallback_source,
                promotion_allowed=False,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                canonical_payload=canonical,
                fallback_payload=fallback,
            )
        reason_codes.append(LOCAL_REPLAY_RESULT_MISSING)
        return BackboneSurfaceResolution(
            surface=surface,
            status=NO_SURFACE_RESULT_AVAILABLE,
            selected_source="none",
            canonical_source=canonical_source,
            fallback_source=fallback_source,
            promotion_allowed=False,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            canonical_payload=canonical,
            fallback_payload=fallback,
        )

    if has_canonical:
        if has_fallback and resolved_policy.compared_fields:
            conflicts = _conflict_fields(
                canonical,
                fallback,
                compared_fields=resolved_policy.compared_fields,
                numeric_tolerance=resolved_policy.numeric_tolerance,
            )
            if conflicts:
                return BackboneSurfaceResolution(
                    surface=surface,
                    status=BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT,
                    selected_source="none",
                    canonical_source=canonical_source,
                    fallback_source=fallback_source,
                    promotion_allowed=False,
                    reason_codes=(BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT,),
                    conflict_fields=conflicts,
                    canonical_payload=canonical,
                    fallback_payload=fallback,
                )
        return BackboneSurfaceResolution(
            surface=surface,
            status=CANONICAL_BACKBONE_USED,
            selected_source=canonical_source,
            canonical_source=canonical_source,
            fallback_source=fallback_source,
            promotion_allowed=True,
            reason_codes=(CANONICAL_BACKBONE_USED,),
            canonical_payload=canonical,
            fallback_payload=fallback,
        )

    reason_codes.append(BACKBONE_RESULT_MISSING)
    if fallback_reason:
        reason_codes.append(fallback_reason)
    if has_fallback:
        reason_codes.append(LOCAL_REPLAY_FALLBACK_USED)
        return BackboneSurfaceResolution(
            surface=surface,
            status=LOCAL_REPLAY_FALLBACK_USED,
            selected_source=fallback_source,
            canonical_source=canonical_source,
            fallback_source=fallback_source,
            promotion_allowed=False,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            canonical_payload=canonical,
            fallback_payload=fallback,
        )

    reason_codes.append(LOCAL_REPLAY_RESULT_MISSING)
    return BackboneSurfaceResolution(
        surface=surface,
        status=NO_SURFACE_RESULT_AVAILABLE,
        selected_source="none",
        canonical_source=canonical_source,
        fallback_source=fallback_source,
        promotion_allowed=False,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        canonical_payload=canonical,
        fallback_payload=fallback,
    )


def attach_backbone_surface_status(
    payload: dict[str, Any],
    resolution: BackboneSurfaceResolution,
) -> dict[str, Any]:
    """Return a copy of payload with a structured backbone status block."""

    updated = dict(payload)
    updated["backbone_surface_status"] = {
        "surface": resolution.surface,
        "status": resolution.status,
        "selected_source": resolution.selected_source,
        "promotion_allowed": resolution.promotion_allowed,
        "reason_codes": resolution.reason_codes,
        "conflict_fields": resolution.conflict_fields,
    }
    return updated


def build_backbone_parity_surface_report(
    resolutions: tuple[BackboneSurfaceResolution, ...],
) -> dict[str, Any]:
    """Build a compact report across migrated surfaces."""

    status_counts: dict[str, int] = {}
    promotion_allowed = True
    for resolution in resolutions:
        status_counts[resolution.status] = status_counts.get(resolution.status, 0) + 1
        promotion_allowed = promotion_allowed and resolution.promotion_allowed
    return {
        "schema_version": "v53.backbone_parity_surface_report.v1",
        "surface_count": len(resolutions),
        "status_counts": status_counts,
        "promotion_allowed": promotion_allowed if resolutions else False,
        "rows": tuple(row.model_dump(mode="json") for row in resolutions),
    }


__all__ = [
    "BACKBONE_CONTRACT_INCOMPLETE",
    "BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT",
    "BACKBONE_RESULT_MISSING",
    "CANONICAL_BACKBONE_USED",
    "LOCAL_REPLAY_FALLBACK_USED",
    "LOCAL_REPLAY_RESULT_MISSING",
    "NO_SURFACE_RESULT_AVAILABLE",
    "BackboneParityPolicy",
    "BackboneSurfaceResolution",
    "attach_backbone_surface_status",
    "build_backbone_parity_surface_report",
    "resolve_backbone_surface",
]
