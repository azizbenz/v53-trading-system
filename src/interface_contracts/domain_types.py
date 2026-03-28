"""
V5.3 — DOMAIN_TYPES
=====================
Sous-composant : interface_contracts.domain_types
Version contrat : 1.0.0

Rôle : Définir les types métier élémentaires utilisés dans tout le système.
Aucune logique métier, aucun état mutable, aucune dépendance externe.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum, unique
from typing import NewType

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════
# ENUMS CANONIQUES
# ═══════════════════════════════════════════════════════════════

@unique
class EngineId(str, Enum):
    """Moteurs de trading V5.3. Light = A+B, Complete = A+B+C+D."""
    A = "engine_a"
    B = "engine_b"
    C = "engine_c"
    D = "engine_d"


@unique
class RegimeId(str, Enum):
    """Régimes de marché détectés par le système."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    UNKNOWN = "unknown"


@unique
class ProfileId(str, Enum):
    """Profil d'activation système."""
    LIGHT = "light"
    COMPLETE = "complete"


@unique
class RuntimeMode(str, Enum):
    """Modes d'exÃ©cution autorisÃ©s pour l'unique V5.3."""
    LOCAL_REPLAY = "local_replay"
    SHADOW = "shadow"
    MICRO_LIVE = "micro_live"
    LIVE = "live"


@unique
class StrategyClassification(str, Enum):
    """Taxonomie canonique d'onboarding des stratÃ©gies V5.3."""
    A_VARIANT = "a_variant"
    B_VARIANT = "b_variant"
    BUILD14_ENABLER = "build14_enabler"
    C_CANDIDATE = "c_candidate"
    D_CANDIDATE = "d_candidate"
    OUT_OF_SCOPE_FOR_V5_3 = "out_of_scope_for_v5_3"


@unique
class PromotionState(str, Enum):
    """Ã‰tat de promotion d'une amÃ©lioration gouvernÃ©e."""
    DRAFT = "draft"
    REPLAY_ONLY = "replay_only"
    VPS_IMPORTED = "vps_imported"
    SHADOW_CANDIDATE = "shadow_candidate"
    MICRO_LIVE_CANDIDATE = "micro_live_candidate"
    LIVE_CANDIDATE = "live_candidate"
    REJECTED = "rejected"


@unique
class ReviewState(str, Enum):
    """Ã‰tat de revue humaine des bundles et hypothÃ¨ses."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


@unique
class DeploymentState(str, Enum):
    """État de déploiement du système ou d'un module."""
    OFFLINE = "offline"
    BOOTSTRAP = "bootstrap"
    SHADOW = "shadow"
    MICRO_LIVE = "micro_live"
    LIVE_LIGHT = "live_light"
    LIVE_COMPLETE = "live_complete"
    DEGRADED = "degraded"
    HALTED = "halted"
    ROLLBACK = "rollback"


@unique
class ModuleLayer(str, Enum):
    """Couche architecturale d'un module dans le DAG."""
    CONTRACTS = "contracts"
    DATA = "data"
    EXECUTION = "execution"
    RISK = "risk"
    SCORING = "scoring"
    ENGINE = "engine"
    PORTFOLIO = "portfolio"
    META = "meta"
    MONITORING = "monitoring"
    UI = "ui"
    PROTOCOL = "protocol"


@unique
class ModuleStatus(str, Enum):
    """Statut d'un module dans le manifest."""
    ACTIVE = "active"
    PLANNED = "planned"
    ARCHIVED = "archived"
    FORBIDDEN = "forbidden"


@unique
class Tier(int, Enum):
    """Tier de liquidité d'une paire."""
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


@unique
class Side(str, Enum):
    """Direction d'un ordre."""
    BUY = "buy"
    SELL = "sell"


@unique
class Timeframe(str, Enum):
    """Fenêtres temporelles supportées pour klines."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


# ═══════════════════════════════════════════════════════════════
# VALUE OBJECTS
# ═══════════════════════════════════════════════════════════════

TradeId = NewType("TradeId", str)
OrderId = NewType("OrderId", str)
RunId = NewType("RunId", str)


# ═══════════════════════════════════════════════════════════════
# CONSTANTES PAIRES
# ═══════════════════════════════════════════════════════════════

LIGHT_PAIRS: frozenset[str] = frozenset({
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT"
})

COMPLETE_ADDITIONAL_PAIRS: frozenset[str] = frozenset({
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "ATOMUSDT", "NEARUSDT"
})

ALL_PAIRS: frozenset[str] = LIGHT_PAIRS | COMPLETE_ADDITIONAL_PAIRS

PAIR_TIER_MAP: dict[str, Tier] = {
    "BTCUSDT": Tier.TIER_1, "ETHUSDT": Tier.TIER_1,
    "BNBUSDT": Tier.TIER_2, "SOLUSDT": Tier.TIER_2,
    "XRPUSDT": Tier.TIER_2, "LINKUSDT": Tier.TIER_2,
    "ADAUSDT": Tier.TIER_2, "AVAXUSDT": Tier.TIER_2,
    "DOTUSDT": Tier.TIER_2, "MATICUSDT": Tier.TIER_2,
    "ATOMUSDT": Tier.TIER_2, "NEARUSDT": Tier.TIER_2,
}

ENGINE_PAIR_MAP: dict[EngineId, frozenset[str]] = {
    EngineId.A: frozenset({"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT"}),
    EngineId.B: frozenset({"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT"}),
    EngineId.C: ALL_PAIRS,
    EngineId.D: ALL_PAIRS,
}


# ═══════════════════════════════════════════════════════════════
# PAIR ID
# ═══════════════════════════════════════════════════════════════

class PairId(BaseModel):
    """Identifiant canonique d'une paire de trading."""
    symbol: str = Field(..., description="Symbole canonique, ex: BTCUSDT", min_length=5, max_length=20)
    tier: Tier = Field(..., description="Tier de liquidité")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ALL_PAIRS:
            raise ValueError(f"Paire '{v}' non autorisée. Autorisées: {sorted(ALL_PAIRS)}")
        return v

    @classmethod
    def from_symbol(cls, symbol: str) -> "PairId":
        symbol = symbol.upper().strip()
        if symbol not in PAIR_TIER_MAP:
            raise ValueError(f"Paire '{symbol}' inconnue du PAIR_TIER_MAP")
        return cls(symbol=symbol, tier=PAIR_TIER_MAP[symbol])

    def is_light(self) -> bool:
        return self.symbol in LIGHT_PAIRS

    model_config = {"frozen": True}


# ═══════════════════════════════════════════════════════════════
# TIMESTAMP MIXIN
# ═══════════════════════════════════════════════════════════════

class TimestampedModel(BaseModel):
    """Base pour tout objet nécessitant un timestamp."""
    timestamp_ms: int = Field(..., description="Timestamp ms epoch UTC", ge=1_000_000_000_000, le=9_999_999_999_999)

    @property
    def timestamp_dt(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp_ms / 1000.0, tz=UTC)

    model_config = {"frozen": True}


# ═══════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════

__all__ = [
    "EngineId", "RegimeId", "ProfileId", "RuntimeMode", "StrategyClassification",
    "PromotionState", "ReviewState", "DeploymentState", "ModuleLayer",
    "ModuleStatus", "Tier", "Side", "Timeframe",
    "TradeId", "OrderId", "RunId",
    "PairId", "TimestampedModel",
    "LIGHT_PAIRS", "COMPLETE_ADDITIONAL_PAIRS", "ALL_PAIRS",
    "PAIR_TIER_MAP", "ENGINE_PAIR_MAP",
]
