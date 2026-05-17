"""Phase 2.5 adapter - actionable warmup blocker explanations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths, WarmupSummary


class WarmupExplainerCheck(BaseModel, frozen=True):
    check_id: str = Field(..., min_length=1)
    status: str = "unknown"
    reason: str = ""
    source_file: str | None = None
    required_action: str = ""
    suggested_command: str = ""


class WarmupExplainerSnapshot(OperationalSourceSnapshot):
    final_state: str = "unknown"
    eligible_to_trade: bool = False
    blocking_reasons: tuple[str, ...] = ()
    readiness_status: str = "unknown"
    required_checks_passed: bool = False
    review_only_checks: tuple[str, ...] = ()
    checks: tuple[WarmupExplainerCheck, ...] = ()


_REQUIRED_CHECK_IDS = {
    "bootstrap_reconciliation",
    "remote_account_state",
    "time_sync",
    "market_data_capture",
    "binance_credentials",
}
_READY_FINAL_STATES = {"ready", "passed", "warmup_ready", "eligible_to_trade"}


def _required_checks_passed(warmup: WarmupSummary) -> bool:
    statuses = {check.check_id: check.status for check in warmup.checks}
    return all(statuses.get(check_id) == "passed" for check_id in _REQUIRED_CHECK_IDS)


def _readiness_status(warmup: WarmupSummary) -> tuple[str, bool, tuple[str, ...]]:
    required_passed = _required_checks_passed(warmup)
    review_only_checks = tuple(
        check.check_id for check in warmup.checks if check.status == "review_only"
    )
    ready_state = warmup.final_state in _READY_FINAL_STATES
    if (
        warmup.eligible_to_trade
        and ready_state
        and not warmup.blocking_reasons
        and required_passed
        and not review_only_checks
    ):
        return "passed", required_passed, review_only_checks
    if review_only_checks and required_passed and not warmup.blocking_reasons:
        return "review_only", required_passed, review_only_checks
    return "blocked", required_passed, review_only_checks


def _explain_check(check_id: str, status: str, reasons: tuple[str, ...]) -> tuple[str, str]:
    if status == "passed":
        return "", ""
    joined = " ".join(reasons)
    if check_id == "bootstrap_reconciliation":
        return (
            "run bootstrap reconciliation",
            "python scripts/run_shadow_bootstrap.py --campaign-root build/build11_live_websocket_campaign",
        )
    if check_id == "remote_account_state":
        return (
            "capture remote account snapshot or run reconciliation bootstrap",
            "python scripts/run_shadow_bootstrap.py --capture-remote-account --campaign-root build/build11_live_websocket_campaign",
        )
    if check_id == "time_sync":
        return (
            "enable or rerun time sync probing",
            "powershell -File .\\scripts\\Run-V53LocalSolution.ps1 -EnableTimeSyncProbe",
        )
    if check_id == "binance_credentials":
        return (
            "verify or bootstrap Binance credentials inventory",
            "python scripts/run_binance_credentials_bootstrap.py",
        )
    if check_id == "account_user_data":
        return (
            "authenticate the user-data stream or accept review-only shadow mode",
            "powershell -File .\\scripts\\Run-V53LocalSolution.ps1",
        )
    if "bootstrap_not_ready" in joined or "shadow.bootstrap.not_ready" in joined:
        return (
            "run bootstrap reconciliation",
            "python scripts/run_shadow_bootstrap.py --campaign-root build/build11_live_websocket_campaign",
        )
    if "time_sync" in joined:
        return (
            "enable or rerun time sync probing",
            "powershell -File .\\scripts\\Run-V53LocalSolution.ps1 -EnableTimeSyncProbe",
        )
    if "credential" in joined:
        return (
            "verify or bootstrap credential inventory",
            "python scripts/run_binance_credentials_bootstrap.py",
        )
    return ("inspect the blocker and refresh warmup inputs", "")


def read_warmup_explainer(
    paths: CockpitPaths,
    *,
    warmup: WarmupSummary | None,
) -> WarmupExplainerSnapshot:
    """Translate blocked and review-only warmup checks into operator next steps."""

    stamp = source_stamp(
        path=paths.warmup_summary,
        stale_after_seconds=300.0,
    )
    if warmup is None:
        return WarmupExplainerSnapshot(
            source_status=stamp["source_status"],
            source_file=str(stamp["source_file"]) if stamp["source_file"] else None,
            last_modified_at=stamp["last_modified_at"],
            age_seconds=stamp["age_seconds"],
            reason_codes=tuple(dict.fromkeys((*stamp["reason_codes"], "warmup_summary_unavailable"))),
            final_state="unknown",
            eligible_to_trade=False,
            blocking_reasons=(),
            readiness_status="unknown",
            required_checks_passed=False,
            review_only_checks=(),
            checks=(),
        )
    readiness_status, required_passed, review_only_checks = _readiness_status(warmup)
    rows = []
    for check in warmup.checks:
        required_action, suggested_command = _explain_check(
            check.check_id,
            check.status,
            check.reasons,
        )
        rows.append(
            WarmupExplainerCheck(
                check_id=check.check_id,
                status=check.status,
                reason=check.reasons[0] if check.reasons else "",
                source_file=str(paths.warmup_summary),
                required_action=required_action,
                suggested_command=suggested_command,
            )
        )
    return WarmupExplainerSnapshot(
        source_status=stamp["source_status"],
        source_file=str(stamp["source_file"]) if stamp["source_file"] else None,
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=stamp["reason_codes"],
        final_state=warmup.final_state,
        eligible_to_trade=warmup.eligible_to_trade,
        blocking_reasons=warmup.blocking_reasons,
        readiness_status=readiness_status,
        required_checks_passed=required_passed,
        review_only_checks=review_only_checks,
        checks=tuple(rows),
    )


__all__ = [
    "WarmupExplainerCheck",
    "WarmupExplainerSnapshot",
    "read_warmup_explainer",
]
