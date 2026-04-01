"""
HARD STATEMENT §0.6 — Promotion Gate Checks.

Centralizes all temporal promotion prerequisites:
1. Light Shadow → 30 consecutive days → Light micro-live/live eligible.
2. Complete Shadow → 30 consecutive days → Complete live eligible.

Non-negotiable. No override. No bypass.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

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


def check_light_to_micro_live(state_dir: Path) -> PromotionGateResult:
    """HARD: Light must have 30 consecutive shadow days before micro-live."""
    passed, report = check_shadow_30j_gate(state_dir, profile="light")
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
        gate_name="light_shadow_30j",
        passed=passed,
        profile="light",
        consecutive_days=consecutive_days,
        remaining_days=remaining_days,
        total_resets=total_resets,
        message=message,
    )


def check_complete_to_live(state_dir: Path) -> PromotionGateResult:
    """HARD: Complete must have 30 consecutive shadow days before going live."""
    passed, report = check_shadow_30j_gate(state_dir, profile="complete")
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
        gate_name="complete_shadow_30j",
        passed=passed,
        profile="complete",
        consecutive_days=consecutive_days,
        remaining_days=remaining_days,
        total_resets=total_resets,
        message=message,
    )


def check_all_gates(state_dir: Path) -> tuple[PromotionGateResult, ...]:
    """Check all HARD STATEMENT promotion gates."""
    return (
        check_light_to_micro_live(state_dir),
        check_complete_to_live(state_dir),
    )
