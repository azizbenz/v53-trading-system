"""Deterministic HC-4 audit for traded pairs versus AAOIFI screening registry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from .contracts import (
    AaoifiPairScreeningAuditFinding,
    AaoifiPairScreeningAuditReport,
    AaoifiPairScreeningRegistry,
    AaoifiPairScreeningSnapshot,
    ShariaPolicy,
)
from .pair_screening import evaluate_pair_screening


class PairScreeningSnapshotProvider(Protocol):
    @property
    def registry(self) -> AaoifiPairScreeningRegistry:
        ...

    def get_snapshot(self, pair: str) -> AaoifiPairScreeningSnapshot | None:
        ...


def audit_traded_pairs_against_screening(
    *,
    traded_pairs: tuple[str, ...],
    provider: PairScreeningSnapshotProvider,
    policy: ShariaPolicy,
    scanned_at: datetime | None = None,
) -> AaoifiPairScreeningAuditReport:
    findings: list[AaoifiPairScreeningAuditFinding] = []
    normalized_pairs = tuple(dict.fromkeys(pair.strip().upper() for pair in traded_pairs if pair.strip()))
    for pair in normalized_pairs:
        snapshot = provider.get_snapshot(pair)
        if snapshot is None:
            findings.append(
                AaoifiPairScreeningAuditFinding(
                    pair=pair,
                    reason_code="PAIR_SCREENING_MISSING",
                    detail=f"no AAOIFI pair-screening snapshot found for {pair}",
                )
            )
            continue
        result = evaluate_pair_screening(snapshot, policy=policy)
        if not result.passed:
            findings.append(
                AaoifiPairScreeningAuditFinding(
                    pair=pair,
                    reason_code="PAIR_SCREENING_FAILED",
                    detail=result.detail,
                )
            )
    return AaoifiPairScreeningAuditReport(
        scanned_at=scanned_at or datetime.now(timezone.utc),
        registry_version=provider.registry.registry_version,
        screened_pairs=normalized_pairs,
        findings=tuple(findings),
    )


__all__ = ["PairScreeningSnapshotProvider", "audit_traded_pairs_against_screening"]
