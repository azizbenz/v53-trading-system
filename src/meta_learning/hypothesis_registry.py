"""Build governed hypotheses from diagnostics."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult, LearningHypothesis
from meta_learning.enums import EvidenceStrength, HypothesisGovernanceStage


_RATIONALE_BY_CATEGORY = {
    "trace_coverage": "Low trace coverage suggests observability is too weak for governed promotion.",
    "sterilization": "Elevated CRA sterilization suggests economic viability is being destroyed downstream.",
    "cost_drift": "Break-even drift indicates the current cost model is no longer representative.",
    "edge_degraded": "Edge degradation suggests the previously credible edge is no longer stable.",
    "near_miss": "Near-miss records suggest valid edge may be blocked by current thresholds.",
    "no_issue": "No material issue detected; keep surveillance and collect more evidence.",
}

_TARGET_BY_CATEGORY = {
    "trace_coverage": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.dtr_core",
        "signal_family": "observability",
        "expected_replay_evidence": (
            "replay_dtr_coverage",
            "diagnostic_trace_density",
        ),
        "expected_shadow_evidence": (
            "shadow_dtr_coverage",
            "shadow_component_assessment",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "observability_export",
        ),
    },
    "sterilization": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.cra_monitor",
        "signal_family": "economics",
        "expected_replay_evidence": (
            "sterilization_rate_delta",
            "ce_net_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_sterilization_rate",
            "shadow_candidate_assessment",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "technical_supervision",
        ),
    },
    "cost_drift": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.break_even_dashboard",
        "signal_family": "execution_cost",
        "expected_replay_evidence": (
            "expected_vs_realized_cost",
            "break_even_drift_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_execution_cost_drift",
            "shadow_report_section",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "observability_export",
        ),
    },
    "edge_degraded": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.edge_tracker_prudent_minimal",
        "signal_family": "edge_quality",
        "expected_replay_evidence": (
            "edge_net_delta",
            "sharpe_per_trade_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_edge_assessment",
            "shadow_component_assessment",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "technical_supervision",
        ),
    },
    "near_miss": {
        "target_module": "scoring_backbone",
        "target_component": "scoring_backbone.hard_block_gate",
        "signal_family": "selection_threshold",
        "expected_replay_evidence": (
            "near_miss_conversion_rate",
            "selection_acceptance_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_comparison_divergence",
            "shadow_candidate_acceptance",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "shadow_supervision",
        ),
    },
}


def build_learning_hypotheses(
    correlation_id: str,
    diagnostics: tuple[DiagnosticResult, ...],
    *,
    source_version: str = "",
) -> tuple[LearningHypothesis, ...]:
    """Convert diagnostics into governed replay hypotheses."""

    hypotheses: list[LearningHypothesis] = []
    categories_in_order: list[str] = []
    refs_by_category: dict[str, list[str]] = {}
    summary_by_category: dict[str, str] = {}

    for diagnostic in diagnostics:
        if diagnostic.category == "no_issue":
            continue
        if diagnostic.category not in refs_by_category:
            categories_in_order.append(diagnostic.category)
            refs_by_category[diagnostic.category] = []
            summary_by_category[diagnostic.category] = diagnostic.summary
        refs_by_category[diagnostic.category].append(diagnostic.diagnostic_id)

    for index, category in enumerate(categories_in_order, start=1):
        diagnostic_ids = tuple(refs_by_category[category])
        sample_size = len(diagnostic_ids)
        if sample_size <= 1:
            evidence_strength = EvidenceStrength.ANECDOTAL
        elif sample_size == 2:
            evidence_strength = EvidenceStrength.WEAK_PATTERN
        elif sample_size < 5:
            evidence_strength = EvidenceStrength.REPEATABLE_PATTERN
        else:
            evidence_strength = EvidenceStrength.ROBUST_CANDIDATE
        hypotheses.append(LearningHypothesis(
            hypothesis_id=f"{correlation_id}:hypothesis:{index}",
            correlation_id=correlation_id,
            category=category,
            title=f"Hypothesis for {category}",
            rationale=_RATIONALE_BY_CATEGORY.get(category, summary_by_category[category]),
            diagnostic_ids=diagnostic_ids,
            target_module=_TARGET_BY_CATEGORY.get(category, {}).get("target_module", "meta_learning"),
            target_component=_TARGET_BY_CATEGORY.get(category, {}).get("target_component", ""),
            signal_family=_TARGET_BY_CATEGORY.get(category, {}).get("signal_family", ""),
            target_parameter_family=category,
            expected_effect=f"Validate whether {category} can be improved in governed replay",
            risk_of_regression="manual_review_required",
            required_replay_scope=f"{category}:local_replay",
            expected_replay_evidence=_TARGET_BY_CATEGORY.get(category, {}).get(
                "expected_replay_evidence",
                (),
            ),
            expected_shadow_evidence=_TARGET_BY_CATEGORY.get(category, {}).get(
                "expected_shadow_evidence",
                (),
            ),
            monitoring_hooks=_TARGET_BY_CATEGORY.get(category, {}).get("monitoring_hooks", ()),
            segmentation_used=(category, "engine_scope", "pair_scope"),
            comparison_metrics=(
                "ce_net",
                "dtr_coverage",
                "sterilization_rate",
                "edge_net",
            ),
            rejection_criteria=(
                "candidate worsens governed economics",
                "candidate reduces observability quality",
            ),
            evidence_strength=evidence_strength,
            sample_size=sample_size,
            shadow_candidate_allowed=False,
            source_version=source_version,
            contracts_version="build9x.contracts.v1",
            governance_stage=HypothesisGovernanceStage.DRAFT,
        ))

    return tuple(hypotheses)


__all__ = [
    "build_learning_hypotheses",
]
