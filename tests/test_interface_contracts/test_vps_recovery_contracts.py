from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)


def test_vps_recovery_check_rejects_passed_status_with_reasons() -> None:
    with pytest.raises(ValidationError):
        VpsRecoveryCheck(
            check_id="artifact_registry",
            status=VpsRecoveryCheckStatus.PASSED,
            reasons=("should not be present",),
        )


def test_vps_recovery_readiness_report_rejects_eligible_flag_with_blocked_check() -> None:
    with pytest.raises(ValidationError):
        VpsRecoveryReadinessReport(
            report_id="recovery-1",
            checks=(
                VpsRecoveryCheck(
                    check_id="artifact_registry",
                    status=VpsRecoveryCheckStatus.BLOCKED,
                    reasons=("manifest mismatch",),
                ),
            ),
            eligible_to_trade=True,
            blocking_reasons=("manifest mismatch",),
        )


def test_vps_warmup_run_summary_requires_matching_eligible_state() -> None:
    report = VpsRecoveryReadinessReport(
        report_id="recovery-2",
        checks=(
            VpsRecoveryCheck(
                check_id="artifact_registry",
                status=VpsRecoveryCheckStatus.PASSED,
            ),
        ),
        eligible_to_trade=True,
    )

    with pytest.raises(ValidationError):
        VpsWarmupRunSummary(
            run_id="warmup-2",
            final_state=VpsWarmupState.WARMUP_SHADOW_ONLY,
            phase_sequence=(VpsWarmupState.COLD_START, VpsWarmupState.WARMUP_SHADOW_ONLY),
            report=report,
            eligible_to_trade=True,
        )
