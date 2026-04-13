"""Local IA Lab tail-risk review over POT-GPD breakers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field

from calibration_methods import (
    PotGpdConfig,
    PotGpdError,
    PotGpdResult,
    apply_human_maximum_cap,
    fit_pot_gpd_tail_risk,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class LocalLabTailRiskStatus(StrEnum):
    """Bounded statuses for Local IA Lab tail-risk review."""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class LocalLabTailRiskBreakerEstimate(BaseModel, frozen=True):
    """One Local IA Lab POT-GPD breaker estimate."""

    threshold_id: str = Field(..., min_length=1)
    period_kind: str = Field(..., min_length=1)
    review_status: LocalLabTailRiskStatus
    fit_ready: bool = False
    period_count: int = Field(default=0, ge=0)
    positive_loss_period_count: int = Field(default=0, ge=0)
    threshold_u: float | None = None
    exceedance_count: int = Field(default=0, ge=0)
    published_value: float | None = None
    hard_cap_human: float = Field(..., gt=0.0)
    hard_cap_satisfied: bool | None = None
    hard_cap_binding: bool | None = None
    var_estimate: float | None = None
    var_ci_lower: float | None = None
    var_ci_upper: float | None = None
    xi_hat: float | None = None
    beta_hat: float | None = None
    bootstrap_dispersion_ratio: float | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    fit_result: PotGpdResult | None = None


class LocalLabTailRiskReview(BaseModel, frozen=True):
    """Audit-ready Local IA Lab tail-risk review."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    review_status: LocalLabTailRiskStatus
    review_ready: bool = False
    breaker_count: int = Field(default=0, ge=0)
    ready_breaker_count: int = Field(default=0, ge=0)
    partial_breaker_count: int = Field(default=0, ge=0)
    blocked_breaker_count: int = Field(default=0, ge=0)
    breakers: tuple[LocalLabTailRiskBreakerEstimate, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def build_local_lab_tail_risk_review(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    records: tuple[DTRRecord, ...],
    config: PotGpdConfig | None = None,
) -> LocalLabTailRiskReview:
    """Build Local IA Lab tail-risk review for daily/weekly/monthly breakers."""

    cfg = PotGpdConfig() if config is None else config
    estimates = (
        _build_breaker_estimate(
            threshold_id="THR-R01",
            period_kind="daily",
            hard_cap_human=0.02,
            records=records,
            config=cfg,
        ),
        _build_breaker_estimate(
            threshold_id="THR-R02",
            period_kind="weekly",
            hard_cap_human=0.05,
            records=records,
            config=cfg,
        ),
        _build_breaker_estimate(
            threshold_id="THR-R03",
            period_kind="monthly",
            hard_cap_human=0.10,
            records=records,
            config=cfg,
        ),
    )
    ready_breaker_count = sum(1 for estimate in estimates if estimate.review_status == "ready")
    partial_breaker_count = sum(1 for estimate in estimates if estimate.review_status == "partial")
    blocked_breaker_count = sum(1 for estimate in estimates if estimate.review_status == "blocked")

    if blocked_breaker_count > 0:
        review_status = LocalLabTailRiskStatus.BLOCKED
    elif partial_breaker_count > 0:
        review_status = LocalLabTailRiskStatus.PARTIAL
    else:
        review_status = LocalLabTailRiskStatus.READY

    return LocalLabTailRiskReview(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        review_status=review_status,
        review_ready=review_status == LocalLabTailRiskStatus.READY,
        breaker_count=len(estimates),
        ready_breaker_count=ready_breaker_count,
        partial_breaker_count=partial_breaker_count,
        blocked_breaker_count=blocked_breaker_count,
        breakers=estimates,
        blocking_reasons=tuple(
            dict.fromkeys(
                reason for estimate in estimates for reason in estimate.blocking_reasons
            )
        ),
        caution_flags=tuple(
            dict.fromkeys(flag for estimate in estimates for flag in estimate.caution_flags)
        ),
    )


def _build_breaker_estimate(
    *,
    threshold_id: str,
    period_kind: str,
    hard_cap_human: float,
    records: tuple[DTRRecord, ...],
    config: PotGpdConfig,
) -> LocalLabTailRiskBreakerEstimate:
    losses = _aggregate_period_losses(records, period_kind)
    positive_loss_period_count = sum(1 for value in losses if value > 0.0)
    if positive_loss_period_count == 0:
        return LocalLabTailRiskBreakerEstimate(
            threshold_id=threshold_id,
            period_kind=period_kind,
            review_status=LocalLabTailRiskStatus.PARTIAL,
            period_count=len(losses),
            positive_loss_period_count=0,
            hard_cap_human=hard_cap_human,
            blocking_reasons=(),
            caution_flags=(f"{threshold_id}_NO_POSITIVE_LOSS_PERIODS",),
        )

    try:
        fit = fit_pot_gpd_tail_risk(losses, config=config)
    except PotGpdError as exc:
        message = str(exc)
        if "exceedances" in message.lower():
            return LocalLabTailRiskBreakerEstimate(
                threshold_id=threshold_id,
                period_kind=period_kind,
                review_status=LocalLabTailRiskStatus.PARTIAL,
                period_count=len(losses),
                positive_loss_period_count=positive_loss_period_count,
                hard_cap_human=hard_cap_human,
                blocking_reasons=(),
                caution_flags=(f"{threshold_id}_INSUFFICIENT_EXCEEDANCES",),
            )
        return LocalLabTailRiskBreakerEstimate(
            threshold_id=threshold_id,
            period_kind=period_kind,
            review_status=LocalLabTailRiskStatus.BLOCKED,
            period_count=len(losses),
            positive_loss_period_count=positive_loss_period_count,
            hard_cap_human=hard_cap_human,
            blocking_reasons=(f"{threshold_id}_POT_GPD_INVALID",),
            caution_flags=(message,),
        )

    hard_cap_policy = apply_human_maximum_cap(fit.var_estimate, hard_cap_human)
    hard_cap_satisfied = hard_cap_policy.hard_cap_satisfied
    published_value = hard_cap_policy.published_value
    blocking_reasons: list[str] = []
    caution_flags: list[str] = []
    review_status = LocalLabTailRiskStatus.READY
    if not fit.passes_dispersion:
        review_status = LocalLabTailRiskStatus.BLOCKED
        blocking_reasons.append(f"{threshold_id}_BOOTSTRAP_DISPERSION_TOO_HIGH")
    if hard_cap_policy.hard_cap_binding:
        caution_flags.append(f"{threshold_id}_HUMAN_HARD_CAP_CLIPPED")

    return LocalLabTailRiskBreakerEstimate(
        threshold_id=threshold_id,
        period_kind=period_kind,
        review_status=review_status,
        fit_ready=review_status == LocalLabTailRiskStatus.READY,
        period_count=len(losses),
        positive_loss_period_count=positive_loss_period_count,
        threshold_u=fit.threshold_u,
        exceedance_count=fit.exceedance_count,
        published_value=published_value,
        hard_cap_human=hard_cap_human,
        hard_cap_satisfied=hard_cap_satisfied,
        hard_cap_binding=hard_cap_policy.hard_cap_binding,
        var_estimate=fit.var_estimate,
        var_ci_lower=fit.var_ci_lower,
        var_ci_upper=fit.var_ci_upper,
        xi_hat=fit.xi_hat,
        beta_hat=fit.beta_hat,
        bootstrap_dispersion_ratio=fit.bootstrap_dispersion_ratio,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        fit_result=fit,
    )


def _aggregate_period_losses(records: tuple[DTRRecord, ...], period_kind: str) -> tuple[float, ...]:
    buckets: dict[str, float] = defaultdict(float)
    for record in records:
        if record.decision_state != DecisionState.EXECUTED:
            continue
        timestamp = datetime.fromtimestamp(record.timestamp, tz=timezone.utc)
        if period_kind == "daily":
            bucket = timestamp.strftime("%Y-%m-%d")
        elif period_kind == "weekly":
            iso = timestamp.isocalendar()
            bucket = f"{iso.year}-W{iso.week:02d}"
        elif period_kind == "monthly":
            bucket = timestamp.strftime("%Y-%m")
        else:
            raise ValueError(f"Unsupported period_kind: {period_kind}")
        buckets[bucket] += record.gross_return - record.realized_cost

    return tuple(max(-net_pnl, 0.0) for _, net_pnl in sorted(buckets.items()))


__all__ = [
    "LocalLabTailRiskBreakerEstimate",
    "LocalLabTailRiskReview",
    "LocalLabTailRiskStatus",
    "build_local_lab_tail_risk_review",
]
