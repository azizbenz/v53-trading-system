from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from risk_backbone.emergency_kill_switch.circuit_breaker import (
    EmergencyCircuitBreaker,
    KillSwitchState,
)
from risk_backbone.loss_budgeter import (
    DailyPnlBreaker,
    DailyPnlBreakerCalibrationConfig,
    DailyPnlBreakerThresholds,
    DailyPnlBreakerVerdict,
    resolve_daily_pnl_breaker_thresholds,
)


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-daily-pnl-breaker-calibration") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def breaker_tmpdir() -> Path:
    root = Path("build/pytest-daily-pnl-breaker-state") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write_signed_yaml(path: Path, *, threshold_id: str, value: int | float) -> None:
    payload = {
        "artifact_id": f"{threshold_id.lower()}-artifact",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-12T09:15:00Z",
        "thresholds": (
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/risk_backbone/loss_budgeter/daily_pnl_breaker.py",
                "calibration_artifact": "config/calibration/v1/risk_breakers.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-12T10:00:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_daily_pnl_breaker_thresholds_loads_thr_r01(calibration_tmpdir: Path):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "r01.yml", threshold_id="THR-R01", value=0.018)

    thresholds = resolve_daily_pnl_breaker_thresholds(
        DailyPnlBreakerCalibrationConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
        )
    )

    assert thresholds.intraday_drawdown_breach_pct == pytest.approx(0.018)


def test_resolve_daily_pnl_breaker_thresholds_rejects_relaxed_value_above_hard_cap(
    calibration_tmpdir: Path,
):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "r01.yml", threshold_id="THR-R01", value=0.03)

    with pytest.raises(CalibrationArtifactValidationError):
        resolve_daily_pnl_breaker_thresholds(
            DailyPnlBreakerCalibrationConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
            )
        )


def test_daily_pnl_breaker_accepts_below_threshold(breaker_tmpdir: Path):
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir)

    assessment = breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_900.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_000.0,
    )

    assert assessment.verdict == DailyPnlBreakerVerdict.ACCEPTED
    assert assessment.should_force_shadow is False
    assert breaker.state.shadow_locked_session_date == ""


def test_daily_pnl_breaker_records_same_day_shadow_lock(breaker_tmpdir: Path):
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir)

    assessment = breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_700.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_001.0,
    )

    assert assessment.verdict == DailyPnlBreakerVerdict.SHADOW_RECOMMENDED
    assert assessment.should_force_shadow is True
    assert breaker.state.shadow_locked_session_date == "2026-04-12"


def test_daily_pnl_breaker_keeps_same_day_lock_even_after_equity_recovers(
    breaker_tmpdir: Path,
):
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir)
    breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_700.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_001.0,
    )

    recovered = breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_980.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_100.0,
    )

    assert recovered.verdict == DailyPnlBreakerVerdict.SHADOW_LOCKED
    assert recovered.should_force_shadow is True
    assert "no automatic same-day reactivation" in recovered.detail


def test_daily_pnl_breaker_clears_lock_on_next_session_date(breaker_tmpdir: Path):
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir)
    breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_700.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_001.0,
    )

    next_day = breaker.evaluate(
        session_date="2026-04-13",
        current_equity=10_050.0,
        session_peak_equity=10_050.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_086_400.0,
    )

    assert next_day.verdict == DailyPnlBreakerVerdict.ACCEPTED
    assert next_day.should_force_shadow is False
    assert breaker.state.shadow_locked_session_date == ""


def test_daily_pnl_breaker_can_trip_circuit_breaker_explicitly(breaker_tmpdir: Path):
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir / "daily")
    circuit_breaker = EmergencyCircuitBreaker(state_dir=breaker_tmpdir / "kill")

    assessment = breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_700.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        circuit_breaker=circuit_breaker,
        trip_circuit_breaker_on_breach=True,
        now_ts=1_700_000_001.0,
    )

    assert assessment.circuit_breaker_tripped is True
    assert circuit_breaker.current_state == KillSwitchState.TRIPPED


def test_daily_pnl_breaker_corrupted_state_file_forces_shadow_until_reset(
    breaker_tmpdir: Path,
):
    state_path = breaker_tmpdir / "daily_pnl_breaker_state.json"
    state_path.write_text("not valid json", encoding="utf-8")
    breaker = DailyPnlBreaker(state_dir=breaker_tmpdir)

    assessment = breaker.evaluate(
        session_date="2026-04-12",
        current_equity=9_950.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_002.0,
    )

    assert assessment.verdict == DailyPnlBreakerVerdict.SHADOW_LOCKED
    assert assessment.should_force_shadow is True
    assert "STATE_CORRUPTED" in assessment.reason_codes[0]

    breaker.reset(operator_detail="operator reviewed")
    accepted = breaker.evaluate(
        session_date="2026-04-12",
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        thresholds=DailyPnlBreakerThresholds(intraday_drawdown_breach_pct=0.02),
        now_ts=1_700_000_100.0,
    )
    assert accepted.verdict == DailyPnlBreakerVerdict.ACCEPTED
