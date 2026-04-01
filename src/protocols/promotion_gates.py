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

from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile


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
    counter = ShadowDayCounter(state_dir=state_dir, profile=ShadowProfile.LIGHT)
    status = counter.get_status()
    passed = counter.is_promotion_ready()
    return PromotionGateResult(
        gate_name="light_shadow_30j",
        passed=passed,
        profile="light",
        consecutive_days=status.consecutive_days,
        remaining_days=status.remaining_days,
        total_resets=status.resets,
        message="PASSED" if passed else f"BLOCKED: {status.remaining_days} days remaining",
    )


def check_complete_to_live(state_dir: Path) -> PromotionGateResult:
    """HARD: Complete must have 30 consecutive shadow days before going live."""
    counter = ShadowDayCounter(state_dir=state_dir, profile=ShadowProfile.COMPLETE)
    status = counter.get_status()
    passed = counter.is_promotion_ready()
    return PromotionGateResult(
        gate_name="complete_shadow_30j",
        passed=passed,
        profile="complete",
        consecutive_days=status.consecutive_days,
        remaining_days=status.remaining_days,
        total_resets=status.resets,
        message="PASSED" if passed else f"BLOCKED: {status.remaining_days} days remaining",
    )


def check_all_gates(state_dir: Path) -> tuple[PromotionGateResult, ...]:
    """Check all HARD STATEMENT promotion gates."""
    return (
        check_light_to_micro_live(state_dir),
        check_complete_to_live(state_dir),
    )
