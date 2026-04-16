"""Portfolio judgment helpers for the governed Shadow runtime."""

from __future__ import annotations

from typing import Mapping

from monitoring import EngineMetrics, TechnicalDashboardPayload
from protocols.contracts import (
    ShadowEngineJudgment,
    ShadowPortfolioJudgment,
    ShadowReportArtifact,
)
from protocols.shadow_runtime_shared import _REQUIRED_SHADOW_ENGINES


def _pressure_level(
    value: float | None,
    *,
    elevated_at: float,
    critical_at: float,
) -> str:
    if value is None:
        return "nominal"
    if value >= critical_at:
        return "critical"
    if value >= elevated_at:
        return "elevated"
    return "nominal"


def _engine_physics_pressure(payload_engine: EngineMetrics | None) -> str:
    if payload_engine is None:
        return "nominal"
    state = payload_engine.physics.physics_pressure_state.strip().lower()
    if state == "critical":
        return "critical"
    if state == "elevated":
        return "elevated"

    fragility_score = payload_engine.physics.fragility_score
    toxicity_score = payload_engine.physics.toxicity_score
    execution_survivability_score = payload_engine.physics.execution_survivability_score
    micro_friction_score = payload_engine.physics.micro_friction_score

    if (
        (fragility_score is not None and fragility_score >= 0.75)
        or (toxicity_score is not None and toxicity_score >= 0.75)
        or (
            execution_survivability_score is not None
            and execution_survivability_score <= 0.25
        )
        or (micro_friction_score is not None and micro_friction_score >= 0.75)
    ):
        return "critical"
    if (
        (fragility_score is not None and fragility_score >= 0.50)
        or (toxicity_score is not None and toxicity_score >= 0.50)
        or (
            execution_survivability_score is not None
            and execution_survivability_score <= 0.50
        )
        or (micro_friction_score is not None and micro_friction_score >= 0.50)
    ):
        return "elevated"
    return "nominal"


def _fallback_shadow_engine_verdicts(
    shadow_payload: TechnicalDashboardPayload | None,
) -> dict[str, str]:
    if shadow_payload is None:
        return {}

    verdicts: dict[str, str] = {}
    for engine in shadow_payload.engines:
        engine_id = engine.engine_id
        if engine_id not in _REQUIRED_SHADOW_ENGINES:
            continue
        if (
            engine.hard_blocked
            or engine.phantom_trade
            or engine.portfolio_verdict_code.startswith("rejected_")
            or engine.selection_outcome_code == "rejected_portfolio"
        ):
            verdicts[engine_id] = "rewrite-required"
        elif (
            engine.selection_outcome_code == "rejected_ranking"
            or engine.risk_decision_severity == "critical"
            or engine.scoring_final_size_multiplier <= 0.1
        ):
            verdicts[engine_id] = "shadow-only"
        else:
            verdicts[engine_id] = "promotable"
    return verdicts


def _shadow_payload_engines(
    shadow_payload: TechnicalDashboardPayload | None,
) -> dict[str, EngineMetrics]:
    if shadow_payload is None:
        return {}
    return {
        engine.engine_id: engine
        for engine in shadow_payload.engines
        if engine.engine_id in _REQUIRED_SHADOW_ENGINES
    }


def _shadow_judgment_verdicts(
    shadow_payload: TechnicalDashboardPayload | None,
    judgments: tuple[ShadowEngineJudgment, ...],
) -> dict[str, str]:
    judgment_verdicts = {
        judgment.engine_id: judgment.judgment_verdict
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
    }
    if not judgment_verdicts and shadow_payload is not None:
        judgment_verdicts = {
            card.engine_id: card.judgment_verdict
            for card in shadow_payload.engine_judgment.cards
            if card.engine_id in _REQUIRED_SHADOW_ENGINES
        }
    return judgment_verdicts or _fallback_shadow_engine_verdicts(shadow_payload)


def _shadow_portfolio_verdict_counts(
    judgment_verdicts: Mapping[str, str],
) -> tuple[int, int, int, int]:
    return (
        sum(1 for verdict in judgment_verdicts.values() if verdict == "promotable"),
        sum(1 for verdict in judgment_verdicts.values() if verdict == "shadow-only"),
        sum(1 for verdict in judgment_verdicts.values() if verdict == "rewrite-required"),
        sum(1 for verdict in judgment_verdicts.values() if verdict == "dormant"),
    )


