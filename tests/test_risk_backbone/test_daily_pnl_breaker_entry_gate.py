from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from risk_backbone import (
    RiskDailyPnlPrecheckInput,
    build_daily_pnl_breaker_entry_gate,
)
from risk_backbone.loss_budgeter import DailyPnlBreaker, DailyPnlBreakerThresholds


@pytest.fixture
def breaker_tmpdir() -> Path:
    root = Path("build/pytest-daily-pnl-breaker-entry-gate") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _hook_input(*, current_equity: float, session_peak_equity: float) -> RiskDailyPnlPrecheckInput:
    return RiskDailyPnlPrecheckInput(
        context_id="risk-runtime:eng-a:ETHUSDT",
        pair="ETHUSDT",
        engine_id="eng-a",
        size=40.0,
        planned_loss=5.0,
        session_date="2026-04-12",
        current_equity=current_equity,
        session_peak_equity=session_peak_equity,
    )


def test_daily_pnl_breaker_entry_gate_accepts_when_drawdown_is_below_threshold(
    breaker_tmpdir: Path,
):
    hook = build_daily_pnl_breaker_entry_gate(
        DailyPnlBreaker(state_dir=breaker_tmpdir),
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
    )

    outcome = hook(_hook_input(current_equity=9_900.0, session_peak_equity=10_000.0))

    assert outcome.accepted is True
    assert outcome.should_force_shadow is False
    assert outcome.verdict == "accepted"


def test_daily_pnl_breaker_entry_gate_blocks_and_keeps_same_day_shadow_lock(
    breaker_tmpdir: Path,
):
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir)
    hook = build_daily_pnl_breaker_entry_gate(
        breaker,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
    )

    first = hook(_hook_input(current_equity=9_700.0, session_peak_equity=10_000.0))
    second = hook(_hook_input(current_equity=9_980.0, session_peak_equity=10_000.0))

    assert first.accepted is False
    assert first.should_force_shadow is True
    assert first.reason_codes == ("RISK_DAILY_BREAKER_BREACHED",)
    assert second.accepted is False
    assert second.verdict == "shadow_locked"
    assert second.reason_codes == ("RISK_DAILY_BREAKER_ALREADY_LOCKED",)
    assert breaker.state.shadow_locked_session_date == "2026-04-12"
