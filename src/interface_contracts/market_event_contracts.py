"""
V5.3 — MARKET_EVENT_CONTRACTS
Version contrat : 1.0.0
Structures de données de marché normalisées.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from .domain_types import Side, Timeframe, TimestampedModel


class TradeEvent(TimestampedModel):
    """Trade individuel observé sur l'exchange."""
    pair: str = Field(..., description="Symbole paire")
    price: float = Field(..., description="Prix USDT", gt=0)
    quantity: float = Field(..., description="Quantité base", gt=0)
    side: Side = Field(..., description="Direction taker")
    trade_id: str = Field(..., description="ID trade exchange", min_length=1)
    is_maker: bool = Field(default=False)

    @property
    def notional_usdt(self) -> float:
        return self.price * self.quantity


class DepthLevel(BaseModel):
    """Niveau de profondeur dans le carnet d'ordres."""
    price: float = Field(..., gt=0)
    quantity: float = Field(..., ge=0)
    model_config = {"frozen": True}


class DepthEvent(TimestampedModel):
    """Snapshot du carnet d'ordres."""
    pair: str = Field(...)
    bids: list[DepthLevel] = Field(..., min_length=1)
    asks: list[DepthLevel] = Field(..., min_length=1)
    last_update_id: Optional[int] = Field(default=None)

    @field_validator("bids")
    @classmethod
    def validate_bids_order(cls, v: list[DepthLevel]) -> list[DepthLevel]:
        for i in range(len(v) - 1):
            if v[i].price < v[i + 1].price:
                raise ValueError("Bids doivent être triés décroissant par prix")
        return v

    @field_validator("asks")
    @classmethod
    def validate_asks_order_and_no_cross(cls, v: list[DepthLevel], info: ValidationInfo) -> list[DepthLevel]:
        """Validate asks sorted ascending + GEM-01: reject crossed book."""
        for i in range(len(v) - 1):
            if v[i].price > v[i + 1].price:
                raise ValueError("Asks doivent être triés croissant par prix")
        # GEM-01: crossed book guard
        data = info.data
        if "bids" in data and data["bids"] and v:
            best_bid = data["bids"][0].price
            best_ask = v[0].price
            if best_bid > best_ask:
                raise ValueError(
                    f"Crossed book: best_bid ({best_bid}) > best_ask ({best_ask})"
                )
        return v

    @property
    def best_bid(self) -> float:
        return self.bids[0].price

    @property
    def best_ask(self) -> float:
        return self.asks[0].price

    @property
    def spread_bps(self) -> float:
        mid = (self.best_bid + self.best_ask) / 2.0
        if mid == 0:
            return 0.0
        return ((self.best_ask - self.best_bid) / mid) * 10_000


class KlineEvent(TimestampedModel):
    """Bougie OHLCV."""
    pair: str = Field(...)
    timeframe: Timeframe = Field(...)
    open_price: float = Field(..., gt=0)
    high_price: float = Field(..., gt=0)
    low_price: float = Field(..., gt=0)
    close_price: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    close_time_ms: Optional[int] = Field(default=None)
    trade_count: Optional[int] = Field(default=None, ge=0)
    is_closed: bool = Field(default=False)

    @field_validator("high_price")
    @classmethod
    def validate_high(cls, v: float, info: ValidationInfo) -> float:
        data = info.data
        if "open_price" in data and v < data["open_price"]:
            raise ValueError(f"high_price ({v}) < open_price ({data['open_price']})")
        if "low_price" in data and v < data["low_price"]:
            raise ValueError(f"high_price ({v}) < low_price ({data['low_price']})")
        return v

    @field_validator("low_price")
    @classmethod
    def validate_low(cls, v: float, info: ValidationInfo) -> float:
        data = info.data
        if "open_price" in data and v > data["open_price"]:
            raise ValueError(f"low_price ({v}) > open_price ({data['open_price']})")
        return v

    @property
    def notional_volume_usdt(self) -> float:
        return self.volume * self.close_price

    @property
    def body_ratio(self) -> float:
        total_range = self.high_price - self.low_price
        if total_range == 0:
            return 0.0
        return abs(self.close_price - self.open_price) / total_range


class HeartbeatEvent(TimestampedModel):
    """Signal de vie d'un flux de données."""
    source: str = Field(..., min_length=1)
    pair: Optional[str] = Field(default=None)
    latency_ms: Optional[int] = Field(default=None, ge=0)


class SnapshotEvent(TimestampedModel):
    """Snapshot complet état marché d'une paire."""
    pair: str = Field(...)
    last_price: float = Field(..., gt=0)
    bid: float = Field(..., gt=0)
    ask: float = Field(..., gt=0)
    volume_24h: float = Field(..., ge=0)
    high_24h: Optional[float] = Field(default=None, gt=0)
    low_24h: Optional[float] = Field(default=None, gt=0)
    funding_rate: Optional[float] = Field(default=None)

    @field_validator("ask")
    @classmethod
    def validate_spread(cls, v: float, info: ValidationInfo) -> float:
        data = info.data
        if "bid" in data and v < data["bid"]:
            raise ValueError(f"ask ({v}) < bid ({data['bid']})")
        return v

    @property
    def spread_bps(self) -> float:
        mid = (self.bid + self.ask) / 2.0
        if mid == 0:
            return 0.0
        return ((self.ask - self.bid) / mid) * 10_000


__all__ = ["TradeEvent", "DepthLevel", "DepthEvent", "KlineEvent", "HeartbeatEvent", "SnapshotEvent"]