def _shadow_physics_counts(
    judgments: tuple[ShadowEngineJudgment, ...],
    *,
    shadow_payload: TechnicalDashboardPayload | None,
    payload_engines: Mapping[str, EngineMetrics],
) -> tuple[int, int]:
    critical_count = sum(
        1
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
        and judgment.physics_pressure_state == "critical"
    )
    elevated_count = sum(
        1
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
        and judgment.physics_pressure_state == "elevated"
    )
    if judgments or shadow_payload is None:
        return critical_count, elevated_count
    payload_pressures = {
        engine_id: _engine_physics_pressure(engine)
        for engine_id, engine in payload_engines.items()
    }
    return (
        sum(1 for pressure in payload_pressures.values() if pressure == "critical"),
        sum(1 for pressure in payload_pressures.values() if pressure == "elevated"),
    )


def _shadow_high_redundancy_engine_count(
    judgments: tuple[ShadowEngineJudgment, ...],
    shadow_payload: TechnicalDashboardPayload | None,
) -> int:
    if judgments:
        return sum(
            1
            for judgment in judgments
            if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
            and (judgment.conflict_rate >= 0.35 or judgment.redundancy_score >= 0.35)
        )
    if shadow_payload is None:
        return 0
    return sum(
        1
        for card in shadow_payload.engine_judgment.cards
        if card.engine_id in _REQUIRED_SHADOW_ENGINES
        and (card.conflict_rate >= 0.35 or card.redundancy_score >= 0.35)
    )


def _shadow_payload_rejection_counts(
    payload_engines: Mapping[str, EngineMetrics],
) -> tuple[int, int, int, int, int, int]:
    portfolio_rejected = sum(
        1
        for engine in payload_engines.values()
        if engine.portfolio_verdict_code.startswith("rejected_")
        or engine.selection_outcome_code == "rejected_portfolio"
    )
    return (
        portfolio_rejected,
        sum(
            1
            for engine in payload_engines.values()
            if engine.portfolio_verdict_code == "rejected_cluster"
        ),
        sum(
            1
            for engine in payload_engines.values()
            if engine.portfolio_verdict_code == "rejected_beta"
        ),
        sum(
            1
            for engine in payload_engines.values()
            if engine.portfolio_verdict_code == "rejected_exposure"
        ),
        sum(
            1
            for engine in payload_engines.values()
            if engine.portfolio_verdict_code == "rejected_loss_budget"
        ),
        sum(
            1
            for engine in payload_engines.values()
            if engine.selection_outcome_code == "rejected_ranking"
        ),
    )


def _shadow_portfolio_surface(
    shadow_payload: TechnicalDashboardPayload | None,
    shadow_report: ShadowReportArtifact | None,
    payload_engines: Mapping[str, EngineMetrics],
) -> tuple[str, float | None, float | None, float | None, float | None, int]:
    dominant_cluster = (
        shadow_payload.portfolio.dominant_cluster
        if shadow_payload is not None and shadow_payload.portfolio.dominant_cluster
        else (shadow_report.dominant_cluster if shadow_report is not None else "")
    )
    payload_phantom_trade_count = sum(
        1 for engine in payload_engines.values() if engine.phantom_trade
    )
    phantom_trade_count = (
        max(shadow_report.phantom_trade_count, payload_phantom_trade_count)
        if shadow_report is not None and shadow_report.phantom_trade_count is not None
        else payload_phantom_trade_count
    )
    return (
        dominant_cluster,
        shadow_payload.portfolio.beta_utilization if shadow_payload is not None else None,
        shadow_payload.portfolio.gross_capacity_used_pct if shadow_payload is not None else None,
        shadow_payload.portfolio.loss_capacity_used_pct if shadow_payload is not None else None,
        shadow_report.hard_block_rate if shadow_report is not None else None,
        phantom_trade_count,
    )


