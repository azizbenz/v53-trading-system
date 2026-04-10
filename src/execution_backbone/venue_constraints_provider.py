"""Optional venue-constraint providers for exchange-facing execution boundaries."""

from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol
from urllib.parse import urlencode
from urllib.request import urlopen

from pydantic import BaseModel, Field

from interface_contracts import decimal_to_canonical_str, execution_decimal
from interface_contracts.atomic_io import atomic_write_json

from .order_decider.intent_builder import VenueConstraintSnapshot


logger = logging.getLogger(__name__)

HttpGet = Callable[[str, float], bytes]


class VenueConstraintProvider(Protocol):
    """Optional metadata source for venue tick/step/min-notional constraints."""

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        ...


class VenueConstraintCacheEntry(BaseModel, frozen=True):
    """Audit-ready cached venue-constraint payload."""

    pair: str
    constraints: VenueConstraintSnapshot
    source: str = "binance_exchange_info"
    fetched_at: float


class VenueConstraintCacheState(BaseModel):
    """Persisted cache state for symbol venue constraints."""

    entries: dict[str, VenueConstraintCacheEntry] = Field(default_factory=dict)


def _default_http_get(url: str, timeout_s: float) -> bytes:
    with urlopen(url, timeout=timeout_s) as response:
        return response.read()


def _positive_decimal_str_or_none(value: object) -> str | None:
    if value in (None, "", "0", 0, 0.0):
        return None
    try:
        decimal_value = execution_decimal(value)
    except (ArithmeticError, TypeError, ValueError):
        return None
    if decimal_value <= 0:
        return None
    return decimal_to_canonical_str(decimal_value)


def parse_binance_exchange_info_payload(
    payload: Mapping[str, Any],
    *,
    pair: str,
) -> VenueConstraintSnapshot | None:
    """Parse Binance exchangeInfo payload into a normalized venue-constraint snapshot."""

    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        return None

    pair_upper = pair.upper()
    for symbol_entry in symbols:
        if not isinstance(symbol_entry, Mapping):
            continue
        if str(symbol_entry.get("symbol", "")).upper() != pair_upper:
            continue

        tick_size: str | None = None
        step_size: str | None = None
        min_notional: str | None = None
        filters = symbol_entry.get("filters")
        if not isinstance(filters, list):
            return None

        for filter_entry in filters:
            if not isinstance(filter_entry, Mapping):
                continue
            filter_type = str(filter_entry.get("filterType", "")).upper()
            if filter_type == "PRICE_FILTER":
                tick_size = _positive_decimal_str_or_none(filter_entry.get("tickSize"))
            elif filter_type == "LOT_SIZE":
                step_size = _positive_decimal_str_or_none(filter_entry.get("stepSize"))
            elif filter_type == "MIN_NOTIONAL":
                min_notional = _positive_decimal_str_or_none(filter_entry.get("minNotional"))
            elif filter_type == "NOTIONAL" and min_notional is None:
                min_notional = _positive_decimal_str_or_none(filter_entry.get("minNotional"))

        if tick_size is None and step_size is None and min_notional is None:
            return None
        return VenueConstraintSnapshot(
            tick_size=tick_size,
            step_size=step_size,
            min_notional=min_notional,
        )

    return None


class BinanceExchangeInfoVenueConstraintProvider:
    """Optional Binance `/exchangeInfo` metadata source with local cache persistence."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.binance.com",
        timeout_s: float = 5.0,
        cache_ttl_s: float = 86400.0,
        cache_path: Path | None = None,
        http_get: HttpGet | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not math.isfinite(cache_ttl_s) or cache_ttl_s <= 0.0:
            raise ValueError("cache_ttl_s must be finite and > 0")
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._cache_ttl_s = cache_ttl_s
        self._cache_path = cache_path
        self._http_get = http_get or _default_http_get
        self._clock = clock
        self._cache_state = self._load_cache()

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        """Return cached constraints only. Never makes network calls.

        BS-66: HTTP must NOT happen on the execution critical path.
        Call pre_warm() at startup to populate the cache for known pairs.
        """
        cached = self._cache_state.entries.get(pair.upper())
        if cached is None:
            return None
        if self._is_entry_expired(cached):
            return None
        return cached.constraints

    def pre_warm(self, pairs: Iterable[str]) -> int:
        """Fetch and cache venue constraints for all given pairs via HTTP.

        MUST be called at startup before the execution loop.
        Returns the number of pairs successfully fetched (cache misses resolved).
        """
        fetched = 0
        for pair in pairs:
            pair_key = pair.upper()
            cached = self._cache_state.entries.get(pair_key)
            if cached is not None and not self._is_entry_expired(cached):
                continue
            if self._fetch_and_cache(pair_key):
                fetched += 1
        return fetched

    def _fetch_and_cache(self, pair_key: str) -> bool:
        """Fetch constraints for one pair from the exchange. Returns True on success."""
        try:
            payload_bytes = self._http_get(self._build_url(pair_key), self._timeout_s)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as exc:
            logger.warning(
                "venue_constraints_fetch_failed",
                extra={"pair": pair_key, "detail": str(exc)},
            )
            return False

        constraints = parse_binance_exchange_info_payload(payload, pair=pair_key)
        if constraints is None:
            logger.warning(
                "venue_constraints_missing_from_payload",
                extra={"pair": pair_key, "source": "binance_exchange_info"},
            )
            return False

        self._cache_state.entries[pair_key] = VenueConstraintCacheEntry(
            pair=pair_key,
            constraints=constraints,
            fetched_at=self._clock(),
        )
        self._persist_cache()
        return True

    def _build_url(self, pair: str) -> str:
        query = urlencode({"symbol": pair.upper()})
        return f"{self._base_url}/api/v3/exchangeInfo?{query}"

    def _is_entry_expired(self, entry: VenueConstraintCacheEntry) -> bool:
        age_s = self._clock() - entry.fetched_at
        if age_s <= 0.0:
            return False
        return age_s > self._cache_ttl_s

    def _load_cache(self) -> VenueConstraintCacheState:
        if self._cache_path is None or not self._cache_path.exists():
            return VenueConstraintCacheState()
        try:
            return VenueConstraintCacheState.model_validate_json(
                self._cache_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            logger.warning(
                "venue_constraints_cache_load_failed",
                extra={"path": str(self._cache_path), "detail": str(exc)},
            )
            return VenueConstraintCacheState()

    def _persist_cache(self) -> None:
        if self._cache_path is None:
            return
        atomic_write_json(
            self._cache_path,
            self._cache_state.model_dump(mode="json"),
        )


__all__ = [
    "BinanceExchangeInfoVenueConstraintProvider",
    "VenueConstraintCacheEntry",
    "VenueConstraintCacheState",
    "VenueConstraintProvider",
    "parse_binance_exchange_info_payload",
]
