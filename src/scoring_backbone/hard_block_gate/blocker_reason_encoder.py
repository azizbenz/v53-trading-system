"""
Build-5 / hard_block_gate / blocker_reason_encoder
Encode block reasons in a stable, audit-able format.
"""

from __future__ import annotations

from pydantic import BaseModel

from scoring_backbone.hard_block_gate.blocker_registry import BlockerID


class EncodedBlockReason(BaseModel, frozen=True):
    """Stable encoded block reason."""

    code: str
    blocker_id: BlockerID
    human_reason: str
    source_subsystem: str = ""


def encode_reasons(
    triggered_blockers: tuple[tuple[BlockerID, str], ...],
) -> tuple[EncodedBlockReason, ...]:
    """Encode triggered blockers into stable reason codes."""
    encoded: list[EncodedBlockReason] = []

    subsystem_map = {
        BlockerID.STALE_HARD: "data_backbone",
        BlockerID.PAIR_SUSPENDED: "data_backbone",
        BlockerID.RISK_BUDGET_EXCEEDED: "risk_backbone",
        BlockerID.RECONCILIATION_CRITICAL: "execution_backbone",
        BlockerID.INFRA_DOWN: "infrastructure",
    }

    for blocker_id, reason in triggered_blockers:
        encoded.append(EncodedBlockReason(
            code=f"HB_{blocker_id.value.upper()}",
            blocker_id=blocker_id,
            human_reason=reason,
            source_subsystem=subsystem_map.get(blocker_id, "unknown"),
        ))

    return tuple(encoded)
