"""
4.5.1 — Module Inventory: canonical table of all V5.3 modules.

Each module has: name, layer, owner, status, priority, profile_scope, build_stage.
This is the single source of truth for what exists in the system.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from interface_contracts.domain_types import ModuleLayer, ModuleStatus, ProfileId


class Priority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class Owner(StrEnum):
    CLAUDE = "claude"
    CHATGPT = "chatgpt"
    SHARED = "shared"


class ProfileScope(StrEnum):
    COMMON = "common"
    LIGHT = "light"
    COMPLETE = "complete"


class ModuleEntry(BaseModel, frozen=True):
    """Single module entry in the inventory."""

    module_name: str = Field(..., min_length=1)
    module_layer: ModuleLayer
    owner: Owner
    status: ModuleStatus
    priority: Priority
    profile_scope: ProfileScope
    build_stage: int = Field(..., ge=0, le=17)
    description: str = Field(default="")


# ─── CANONICAL MODULE TABLE ───────────────────────────────────────────

MODULES: tuple[ModuleEntry, ...] = (
    # ── Build-1: Dependency Architecture ──
    ModuleEntry(
        module_name="interface_contracts",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Langage commun: types, contrats, erreurs",
    ),
    ModuleEntry(
        module_name="manifest_registry",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Registre unique des modules et dépendances",
    ),
    ModuleEntry(
        module_name="dag_validator",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Validateur de dépendances et cycles",
    ),
    ModuleEntry(
        module_name="contract_test_suite",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Tests de contrat par module",
    ),
    ModuleEntry(
        module_name="smoke_bootstrap_recovery",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Bootstrap et recovery propres",
    ),
    # ── Build-2: Data Backbone ──
    ModuleEntry(
        module_name="data_backbone",
        module_layer=ModuleLayer.DATA,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=2,
        description="Ingestion WS, normalisation, qualité data, santé paire",
    ),
    # ── Build-3: Execution Backbone ──
    ModuleEntry(
        module_name="execution_backbone",
        module_layer=ModuleLayer.EXECUTION,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=3,
        description="Exécution, coûts réels, réconciliation",
    ),
    # ── Build-4: Risk Backbone ──
    ModuleEntry(
        module_name="risk_backbone",
        module_layer=ModuleLayer.RISK,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=4,
        description="Budgets risque, exposition, corrélation, facteur BTC",
    ),
    # ── Build-5: Scoring Backbone ──
    ModuleEntry(
        module_name="scoring_backbone",
        module_layer=ModuleLayer.SCORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=5,
        description="Hard/soft/rank scoring pipeline",
    ),
    # ── Build-6: Engine A ──
    ModuleEntry(
        module_name="engine_a",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LIGHT,
        build_stage=6,
        description="Premium Trend / Expansion",
    ),
    # ── Build-7: Engine B ──
    ModuleEntry(
        module_name="engine_b",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LIGHT,
        build_stage=7,
        description="Mean Reversion Intraday",
    ),
    # ── Build-8: Portfolio Minimal ──
    ModuleEntry(
        module_name="portfolio",
        module_layer=ModuleLayer.PORTFOLIO,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LIGHT,
        build_stage=8,
        description="Sélection opportunités et allocation",
    ),
    # ── Build-9: Meta Minimal ──
    ModuleEntry(
        module_name="meta",
        module_layer=ModuleLayer.META,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LIGHT,
        build_stage=9,
        description="DTR, CRA, break-even, edge tracker",
    ),
    ModuleEntry(
        module_name="local_replay_runtime",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=10,
        description="Scaffold LOCAL_REPLAY unifie local/VPS, sans fork ni BACKTEST_PROFILE",
    ),
    ModuleEntry(
        module_name="backtest_artifact_import",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=10,
        description="Import artifact local->VPS gouverne, sans promotion implicite",
    ),
    ModuleEntry(
        module_name="meta_learning",
        module_layer=ModuleLayer.META,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.LIGHT,
        build_stage=10,
        description="Build-9X gouverne: diagnostics, hypotheses, candidats et exports de revue",
    ),
    # ── Build-10: Monitoring + locked operator UI (historical: Light UI) ──
    ModuleEntry(
        module_name="monitoring",
        module_layer=ModuleLayer.MONITORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LIGHT,
        build_stage=10,
        description="Métriques, alertes, dashboard backend pour la supervision opérateur verrouillée",
    ),
    ModuleEntry(
        module_name="ui",
        module_layer=ModuleLayer.UI,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.LIGHT,
        build_stage=10,
        description="UI opérateur verrouillée (surface historique: Light UI)",
    ),
    # ── Build-11/12/13: Governed protocols rail (historical labels kept) ──
    ModuleEntry(
        module_name="protocols",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LIGHT,
        build_stage=11,
        description="Build-11 Shadow, Build-12 Micro-live et Build-13 Live gouvernes sur le rail runtime actif COMPLETE; les labels Shadow Light / Micro-live Light / Live-Light restent historiques",
    ),
    # ── Build-14: Complete Enablers ──
    ModuleEntry(
        module_name="complete_enablers",
        module_layer=ModuleLayer.SCORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMPLETE,
        build_stage=14,
        description="Microstructure, régime, covariance enrichis",
    ),
    # ── Build-15: Engine C ──
    ModuleEntry(
        module_name="engine_c",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMPLETE,
        build_stage=15,
        description="Breakout Continuation",
    ),
    # ── Build-16: Engine D ──
    ModuleEntry(
        module_name="engine_d",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMPLETE,
        build_stage=16,
        description="Re-entry / Second Chance",
    ),
)


# ─── LOOKUP HELPERS ───────────────────────────────────────────────────

_MODULE_MAP: dict[str, ModuleEntry] = {m.module_name: m for m in MODULES}


def get_module(name: str) -> Optional[ModuleEntry]:
    """Get a module entry by name. Returns None if not found."""
    return _MODULE_MAP.get(name)


def get_all_modules() -> tuple[ModuleEntry, ...]:
    """Return the full canonical module list."""
    return MODULES


def get_modules_by_build(build_stage: int) -> tuple[ModuleEntry, ...]:
    """Return all modules belonging to a specific build stage."""
    return tuple(m for m in MODULES if m.build_stage == build_stage)


def get_modules_by_layer(layer: ModuleLayer) -> tuple[ModuleEntry, ...]:
    """Return all modules in a specific layer."""
    return tuple(m for m in MODULES if m.module_layer == layer)


def get_modules_by_status(status: ModuleStatus) -> tuple[ModuleEntry, ...]:
    """Return all modules with a given status."""
    return tuple(m for m in MODULES if m.status == status)


def get_modules_by_profile(scope: ProfileScope) -> tuple[ModuleEntry, ...]:
    """Return all modules for a given profile scope."""
    return tuple(m for m in MODULES if m.profile_scope == scope)


def get_module_names() -> frozenset[str]:
    """Return the set of all registered module names."""
    return frozenset(_MODULE_MAP.keys())


def validate_no_duplicates() -> bool:
    """Assert that no module name appears twice."""
    return len(MODULES) == len(_MODULE_MAP)
