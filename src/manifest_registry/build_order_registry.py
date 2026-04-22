"""
4.5.4 — Build Order Registry: official implementation order.

Build order is strict and sequential:
- Build N must be validated before Build N+1 starts.
- Within a build, modules follow their declared order.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from manifest_registry.module_inventory import MODULES, ModuleEntry


class BuildStage(BaseModel, frozen=True):
    """Description of a single build stage."""

    stage: int = Field(..., ge=0, le=17)
    name: str
    description: str
    modules: tuple[str, ...]


# ─── OFFICIAL BUILD ORDER ─────────────────────────────────────────────

BUILD_STAGES: tuple[BuildStage, ...] = (
    BuildStage(
        stage=0,
        name="Foundations Freeze",
        description="Geler docs, nomenclature, conventions",
        modules=(),
    ),
    BuildStage(
        stage=1,
        name="Dependency Architecture",
        description="Socle non-negociable: contrats, manifest, DAG, tests, bootstrap",
        modules=(
            "interface_contracts",
            "manifest_registry",
            "dag_validator",
            "contract_test_suite",
            "smoke_bootstrap_recovery",
            "calibration_loader",
        ),
    ),
    BuildStage(
        stage=2,
        name="Data Backbone",
        description="Ingestion WS, normalisation, qualite data, sante paire",
        modules=("data_backbone", "regime_classifier"),
    ),
    BuildStage(
        stage=3,
        name="Execution Backbone",
        description="Execution, couts reels, reconciliation",
        modules=("sharia_compliance", "execution_backbone"),
    ),
    BuildStage(
        stage=4,
        name="Risk Backbone",
        description="Budgets risque, exposition, correlation, facteur BTC",
        modules=("risk_backbone",),
    ),
    BuildStage(
        stage=5,
        name="Scoring Backbone",
        description="Hard/soft/rank scoring pipeline",
        modules=("scoring_backbone",),
    ),
    BuildStage(
        stage=6,
        name="Engine A",
        description="Premium Trend / Expansion",
        modules=("engine_a",),
    ),
    BuildStage(
        stage=7,
        name="Engine B",
        description="Mean Reversion Intraday",
        modules=("engine_b",),
    ),
    BuildStage(
        stage=8,
        name="Portfolio Minimal",
        description="Arbitrage A/B sur 6 paires",
        modules=("portfolio",),
    ),
    BuildStage(
        stage=9,
        name="Meta Minimal",
        description="DTR, CRA, break-even, edge tracker",
        modules=("meta",),
    ),
    BuildStage(
        stage=10,
        name="Monitoring + Operator UI",
        description="Supervision operateur verrouillee + Build-9X gouverne + scaffolds replay/import minimaux",
        modules=(
            "calibration_methods",
            "local_replay_runtime",
            "backtest_artifact_import",
            "meta_learning",
            "monitoring",
            "ui",
        ),
    ),
    BuildStage(
        stage=11,
        name="Shadow Runtime",
        description="Validation Shadow gouvernee sur le rail runtime actif complet, sans capital; Build-12 Micro-live puis Build-13 Live ouvrent ensuite dans le meme module",
        modules=("secrets_manager", "alerting", "venue_adapters", "protocols"),
    ),
    BuildStage(
        stage=12,
        name="Micro-live",
        description="Validation Micro-live gouvernee sur le rail runtime actif complet, avec capital reel ultra-prudent; Build-13 Live reste ensuite gouverne et distinct",
        modules=("protocols",),
    ),
    BuildStage(
        stage=13,
        name="Live-Light",
        description="Premiere execution reelle minimale et gouvernee sur le rail runtime actif complet, sans ouvrir l'extension gouvernee",
        modules=("protocols",),
    ),
    BuildStage(
        stage=14,
        name="Governed Enablers",
        description="Enrichissements sans casser le rail gouverne courant",
        modules=("complete_enablers",),
    ),
    BuildStage(
        stage=15,
        name="Engine C",
        description="Breakout Continuation (governed extension)",
        modules=("engine_c",),
    ),
    BuildStage(
        stage=16,
        name="Engine D",
        description="Re-entry / Second Chance (governed extension)",
        modules=("engine_d",),
    ),
    BuildStage(
        stage=17,
        name="UI Complete + Live-Complete",
        description="Extension finale: UI operateur et protocole live gouverne etendu",
        modules=("ui", "protocols"),
    ),
)

_STAGE_MAP: dict[int, BuildStage] = {s.stage: s for s in BUILD_STAGES}


# ─── QUERY HELPERS ────────────────────────────────────────────────────


def get_build_stage(stage: int) -> BuildStage | None:
    """Get a build stage by number."""
    return _STAGE_MAP.get(stage)


def get_all_stages() -> tuple[BuildStage, ...]:
    """Return all build stages in order."""
    return BUILD_STAGES


def get_modules_in_order() -> tuple[ModuleEntry, ...]:
    """Return all modules sorted by build_stage then by declaration order."""
    return tuple(sorted(MODULES, key=lambda m: m.build_stage))


def get_next_stage(current: int) -> BuildStage | None:
    """Return the next build stage after `current`."""
    stages = sorted(_STAGE_MAP.keys())
    for s in stages:
        if s > current:
            return _STAGE_MAP[s]
    return None


def get_prerequisite_modules(module_name: str) -> tuple[str, ...]:
    """Return all modules from earlier build stages (prerequisites)."""
    target = next((m for m in MODULES if m.module_name == module_name), None)
    if target is None:
        return ()
    return tuple(
        m.module_name for m in MODULES if m.build_stage < target.build_stage
    )


def validate_build_order_coherent() -> list[str]:
    """Check that every module in BUILD_STAGES exists in inventory. Returns unknowns."""
    from manifest_registry.module_inventory import get_module_names

    known = get_module_names()
    errors: list[str] = []
    for stage in BUILD_STAGES:
        for mod in stage.modules:
            if mod not in known:
                errors.append(f"Stage {stage.stage}: unknown module '{mod}'")
    return errors


def validate_modules_have_stages() -> list[str]:
    """Check that every inventory module appears in at least one build stage. Returns missing."""
    declared: set[str] = set()
    for stage in BUILD_STAGES:
        declared.update(stage.modules)
    from manifest_registry.module_inventory import get_module_names

    known = get_module_names()
    return sorted(known - declared)
