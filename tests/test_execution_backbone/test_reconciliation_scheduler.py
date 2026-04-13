from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from execution_backbone.execution_runtime import RuntimeReconciliationResult
from execution_backbone.reconciliation_layer.divergence_classifier import (
    DivergenceClassification,
    DivergenceSeverity,
)
from execution_backbone.reconciliation_layer.fill_reconciler import FillReconciliationResult
from execution_backbone.reconciliation_layer.order_reconciler import OrderReconciliationResult
from execution_backbone.reconciliation_layer.position_reconciler import (
    PositionReconciliationResult,
)
from execution_backbone.reconciliation_layer.recovery_trigger import (
    RecoveryAction,
    RecoveryDecision,
)
from execution_backbone.reconciliation_layer.scheduler import (
    ReconciliationScheduler,
    ReconciliationSchedulerCalibrationConfig,
    resolve_reconciliation_scheduler_thresholds,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import (
    EmergencyCircuitBreaker,
    KillSwitchState,
)


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-reconciliation-scheduler-calibration") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def breaker_tmpdir() -> Path:
    root = Path("build/pytest-reconciliation-scheduler-breaker") / uuid4().hex
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
        "generated_at": "2026-04-12T12:00:00Z",
        "thresholds": (
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/execution_backbone/reconciliation_layer/scheduler.py",
                "calibration_artifact": "config/calibration/v1/infra.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-12T12:05:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _runtime_result(
    *,
    severity: DivergenceSeverity,
    action: RecoveryAction,
    total_divergences: int,
) -> RuntimeReconciliationResult:
    return RuntimeReconciliationResult(
        order_result=OrderReconciliationResult(
            aligned=total_divergences == 0,
            local_open_count=0,
            remote_open_count=0,
            order_diff=0,
        ),
        fill_result=FillReconciliationResult(
            policy_id="fill_reconciliation.tolerance.v1",
            aligned=total_divergences == 0,
            total_compared=0,
        ),
        position_result=PositionReconciliationResult(
            policy_id="position_reconciliation.tolerance.v1",
            aligned=total_divergences == 0,
            total_assets_compared=0,
        ),
        divergence_summary=DivergenceClassification(
            max_severity=severity,
            is_blocking=severity in {DivergenceSeverity.BLOCKING, DivergenceSeverity.CRITICAL},
            is_critical=severity == DivergenceSeverity.CRITICAL,
            total_divergences=total_divergences,
        ),
        recovery_decision=RecoveryDecision(
            action=action,
            reason=f"{action.value}:{severity.value}",
            severity=severity,
        ),
    )


class _FakeExecutor:
    def __init__(self, *results: RuntimeReconciliationResult) -> None:
        self._results = list(results)
        self.calls: list[float] = []

    def reconcile(self, now: float) -> RuntimeReconciliationResult:
        self.calls.append(now)
        if not self._results:
            raise AssertionError("unexpected reconcile call")
        return self._results.pop(0)


def test_resolve_reconciliation_scheduler_thresholds_loads_thr_i04(calibration_tmpdir: Path):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "infra.yml", threshold_id="THR-I04", value=1800)

    thresholds = resolve_reconciliation_scheduler_thresholds(
        ReconciliationSchedulerCalibrationConfig(
            calibration_root=str(calibration_tmpdir),
            calibration_version="v1",
        )
    )

    assert thresholds.periodic_interval_s == pytest.approx(1800.0)


def test_resolve_reconciliation_scheduler_thresholds_rejects_below_minimum(
    calibration_tmpdir: Path,
):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "infra.yml", threshold_id="THR-I04", value=30)

    with pytest.raises(CalibrationArtifactValidationError):
        resolve_reconciliation_scheduler_thresholds(
            ReconciliationSchedulerCalibrationConfig(
                calibration_root=str(calibration_tmpdir),
                calibration_version="v1",
            )
        )


def test_boot_reconcile_blocks_and_trips_circuit_breaker_on_unresolved_divergence(
    breaker_tmpdir: Path,
):
    scheduler = ReconciliationScheduler()
    executor = _FakeExecutor(
        _runtime_result(
            severity=DivergenceSeverity.BLOCKING,
            action=RecoveryAction.HARD_RESYNC,
            total_divergences=2,
        )
    )
    circuit_breaker = EmergencyCircuitBreaker(state_dir=breaker_tmpdir)

    run = scheduler.boot_reconcile(executor, now=1_700_000_000.0, circuit_breaker=circuit_breaker)

    assert run.executed is True
    assert run.trading_blocked is True
    assert run.circuit_breaker_tripped is True
    assert run.state.boot_completed is True
    assert run.state.boot_blocked_trading is True
    assert circuit_breaker.current_state == KillSwitchState.TRIPPED


def test_boot_reconcile_schedules_next_due_when_aligned():
    scheduler = ReconciliationScheduler()
    executor = _FakeExecutor(
        _runtime_result(
            severity=DivergenceSeverity.INFO,
            action=RecoveryAction.NONE,
            total_divergences=0,
        )
    )

    run = scheduler.boot_reconcile(executor, now=1_700_000_000.0)

    assert run.executed is True
    assert run.trading_blocked is False
    assert run.state.next_due_ts == pytest.approx(1_700_003_600.0)


def test_run_periodic_if_due_skips_when_interval_not_reached():
    scheduler = ReconciliationScheduler()
    executor = _FakeExecutor(
        _runtime_result(
            severity=DivergenceSeverity.INFO,
            action=RecoveryAction.NONE,
            total_divergences=0,
        )
    )
    scheduler.boot_reconcile(executor, now=1_700_000_000.0)

    skipped = scheduler.run_periodic_if_due(executor, now=1_700_000_100.0)

    assert skipped.executed is False
    assert skipped.detail == "periodic reconciliation not due yet"


def test_run_periodic_if_due_trips_circuit_breaker_on_critical_divergence(
    breaker_tmpdir: Path,
):
    scheduler = ReconciliationScheduler()
    executor = _FakeExecutor(
        _runtime_result(
            severity=DivergenceSeverity.INFO,
            action=RecoveryAction.NONE,
            total_divergences=0,
        ),
        _runtime_result(
            severity=DivergenceSeverity.CRITICAL,
            action=RecoveryAction.HALT_TRADING,
            total_divergences=6,
        ),
    )
    circuit_breaker = EmergencyCircuitBreaker(state_dir=breaker_tmpdir)
    scheduler.boot_reconcile(executor, now=1_700_000_000.0)

    run = scheduler.run_periodic_if_due(
        executor,
        now=1_700_003_601.0,
        circuit_breaker=circuit_breaker,
    )

    assert run.executed is True
    assert run.trading_blocked is True
    assert run.circuit_breaker_tripped is True
    assert run.state.last_run_trigger.value == "periodic"
    assert circuit_breaker.current_state == KillSwitchState.TRIPPED
