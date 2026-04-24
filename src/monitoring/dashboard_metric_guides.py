"""Canonical Grafana metric guide text for local operator dashboards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricGuideEntry:
    """One governed metric explanation line for Grafana text panels."""

    metric_name: str
    explanation: str


@dataclass(frozen=True)
class MetricGuideSection:
    """One titled section in a Grafana metric guide."""

    title: str
    entries: tuple[MetricGuideEntry, ...]
    notes: tuple[str, ...] = ()


_SHARED_OPERATOR_RULES = (
    "Prometheus remains the compact machine-readable surface.",
    "Grafana is the explanation surface.",
    "Read labels and paired counters together before concluding that a system is healthy or promotion-ready.",
)


_LOCAL_LAB_SECTIONS = (
    MetricGuideSection(
        title="Live-Light gate groups",
        entries=(
            MetricGuideEntry(
                metric_name="v53_live_light_gate_group_status",
                explanation=(
                    "Compact state code per gate family. `0=passed`, "
                    "`1=review_only`, `2=blocked`."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_live_light_gate_group_reason_count",
                explanation=(
                    "Number of reasons attached to the same gate family. `0` is "
                    "the normal nominal case for a passed group."
                ),
            ),
        ),
        notes=(
            "`review_only` means the group did not hard-block the run, but still requires operator attention or a governed review path.",
            "`blocked` means the gate family is fail-closed in the current summary.",
        ),
    ),
    MetricGuideSection(
        title="Build-14 bounded influence",
        entries=(
            MetricGuideEntry(
                metric_name="v53_build14_action",
                explanation=(
                    "State metric carried by the `action` label. Current governed "
                    "actions are `observe`, `downgrade_confidence`, "
                    "`review_only`, and `soft_veto`."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_build14_recommended_budget_factor",
                explanation=(
                    "Ratio in `[0, 1]`. `1.0` means nominal budget, values like "
                    "`0.85` or `0.75` mean bounded reduction, and `0.0` means "
                    "review-only or veto posture."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_build14_confidence_penalty_weight",
                explanation=(
                    "Governed penalty weight. `0.0` is nominal, `0.10-0.15` is "
                    "bounded downgrade, `0.25` is critical."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_build14_requires_manual_review",
                explanation=(
                    "`1` means manual review remains mandatory before "
                    "live-light progression."
                ),
            ),
        ),
        notes=(
            "Do not infer promotion readiness from one metric alone; read the gate-group state together with the final live-light verdict.",
        ),
    ),
)


_SHADOW_VPS_SECTIONS = (
    MetricGuideSection(
        title="Service and promotion",
        entries=(
            MetricGuideEntry(
                metric_name="v53_shadow_vps_service_status",
                explanation=(
                    "State metric carried by labels such as `status`, "
                    "`acquisition_mode`, and `runtime_data_source`."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_service_promotion_gate_passed",
                explanation=(
                    "Boolean state. `1` means the promotion gate is currently "
                    "passed, `0` means it is not."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_service_heartbeat_age_ms",
                explanation=(
                    "Heartbeat age in milliseconds. Higher values mean the "
                    "service is becoming stale."
                ),
            ),
        ),
    ),
    MetricGuideSection(
        title="Execution projection",
        entries=(
            MetricGuideEntry(
                metric_name="v53_shadow_vps_execution_runtime_projection_ready",
                explanation=(
                    "Boolean state for the projection bundle as a whole."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_execution_runtime_projection_bridge_loaded",
                explanation=(
                    "Boolean state for the bridge itself, with the "
                    "`bridge_status` label carrying the qualitative status."
                ),
            ),
            MetricGuideEntry(
                metric_name=(
                    "v53_shadow_vps_execution_runtime_projection_ready_consumer_count"
                ),
                explanation=(
                    "Ready downstream consumer count. Read together with the "
                    "paired partial and blocked counters."
                ),
            ),
            MetricGuideEntry(
                metric_name=(
                    "v53_shadow_vps_execution_runtime_projection_partial_consumer_count"
                ),
                explanation=(
                    "Partial downstream consumer count."
                ),
            ),
            MetricGuideEntry(
                metric_name=(
                    "v53_shadow_vps_execution_runtime_projection_blocked_consumer_count"
                ),
                explanation=(
                    "Blocked downstream consumer count."
                ),
            ),
        ),
    ),
    MetricGuideSection(
        title="Recovery and governed control",
        entries=(
            MetricGuideEntry(
                metric_name="v53_shadow_vps_recovery_status",
                explanation=(
                    "Current VPS recovery state with `recovery_status`, "
                    "`eligible_to_trade`, and the readiness report reference carried "
                    "in labels."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_warmup_state",
                explanation=(
                    "Current VPS warm-up state with `warmup_final_state` and "
                    "eligibility labels."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_dashboard_control_halted",
                explanation=(
                    "Governed operator halt state. Labels carry the target profile, "
                    "deployment state, and latest command/result pair."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_active_regime_detector_artifact",
                explanation=(
                    "Active RegimeDetector artifact identity surface. Read the "
                    "`artifact_hash` and `artifact_id` labels before concluding the "
                    "VPS is running the expected artifact."
                ),
            ),
        ),
        notes=(
            "Recovery and warm-up must both be eligible before any trading progression is treated as healthy.",
            "Dashboard control metrics are governed operator surfaces only; Grafana does not execute the commands itself.",
        ),
    ),
    MetricGuideSection(
        title="Regime-lite governance",
        entries=(
            MetricGuideEntry(
                metric_name="v53_shadow_vps_regime_lite_safing_status",
                explanation=(
                    "Governed regime-lite state; the labels carry "
                    "`governance_status`, `severity`, `state`, and "
                    "`recommended_action`."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_regime_lite_entries_blocked",
                explanation=(
                    "`1` means new entries are currently blocked by "
                    "regime-lite governance."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_shadow_vps_regime_lite_should_exit_all",
                explanation=(
                    "`1` means the governed recommendation is to exit all "
                    "current exposure."
                ),
            ),
        ),
    ),
    MetricGuideSection(
        title="Telegram alerting",
        entries=(
            MetricGuideEntry(
                metric_name="v53_shadow_vps_telegram_alert_delivery_status",
                explanation=(
                    "State metric carried by `delivery_status`, "
                    "`alert_event_type`, `config_source`, and `error_present`."
                ),
            ),
        ),
        notes=(
            "Interpret the delivery outcome through the labels rather than through the numeric value alone.",
        ),
    ),
)


def _render_metric_guide_markdown(
    *,
    intro: str,
    sections: tuple[MetricGuideSection, ...],
) -> str:
    lines = ["## Metric guide", "", intro, ""]
    for section in sections:
        lines.append(f"### {section.title}")
        for entry in section.entries:
            lines.append(f"- `{entry.metric_name}`: {entry.explanation}")
        for note in section.notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.append("### Operator reading rule")
    for rule in _SHARED_OPERATOR_RULES:
        lines.append(f"- {rule}")
    return "\n".join(lines).strip()


def render_local_lab_metric_guide_markdown() -> str:
    """Render the canonical Local IA Lab metric guide markdown."""

    return _render_metric_guide_markdown(
        intro=(
            "This panel documents the governed semantics of the current Local IA "
            "Lab promotion and Build-14 metrics. It is intentionally concise "
            "and only covers metrics already emitted by the repo."
        ),
        sections=_LOCAL_LAB_SECTIONS,
    )


def render_shadow_vps_metric_guide_markdown() -> str:
    """Render the canonical Shadow VPS metric guide markdown."""

    return _render_metric_guide_markdown(
        intro=(
            "This panel documents the governed meaning of the current Shadow VPS "
            "observability metrics already exported by the repo."
        ),
        sections=_SHADOW_VPS_SECTIONS,
    )


__all__ = [
    "MetricGuideEntry",
    "MetricGuideSection",
    "render_local_lab_metric_guide_markdown",
    "render_shadow_vps_metric_guide_markdown",
]
