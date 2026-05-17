"""Pair bounds registry — clamp des champs economiques par pair (MVP 2026-05-07).

Bornes calibrees par pair pour proteger contre les outliers de donnees :
  - book gap → spread 100000 bps
  - donnees corrompues → negative spread
  - flash crash → fee venue temporaire renegociee
  - latency anormale Bybit incident

Architecture :
  - PAIR_BOUNDS[pair] expose `EconomicBounds` (floor, ceiling) par champ
  - DEFAULT_BOUNDS pour les pairs non listees (conservateur safety-first)
  - Bornes refresh mensuel par calibration walk-forward (TO_CALIBRATE)

Philosophie :
  - Pas hardcoded forever — refresh discipline
  - Les bornes elles-memes sont MEASURED_HISTORICALLY (99e percentile rolling)
  - Quand le clamp s'active, un warning audit-ready est emis
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EconomicBounds:
    """Bornes (floor, ceiling) par champ economique pour une pair.

    floor    : valeur minimum acceptable. En dessous, on borne au floor + warning.
    ceiling  : valeur maximum acceptable. Au-dessus, outlier → borne au ceiling
                + warning. Si > 2 * ceiling, on REJETTE le candidat (donnees
                corrompues probable).
    reject_threshold : multiplicateur ceiling au-dessus duquel on rejette.
    """

    spread_bps: tuple[float, float]
    slippage_bps: tuple[float, float]
    fee_bps: tuple[float, float]
    latency_bps: tuple[float, float]
    edge_bps: tuple[float, float]
    reject_threshold_multiplier: float = 2.0


# Bornes BNBUSDT spot (Bybit) — calibration TO_CALIBRATE
# Source : observation historique 30 jours + spec doc 23 microstructure
BNBUSDT_SPOT_BOUNDS = EconomicBounds(
    # Spread observe : median ~1.5 bps, p99 ~12 bps. Floor 0.5 bps (1 tick).
    # Ceiling 50 bps : largement au-dessus du p99, avant rejet flash crash.
    spread_bps=(0.5, 50.0),
    # Slippage : top tier liquide, Kyle lambda observe 0.1-3 bps standard
    # notional 100 USDT. Ceiling 10 bps = signal d'incident liquidite.
    slippage_bps=(0.1, 10.0),
    # Fee : Bybit retail = 10 bps taker, VIP = 7.5 bps. Ceiling 25 bps
    # securite contre fee renegocie (pas vu en pratique sur Bybit).
    fee_bps=(5.0, 25.0),
    # Latency : Bybit spot RTT 1-50 ms. Ceiling 50 bps = signal d'incident.
    latency_bps=(0.1, 50.0),
    # Edge : forward return 5min observe -30 a +30 bps. Floor 0 (on long
    # uniquement). Ceiling 30 bps = anti-overconfidence du predictor.
    edge_bps=(0.0, 30.0),
)

# Bornes default conservatives pour pairs non listees
DEFAULT_BOUNDS = EconomicBounds(
    spread_bps=(0.5, 100.0),
    slippage_bps=(0.1, 20.0),
    fee_bps=(5.0, 50.0),
    latency_bps=(0.1, 100.0),
    edge_bps=(0.0, 50.0),
)


PAIR_BOUNDS: dict[str, EconomicBounds] = {
    "BNBUSDT": BNBUSDT_SPOT_BOUNDS,
}


def get_bounds_for_pair(pair: str) -> EconomicBounds:
    """Retourne les bornes calibrees pour une pair, ou DEFAULT_BOUNDS sinon."""
    return PAIR_BOUNDS.get(pair.strip().upper(), DEFAULT_BOUNDS)


def clamp_with_warning(
    value: float,
    *,
    field_name: str,
    pair: str,
    bounds: tuple[float, float],
    reject_threshold: float = 2.0,
) -> tuple[float, str | None, bool]:
    """Clamp une valeur dans [floor, ceiling] avec audit-ready warning.

    Retourne :
      (clamped_value, warning_or_none, rejected)

    Si value > ceiling × reject_threshold → rejected=True (donnees corrompues
    probable, le caller doit refuser le candidat).
    """
    floor, ceiling = bounds
    if not isinstance(value, (int, float)) or value != value:  # NaN check
        return floor, f"{field_name}_NAN_REPLACED_BY_FLOOR", False
    if value > ceiling * reject_threshold:
        return ceiling, (
            f"{field_name}_REJECTED_AS_OUTLIER:value={value:.4f}>"
            f"{ceiling*reject_threshold:.4f}_ceiling*{reject_threshold}_pair={pair}"
        ), True
    if value < floor:
        return floor, (
            f"{field_name}_CLAMPED_AT_FLOOR:value={value:.4f}<"
            f"{floor:.4f}_pair={pair}"
        ), False
    if value > ceiling:
        return ceiling, (
            f"{field_name}_CLAMPED_AT_CEILING:value={value:.4f}>"
            f"{ceiling:.4f}_pair={pair}"
        ), False
    return value, None, False


__all__ = [
    "BNBUSDT_SPOT_BOUNDS",
    "DEFAULT_BOUNDS",
    "EconomicBounds",
    "PAIR_BOUNDS",
    "clamp_with_warning",
    "get_bounds_for_pair",
]