def _shadow_portfolio_pressures(
    *,
    critical_physics_engine_count: int,
    elevated_physics_engine_count: int,
    high_redundancy_engine_count: int,
    cluster_rejected_engine_count: int,
    dominant_cluster: str,
    beta_rejected_engine_count: int,
    beta_utilization: float | None,
    exposure_rejected_engine_count: int,
    gross_capacity_used_pct: float | None,
    loss_budget_rejected_engine_count: int,
    loss_capacity_used_pct: float | None,
) -> tuple[str, str, str, str, str, str]:
    return (
        "critical"
        if critical_physics_engine_count >= 2
        else "elevated"
        if critical_physics_engine_count >= 1 or elevated_physics_engine_count >= 2
        else "nominal",
        "critical"
        if high_redundancy_engine_count >= 2
        else "elevated"
        if high_redundancy_engine_count >= 1
        else "nominal",
        "critical"
        if cluster_rejected_engine_count >= 2
        else "elevated"
        if cluster_rejected_engine_count >= 1
        or (dominant_cluster and high_redundancy_engine_count >= 1)
        else "nominal",
        "critical"
        if beta_rejected_engine_count >= 2
        else "elevated"
        if beta_rejected_engine_count >= 1
        else _pressure_level(beta_utilization, elevated_at=0.75, critical_at=1.0),
        "critical"
        if exposure_rejected_engine_count >= 2
        else "elevated"
        if exposure_rejected_engine_count >= 1
        else _pressure_level(gross_capacity_used_pct, elevated_at=85.0, critical_at=100.0),
        "critical"
        if loss_budget_rejected_engine_count >= 2
        else "elevated"
        if loss_budget_rejected_engine_count >= 1
        else _pressure_level(loss_capacity_used_pct, elevated_at=85.0, critical_at=100.0),
    )


def _shadow_portfolio_verdict(
    *,
    hard_block_rate: float | None,
    rewrite_required_engine_count: int,
    shadow_only_engine_count: int,
    portfolio_rejected_engine_count: int,
    ranking_rejected_engine_count: int,
    phantom_trade_count: int,
    physics_pressure: str,
    redundancy_pressure: str,
    cluster_pressure: str,
    beta_pressure: str,
    gross_capacity_pressure: str,
    loss_capacity_pressure: str,
) -> tuple[str, str]:
    if hard_block_rate is not None and hard_block_rate >= 0.25:
        return (
            "rewrite-required",
            "Shadow portfolio hard-block rate stayed above the governed rewrite threshold",
        )
    pressure_states = {
        physics_pressure,
        redundancy_pressure,
        cluster_pressure,
        beta_pressure,
        gross_capacity_pressure,
        loss_capacity_pressure,
    }
    if (
        rewrite_required_engine_count >= 2
        or portfolio_rejected_engine_count >= 2
        or phantom_trade_count >= 2
        or "critical" in pressure_states
    ):
        return (
            "rewrite-required",
            "portfolio concentration, rejection load, or capital pressure remained too high for governed promotion",
        )
    if (
        shadow_only_engine_count >= 1
        or portfolio_rejected_engine_count >= 1
        or ranking_rejected_engine_count >= 1
        or phantom_trade_count >= 1
        or "elevated" in pressure_states
    ):
        return (
            "shadow-only",
            "portfolio-level pressure is still elevated, so Shadow must continue before governed promotion",
        )
    return (
        "promotable",
        "engine mix and portfolio pressure stayed within governed promotion bounds",
    )


