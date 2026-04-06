"""
HARD STATEMENT §0.6 - Promotion Gate Checks.

Centralizes all temporal promotion prerequisites:
1. COMPLETE Shadow -> 30 consecutive days -> COMPLETE micro-live eligible.
2. COMPLETE Shadow -> 30 consecutive days -> COMPLETE live eligible.
3. LIGHT Shadow compatibility gates remain available only for legacy callers/tests.

Non-negotiable. No override. No bypass.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from protocols.shadow_runtime import check_shadow_30j_gate


class PromotionGateResult(BaseModel, frozen=True):
    """Result of a promotion gate check."""

    gate_name: str
    passed: bool
    profile: str
    consecutive_days: int
    required_days: int = 30
    remaining_days: int
    total_resets: int = 0
    message: str = ""


def _check_shadow_gate(
    state_dir: Path,
    *,
    profile: str,
    gate_name: str,
) -> PromotionGateResult:
    passed, report = check_shadow_30j_gate(state_dir, profile=profile)
    consecutive_days = int(report.get("consecutive_days", 0))
    remaining_days = int(report.get("remaining_days", 30))
    total_resets = int(report.get("total_resets", 0))
    report_ready = bool(report.get("shadow_report_ready", False))
    missing_sections = tuple(report.get("missing_sections", ()))
    if passed:
        message = "PASSED"
    elif consecutive_days < 30:
        message = f"BLOCKED: {remaining_days} days remaining"
    elif not report_ready:
        detail = ", ".join(missing_sections) if missing_sections else "shadow report incomplete"
        message = f"BLOCKED: shadow report incomplete ({detail})"
    else:
        message = "BLOCKED"
    return PromotionGateResult(
        gate_name=gate_name,
        passed=passed,
        profile=profile,
        consecutive_days=consecutive_days,
        remaining_days=remaining_days,
        total_resets=total_resets,
        message=message,
    )


def check_light_to_micro_live(state_dir: Path) -> PromotionGateResult:
    """Compatibility helper for legacy LIGHT callers/tests."""
    return _check_shadow_gate(
        state_dir,
        profile="light",
        gate_name="light_shadow_30j",
    )


def check_complete_to_micro_live(state_dir: Path) -> PromotionGateResult:
    """HARD: COMPLETE must have 30 consecutive shadow days before Micro-live."""
    return _check_shadow_gate(
        state_dir,
        profile="complete",
        gate_name="complete_shadow_30j_for_micro_live",
    )


def check_complete_to_live(state_dir: Path) -> PromotionGateResult:
    """HARD: COMPLETE must have 30 consecutive shadow days before going live."""
    return _check_shadow_gate(
        state_dir,
        profile="complete",
        gate_name="complete_shadow_30j",
    )


def check_all_gates(state_dir: Path) -> tuple[PromotionGateResult, ...]:
    """Compatibility surface returning the historical dual-profile gate set."""
    return (
        check_light_to_micro_live(state_dir),
        check_complete_to_live(state_dir),
    )

