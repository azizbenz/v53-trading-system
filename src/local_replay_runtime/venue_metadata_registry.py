"""Venue metadata registry — fees + latency par venue (2026-05-07).

Service-oriented venue-aware. Le caller dit "j'ai besoin du fee/latency pour
trader sur venue X au timestamp t" → le service va chercher la valeur dans
la source venue-specifique :

  Tier 1 (live)     : API account dynamique (BinanceAccountSnapshot.taker_commission)
  Tier 2 (backtest) : metadata historique du venue (Bybit research, Binance default)
  Tier 3 (fallback) : conservative default + DEGRADED_FALLBACK provenance flag

Architecture critique :
  - **JAMAIS hardcoder un venue specifique dans compute_economic_provenance**
  - Le caller fournit `venue: str` → le registry route vers le bon provider
  - Fallback safety : si venue inconnu, default conservative + warning

Detection venue :
  - Auto-detect depuis raw paths (ex : path contient "bybit/" → venue="bybit")
  - Override caller via parametre `venue=...`
  - Fallback "unknown" → DEGRADED_FALLBACK

References :
  - Binance Spot fees : maker/taker = 10 bps standard, 7.5 bps avec BNB
  - Bybit Spot fees   : maker/taker = 10 bps standard
  - Binance Spot latency : 3-10 ms US-East, 50-200 ms intercont.
  - Bybit Spot latency  : 5-50 ms US-East, 100-300 ms intercont.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VenueEconomicMetadata:
    """Metadata economique d'un venue : fees default + latency conservative.

    Ces valeurs sont :
      - Pour le BACKTEST : sources canoniques du venue (research published rates)
      - Pour le LIVE    : fallback si l'API account n'est pas connectee/cache stale

    En live, le caller doit privilegier l'API account dynamique (cf
    BinanceAccountSnapshot.taker_commission) et n'utiliser ces valeurs que
    comme fallback.
    """

    venue_id: str
    venue_display_name: str
    # Fees publishes par le venue (basis points)
    maker_fee_bps: float
    taker_fee_bps: float
    # Latency conservative observee historiquement (basis points cost equivalent)
    latency_bps_conservative: float
    # Sources / provenance
    fee_provenance: str
    latency_provenance: str


# ============================================================================
# Binance Spot — venue cible production live
# ============================================================================
# Source fees : Binance Spot official trading fees public schedule
#   Standard (no VIP, no BNB discount) : maker/taker = 0.10% = 10 bps
#   With BNB discount (Spot)            : 7.5 bps
#   VIP1 (>= $1M monthly volume)        : 9 bps maker / 10 bps taker
# Conservative MVP : 10 bps taker (pessimiste, pas de BNB discount)
#
# Source latency : Binance Spot REST median (US-East colocation observe)
#   Median 3-10 ms, p95 ~30 ms intercontinental
# Conservative MVP : 1.5 bps cost equivalent
BINANCE_SPOT_METADATA = VenueEconomicMetadata(
    venue_id="binance_spot",
    venue_display_name="Binance Spot",
    maker_fee_bps=10.0,
    taker_fee_bps=10.0,
    latency_bps_conservative=1.5,
    fee_provenance="MEASURED_FROM_BINANCE_SPOT_PUBLIC_RATES",
    latency_provenance="STATIC_CONSERVATIVE_FROM_BINANCE_HISTORICAL",
)

# ============================================================================
# Bybit Spot — venue source data historique backtest
# ============================================================================
# Source fees : bybit_historical_metadata.BYBIT_RESEARCH_TAKER_FEE_RATE = 0.001
#   maker/taker = 0.10% = 10 bps standard retail
#
# Source latency : Bybit Spot WS observabilite reseau historique
#   Median 5-15 ms, p95 ~50-100 ms
# Conservative MVP : 1.5 bps
BYBIT_SPOT_METADATA = VenueEconomicMetadata(
    venue_id="bybit_spot",
    venue_display_name="Bybit Spot",
    maker_fee_bps=10.0,
    taker_fee_bps=10.0,
    latency_bps_conservative=1.5,
    fee_provenance="MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
    latency_provenance="STATIC_CONSERVATIVE_FROM_BYBIT_HISTORICAL",
)

# ============================================================================
# Default fallback — venue inconnu
# ============================================================================
# Conservative pour proteger contre venues exotiques : 25 bps fee, 5 bps latency.
# Si on tombe la, c'est un signal qu'il faut ajouter le venue au registry.
UNKNOWN_VENUE_METADATA = VenueEconomicMetadata(
    venue_id="unknown",
    venue_display_name="Unknown Venue",
    maker_fee_bps=25.0,
    taker_fee_bps=25.0,
    latency_bps_conservative=5.0,
    fee_provenance="DEGRADED_FALLBACK_UNKNOWN_VENUE",
    latency_provenance="DEGRADED_FALLBACK_UNKNOWN_VENUE",
)


VENUE_REGISTRY: dict[str, VenueEconomicMetadata] = {
    "binance_spot": BINANCE_SPOT_METADATA,
    "binance": BINANCE_SPOT_METADATA,  # alias
    "bybit_spot": BYBIT_SPOT_METADATA,
    "bybit": BYBIT_SPOT_METADATA,  # alias
}


def get_venue_metadata(venue_id: str | None) -> VenueEconomicMetadata:
    """Retourne le metadata du venue demande, ou UNKNOWN_VENUE_METADATA en fallback.

    Le `venue_id` est case-insensitive. Aliases supportes :
      - "binance" / "binance_spot" → Binance Spot
      - "bybit" / "bybit_spot"     → Bybit Spot
    """
    if not venue_id:
        return UNKNOWN_VENUE_METADATA
    normalized = venue_id.strip().lower()
    return VENUE_REGISTRY.get(normalized, UNKNOWN_VENUE_METADATA)


def detect_venue_from_path(raw_path: str | None) -> str | None:
    """Auto-detecte le venue depuis un path raw_window.

    Convention silver canonique :
      silver/bybit/spot/...   → "bybit_spot"
      silver/binance/spot/... → "binance_spot"

    Retourne None si pas de detection possible (path absent ou format inconnu).
    """
    if not raw_path:
        return None
    p = str(raw_path).lower().replace("\\", "/")
    if "/bybit/spot/" in p or "/bybit_spot/" in p:
        return "bybit_spot"
    if "/binance/spot/" in p or "/binance_spot/" in p:
        return "binance_spot"
    return None


# Audit 2026-05-13 W1 fix: map silver_index.entries[i].exchange + market_type
# vers les venue_id du registry. Source canonique : `silver_index.json` produit
# par data_factory (`exchange="bybit"` + `market_type="spot"` etc.).
# Cette resolution prend precedence sur l'auto-detect path, qui echoue quand
# `raw_book_path` pointe vers les raw_windows extraits (pas le silver direct).
_SILVER_EXCHANGE_TO_VENUE_ID: dict[tuple[str, str], str] = {
    ("bybit", "spot"): "bybit_spot",
    ("binance", "spot"): "binance_spot",
}


def venue_id_from_silver_exchange(
    exchange: str | None,
    *,
    market_type: str = "spot",
) -> str | None:
    """Resout un venue_id canonique depuis silver_index.entries[i].exchange.

    Conventions :
      ("bybit", "spot")   → "bybit_spot"
      ("binance", "spot") → "binance_spot"

    Retourne None si la combinaison n'est pas reconnue (le caller doit alors
    documenter explicitement le venue ou tomber sur UNKNOWN_VENUE_METADATA).
    """
    if not exchange:
        return None
    key = (exchange.strip().lower(), (market_type or "spot").strip().lower())
    return _SILVER_EXCHANGE_TO_VENUE_ID.get(key)


def resolve_venue(
    *,
    venue_override: str | None = None,
    silver_exchange: str | None = None,
    silver_market_type: str = "spot",
    raw_path_for_detection: str | None = None,
) -> tuple[str, VenueEconomicMetadata, str]:
    """Resolution venue avec ordre de priorite :

      1. venue_override fourni explicitement par caller
      2. silver_exchange + silver_market_type (source canonique silver_index)
      3. auto-detect depuis raw_path_for_detection (fallback legacy)
      4. fallback UNKNOWN_VENUE_METADATA

    Retourne (resolved_venue_id, metadata, resolution_status) avec
    resolution_status :
      - "VENUE_OVERRIDE"           : caller explicite
      - "VENUE_FROM_SILVER_INDEX"  : depuis silver_index.entries[i].exchange
      - "VENUE_AUTO_DETECTED"     : detecte depuis path silver/{venue}/...
      - "VENUE_OVERRIDE_UNKNOWN"  : override fourni mais venue inconnu
      - "VENUE_UNKNOWN"           : fallback degraded (rien resolu)
    """
    if venue_override:
        normalized = venue_override.strip().lower()
        if normalized in VENUE_REGISTRY:
            return normalized, VENUE_REGISTRY[normalized], "VENUE_OVERRIDE"
        # Override fourni mais inconnu → on retourne le fallback avec status explicite
        return normalized, UNKNOWN_VENUE_METADATA, "VENUE_OVERRIDE_UNKNOWN"

    silver_resolved = venue_id_from_silver_exchange(
        silver_exchange,
        market_type=silver_market_type,
    )
    if silver_resolved and silver_resolved in VENUE_REGISTRY:
        return (
            silver_resolved,
            VENUE_REGISTRY[silver_resolved],
            "VENUE_FROM_SILVER_INDEX",
        )

    detected = detect_venue_from_path(raw_path_for_detection)
    if detected and detected in VENUE_REGISTRY:
        return detected, VENUE_REGISTRY[detected], "VENUE_AUTO_DETECTED"

    return "unknown", UNKNOWN_VENUE_METADATA, "VENUE_UNKNOWN"


__all__ = [
    "BINANCE_SPOT_METADATA",
    "BYBIT_SPOT_METADATA",
    "UNKNOWN_VENUE_METADATA",
    "VENUE_REGISTRY",
    "VenueEconomicMetadata",
    "detect_venue_from_path",
    "get_venue_metadata",
    "resolve_venue",
    "venue_id_from_silver_exchange",
]
