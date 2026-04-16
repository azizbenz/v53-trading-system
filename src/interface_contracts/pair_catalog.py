"""Venue-specific market filter specifications for the 7 V5.3 canonical pairs.

Each `PairEntry` holds the Binance exchangeInfo filter values needed for
correct order sizing and placement (tick_size, step_size, min_notional).

These defaults are the canonical V5.3 values.  In production they MUST be
refreshed at bootstrap via ``BinanceRestClient.get_exchange_info()`` so that
any Binance-side filter change is picked up without a code deploy.

Usage pattern
-------------
At bootstrap:
    catalog = PairCatalog.from_exchange_info(exchange_info)

At order construction:
    entry = V53_PAIR_CATALOG.get("BTCUSDT")   # or catalog.get(...)
    quantized_qty = quantize_down_to_step(qty, Decimal(entry.step_size))
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from .binance_contracts import BinanceExchangeInfo


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class PairEntry(BaseModel, frozen=True):
    """Binance Spot filter spec for one canonical pair."""

    symbol: str = Field(..., min_length=5, max_length=20)
    tick_size: str = Field(..., min_length=1, description="PRICE_FILTER tickSize")
    step_size: str = Field(..., min_length=1, description="LOT_SIZE stepSize")
    min_notional: str = Field(..., min_length=1, description="MIN_NOTIONAL / NOTIONAL minNotional")
    min_qty: str = Field(default="0", min_length=1, description="LOT_SIZE minQty")

    @model_validator(mode="after")
    def _validate_positive_decimals(self) -> "PairEntry":
        # tick_size, step_size, min_notional must be strictly positive.
        # min_qty is allowed to be "0" (Binance uses 0 to mean "no minimum").
        for field_name in ("tick_size", "step_size", "min_notional"):
            raw = getattr(self, field_name)
            try:
                value = Decimal(raw)
            except Exception as exc:
                raise ValueError(f"{field_name}={raw!r} is not a valid decimal") from exc
            if value <= Decimal(0):
                raise ValueError(f"{field_name}={raw!r} must be > 0")
        # min_qty: must be a valid decimal and >= 0
        try:
            min_qty_val = Decimal(self.min_qty)
        except Exception as exc:
            raise ValueError(f"min_qty={self.min_qty!r} is not a valid decimal") from exc
        if min_qty_val < Decimal(0):
            raise ValueError(f"min_qty={self.min_qty!r} must be >= 0")
        return self


class PairCatalog(BaseModel, frozen=True):
    """Immutable catalog of venue filter specs for the 7 V5.3 canonical pairs."""

    entries: tuple[PairEntry, ...] = Field(..., min_length=1)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, symbol: str) -> PairEntry | None:
        """Return the PairEntry for *symbol* (case-insensitive), or None."""
        upper = symbol.upper()
        for entry in self.entries:
            if entry.symbol == upper:
                return entry
        return None

    def require(self, symbol: str) -> PairEntry:
        """Return the PairEntry for *symbol* or raise ``KeyError``."""
        entry = self.get(symbol)
        if entry is None:
            raise KeyError(
                f"Symbol {symbol!r} not found in PairCatalog "
                f"(known: {[e.symbol for e in self.entries]})"
            )
        return entry

    @property
    def symbols(self) -> frozenset[str]:
        return frozenset(e.symbol for e in self.entries)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_exchange_info(cls, exchange_info: BinanceExchangeInfo) -> "PairCatalog":
        """Build a PairCatalog from live Binance exchangeInfo.

        Only the 7 canonical V5.3 pairs are extracted.  If any pair is
        absent from the exchangeInfo the corresponding entry from
        ``V53_PAIR_CATALOG`` (the static default) is kept as fallback.
        """
        live_entries: dict[str, PairEntry] = {}
        for sym_info in exchange_info.symbols:
            symbol = sym_info.symbol.upper()
            if symbol not in _V53_CANONICAL_SYMBOLS:
                continue
            # Parse filter fields from BinanceSymbolInfo — these are already
            # normalised strings by the REST client.
            entry = PairEntry(
                symbol=symbol,
                tick_size=sym_info.tick_size or "0.01",
                step_size=sym_info.step_size or "0.00001",
                min_notional=sym_info.min_notional or "5",
                min_qty="0",  # min_qty not yet in BinanceSymbolInfo; extend when needed
            )
            live_entries[symbol] = entry

        # Merge: live overrides static defaults; fall back to static if missing
        merged = []
        for entry in V53_PAIR_CATALOG.entries:
            merged.append(live_entries.get(entry.symbol, entry))
        return cls(entries=tuple(merged))


# ---------------------------------------------------------------------------
# Canonical 7-pair static defaults (valid as of 2026-04)
# These are conservative defaults only — always refresh from exchangeInfo.
# ---------------------------------------------------------------------------

_V53_CANONICAL_SYMBOLS: frozenset[str] = frozenset({
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
    "LINKUSDT", "BNBUSDT", "ADAUSDT",
})

V53_PAIR_CATALOG: PairCatalog = PairCatalog(
    entries=(
        PairEntry(
            symbol="BTCUSDT",
            tick_size="0.01",
            step_size="0.00001",
            min_notional="5",
            min_qty="0.00001",
        ),
        PairEntry(
            symbol="ETHUSDT",
            tick_size="0.01",
            step_size="0.0001",
            min_notional="5",
            min_qty="0.0001",
        ),
        PairEntry(
            symbol="SOLUSDT",
            tick_size="0.01",
            step_size="0.001",
            min_notional="5",
            min_qty="0.001",
        ),
        PairEntry(
            symbol="XRPUSDT",
            tick_size="0.0001",
            step_size="0.1",
            min_notional="5",
            min_qty="0.1",
        ),
        PairEntry(
            symbol="LINKUSDT",
            tick_size="0.001",
            step_size="0.01",
            min_notional="5",
            min_qty="0.01",
        ),
        PairEntry(
            symbol="BNBUSDT",
            tick_size="0.01",
            step_size="0.001",
            min_notional="5",
            min_qty="0.001",
        ),
        PairEntry(
            symbol="ADAUSDT",
            tick_size="0.0001",
            step_size="0.1",
            min_notional="5",
            min_qty="0.1",
        ),
    )
)


__all__ = [
    "PairEntry",
    "PairCatalog",
    "V53_PAIR_CATALOG",
]
