"""Bounded compatibility-registry policy for governed artifact intake."""

from __future__ import annotations

from datetime import date
import re

from backtest_artifact_import.contracts import ArtifactCompatibilityCheckResult
from interface_contracts import (
    ArtifactCompatibilityEntry,
    ArtifactCompatibilityStatus,
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_TRANSFORM_SET_VERSION,
)
from local_replay_runtime.artifact_manifest import ArtifactManifest

_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


DEFAULT_ARTIFACT_COMPATIBILITY_REGISTRY: tuple[ArtifactCompatibilityEntry, ...] = (
    ArtifactCompatibilityEntry(
        artifact_schema_version="1.0.0",
        feature_set_version=CANONICAL_FEATURE_SET_VERSION,
        transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
        status=ArtifactCompatibilityStatus.SUPPORTED,
        activated_on=date(2026, 4, 5),
        migration_note="initial governed semver baseline",
    ),
    ArtifactCompatibilityEntry(
        artifact_schema_version="2.0.0",
        feature_set_version="2.0.0",
        transform_set_version="2.0.0",
        status=ArtifactCompatibilityStatus.SUPPORTED,
        activated_on=date(2026, 4, 5),
        migration_note="fixture compatibility window",
    ),
    ArtifactCompatibilityEntry(
        artifact_schema_version="3.0.0",
        feature_set_version="3.0.0",
        transform_set_version="3.0.0",
        status=ArtifactCompatibilityStatus.SUPPORTED,
        activated_on=date(2026, 4, 5),
        migration_note="fixture compatibility window",
    ),
    ArtifactCompatibilityEntry(
        artifact_schema_version="4.0.0",
        feature_set_version="4.0.0",
        transform_set_version="4.0.0",
        status=ArtifactCompatibilityStatus.SUPPORTED,
        activated_on=date(2026, 4, 5),
        migration_note="fixture compatibility window",
    ),
)


def _parse_semver(version: str) -> tuple[int, int, int] | None:
    match = _SEMVER_RE.fullmatch(version)
    if match is None:
        return None
    return tuple(int(group) for group in match.groups())


def _classify_schema_version(
    version: str,
    *,
    registry: tuple[ArtifactCompatibilityEntry, ...],
) -> str | None:
    parsed = _parse_semver(version)
    if parsed is None:
        return "ARTIFACT_SCHEMA_UNKNOWN"
    known = tuple(
        parsed_entry
        for parsed_entry in (
            _parse_semver(entry.artifact_schema_version)
            for entry in registry
        )
        if parsed_entry is not None
    )
    if version in {entry.artifact_schema_version for entry in registry}:
        return None
    if not any(candidate[0] == parsed[0] for candidate in known):
        return "ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE"
    return "ARTIFACT_SCHEMA_MINOR_UNSUPPORTED"


def _classify_family_version(
    version: str,
    *,
    known_versions: tuple[str, ...],
    unknown_code: str,
    incompatible_code: str,
) -> str | None:
    parsed = _parse_semver(version)
    if parsed is None:
        return unknown_code
    if version in known_versions:
        return None
    known = tuple(value for value in (_parse_semver(item) for item in known_versions) if value is not None)
    if not any(candidate[0] == parsed[0] for candidate in known):
        return incompatible_code
    return unknown_code


def evaluate_artifact_compatibility_policy(
    manifest: ArtifactManifest,
    *,
    registry: tuple[ArtifactCompatibilityEntry, ...] = DEFAULT_ARTIFACT_COMPATIBILITY_REGISTRY,
) -> ArtifactCompatibilityCheckResult:
    """Evaluate exact-version and semver-family compatibility against the VPS registry."""

    reasons: list[str] = []

    schema_reason = _classify_schema_version(
        manifest.artifact_schema_version,
        registry=registry,
    )
    if schema_reason is not None:
        reasons.append(schema_reason)

    feature_reason = _classify_family_version(
        manifest.feature_set_version,
        known_versions=tuple(entry.feature_set_version for entry in registry),
        unknown_code="FEATURE_SET_UNKNOWN",
        incompatible_code="FEATURE_SET_INCOMPATIBLE",
    )
    if feature_reason is not None:
        reasons.append(feature_reason)

    transform_reason = _classify_family_version(
        manifest.transform_set_version,
        known_versions=tuple(entry.transform_set_version for entry in registry),
        unknown_code="TRANSFORM_SET_UNKNOWN",
        incompatible_code="TRANSFORM_SET_INCOMPATIBLE",
    )
    if transform_reason is not None:
        reasons.append(transform_reason)

    matching_entry = next(
        (
            entry
            for entry in registry
            if entry.artifact_schema_version == manifest.artifact_schema_version
            and entry.feature_set_version == manifest.feature_set_version
            and entry.transform_set_version == manifest.transform_set_version
        ),
        None,
    )
    if matching_entry is None:
        if not reasons:
            reasons.append("ARTIFACT_REQUIRES_MIGRATION")
        return ArtifactCompatibilityCheckResult(
            status=ArtifactCompatibilityStatus.REJECTED,
            accepted=False,
            reasons=tuple(reasons),
            matched_entry=None,
        )
    if matching_entry.status != ArtifactCompatibilityStatus.SUPPORTED:
        reasons.append("ARTIFACT_REQUIRES_MIGRATION")
    return ArtifactCompatibilityCheckResult(
        status=matching_entry.status,
        accepted=matching_entry.status == ArtifactCompatibilityStatus.SUPPORTED and not reasons,
        reasons=tuple(reasons),
        matched_entry=matching_entry,
    )


__all__ = [
    "DEFAULT_ARTIFACT_COMPATIBILITY_REGISTRY",
    "evaluate_artifact_compatibility_policy",
]
