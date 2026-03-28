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
        ),
    ),
    BuildStage(
        stage=2,
        name="Data Backbone",
        description="Ingestion WS, normalisation, qualite data, sante paire",
        modules=("data_backbone",),
    ),
    BuildStage(
        stage=3,
        name="Execution Backbone",
        description="Execution, couts reels, reconciliation",
        modules=("execution_backbone",),
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
        name="Monitoring + UI Light",
        description="Supervision verrouillee + Build-9X gouverne + scaffolds replay/import minimaux",
        modules=(
            "local_replay_runtime",
            "backtest_artifact_import",
            "meta_learning",
            "monitoring",
            "ui",
        ),
    ),
    BuildStage(
        stage=11,
        name="Shadow Light",
        description="Validation Shadow gouvernee sans capital; Build-12 Micro-live puis Build-13 Live-Light ouvrent ensuite dans le meme module",
        modules=("protocols",),
    ),
    BuildStage(
        stage=12,
        name="Micro-live Light",
        description="Validation gouvernee avec capital reel ultra-prudent, budget micro et probes minimaux; Build-13 Live-Light reste ensuite gouverne et distinct",
        modules=("protocols",),
    ),
    BuildStage(
        stage=13,
        name="Live-Light",
        description="Premiere execution reelle minimale et gouvernee en profil Light, sans ouvrir Complete",
        modules=("protocols",),
    ),
    BuildStage(
        stage=14,
        name="Complete Enablers",
        description="Enrichissements sans casser Light",
        modules=("complete_enablers",),
    ),
    BuildStage(
        stage=15,
        name="Engine C",
        description="Breakout Continuation (Complete only)",
        modules=("engine_c",),
    ),
    BuildStage(
        stage=16,
        name="Engine D",
        description="Re-entry / Second Chance (Complete only)",
        modules=("engine_d",),
    ),
    BuildStage(
        stage=17,
        name="UI Complete + Live-Complete",
        description="Extension finale: UI Complete et protocole Live-Complete",
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
