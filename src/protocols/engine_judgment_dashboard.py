from __future__ import annotations

from monitoring import EngineJudgmentCard, EngineJudgmentProjection
from protocols.contracts import ShadowEngineJudgmentSummary


def _card_status_from_verdict(verdict: str) -> str:
    if verdict == "promotable":
        return "healthy"
    if verdict == "shadow-only":
        return "warning"
    if verdict == "rewrite-required":
        return "critical"
    return "planned"


def _projection_status_from_summary(summary: ShadowEngineJudgmentSummary) -> str:
    if not summary.judgments:
        return "planned"

    portfolio_verdict = summary.portfolio_judgment.judgment_verdict
    verdicts = {judgment.judgment_verdict for judgment in summary.judgments}
    if portfolio_verdict == "rewrite-required" or "rewrite-required" in verdicts:
        return "critical"
    if portfolio_verdict in {"shadow-only", "dormant"} or verdicts & {"shadow-only", "dormant"}:
        return "warning"
    return "healthy"


def build_engine_judgment_projection(
    summary: ShadowEngineJudgmentSummary,
) -> EngineJudgmentProjection:
    """Project governed Shadow engine judgments into the normalized monitoring surface."""

    portfolio = summary.portfolio_judgment
    return EngineJudgmentProjection(
        status=_projection_status_from_summary(summary),  # type: ignore[arg-type]
        source_report_id=summary.source_report_id,
        source_shadow_run_id=summary.source_shadow_run_id,
        source_shadow_days_completed=summary.source_shadow_days_completed,
        source_shadow_required_days=summary.source_shadow_required_days,
        portfolio_judgment_verdict=portfolio.judgment_verdict,
        portfolio_physics_pressure=portfolio.physics_pressure,
        portfolio_redundancy_pressure=portfolio.redundancy_pressure,
        portfolio_cluster_pressure=portfolio.cluster_pressure,
        portfolio_beta_pressure=portfolio.beta_pressure,
        portfolio_gross_capacity_pressure=portfolio.gross_capacity_pressure,
        portfolio_loss_capacity_pressure=portfolio.loss_capacity_pressure,
        portfolio_rejected_engine_count=portfolio.portfolio_rejected_engine_count,
        ranking_rejected_engine_count=portfolio.ranking_rejected_engine_count,
        elevated_physics_engine_count=portfolio.elevated_physics_engine_count,
        critical_physics_engine_count=portfolio.critical_physics_engine_count,
        phantom_trade_count=portfolio.phantom_trade_count or 0,
        portfolio_rationale=portfolio.rationale,
        cards=tuple(
            EngineJudgmentCard(
                engine_id=judgment.engine_id,
                component_verdict=judgment.component_verdict,
                judgment_verdict=judgment.judgment_verdict,
                status=_card_status_from_verdict(judgment.judgment_verdict),  # type: ignore[arg-type]
                useful_frequency=judgment.useful_frequency,
                ce_expected=judgment.ce_expected or 0.0,
                estimated_cost_bps=judgment.estimated_cost_bps,
                edge_net=judgment.edge_net,
                economic_pass_rate=judgment.economic_pass_rate,
                conflict_rate=judgment.conflict_rate,
                marginal_edge=judgment.marginal_edge,
                redundancy_score=judgment.redundancy_score,
                portfolio_contribution=judgment.portfolio_contribution,
                observations=judgment.observations,
                rationale=judgment.rationale,
                evidence_summary=judgment.evidence_summary,
            )
            for judgment in summary.judgments
        ),
    )


__all__ = ["build_engine_judgment_projection"]
