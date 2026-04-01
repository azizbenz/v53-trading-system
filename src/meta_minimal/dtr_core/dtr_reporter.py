"""
Build-9 / dtr_core / dtr_reporter
Expose DTRs for UI, monitoring, and audits.

DTRCoverage = N_dtr / N_opportunities
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class DTRSummary(BaseModel, frozen=True):
    """Summary of DTR records for reporting."""

    total_records: int = 0
    by_state: dict[str, int] = Field(default_factory=dict)
    by_engine: dict[str, int] = Field(default_factory=dict)
    by_pair: dict[str, int] = Field(default_factory=dict)
    dtr_coverage: float = 0.0  # N_dtr / N_opportunities
    synthetic_input_count: int = 0
    local_replay_input_count: int = 0
    incomplete_path_count: int = 0


def build_dtr_summary(
    records: tuple[DTRRecord, ...],
    total_opportunities: int = 0,
) -> DTRSummary:
    """Build a summary of DTR records for audit/monitoring.

    Args:
        records: All DTR records to summarize.
        total_opportunities: Total significant opportunities (for coverage calculation).
    """
    by_state: dict[str, int] = {}
    by_engine: dict[str, int] = {}
    by_pair: dict[str, int] = {}
    synthetic_input_count = 0
    local_replay_input_count = 0
    incomplete_path_count = 0

    for r in records:
        by_state[r.decision_state] = by_state.get(r.decision_state, 0) + 1
        by_engine[r.engine_id] = by_engine.get(r.engine_id, 0) + 1
        by_pair[r.pair] = by_pair.get(r.pair, 0) + 1
        if r.input_source == "synthetic":
            synthetic_input_count += 1
        if r.input_source == "local_replay":
            local_replay_input_count += 1
        if not r.path_complete:
            incomplete_path_count += 1

    coverage = len(records) / total_opportunities if total_opportunities > 0 else 0.0

    return DTRSummary(
        total_records=len(records),
        by_state=by_state,
        by_engine=by_engine,
        by_pair=by_pair,
        dtr_coverage=coverage,
        synthetic_input_count=synthetic_input_count,
        local_replay_input_count=local_replay_input_count,
        incomplete_path_count=incomplete_path_count,
    )
