"""Bounded information-stress detector and risk precheck for entry vetoes."""

from __future__ import annotations

from enum import StrEnum
import math

from pydantic import BaseModel, Field

from .risk_runtime import (
    RiskInfoStressPrecheckHook,
    RiskInfoStressPrecheckInput,
    RiskInfoStressPrecheckOutcome,
)


class InfoStressLevel(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    EXTREME = "extreme"


class InfoStressThresholds(BaseModel, frozen=True):
    spread_ratio_alert_threshold: float = Field(default=5.0, gt=1.0)
    depth_ratio_min_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    cancellation_rate_alert_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    taker_imbalance_alert_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    micro_vol_divergence_alert_threshold: float = Field(default=3.0, gt=0.0)
    extreme_alert_count: int = Field(default=3, ge=1, le=5)
    cooldown_s: int = Field(default=600, ge=1)


class InfoStressAssessment(BaseModel, frozen=True):
    pair: str = Field(..., min_length=1)
    level: InfoStressLevel = InfoStressLevel.NORMAL
    alert_count: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = ()
    entries_blocked: bool = False
    entries_blocked_until_ts: int = Field(default=0, ge=0)
    detail: str = ""


class InfoStressMonitor:
    """Stateful per-pair info-stress classifier with bounded cooldown semantics."""

    def __init__(
        self,
        *,
        thresholds: InfoStressThresholds | None = None,
    ) -> None:
        self._thresholds = thresholds or InfoStressThresholds()
        self._cooldown_until_by_pair: dict[str, int] = {}

    @property
    def thresholds(self) -> InfoStressThresholds:
        return self._thresholds

    def assess(
        self,
        *,
        pair: str,
        now: float,
        spread_bps: float | None = None,
        reference_spread_bps: float | None = None,
        depth_ratio: float | None = None,
        order_cancellation_rate: float | None = None,
        taker_imbalance: float | None = None,
        micro_vol_divergence: float | None = None,
    ) -> InfoStressAssessment:
        if not math.isfinite(now) or now <= 0.0:
            raise ValueError("InfoStressMonitor.assess requires finite now > 0")

        reason_codes = tuple(
            code
            for code in (
                self._spread_reason(
                    spread_bps=spread_bps,
                    reference_spread_bps=reference_spread_bps,
                ),
                self._depth_reason(depth_ratio=depth_ratio),
                self._cancellation_reason(
                    order_cancellation_rate=order_cancellation_rate
                ),
                self._taker_reason(taker_imbalance=taker_imbalance),
                self._micro_vol_reason(
                    micro_vol_divergence=micro_vol_divergence
                ),
            )
            if code
        )
        alert_count = len(reason_codes)
        cooldown_until_ts = self._cooldown_until_by_pair.get(pair, 0)

        if alert_count >= self._thresholds.extreme_alert_count:
            cooldown_until_ts = int(now + self._thresholds.cooldown_s)
            self._cooldown_until_by_pair[pair] = cooldown_until_ts
            return InfoStressAssessment(
                pair=pair,
                level=InfoStressLevel.EXTREME,
                alert_count=alert_count,
                reason_codes=reason_codes,
                entries_blocked=True,
                entries_blocked_until_ts=cooldown_until_ts,
                detail=(
                    "info_stress reached EXTREME with "
                    f"{alert_count} active anomaly signal(s); "
                    f"entry cooldown active until {cooldown_until_ts}"
                ),
            )

        if cooldown_until_ts > int(now):
            return InfoStressAssessment(
                pair=pair,
                level=InfoStressLevel.ELEVATED,
                alert_count=alert_count,
                reason_codes=reason_codes + ("INFO_STRESS_COOLDOWN_ACTIVE",),
                entries_blocked=True,
                entries_blocked_until_ts=cooldown_until_ts,
                detail=(
                    "info_stress cooldown remains active "
                    f"until {cooldown_until_ts}"
                ),
            )

        level = (
            InfoStressLevel.NORMAL if alert_count == 0 else InfoStressLevel.ELEVATED
        )
        detail = (
            "info_stress nominal"
            if level == InfoStressLevel.NORMAL
            else f"info_stress elevated with {alert_count} active anomaly signal(s)"
        )
        return InfoStressAssessment(
            pair=pair,
            level=level,
            alert_count=alert_count,
            reason_codes=reason_codes,
            entries_blocked=False,
            entries_blocked_until_ts=0,
            detail=detail,
        )

    def _spread_reason(
        self,
        *,
        spread_bps: float | None,
        reference_spread_bps: float | None,
    ) -> str:
        if spread_bps is None or reference_spread_bps is None:
            return ""
        if not math.isfinite(spread_bps) or not math.isfinite(reference_spread_bps):
            return ""
        if spread_bps < 0.0 or reference_spread_bps <= 0.0:
            return ""
        spread_ratio = spread_bps / reference_spread_bps
        if spread_ratio >= self._thresholds.spread_ratio_alert_threshold:
            return "INFO_STRESS_SPREAD_EXPLOSION"
        return ""

    def _depth_reason(self, *, depth_ratio: float | None) -> str:
        if depth_ratio is None or not math.isfinite(depth_ratio):
            return ""
        if depth_ratio < 0.0 or depth_ratio > 1.0:
            return ""
        if depth_ratio <= self._thresholds.depth_ratio_min_threshold:
            return "INFO_STRESS_DEPTH_RATIO_COLLAPSE"
        return ""

    def _cancellation_reason(
        self,
        *,
        order_cancellation_rate: float | None,
    ) -> str:
        if order_cancellation_rate is None or not math.isfinite(order_cancellation_rate):
            return ""
        if order_cancellation_rate < 0.0 or order_cancellation_rate > 1.0:
            return ""
        if (
            order_cancellation_rate
            >= self._thresholds.cancellation_rate_alert_threshold
        ):
            return "INFO_STRESS_CANCELLATION_SPIKE"
        return ""

    def _taker_reason(self, *, taker_imbalance: float | None) -> str:
        if taker_imbalance is None or not math.isfinite(taker_imbalance):
            return ""
        if taker_imbalance < -1.0 or taker_imbalance > 1.0:
            return ""
        if abs(taker_imbalance) >= self._thresholds.taker_imbalance_alert_threshold:
            return "INFO_STRESS_TAKER_IMBALANCE_SATURATED"
        return ""

    def _micro_vol_reason(
        self,
        *,
        micro_vol_divergence: float | None,
    ) -> str:
        if micro_vol_divergence is None or not math.isfinite(micro_vol_divergence):
            return ""
        if micro_vol_divergence < 0.0:
            return ""
        if (
            micro_vol_divergence
            >= self._thresholds.micro_vol_divergence_alert_threshold
        ):
            return "INFO_STRESS_MICRO_VOL_DIVERGENCE"
        return ""


def build_info_stress_entry_gate(
    monitor: InfoStressMonitor,
) -> RiskInfoStressPrecheckHook:
    """Build a bounded risk precheck from the typed info-stress monitor."""

    def _hook(
        hook_input: RiskInfoStressPrecheckInput,
    ) -> RiskInfoStressPrecheckOutcome:
        assessment = monitor.assess(
            pair=hook_input.pair,
            now=hook_input.now_ts,
            spread_bps=hook_input.spread_bps,
            reference_spread_bps=hook_input.reference_spread_bps,
            depth_ratio=hook_input.depth_ratio,
            order_cancellation_rate=hook_input.order_cancellation_rate,
            taker_imbalance=hook_input.taker_imbalance,
            micro_vol_divergence=hook_input.micro_vol_divergence,
        )
        if assessment.entries_blocked:
            return RiskInfoStressPrecheckOutcome(
                accepted=False,
                stress_level=assessment.level.value,
                alert_count=assessment.alert_count,
                entries_blocked=True,
                entries_blocked_until_ts=assessment.entries_blocked_until_ts,
                reason_codes=assessment.reason_codes or ("RISK_INFO_STRESS_EXTREME",),
                detail=assessment.detail,
            )
        return RiskInfoStressPrecheckOutcome(
            accepted=True,
            stress_level=assessment.level.value,
            alert_count=assessment.alert_count,
            entries_blocked=False,
            entries_blocked_until_ts=assessment.entries_blocked_until_ts,
            reason_codes=assessment.reason_codes,
            detail=assessment.detail,
        )

    return _hook


__all__ = [
    "InfoStressAssessment",
    "InfoStressLevel",
    "InfoStressMonitor",
    "InfoStressThresholds",
    "build_info_stress_entry_gate",
]
