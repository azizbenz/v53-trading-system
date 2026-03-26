"""
V5.3 — DECISION_CONTRACTS
Version contrat : 1.0.0
Structures de décision: signal → score → risk → execution → portfolio.
"""
from __future__ import annotations
from enum import Enum, unique
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from .domain_types import EngineId, RegimeId, Side, TimestampedModel


@unique
class SignalType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"

@unique
class BlockReason(str, Enum):
    DATA_STALE = "data_stale"
    PAIR_SUSPENDED = "pair_suspended"
    BUDGET_EXCEEDED = "budget_exceeded"
    CLUSTER_BREACH = "cluster_breach"
    BTC_FACTOR_BREACH = "btc_factor_breach"
    SPREAD_TOO_WIDE = "spread_too_wide"
    REGIME_HOSTILE = "regime_hostile"
    ENGINE_DISABLED = "engine_disabled"
    PROFILE_MISMATCH = "profile_mismatch"
    COOLDOWN_ACTIVE = "cooldown_active"
    MAX_POSITIONS_REACHED = "max_positions_reached"

@unique
class RiskVerdict(str, Enum):
    APPROVED = "approved"
    REDUCED = "reduced"
    HARD_BLOCKED = "hard_blocked"

@unique
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

@unique
class PortfolioAction(str, Enum):
    ACCEPT = "accept"
    DEFER = "defer"
    REJECT = "reject"
    REPLACE = "replace"


class SignalCandidate(TimestampedModel):
    """Signal brut émis par un moteur."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    signal_type: SignalType = Field(...)
    side: Side = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    regime: RegimeId = Field(...)
    entry_price: float = Field(..., gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    max_hold_ms: Optional[int] = Field(default=None, gt=0)
    reason: Optional[str] = Field(default=None)

    @property
    def expected_risk_reward(self) -> Optional[float]:
        if self.stop_loss is None or self.take_profit is None:
            return None
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        if risk == 0:
            return None
        return reward / risk


class PenaltyDetail(BaseModel):
    """Détail d'une pénalité soft."""
    name: str = Field(..., min_length=1)
    value: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., min_length=1)
    model_config = {"frozen": True}


class ScorePayload(TimestampedModel):
    """Score composite d'un signal."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    raw_score: float = Field(..., ge=0.0, le=1.0)
    penalty_total: float = Field(..., ge=0.0, le=1.0)
    final_score: float = Field(..., ge=0.0, le=1.0)
    rank: int = Field(..., ge=1)
    hard_blocked: bool = Field(...)
    penalties: list[PenaltyDetail] = Field(default_factory=list)
    block_reasons: list[BlockReason] = Field(default_factory=list)
    estimated_cost_bps: Optional[float] = Field(default=None, ge=0.0)


class RiskDecision(TimestampedModel):
    """Verdict du module risque."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    verdict: RiskVerdict = Field(...)
    requested_size: float = Field(..., gt=0)
    approved_size: float = Field(..., ge=0)
    exposure_used_pct: float = Field(..., ge=0.0, le=100.0)
    loss_budget_used_pct: float = Field(..., ge=0.0, le=100.0)
    block_reasons: list[BlockReason] = Field(default_factory=list)
    btc_beta: Optional[float] = Field(default=None)
    cluster_exposure: Optional[float] = Field(default=None, ge=0.0)

    @field_validator("approved_size")
    @classmethod
    def validate_approved_size(cls, v: float, info) -> float:
        data = info.data
        if "requested_size" in data and v > data["requested_size"]:
            raise ValueError(f"approved_size ({v}) > requested_size ({data['requested_size']})")
        if "verdict" in data and data["verdict"] == RiskVerdict.HARD_BLOCKED and v != 0:
            raise ValueError("approved_size doit être 0 si HARD_BLOCKED")
        return v


class ExecutionIntent(TimestampedModel):
    """Intention d'exécution validée."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    side: Side = Field(...)
    size: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    order_type: str = Field(..., pattern="^(limit|market)$")
    status: ExecutionStatus = Field(...)
    order_id: Optional[str] = Field(default=None)
    filled_size: Optional[float] = Field(default=None, ge=0)
    filled_price: Optional[float] = Field(default=None, gt=0)
    fill_latency_ms: Optional[int] = Field(default=None, ge=0)
    execution_cost_bps: Optional[float] = Field(default=None, ge=0)

    @property
    def fill_ratio(self) -> Optional[float]:
        if self.filled_size is None:
            return None
        return self.filled_size / self.size

    @property
    def slippage_bps(self) -> Optional[float]:
        if self.filled_price is None:
            return None
        return abs(self.filled_price - self.target_price) / self.target_price * 10_000


class PortfolioDecision(TimestampedModel):
    """Décision finale du portfolio manager."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    action: PortfolioAction = Field(...)
    score_rank: int = Field(..., ge=1)
    reason: Optional[str] = Field(default=None)
    replaced_by: Optional[str] = Field(default=None)
    deferred_until_ms: Optional[int] = Field(default=None)


__all__ = [
    "SignalType", "BlockReason", "RiskVerdict", "ExecutionStatus", "PortfolioAction",
    "SignalCandidate", "PenaltyDetail", "ScorePayload", "RiskDecision",
    "ExecutionIntent", "PortfolioDecision",
]
