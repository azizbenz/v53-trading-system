"""
V5.3 — INTERFACE_CONTRACTS
===========================
Module Build-1 / Étape 1 — P0 absolue

Mission : Fournir le langage officiel de communication entre modules.
- Types métier stables et versionnés
- Structures d'événements, signaux, décisions, ordres, métriques
- Erreurs métier standardisées
- Invariants contractuels testables

Ce module NE DOIT PAS :
- Contenir de logique métier
- Importer des implémentations concrètes
- Gérer le runtime
- Effectuer des calculs d'edge
"""

__contract_version__ = "1.0.0"

from .domain_types import *
from .market_event_contracts import *
from .decision_contracts import *
from .meta_contracts import *
from .error_contracts import *
from .operator_contracts import *

__all__ = [
    # domain_types — Enums
    "EngineId", "RegimeId", "ProfileId", "RuntimeMode", "StrategyClassification",
    "PromotionState", "ReviewState", "Tier", "Timeframe", "Side",
    "ModuleLayer", "ModuleStatus", "SignalType", "PairHealthLevel",
    "ExecutionStatus", "RiskVerdict", "DeploymentState",
    # domain_types — Pairs
    "LIGHT_PAIRS", "COMPLETE_ADDITIONAL_PAIRS", "ALL_PAIRS",
    "ENGINE_PAIR_MAP", "PAIR_TIER_MAP",
    # domain_types — NewTypes & base
    "PairId", "OrderId", "TradeId", "RunId", "TimestampedModel",
    # market_event_contracts
    "KlineEvent", "TradeEvent", "DepthLevel", "DepthEvent",
    "SnapshotEvent", "HeartbeatEvent",
    # decision_contracts
    "ScorePayload", "SignalCandidate", "EdgeEstimate",
    "ExecutionIntent", "RiskDecision", "PortfolioAction", "PortfolioDecision",
    "PairHealthStatus", "BlockReason",
    # meta_contracts
    "DTROutcome", "DTRRecord", "CostRecord", "PenaltyDetail", "AlertSeverity",
    "AlertCategory", "AlertRecord",
    # error_contracts
    "V53BaseError", "ContractViolationError", "DependencyViolationError",
    "DataStaleError", "RiskBudgetExceededError", "PairSuspendedError",
    "EngineNotAllowedError", "InvalidProfileActivationError",
    "ReconciliationError", "BootstrapError",
    # operator_contracts
    "OperatorSafingAction", "OperatorSafingRequest",
]
