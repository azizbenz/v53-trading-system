"""
HARD STATEMENT §0.6 — Shadow Day Counter.

Non-negotiable rules:
1. Light must shadow trade 30 consecutive days before Complete activation.
2. Complete must shadow trade 30 consecutive days before going live.
3. A gap > 24h between shadow runs resets the counter to 0.
4. Counter is persisted to disk (survives restart).
5. Daily report is generated at each day increment.

This module tracks shadow day counts for both LIGHT and COMPLETE profiles.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from protocols.contracts import (
    ShadowBuild14Contribution,
    ShadowEngineReport,
    ShadowReportArtifact,
)


class ShadowProfile(StrEnum):
    LIGHT = "light"
    COMPLETE = "complete"


class ShadowDayRecord(BaseModel, frozen=True):
    """Record of a single shadow day."""

    day_number: int
    date: str  # ISO date
    timestamp: float
    profile: ShadowProfile
    passed_all_gates: bool
    metrics_summary: dict[str, float] = Field(default_factory=dict)


class ShadowCounterState(BaseModel):
    """Persisted counter state."""

    profile: ShadowProfile
    consecutive_days: int = 0
    required_days: int = 30
    last_shadow_timestamp: float | None = None
    started_at: float | None = None
    daily_records: list[ShadowDayRecord] = Field(default_factory=list)
    resets: int = 0  # number of times counter was reset due to gap

    @property
    def is_complete(self) -> bool:
        return self.consecutive_days >= self.required_days

    @property
    def remaining_days(self) -> int:
        return max(0, self.required_days - self.consecutive_days)


_MAX_GAP_SECONDS = 24 * 3600  # 24h — HARD STATEMENT
_STATE_FILENAME = "shadow_counter_{profile}.json"
_REQUIRED_ENGINE_IDS = ("engine_a", "engine_b", "engine_c", "engine_d")
_REQUIRED_BUILD14_IDS = (
    "build14_microstructure",
    "build14_regime",
    "build14_covariance",
    "build14_risk_contribution",
    "build14_edge_diversity",
)
_REQUIRED_GLOBAL_METRICS = (
    "dtr_coverage",
    "ce_net",
    "estimated_cost_bps",
    "edge_net",
    "drawdown_pct",
    "stale_rate",
    "economic_pass_rate",
    "pair_health_ratio",
    "backlog_avg",
)


class ShadowDayCounter:
    """Track consecutive shadow trading days with persistence.

    HARD STATEMENT compliance:
    - 30 consecutive days required.
    - > 24h gap resets to 0.
    - State persisted atomically to disk.
    """

    def __init__(self, state_dir: Path, profile: ShadowProfile) -> None:
        self._state_dir = state_dir
        self._profile = profile
        self._state_file = state_dir / _STATE_FILENAME.format(profile=profile.value)
        self._state = self._load_or_create()

    def _load_or_create(self) -> ShadowCounterState:
        """Load persisted state or create fresh."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                return ShadowCounterState(**data)
            except (json.JSONDecodeError, ValueError):
                pass  # corrupted — start fresh
        return ShadowCounterState(profile=self._profile)

    def _persist(self) -> None:
        """Atomically persist state to disk."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    def record_shadow_day(
        self,
        passed_all_gates: bool,
        metrics_summary: dict[str, float] | None = None,
        now: float | None = None,
    ) -> ShadowDayRecord:
        """Record a completed shadow trading day.

        Args:
            passed_all_gates: Whether all shadow validation gates passed.
            metrics_summary: Optional summary of key metrics for the day.
            now: Override timestamp (for testing).

        Returns:
            The ShadowDayRecord for this day.

        HARD STATEMENT rules applied:
        - If gap since last shadow > 24h → reset counter to 0.
        - If gates failed → day not counted (counter unchanged).
        """
        ts = now or time.time()

        # Check for 24h gap reset
        if self._state.last_shadow_timestamp is not None:
            gap = ts - self._state.last_shadow_timestamp
            if gap > _MAX_GAP_SECONDS:
                self._state.consecutive_days = 0
                self._state.resets += 1
                self._state.daily_records = []
                self._state.started_at = None

        # Update timestamp regardless (attempt was made)
        self._state.last_shadow_timestamp = ts

        if not passed_all_gates:
            # Day does not count, but we record the attempt
            record = ShadowDayRecord(
                day_number=self._state.consecutive_days,
                date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                timestamp=ts,
                profile=self._profile,
                passed_all_gates=False,
                metrics_summary=metrics_summary or {},
            )
            self._persist()
            return record

        # Successful day
        if self._state.started_at is None:
            self._state.started_at = ts

        self._state.consecutive_days += 1

        record = ShadowDayRecord(
            day_number=self._state.consecutive_days,
            date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            timestamp=ts,
            profile=self._profile,
            passed_all_gates=True,
            metrics_summary=metrics_summary or {},
        )
        self._state.daily_records.append(record)
        self._persist()
        return record

    def is_promotion_ready(self) -> bool:
        """Check if the required 30 consecutive days are met."""
        return self._state.is_complete

    def get_status(self) -> ShadowCounterState:
        """Return current counter state."""
        return self._state

    def _successful_daily_records(self) -> list[ShadowDayRecord]:
        return [record for record in self._state.daily_records if record.passed_all_gates]

    @staticmethod
    def _metric_values(
        records: list[ShadowDayRecord],
        metric_name: str,
    ) -> list[float]:
        values: list[float] = []
        for record in records:
            raw_value = record.metrics_summary.get(metric_name)
            if raw_value is None:
                continue
            values.append(float(raw_value))
        return values

    @classmethod
    def _metric_average(
        cls,
        records: list[ShadowDayRecord],
        metric_name: str,
    ) -> float | None:
        values = cls._metric_values(records, metric_name)
        if not values:
            return None
        return round(sum(values) / len(values), 8)

    @classmethod
    def _metric_flag(
        cls,
        records: list[ShadowDayRecord],
        metric_name: str,
    ) -> bool:
        values = cls._metric_values(records, metric_name)
        return bool(values) and all(value >= 0.5 for value in values)

    @classmethod
    def _build_engine_report(
        cls,
        records: list[ShadowDayRecord],
        engine_id: str,
    ) -> ShadowEngineReport | None:
        gross_frequency = cls._metric_average(records, f"{engine_id}.gross_frequency")
        useful_frequency = cls._metric_average(records, f"{engine_id}.useful_frequency")
        estimated_cost_bps = cls._metric_average(
            records, f"{engine_id}.estimated_cost_bps"
        )
        edge_net = cls._metric_average(records, f"{engine_id}.edge_net")
        economic_pass_rate = cls._metric_average(
            records, f"{engine_id}.economic_pass_rate"
        )
        conflict_rate = cls._metric_average(records, f"{engine_id}.conflict_rate")
        marginal_edge = cls._metric_average(records, f"{engine_id}.marginal_edge")
        observations = len(cls._metric_values(records, f"{engine_id}.gross_frequency"))
        if (
            gross_frequency is None
            or useful_frequency is None
            or estimated_cost_bps is None
            or edge_net is None
            or economic_pass_rate is None
            or conflict_rate is None
            or observations == 0
        ):
            return None
        return ShadowEngineReport(
            engine_id=engine_id,
            gross_frequency=gross_frequency,
            useful_frequency=useful_frequency,
            estimated_cost_bps=estimated_cost_bps,
            edge_net=edge_net,
            economic_pass_rate=economic_pass_rate,
            conflict_rate=conflict_rate,
            marginal_edge=marginal_edge or 0.0,
            observations=observations,
        )

    @classmethod
    def _build_build14_contribution(
        cls,
        records: list[ShadowDayRecord],
        component_id: str,
    ) -> ShadowBuild14Contribution | None:
        contribution_score = cls._metric_average(
            records, f"{component_id}.contribution_score"
        )
        interaction_score = cls._metric_average(
            records, f"{component_id}.interaction_score"
        )
        observations = len(
            cls._metric_values(records, f"{component_id}.contribution_score")
        )
        if contribution_score is None or observations == 0:
            return None
        return ShadowBuild14Contribution(
            component_id=component_id,
            contribution_score=contribution_score,
            interaction_score=interaction_score or 0.0,
            observations=observations,
        )

    def generate_report(self) -> dict:
        """Generate a shadow validation report for promotion gate.

        HARD STATEMENT: this report is required before any promotion.
        """
        successful_records = self._successful_daily_records()
        global_metrics = {
            metric_name: self._metric_average(successful_records, metric_name)
            for metric_name in _REQUIRED_GLOBAL_METRICS
        }
        dtr_complete = self._metric_flag(successful_records, "dtr_complete")
        decisions_reproducible = self._metric_flag(
            successful_records, "decisions_reproducible"
        )
        infra_stable = self._metric_flag(successful_records, "infra_stable")
        costs_plausible = self._metric_flag(successful_records, "costs_plausible")

        inter_engine_comparison = tuple(
            report
            for engine_id in _REQUIRED_ENGINE_IDS
            if (report := self._build_engine_report(successful_records, engine_id))
            is not None
        )
        build14_contribution = tuple(
            contribution
            for component_id in _REQUIRED_BUILD14_IDS
            if (
                contribution := self._build_build14_contribution(
                    successful_records, component_id
                )
            )
            is not None
        )
        inter_engine_comparison_ready = len(inter_engine_comparison) == len(
            _REQUIRED_ENGINE_IDS
        )
        build14_contribution_ready = len(build14_contribution) == len(
            _REQUIRED_BUILD14_IDS
        )

        missing_sections: list[str] = []
        if not self._state.is_complete:
            missing_sections.append("30_day_counter")
        if not dtr_complete:
            missing_sections.append("dtr_complete")
        if not decisions_reproducible:
            missing_sections.append("decisions_reproducible")
        if not infra_stable:
            missing_sections.append("infra_stable")
        if not costs_plausible:
            missing_sections.append("costs_plausible")
        for metric_name, value in global_metrics.items():
            if value is None:
                missing_sections.append(metric_name)
        if not inter_engine_comparison_ready:
            missing_sections.append("inter_engine_comparison")
        if not build14_contribution_ready:
            missing_sections.append("build14_contribution")

        report = ShadowReportArtifact(
            report_id=(
                f"shadow_report:{self._profile.value}:{self._state.consecutive_days}"
            ),
            profile=self._profile.value,
            report_generated_at=time.time(),
            consecutive_days=self._state.consecutive_days,
            required_days=self._state.required_days,
            remaining_days=self._state.remaining_days,
            is_complete=self._state.is_complete,
            started_at=self._state.started_at,
            last_shadow_timestamp=self._state.last_shadow_timestamp,
            total_resets=self._state.resets,
            daily_records_count=len(self._state.daily_records),
            dtr_coverage=global_metrics["dtr_coverage"],
            dtr_complete=dtr_complete,
            ce_net=global_metrics["ce_net"],
            estimated_cost_bps=global_metrics["estimated_cost_bps"],
            edge_net=global_metrics["edge_net"],
            drawdown_pct=global_metrics["drawdown_pct"],
            stale_rate=global_metrics["stale_rate"],
            economic_pass_rate=global_metrics["economic_pass_rate"],
            pair_health_ratio=global_metrics["pair_health_ratio"],
            backlog_avg=global_metrics["backlog_avg"],
            decisions_reproducible=decisions_reproducible,
            infra_stable=infra_stable,
            costs_plausible=costs_plausible,
            shadow_report_ready=not missing_sections,
            inter_engine_comparison_ready=inter_engine_comparison_ready,
            build14_contribution_ready=build14_contribution_ready,
            inter_engine_comparison=inter_engine_comparison,
            build14_contribution=build14_contribution,
            missing_sections=tuple(missing_sections),
        )
        return report.model_dump(mode="json")

    def save_report(self, report_dir: Path | None = None) -> Path:
        """Persist the shadow report to disk."""
        target_dir = report_dir or self._state_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        report = self.generate_report()
        ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_file = target_dir / f"shadow_report_{self._profile.value}_{ts}.json"
        atomic_write_json(report_file, report)
        return report_file
