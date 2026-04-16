"""Minimal real Build-11 Shadow orchestration.

HARD STATEMENT §0.6: 30 consecutive shadow days required before promotion.
"""

from __future__ import annotations

from pathlib import Path

from protocols.shadow_runtime_inputs import (
    build_shadow_input_from_payloads,
    build_shadow_runtime_evidence,
)
from protocols.shadow_runtime_judgments import (
    compare_shadow_candidate,
    derive_shadow_engine_judgment_summary,
)
from protocols.shadow_runtime_portfolio import derive_shadow_portfolio_judgment
from protocols.shadow_runtime_validation import run_shadow_validation


def check_shadow_30j_gate(
    state_dir: Path,
    profile: str,
) -> tuple[bool, dict]:
    """HARD STATEMENT §0.6: check if 30 consecutive shadow days are met.

    Args:
        state_dir: Directory containing persisted shadow counter state.
        profile: "light" or "complete".

    Returns:
        (gate_passed, report_dict)
    """
    from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile

    shadow_profile = ShadowProfile(profile)
    counter = ShadowDayCounter(state_dir=state_dir, profile=shadow_profile)
    report = counter.generate_report()
    gate_passed = counter.is_promotion_ready() and bool(
        report.get("shadow_report_ready", False)
    )
    return gate_passed, report


__all__ = [
    "build_shadow_runtime_evidence",
    "build_shadow_input_from_payloads",
    "derive_shadow_portfolio_judgment",
    "derive_shadow_engine_judgment_summary",
    "compare_shadow_candidate",
    "run_shadow_validation",
    "check_shadow_30j_gate",
]
