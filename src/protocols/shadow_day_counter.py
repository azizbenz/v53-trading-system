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
from datetime import date, datetime, timezone
from pathlib import Path
from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from protocols.contracts import (
    ShadowBuild14Contribution,
    ShadowBuild14ReaderContribution,
    ShadowEngineReport,
    ShadowReportArtifact,
    ShadowReportSection,
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
    metrics_summary: dict[str, float | str] = Field(default_factory=dict)


class ShadowCounterState(BaseModel, frozen=True):
    """Persisted counter state."""

    profile: ShadowProfile
    consecutive_days: int = 0
    required_days: int = 30
    last_shadow_timestamp: float | None = None
    started_at: float | None = None
    daily_records: list[ShadowDayRecord] = Field(default_factory=list)
    resets: int = 0  # number of times counter was reset due to gap
    last_error: str | None = None  # BS-65: set when state file was corrupted on load

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
_OPTIONAL_BUILD14_READER_IDS = (
    "market_toxicity_snapshot",
    "execution_fragility_score",
    "lob_deep_filter_vwa",
    "order_book_imbalance",
    "false_breakout_model",
    "hurst_regime_classifier",
    "competition_monitor",
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
_REQUIRED_PORTFOLIO_METRICS = (
    "capital_simulated_usdt",
    "gross_exposure_shadow_pct",
    "loss_budget_shadow_pct",
    "capital_free_usdt",
    "beta_btc_shadow",
)
_REQUIRED_INFRA_METRICS = (
    "dtr_loss_rate",
    "log_loss_rate",
    "event_latency_ms",
)
_REQUIRED_DECISION_METRICS = (
    "hard_block_rate",
    "phantom_trade_count",
)
_REQUIRED_BOOLEAN_FLAGS = (
    "dtr_complete",
    "decisions_reproducible",
    "infra_stable",
    "costs_plausible",
    "break_even_visible",
    "critical_alerts_visible",
    "operator_actions_logged",
    "ui_locked",
    "go_no_go_rendered",
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
                if not isinstance(data, dict):
                    raise ValueError(f"State root must be a JSON object, got {type(data).__name__}")
                return ShadowCounterState.model_validate(data)
            except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                # BS-65: fail-safe — backup corrupted file, reset with error marker
                backup = self._state_file.with_suffix(".corrupted")
                try:
                    self._state_file.rename(backup)
                except OSError:
                    pass
                return ShadowCounterState(
                    profile=self._profile,
                    last_error=f"state_file_corrupted:{type(exc).__name__}:{exc}",
                )
        return ShadowCounterState(profile=self._profile)

    def _persist(self) -> None:
        """Atomically persist state to disk."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    def _replace_state(self, **updates: object) -> None:
        payload = self._state.model_dump(mode="python")
        payload.update(updates)
        self._state = ShadowCounterState.model_validate(payload)

    def record_shadow_day(
        self,
        passed_all_gates: bool,
        metrics_summary: dict[str, float | str] | None = None,
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
        ts = time.time() if now is None else now

        # Check for 24h gap reset
        if self._state.last_shadow_timestamp is not None:
            gap = ts - self._state.last_shadow_timestamp
            if gap > _MAX_GAP_SECONDS:
                self._replace_state(
                    consecutive_days=0,
                    resets=self._state.resets + 1,
                    daily_records=[],
                    started_at=None,
                )

        # Update timestamp regardless (attempt was made)
        self._replace_state(last_shadow_timestamp=ts)

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
            self._replace_state(started_at=ts)

        next_consecutive_days = self._state.consecutive_days + 1

        record = ShadowDayRecord(
            day_number=next_consecutive_days,
            date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            timestamp=ts,
            profile=self._profile,
            passed_all_gates=True,
            metrics_summary=metrics_summary or {},
        )
        self._replace_state(
            consecutive_days=next_consecutive_days,
            daily_records=[*self._state.daily_records, record],
        )
        self._persist()
        return record

    def is_promotion_ready(self) -> bool:
        """Check if the required 30 consecutive days are met."""
        return self._state.is_complete

    def get_status(self) -> ShadowCounterState:
        """Return current counter state."""
        return self._state

    def recover_from_records(self, records: tuple[ShadowDayRecord, ...]) -> None:
        """Rebuild semantic state from persisted successful day records.

        This recovery path is used after a corrupted counter file was reset but the
        durable day-record artifacts still exist on disk.
        """

        if not records:
            raise ValueError("ShadowDayCounter.recover_from_records requires at least one record")

        previous_date: date | None = None
        previous_timestamp: float | None = None
        for index, record in enumerate(records, start=1):
            if record.profile != self._profile:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires matching profile records"
                )
            if not record.passed_all_gates:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires successful records only"
                )
            if record.day_number != index:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires contiguous day_number values"
                )
            current_date = date.fromisoformat(record.date)
            if previous_date is not None and current_date <= previous_date:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires strictly increasing dates"
                )
            if previous_timestamp is not None and record.timestamp <= previous_timestamp:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires strictly increasing timestamps"
                )
            previous_date = current_date
            previous_timestamp = record.timestamp

        self._replace_state(
            consecutive_days=len(records),
            last_shadow_timestamp=records[-1].timestamp,
            started_at=records[0].timestamp,
            daily_records=list(records),
            last_error=None,
        )
        self._persist()

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
            if isinstance(raw_value, (int, float)):
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
    def _metric_sum(
        cls,
        records: list[ShadowDayRecord],
        metric_name: str,
    ) -> float | None:
        values = cls._metric_values(records, metric_name)
        if not values:
            return None
        return round(sum(values), 8)

    @classmethod
    def _metric_latest(
        cls,
        records: list[ShadowDayRecord],
        metric_name: str,
    ) -> float | None:
        for record in reversed(records):
            raw_value = record.metrics_summary.get(metric_name)
            if isinstance(raw_value, (int, float)):
                return float(raw_value)
        return None

    @staticmethod
    def _text_metric_latest(
        records: list[ShadowDayRecord],
        metric_name: str,
    ) -> str:
        for record in reversed(records):
            raw_value = record.metrics_summary.get(metric_name)
            if isinstance(raw_value, str) and raw_value.strip():
                return raw_value.strip()
        return ""

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

    @classmethod
    def _build_build14_reader_contribution(
        cls,
        records: list[ShadowDayRecord],
        reader_name: str,
    ) -> ShadowBuild14ReaderContribution | None:
        metric_prefix = f"build14_reader.{reader_name}"
        average_observed_value = cls._metric_average(
            records, f"{metric_prefix}.observed_value"
        )
        average_severity_score = cls._metric_average(
            records, f"{metric_prefix}.severity_score"
        )
        latest_status = cls._text_metric_latest(records, f"{metric_prefix}.status")
        signal_family = cls._text_metric_latest(
            records, f"{metric_prefix}.signal_family"
        )
        latest_detail = cls._text_metric_latest(records, f"{metric_prefix}.detail")
        structured_log_key = cls._text_metric_latest(
            records, f"{metric_prefix}.structured_log_key"
        )
        observations = len(
            cls._metric_values(records, f"{metric_prefix}.observed_value")
        )
        if (
            average_observed_value is None
            or average_severity_score is None
            or not latest_status
            or not signal_family
            or observations == 0
        ):
            return None
        return ShadowBuild14ReaderContribution(
            reader_name=reader_name,
            signal_family=signal_family,
            average_observed_value=average_observed_value,
            average_severity_score=average_severity_score,
            latest_status=latest_status,
            latest_detail=latest_detail,
            structured_log_key=structured_log_key,
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
        portfolio_metrics = {
            metric_name: self._metric_latest(successful_records, metric_name)
            for metric_name in _REQUIRED_PORTFOLIO_METRICS
        }
        infra_metrics = {
            metric_name: self._metric_average(successful_records, metric_name)
            for metric_name in _REQUIRED_INFRA_METRICS
        }
        decision_metrics = {
            "hard_block_rate": self._metric_average(
                successful_records, "hard_block_rate"
            ),
            "phantom_trade_count": self._metric_sum(
                successful_records, "phantom_trade_count"
            ),
        }
        dominant_cluster = self._text_metric_latest(
            successful_records, "dominant_cluster"
        )
        dtr_complete = self._metric_flag(successful_records, "dtr_complete")
        decisions_reproducible = self._metric_flag(
            successful_records, "decisions_reproducible"
        )
        infra_stable = self._metric_flag(successful_records, "infra_stable")
        costs_plausible = self._metric_flag(successful_records, "costs_plausible")
        break_even_visible = self._metric_flag(successful_records, "break_even_visible")
        critical_alerts_visible = self._metric_flag(
            successful_records, "critical_alerts_visible"
        )
        operator_actions_logged = self._metric_flag(
            successful_records, "operator_actions_logged"
        )
        ui_locked = self._metric_flag(successful_records, "ui_locked")
        go_no_go_rendered = self._metric_flag(successful_records, "go_no_go_rendered")

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
        build14_reader_contribution = tuple(
            contribution
            for reader_name in _OPTIONAL_BUILD14_READER_IDS
            if (
                contribution := self._build_build14_reader_contribution(
                    successful_records, reader_name
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
        data_infra_report_ready = (
            infra_stable
            and all(value is not None for value in infra_metrics.values())
            and global_metrics["stale_rate"] is not None
            and global_metrics["pair_health_ratio"] is not None
            and global_metrics["backlog_avg"] is not None
        )
        decisions_dtr_report_ready = (
            dtr_complete
            and decisions_reproducible
            and global_metrics["dtr_coverage"] is not None
            and decision_metrics["hard_block_rate"] is not None
            and decision_metrics["phantom_trade_count"] is not None
        )
        costs_break_even_report_ready = (
            costs_plausible
            and break_even_visible
            and global_metrics["estimated_cost_bps"] is not None
            and global_metrics["edge_net"] is not None
            and global_metrics["economic_pass_rate"] is not None
        )
        portfolio_report_ready = (
            global_metrics["ce_net"] is not None
            and self._metric_sum(successful_records, "pnl_shadow") is not None
            and all(value is not None for value in portfolio_metrics.values())
            and bool(dominant_cluster)
        )
        ui_alerting_report_ready = (
            critical_alerts_visible and operator_actions_logged and ui_locked
        )
        go_no_go_report_ready = go_no_go_rendered

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
        for metric_name, value in portfolio_metrics.items():
            if value is None:
                missing_sections.append(metric_name)
        for metric_name, value in infra_metrics.items():
            if value is None:
                missing_sections.append(metric_name)
        for metric_name, value in decision_metrics.items():
            if value is None:
                missing_sections.append(metric_name)
        if not dominant_cluster:
            missing_sections.append("dominant_cluster")
        for metric_name in _REQUIRED_BOOLEAN_FLAGS:
            if not self._metric_flag(successful_records, metric_name):
                missing_sections.append(metric_name)
        if not data_infra_report_ready:
            missing_sections.append("data_infra_report")
        if not decisions_dtr_report_ready:
            missing_sections.append("decisions_dtr_report")
        if not costs_break_even_report_ready:
            missing_sections.append("costs_break_even_report")
        if not inter_engine_comparison_ready:
            missing_sections.append("inter_engine_comparison")
        if not build14_contribution_ready:
            missing_sections.append("build14_contribution")
        if not portfolio_report_ready:
            missing_sections.append("portfolio_report")
        if not ui_alerting_report_ready:
            missing_sections.append("ui_alerting_report")
        if not go_no_go_report_ready:
            missing_sections.append("go_no_go_report")

        rendered_sections = (
            ShadowReportSection(
                section_id="data_infra_report",
                title="rapport stabilite data / infra",
                ready=data_infra_report_ready,
                summary=(
                    f"stale={global_metrics['stale_rate'] if global_metrics['stale_rate'] is not None else 'n/a'} / "
                    f"pair_health={global_metrics['pair_health_ratio'] if global_metrics['pair_health_ratio'] is not None else 'n/a'} / "
                    f"dtr_loss={infra_metrics['dtr_loss_rate'] if infra_metrics['dtr_loss_rate'] is not None else 'n/a'} / "
                    f"log_loss={infra_metrics['log_loss_rate'] if infra_metrics['log_loss_rate'] is not None else 'n/a'}"
                ),
            ),
            ShadowReportSection(
                section_id="decisions_dtr_report",
                title="rapport decisions & dtr",
                ready=decisions_dtr_report_ready,
                summary=(
                    f"dtr={global_metrics['dtr_coverage'] if global_metrics['dtr_coverage'] is not None else 'n/a'} / "
                    f"hard_block={decision_metrics['hard_block_rate'] if decision_metrics['hard_block_rate'] is not None else 'n/a'} / "
                    f"phantom={decision_metrics['phantom_trade_count'] if decision_metrics['phantom_trade_count'] is not None else 'n/a'}"
                ),
            ),
            ShadowReportSection(
                section_id="costs_break_even_report",
                title="rapport couts & break-even",
                ready=costs_break_even_report_ready,
                summary=(
                    f"cost_bps={global_metrics['estimated_cost_bps'] if global_metrics['estimated_cost_bps'] is not None else 'n/a'} / "
                    f"edge={global_metrics['edge_net'] if global_metrics['edge_net'] is not None else 'n/a'} / "
                    f"economic_pass={global_metrics['economic_pass_rate'] if global_metrics['economic_pass_rate'] is not None else 'n/a'}"
                ),
            ),
            ShadowReportSection(
                section_id="engine_comparison_report",
                title="rapport A vs B vs C vs D",
                ready=inter_engine_comparison_ready and build14_contribution_ready,
                summary=(
                    f"engines={len(inter_engine_comparison)}/{len(_REQUIRED_ENGINE_IDS)} / "
                    f"build14={len(build14_contribution)}/{len(_REQUIRED_BUILD14_IDS)} / "
                    f"readers={len(build14_reader_contribution)}/{len(_OPTIONAL_BUILD14_READER_IDS)}"
                ),
            ),
            ShadowReportSection(
                section_id="portfolio_report",
                title="rapport portefeuille shadow",
                ready=portfolio_report_ready,
                summary=(
                    f"ce={global_metrics['ce_net'] if global_metrics['ce_net'] is not None else 'n/a'} / "
                    f"pnl={self._metric_sum(successful_records, 'pnl_shadow') if self._metric_sum(successful_records, 'pnl_shadow') is not None else 'n/a'} / "
                    f"beta={portfolio_metrics['beta_btc_shadow'] if portfolio_metrics['beta_btc_shadow'] is not None else 'n/a'} / "
                    f"cluster={dominant_cluster or 'n/a'}"
                ),
            ),
            ShadowReportSection(
                section_id="ui_alerting_report",
                title="rapport ui / alerting",
                ready=ui_alerting_report_ready,
                summary=(
                    f"critical_alerts={'yes' if critical_alerts_visible else 'no'} / "
                    f"operator_log={'yes' if operator_actions_logged else 'no'} / "
                    f"ui_locked={'yes' if ui_locked else 'no'}"
                ),
            ),
            ShadowReportSection(
                section_id="go_no_go_report",
                title="verdict go / no-go micro-live",
                ready=go_no_go_report_ready,
                summary=(
                    "go/no-go rendered"
                    if go_no_go_report_ready
                    else "go/no-go missing"
                ),
            ),
        )

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
            capital_simulated_usdt=portfolio_metrics["capital_simulated_usdt"],
            gross_exposure_shadow_pct=portfolio_metrics["gross_exposure_shadow_pct"],
            loss_budget_shadow_pct=portfolio_metrics["loss_budget_shadow_pct"],
            capital_free_usdt=portfolio_metrics["capital_free_usdt"],
            beta_btc_shadow=portfolio_metrics["beta_btc_shadow"],
            dominant_cluster=dominant_cluster,
            pnl_shadow=self._metric_sum(successful_records, "pnl_shadow"),
            dtr_loss_rate=infra_metrics["dtr_loss_rate"],
            log_loss_rate=infra_metrics["log_loss_rate"],
            event_latency_ms=infra_metrics["event_latency_ms"],
            hard_block_rate=decision_metrics["hard_block_rate"],
            phantom_trade_count=(
                int(decision_metrics["phantom_trade_count"])
                if decision_metrics["phantom_trade_count"] is not None
                else None
            ),
            decisions_reproducible=decisions_reproducible,
            infra_stable=infra_stable,
            costs_plausible=costs_plausible,
            break_even_visible=break_even_visible,
            critical_alerts_visible=critical_alerts_visible,
            operator_actions_logged=operator_actions_logged,
            ui_locked=ui_locked,
            shadow_report_ready=not missing_sections,
            data_infra_report_ready=data_infra_report_ready,
            decisions_dtr_report_ready=decisions_dtr_report_ready,
            costs_break_even_report_ready=costs_break_even_report_ready,
            inter_engine_comparison_ready=inter_engine_comparison_ready,
            build14_contribution_ready=build14_contribution_ready,
            portfolio_report_ready=portfolio_report_ready,
            ui_alerting_report_ready=ui_alerting_report_ready,
            go_no_go_report_ready=go_no_go_report_ready,
            inter_engine_comparison=inter_engine_comparison,
            build14_contribution=build14_contribution,
            build14_reader_contribution=build14_reader_contribution,
            rendered_sections=rendered_sections,
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