def derive_shadow_portfolio_judgment(
    shadow_payload: TechnicalDashboardPayload | None = None,
    *,
    shadow_report: ShadowReportArtifact | None = None,
    judgments: tuple[ShadowEngineJudgment, ...] = (),
) -> ShadowPortfolioJudgment:
    """Derive a portfolio-level promotion judgment from governed Shadow surfaces."""

    payload_engines = _shadow_payload_engines(shadow_payload)
    judgment_verdicts = _shadow_judgment_verdicts(shadow_payload, judgments)
    if not judgment_verdicts and not payload_engines:
        return ShadowPortfolioJudgment(
            judgment_verdict="shadow-only",
            rationale="governed Shadow portfolio evidence is incomplete",
        )
    (
        promotable_engine_count,
        shadow_only_engine_count,
        rewrite_required_engine_count,
        dormant_engine_count,
    ) = _shadow_portfolio_verdict_counts(judgment_verdicts)
    critical_physics_engine_count, elevated_physics_engine_count = _shadow_physics_counts(
        judgments,
        shadow_payload=shadow_payload,
        payload_engines=payload_engines,
    )
    high_redundancy_engine_count = _shadow_high_redundancy_engine_count(
        judgments,
        shadow_payload,
    )
    (
        portfolio_rejected_engine_count,
        cluster_rejected_engine_count,
        beta_rejected_engine_count,
        exposure_rejected_engine_count,
        loss_budget_rejected_engine_count,
        ranking_rejected_engine_count,
    ) = _shadow_payload_rejection_counts(payload_engines)
    (
        dominant_cluster,
        beta_utilization,
        gross_capacity_used_pct,
        loss_capacity_used_pct,
        hard_block_rate,
        phantom_trade_count,
    ) = _shadow_portfolio_surface(shadow_payload, shadow_report, payload_engines)
    (
        physics_pressure,
        redundancy_pressure,
        cluster_pressure,
        beta_pressure,
        gross_capacity_pressure,
        loss_capacity_pressure,
    ) = _shadow_portfolio_pressures(
        critical_physics_engine_count=critical_physics_engine_count,
        elevated_physics_engine_count=elevated_physics_engine_count,
        high_redundancy_engine_count=high_redundancy_engine_count,
        cluster_rejected_engine_count=cluster_rejected_engine_count,
        dominant_cluster=dominant_cluster,
        beta_rejected_engine_count=beta_rejected_engine_count,
        beta_utilization=beta_utilization,
        exposure_rejected_engine_count=exposure_rejected_engine_count,
        gross_capacity_used_pct=gross_capacity_used_pct,
        loss_budget_rejected_engine_count=loss_budget_rejected_engine_count,
        loss_capacity_used_pct=loss_capacity_used_pct,
    )
    judgment_verdict, rationale = _shadow_portfolio_verdict(
        hard_block_rate=hard_block_rate,
        rewrite_required_engine_count=rewrite_required_engine_count,
        shadow_only_engine_count=shadow_only_engine_count,
        portfolio_rejected_engine_count=portfolio_rejected_engine_count,
        ranking_rejected_engine_count=ranking_rejected_engine_count,
        phantom_trade_count=phantom_trade_count,
        physics_pressure=physics_pressure,
        redundancy_pressure=redundancy_pressure,
        cluster_pressure=cluster_pressure,
        beta_pressure=beta_pressure,
        gross_capacity_pressure=gross_capacity_pressure,
        loss_capacity_pressure=loss_capacity_pressure,
    )

    return ShadowPortfolioJudgment(
        judgment_verdict=judgment_verdict,
        physics_pressure=physics_pressure,  # type: ignore[arg-type]
        redundancy_pressure=redundancy_pressure,  # type: ignore[arg-type]
        cluster_pressure=cluster_pressure,  # type: ignore[arg-type]
        beta_pressure=beta_pressure,  # type: ignore[arg-type]
        gross_capacity_pressure=gross_capacity_pressure,  # type: ignore[arg-type]
        loss_capacity_pressure=loss_capacity_pressure,  # type: ignore[arg-type]
        dominant_cluster=dominant_cluster,
        beta_utilization=beta_utilization,
        gross_capacity_used_pct=gross_capacity_used_pct,
        loss_capacity_used_pct=loss_capacity_used_pct,
        hard_block_rate=hard_block_rate,
        phantom_trade_count=phantom_trade_count,
        promotable_engine_count=promotable_engine_count,
        shadow_only_engine_count=shadow_only_engine_count,
        rewrite_required_engine_count=rewrite_required_engine_count,
        dormant_engine_count=dormant_engine_count,
        elevated_physics_engine_count=elevated_physics_engine_count,
        critical_physics_engine_count=critical_physics_engine_count,
        portfolio_rejected_engine_count=portfolio_rejected_engine_count,
        ranking_rejected_engine_count=ranking_rejected_engine_count,
        cluster_rejected_engine_count=cluster_rejected_engine_count,
        beta_rejected_engine_count=beta_rejected_engine_count,
        exposure_rejected_engine_count=exposure_rejected_engine_count,
        loss_budget_rejected_engine_count=loss_budget_rejected_engine_count,
        rationale=rationale,
    )


__all__ = ["derive_shadow_portfolio_judgment", "_shadow_payload_engines"]
