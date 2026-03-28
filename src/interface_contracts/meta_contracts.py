"""
V5.3 — META_CONTRACTS
Version contrat : 1.0.0
Objets d'observabilité et de diagnostic.
"""
from __future__ import annotations
from enum import Enum, unique
from typing import Optional
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from .domain_types import EngineId, RegimeId, TimestampedModel


@unique
class PairHealthLevel(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    SUSPENDED = "suspended"
    OFFLINE = "offline"

@unique
class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"

@unique
class AlertCategory(str, Enum):
    DATA = "data"
    EXECUTION = "execution"
    RISK = "risk"
    ENGINE = "engine"
    INFRA = "infra"
    COST = "cost"
    RECONCILIATION = "reconciliation"

@unique
class DTROutcome(str, Enum):
    PROFIT = "profit"
    LOSS = "loss"
    BREAK_EVEN = "break_even"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PHANTOM = "phantom"


class DTRRecord(TimestampedModel):
    """Decision Trail Record — traçabilité complète."""
    dtr_id: str = Field(..., min_length=1)
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    regime: RegimeId = Field(...)
    signal_confidence: float = Field(..., ge=0.0, le=1.0)
    raw_score: float = Field(..., ge=0.0, le=1.0)
    final_score: float = Field(..., ge=0.0, le=1.0)
    hard_blocked: bool = Field(...)
    risk_verdict: str = Field(...)
    outcome: DTROutcome = Field(...)
    entry_price: Optional[float] = Field(default=None, gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    pnl_usdt: Optional[float] = Field(default=None)
    cost_total_bps: Optional[float] = Field(default=None, ge=0)
    hold_duration_ms: Optional[int] = Field(default=None, ge=0)
    block_reasons: list[str] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)

    @property
    def is_phantom(self) -> bool:
        return self.outcome == DTROutcome.PHANTOM

    @property
    def net_pnl_usdt(self) -> Optional[float]:
        if self.pnl_usdt is None or self.entry_price is None or self.cost_total_bps is None:
            return None
        cost_usdt = self.entry_price * (self.cost_total_bps / 10_000)
        return self.pnl_usdt - cost_usdt


class PairHealthStatus(TimestampedModel):
    """État de santé d'une paire."""
    pair: str = Field(...)
    health: PairHealthLevel = Field(...)
    freshness_ms: int = Field(..., ge=0)
    stale_count_5m: int = Field(..., ge=0)
    consistency_ok: bool = Field(...)
    ws_connected: Optional[bool] = Field(default=None)
    last_trade_ms: Optional[int] = Field(default=None)
    backlog_depth: Optional[int] = Field(default=None, ge=0)
    error_rate_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class CostRecord(TimestampedModel):
    """Enregistrement de coût d'exécution."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    fee_bps: float = Field(..., ge=0)
    spread_cost_bps: float = Field(..., ge=0)
    slippage_bps: float = Field(..., ge=0)
    total_cost_bps: float = Field(..., ge=0)
    notional_usdt: float = Field(..., gt=0)
    expected_cost_bps: Optional[float] = Field(default=None, ge=0)
    cost_surprise_bps: Optional[float] = Field(default=None)

    @field_validator("total_cost_bps")
    @classmethod
    def validate_total_cost(cls, v: float, info: ValidationInfo) -> float:
        data = info.data
        if all(k in data for k in ("fee_bps", "spread_cost_bps", "slippage_bps")):
            expected = data["fee_bps"] + data["spread_cost_bps"] + data["slippage_bps"]
            if abs(v - expected) > 0.01:
                raise ValueError(f"total_cost_bps ({v}) != fee+spread+slippage ({expected})")
        return v


class EdgeEstimate(TimestampedModel):
    """Estimation de l'edge net."""
    pair: str = Field(...)
    engine_id: EngineId = Field(...)
    gross_edge_bps: float = Field(...)
    cost_drag_bps: float = Field(..., ge=0)
    net_edge_bps: float = Field(...)
    sample_size: int = Field(..., gt=0)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    win_rate: Optional[float] = Field(default=None, ge=0, le=1)
    profit_factor: Optional[float] = Field(default=None, ge=0)
    ce_ratio: Optional[float] = Field(default=None)

    @field_validator("net_edge_bps")
    @classmethod
    def validate_net_edge(cls, v: float, info: ValidationInfo) -> float:
        data = info.data
        if "gross_edge_bps" in data and "cost_drag_bps" in data:
            expected = data["gross_edge_bps"] - data["cost_drag_bps"]
            if abs(v - expected) > 0.01:
                raise ValueError(f"net_edge_bps ({v}) != gross - cost ({expected})")
        return v


class AlertRecord(TimestampedModel):
    """Alerte système."""
    alert_id: str = Field(..., min_length=1)
    severity: AlertSeverity = Field(...)
    category: AlertCategory = Field(...)
    message: str = Field(..., min_length=1)
    pair: Optional[str] = Field(default=None)
    engine_id: Optional[EngineId] = Field(default=None)
    module: Optional[str] = Field(default=None)
    resolved: bool = Field(default=False)
    resolved_ms: Optional[int] = Field(default=None)


__all__ = [
    "PairHealthLevel", "AlertSeverity", "AlertCategory", "DTROutcome",
    "DTRRecord", "PairHealthStatus", "CostRecord", "EdgeEstimate", "AlertRecord",
]
