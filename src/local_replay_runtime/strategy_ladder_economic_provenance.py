"""Strategy Ladder economic provenance module — comble la limitation P0
CE/cost provenance (Audit 2026-05-07, MVP service-oriented).

Service-oriented : le caller dit "j'ai besoin de l'economic provenance pour
ce candidat a ce timestamp" — le service va chercher chaque valeur dans la
bonne source (book, trades, venue metadata, edge model) avec bounds par pair.

Architecture (Tier 1/2/3 par champ) :
  Tier 1 (preferred) : MESURE depuis raw data au timestamp t
                        - spread_bps     ← orderbook snapshot
                        - slippage_bps   ← Kyle lambda × notional
                        - fee_bps        ← venue metadata Bybit
                        - latency_bps    ← venue conservative
                        - edge_bps       ← forward return median rolling 1h
  Tier 2 (fallback)  : derniere mesure connue avec marqueur DEGRADED_FALLBACK
  Tier 3 (last resort): default conservateur EMERGENCY_DEFAULT (bloque promotion)

Bornes par pair (clamp) protege contre outliers de donnees :
  pair_bounds_registry.PAIR_BOUNDS[pair] expose floor/ceiling par champ

PHILOSOPHIE PRESERVEE :
- AUCUN engine modifie
- Module dans `local_replay_runtime/` cote caller
- Provenance flag par champ
- Tant qu'au moins un champ est en DEFAULT_TO_CALIBRATE → la promotion est
  bloquee (audit-ready)
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Protocol

from data_backbone.microstructure.kyle_lambda import (
    KyleTradePoint,
    compute_kyle_lambda,
)
from local_replay_runtime.pair_bounds_registry import (
    DEFAULT_BOUNDS,
    EconomicBounds,
    clamp_with_warning,
    get_bounds_for_pair,
)
from local_replay_runtime.venue_metadata_registry import (
    UNKNOWN_VENUE_METADATA,
    VenueEconomicMetadata,
    resolve_venue,
)


# Defaults canoniques TO_CALIBRATE (legacy fallback uniquement quand venue/edge
# model sources sont indisponibles).
DEFAULT_EXPECTED_EDGE_BPS = 5.0
DEFAULT_SLIPPAGE_BPS = 2.0
DEFAULT_LATENCY_PENALTY_BPS = 1.0

# Backward-compat aliases (sont remplaces par le venue registry resolu
# dynamiquement). Conserves pour ne pas casser les tests legacy qui peuvent
# importer ces noms ; ils refletent les valeurs Bybit (legacy default avant
# l'ajout du venue registry 2026-05-07).
BYBIT_SPOT_LATENCY_PENALTY_BPS = 1.5
BYBIT_SPOT_LATENCY_PROVENANCE = "STATIC_CONSERVATIVE_FROM_BYBIT_HISTORICAL"
BYBIT_SPOT_TAKER_FEE_BPS = 10.0
BYBIT_SPOT_FEE_PROVENANCE = "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"

# Spread defaults (legacy mapping si pas de mesure depuis book) — alignes sur
# l'ancien `data_factory.py:1862` :
#   BOOK_DEPTH20_AVAILABLE        → 4.0 bps
#   BOOK_LIMITED_DEPTH_AVAILABLE  → 6.0 bps
#   BOOK_TOP_OF_BOOK_ONLY         → 6.0 bps (etendu, plus prudent)
#   BOOK_DEPTH_NOT_PROVEN         → 0.0 bps (sans mesure, fallback agressif)
DEFAULT_SPREAD_BPS_BY_BOOK_STATUS: dict[str, float] = {
    "BOOK_DEPTH20_AVAILABLE": 4.0,
    "BOOK_LIMITED_DEPTH_AVAILABLE": 6.0,
    "BOOK_TOP_OF_BOOK_ONLY": 6.0,
    "BOOK_DEPTH_NOT_PROVEN": 0.0,
}


@dataclass(frozen=True)
class EconomicProvenance:
    """Provenance audit-ready des 4 champs economiques d'une feature_row.

    Chaque champ a son flag de provenance individuelle. Le manifest run
    `economic_constants_provenance` est l'aggregation max-conservative de
    ces provenances (HARDCODED si tous hardcoded, MEASURED_FROM_BRIDGE si
    au moins un mesure, FULLY_MEASURED si les 4 mesures).
    """

    expected_edge_bps: float
    expected_edge_provenance: str  # governed model/override, proxy, or DEFAULT_TO_CALIBRATE
    spread_bps: float
    spread_provenance: str  # "DEFAULT_BY_BOOK_STATUS" | "MEASURED_FROM_BOOK_SNAPSHOT" | "MEASURED_FROM_BOOK_RECONSTRUCTION" | "MEASURED_FROM_BOOK_SNAPSHOT_STALE"
    slippage_bps: float
    slippage_provenance: str  # "DEFAULT_TO_CALIBRATE" | "MEASURED_FROM_KYLE_LAMBDA"
    latency_penalty_bps: float
    latency_provenance: str  # "DEFAULT_TO_CALIBRATE" | "MEASURED_FROM_VENUE_MODEL"
    fee_bps: float
    fee_provenance: str  # "DEFAULT_TO_CALIBRATE" | "MEASURED_FROM_VENUE_METADATA"
    measurement_warnings: tuple[str, ...] = ()
    expected_edge_model_status: str = "EXPECTED_EDGE_MODEL_NOT_USED"
    expected_edge_model_artifact_hash: str | None = None
    expected_edge_model_feature_hash: str | None = None
    measured_cost_governance: dict[str, object] = field(default_factory=dict)

    @property
    def aggregated_provenance(self) -> str:
        """Provenance aggregee audit-ready au niveau row.

        Considere comme "MEASURED" : MEASURED_* OU STATIC_CONSERVATIVE_* (la
        latency Bybit est statique mais issue d'observabilite venue, pas un
        hardcoded arbitraire). Les proxies `*_TO_CALIBRATE` ne sont pas de la
        verite backtest et ne comptent donc pas comme mesures gouvernees.

        Hierarchie :
          - "FULLY_MEASURED"           tous les 5 (edge/spread/slippage/latency/fee)
          - "PARTIALLY_MEASURED"       au moins 1 mesure
          - "SPREAD_MEASURED_OTHERS_HARDCODED" backward-compat (legacy test)
          - "HARDCODED_PROXY_CONSTANTS" tout en default
        """
        flags = (
            self.expected_edge_provenance,
            self.spread_provenance,
            self.slippage_provenance,
            self.latency_provenance,
            self.fee_provenance,
        )
        is_measured_or_static = lambda f: (
            f.startswith("MEASURED_")
            or f.startswith("STATIC_CONSERVATIVE_")
            or f.startswith("GOVERNED_")
        )
        n_measured = sum(1 for f in flags if is_measured_or_static(f))
        if n_measured == len(flags):
            return "FULLY_MEASURED"
        if n_measured > 0:
            return "PARTIALLY_MEASURED"
        return "HARDCODED_PROXY_CONSTANTS"


def is_expected_edge_backtest_truth(provenance: str | None) -> bool:
    """Return True only for an edge source usable as governed backtest truth."""

    value = str(provenance or "").strip().upper()
    if not value:
        return False
    if "TO_CALIBRATE" in value:
        return False
    if value.startswith(("DEFAULT", "PROXY", "UNKNOWN")):
        return False
    return value.startswith("MEASURED_") or value.startswith("GOVERNED_")


def expected_edge_backtest_truth_status(provenance: str | None) -> str:
    """Audit status for the expected-edge rail."""

    if is_expected_edge_backtest_truth(provenance):
        return "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
    value = str(provenance or "").strip().upper()
    if not value:
        return "EXPECTED_EDGE_NOT_PROVEN"
    if value.startswith("DEFAULT"):
        return "EXPECTED_EDGE_DEFAULT_BLOCKED"
    if value.startswith("EDGE_MODEL_BLOCKED") or "EDGE_MODEL_BLOCKED" in value:
        return "EXPECTED_EDGE_MODEL_BLOCKED"
    return "EXPECTED_EDGE_PROXY_BLOCKED"


class ExpectedEdgeModelProtocol(Protocol):
    """Minimal runtime protocol for governed expected-edge scoring."""

    artifact_hash: str
    feature_hash: str

    def estimate_expected_edge_bps(
        self,
        *,
        pair: str,
        timeframe: str | None = None,
        timestamp_ms: int,
        feature_values: Mapping[str, object] | None = None,
        route_features: Mapping[str, object] | None = None,
    ) -> object:
        ...


def _derive_orderbook_delta_path(snapshot_path: Path) -> Path | None:
    """Audit 2026-05-13 W2 fix : derive `orderbook_delta.jsonl` depuis le
    `orderbook_snapshot.jsonl` selon la convention raw_window canonique
    (silver/{venue}/spot/ et raw_windows/{pair}/{cand}/ posent les deux
    fichiers cote a cote)."""
    name = snapshot_path.name
    candidates: list[str] = []
    if "orderbook_snapshot" in name:
        candidates.append(name.replace("orderbook_snapshot", "orderbook_delta"))
    if "snapshot" in name.lower():
        candidates.append(
            name.replace("snapshot", "delta").replace("Snapshot", "Delta")
        )
    parent = snapshot_path.parent
    for candidate in candidates:
        derived = parent / candidate
        if derived.is_file():
            return derived
    # Fallback : same parent dir contains "orderbook_delta.jsonl"
    default_delta = parent / "orderbook_delta.jsonl"
    if default_delta.is_file():
        return default_delta
    return None


def _spread_bps_from_book_levels(
    bids: list[list[object]] | None,
    asks: list[list[object]] | None,
) -> tuple[float | None, str]:
    """Calcule spread_bps depuis 2 listes de levels top-of-book.

    Retourne (None, reason_code) si donnees insuffisantes ou degenerees.
    """
    if not bids or not asks:
        return None, "BOOK_EMPTY_SIDES"
    try:
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
    except (TypeError, ValueError, IndexError):
        return None, "BOOK_LEVELS_PARSE_FAILED"
    if best_bid <= 0.0 or best_ask <= 0.0 or best_ask < best_bid:
        return None, "BOOK_INVALID_LEVELS"
    mid_price = (best_bid + best_ask) / 2.0
    if mid_price <= 0.0:
        return None, "BOOK_DEGENERATE_MID"
    spread_bps = (best_ask - best_bid) / mid_price * 10_000.0
    return spread_bps, "OK"


def _measure_spread_via_reconstruction(
    *,
    snapshot_path: Path,
    delta_path: Path,
    timestamp_ms: int,
    tolerance_ms: int,
) -> tuple[float | None, str]:
    """Audit 2026-05-13 W2 fix : reconstruction snapshot + deltas pour mesurer
    le spread reel au timestamp lorsque le snapshot direct est `TOO_FAR`.

    Algorithme :
      1. Charger le snapshot le plus recent <= timestamp_ms (base state)
      2. Appliquer sequentiellement les deltas (update_id > base.update_id)
         tant que delta.timestamp_ms <= timestamp_ms + tolerance_ms
      3. A chaque delta, capturer (best_bid, best_ask). Garder celui dont
         timestamp_ms est le plus proche du candidat
      4. Calcule spread_bps depuis ce best_state

    Retourne (None, reason_code) si reconstruction echoue.
    """
    # Charger snapshot le plus recent <= timestamp_ms
    base_snapshot: dict[str, object] | None = None
    base_ts = -1
    try:
        with snapshot_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                    ts = int(row.get("timestamp_ms") or 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                if ts <= timestamp_ms and ts > base_ts:
                    base_ts = ts
                    base_snapshot = row
    except OSError as exc:
        return None, f"BOOK_RECONSTRUCTION_SNAPSHOT_IO_FAILED:{type(exc).__name__}"

    if base_snapshot is None:
        return None, "BOOK_RECONSTRUCTION_NO_BASE_SNAPSHOT"

    base_update_id = int(base_snapshot.get("update_id") or 0)
    bid_book: dict[float, float] = {}
    ask_book: dict[float, float] = {}
    for level in (base_snapshot.get("bids") or []):
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if size > 0.0:
            bid_book[price] = size
    for level in (base_snapshot.get("asks") or []):
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if size > 0.0:
            ask_book[price] = size

    deltas: list[dict[str, object]] = []
    # Audit 2026-05-13 W2 fix : causalite stricte sur les deltas (ts <=
    # timestamp_ms). La tolerance ne filtre PAS l'input mais s'applique sur le
    # `best_dt` final entre l'etat reconstruit et le candidat. Cela permet de
    # capturer le state book le plus proche AVANT le candidat, meme si le
    # premier delta est plus ancien que `timestamp_ms - tolerance_ms`.
    causal_upper_ts = timestamp_ms
    try:
        with delta_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                    uid = int(row.get("update_id") or 0)
                    ts = int(row.get("timestamp_ms") or 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                if uid > base_update_id and ts <= causal_upper_ts:
                    deltas.append(row)
    except OSError as exc:
        return None, f"BOOK_RECONSTRUCTION_DELTAS_IO_FAILED:{type(exc).__name__}"

    deltas.sort(key=lambda r: int(r.get("update_id") or 0))

    best_spread: float | None = None
    best_dt = float("inf")
    best_state_ts = -1

    def _capture_top_of_book() -> tuple[float | None, float | None]:
        if not bid_book or not ask_book:
            return None, None
        best_bid_price = max(bid_book.keys())
        best_ask_price = min(ask_book.keys())
        return best_bid_price, best_ask_price

    # Etat initial : evaluer aussi le base snapshot
    bb, ba = _capture_top_of_book()
    if bb is not None and ba is not None and ba > bb > 0.0:
        mid = (bb + ba) / 2.0
        if mid > 0.0:
            dt = abs(base_ts - timestamp_ms)
            if dt < best_dt:
                best_dt = dt
                best_state_ts = base_ts
                best_spread = (ba - bb) / mid * 10_000.0

    for delta in deltas:
        for level in (delta.get("bids") or []):
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                bid_book.pop(price, None)
            else:
                bid_book[price] = size
        for level in (delta.get("asks") or []):
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                ask_book.pop(price, None)
            else:
                ask_book[price] = size

        try:
            delta_ts = int(delta.get("timestamp_ms") or 0)
        except (TypeError, ValueError):
            continue
        bb, ba = _capture_top_of_book()
        if bb is None or ba is None or ba <= bb:
            continue
        mid = (bb + ba) / 2.0
        if mid <= 0.0:
            continue
        dt = abs(delta_ts - timestamp_ms)
        if dt < best_dt:
            best_dt = dt
            best_state_ts = delta_ts
            best_spread = (ba - bb) / mid * 10_000.0

    if best_spread is None:
        return None, "BOOK_RECONSTRUCTION_NO_VALID_STATE"
    if best_dt > tolerance_ms:
        return (
            None,
            f"BOOK_RECONSTRUCTION_STATE_TOO_FAR:{int(best_dt)}ms_>_{tolerance_ms}ms",
        )
    return best_spread, "MEASURED_FROM_BOOK_RECONSTRUCTION"


def measure_spread_bps_from_book_snapshot(
    *,
    raw_book_path: Path | str | None,
    timestamp_ms: int,
    tolerance_ms: int = 60_000,
    raw_book_delta_path: Path | str | None = None,
    enable_reconstruction_fallback: bool = True,
    stale_snapshot_max_age_ms: int = 24 * 60 * 60 * 1000,
) -> tuple[float | None, str]:
    """Mesure le spread reel depuis le snapshot orderbook le plus proche,
    avec fallbacks de reconstruction snapshot+deltas et stale-snapshot.

    Strategie tier-1 / tier-2 / tier-3 / fallback :
      Tier 1 : snapshot direct dans la tolerance (cas silver dense)
      Tier 2 : reconstruction snapshot+deltas (W2 fix 2026-05-13)
               causal jusqu'a timestamp_ms ; rejette les etats `cross book`
      Tier 3 : snapshot stale (au-dela de tolerance, dans
               `stale_snapshot_max_age_ms`) avec provenance
               `MEASURED_FROM_BOOK_SNAPSHOT_STALE` ; mieux que le hardcoded
               `DEFAULT_BY_BOOK_STATUS` car c'est une mesure reelle
      Fallback : (None, reason_code) → caller utilise DEFAULT_BY_BOOK_STATUS

    Provenance retournee :
      - "MEASURED_FROM_BOOK_SNAPSHOT"           : tier 1
      - "MEASURED_FROM_BOOK_RECONSTRUCTION"     : tier 2
      - "MEASURED_FROM_BOOK_SNAPSHOT_STALE"     : tier 3 (mesure stale)
      - reason_code (string "BOOK_*")           : fallback
    """
    if raw_book_path is None:
        return None, "BOOK_PATH_MISSING"
    book_path = Path(raw_book_path)
    if not book_path.exists():
        return None, f"BOOK_PATH_NOT_FOUND:{book_path}"

    closest_row: dict[str, object] | None = None
    closest_dt = float("inf")
    try:
        with book_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                    ts = int(row.get("timestamp_ms") or 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                dt = abs(ts - timestamp_ms)
                if dt < closest_dt:
                    closest_dt = dt
                    closest_row = row
    except OSError as exc:
        return None, f"BOOK_LOAD_FAILED:{type(exc).__name__}"

    # Tier 1 : snapshot direct dans la tolerance
    if closest_row is not None and closest_dt <= tolerance_ms:
        spread_bps, status = _spread_bps_from_book_levels(
            closest_row.get("bids"),
            closest_row.get("asks"),
        )
        if spread_bps is not None:
            return spread_bps, "MEASURED_FROM_BOOK_SNAPSHOT"

    # Tier 2 : reconstruction snapshot+deltas (W2 fix)
    reconstruction_status: str | None = None
    if enable_reconstruction_fallback:
        delta_path = (
            Path(raw_book_delta_path)
            if raw_book_delta_path
            else _derive_orderbook_delta_path(book_path)
        )
        if delta_path is not None and delta_path.is_file():
            spread_bps, reconstruction_status = _measure_spread_via_reconstruction(
                snapshot_path=book_path,
                delta_path=delta_path,
                timestamp_ms=timestamp_ms,
                tolerance_ms=tolerance_ms,
            )
            if spread_bps is not None:
                return spread_bps, reconstruction_status

    # Tier 3 : stale snapshot (mesure reelle mais ancienne, mieux que hardcoded).
    # Audit 2026-05-13 W2 partial fix : sur les raw_windows B2, le snapshot
    # Bybit peut etre a -85min du target (frequence Bybit ~2 snapshots/jour).
    # La reconstruction echoue souvent (cross-book persistant) car les levels
    # stale du snapshot ne sont pas cleanes par les deltas. Plutot que de
    # retomber sur DEFAULT_BY_BOOK_STATUS (4.0 bps hardcoded), on retourne
    # le spread du snapshot stale (mesure reelle marquee MEASURED_*_STALE)
    # tant qu'il est dans `stale_snapshot_max_age_ms` (default 24h).
    if closest_row is not None and closest_dt <= stale_snapshot_max_age_ms:
        spread_bps, status = _spread_bps_from_book_levels(
            closest_row.get("bids"),
            closest_row.get("asks"),
        )
        if spread_bps is not None:
            return spread_bps, "MEASURED_FROM_BOOK_SNAPSHOT_STALE"

    # Fallback : retourne le code raison le plus precis
    if closest_row is None:
        return None, "BOOK_NO_SNAPSHOTS"
    if reconstruction_status is not None:
        return None, reconstruction_status
    if closest_dt > stale_snapshot_max_age_ms:
        return None, (
            f"BOOK_SNAPSHOT_TOO_FAR_BEYOND_STALE_MAX:{int(closest_dt)}ms_>_"
            f"{stale_snapshot_max_age_ms}ms"
        )
    return None, f"BOOK_SNAPSHOT_TOO_FAR:{int(closest_dt)}ms_>_{tolerance_ms}ms"


def _measure_slippage_from_kyle_lambda(
    *,
    raw_trade_path: Path | str | None,
    timestamp_ms: int,
    pair: str,
    lookback_ms: int = 60_000,
    standard_notional_usdt: float = 100.0,
) -> tuple[float | None, str]:
    """Mesure ex-ante le slippage via Kyle lambda × standard notional.

    Charge les trades dans [timestamp_ms - lookback_ms, timestamp_ms],
    calcule Kyle lambda et retourne le slippage estime en bps pour un
    notional standard (default 100 USDT).
    """
    if raw_trade_path is None:
        return None, "TRADE_PATH_MISSING"
    trade_path = Path(raw_trade_path)
    if not trade_path.exists():
        return None, f"TRADE_PATH_NOT_FOUND:{trade_path}"

    points: list[KyleTradePoint] = []
    extended_start_ms = timestamp_ms - lookback_ms
    try:
        if trade_path.name.lower().endswith(".gz"):
            handle_cm = gzip.open(trade_path, "rt", encoding="utf-8-sig")
        else:
            handle_cm = trade_path.open("r", encoding="utf-8-sig")
        with handle_cm as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                    ts_ms = int(row.get("timestamp_ms") or 0)
                    price = float(row.get("price") or 0.0)
                    volume = float(row.get("qty") or row.get("volume") or 0.0)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
                if price <= 0.0 or volume <= 0.0:
                    continue
                if extended_start_ms <= ts_ms <= timestamp_ms:
                    points.append(
                        KyleTradePoint(
                            timestamp_ns=ts_ms * 1_000_000,
                            price=price,
                            volume=volume,
                            mid_price=None,
                        )
                    )
    except OSError as exc:
        return None, f"TRADE_LOAD_FAILED:{type(exc).__name__}"

    if len(points) < 2:
        return None, f"INSUFFICIENT_TRADES:{len(points)}<2"

    window_seconds = max(1.0, lookback_ms / 1000.0)
    # Kyle lambda requires at least 2 populated intervals. Using one bucket
    # equal to the full lookback (e.g. 60s window -> 60s bucket) makes the
    # measurement fail almost deterministically on otherwise healthy data.
    bucket_seconds = min(60.0, max(1.0, window_seconds / 4.0))

    try:
        record = compute_kyle_lambda(
            points,
            pair=pair,
            window_seconds=window_seconds,
            bucket_seconds=bucket_seconds,
            standard_quote_notional=standard_notional_usdt,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"KYLE_FAILED:{type(exc).__name__}:{exc}"

    if record.is_stale or record.value <= 0.0:
        return None, f"KYLE_STALE:{record.stale_reason}"

    # Kyle's normalized impact bps for standard notional est exactement le
    # slippage attendu pour un trade de standard_notional_usdt.
    impact_bps = record.normalized_kyle_impact_bps_for_standard_notional
    if impact_bps is None or not math.isfinite(impact_bps) or impact_bps < 0.0:
        return None, "KYLE_IMPACT_NOT_NORMALIZED"
    return impact_bps, "MEASURED_FROM_KYLE_LAMBDA"


def compute_economic_provenance(
    *,
    timestamp_ms: int,
    book_status: str,
    pair: str = "",
    timeframe: str | None = None,
    raw_book_path: Path | str | None = None,
    raw_trade_path: Path | str | None = None,
    raw_ohlcv_path: Path | str | None = None,
    expected_edge_model: ExpectedEdgeModelProtocol | None = None,
    expected_edge_model_required: bool = False,
    expected_edge_model_load_status: str = "",
    expected_edge_feature_values: Mapping[str, object] | None = None,
    expected_edge_route_features: Mapping[str, object] | None = None,
    expected_edge_bps_override: float | None = None,
    slippage_bps_override: float | None = None,
    latency_penalty_bps_override: float | None = None,
    fee_bps_override: float | None = None,
    spread_tolerance_ms: int = 60_000,
    edge_lookback_ms: int = 60 * 60 * 1000,
    slippage_lookback_ms: int = 60_000,
    measure_slippage_from_trades: bool = True,
    apply_pair_bounds: bool = True,
    standard_notional_usdt: float = 100.0,
    venue: str | None = None,
    silver_exchange: str | None = None,
    silver_market_type: str = "spot",
    use_taker_fee: bool = True,
) -> EconomicProvenance:
    """Calcule l'EconomicProvenance service-oriented pour une feature_row.

    Le caller fournit les paths sources (book / trade / ohlcv) et le service
    va chercher chaque champ economique dans la bonne source :
      - **spread_bps** : best_ask − best_bid depuis raw_book_path
      - **slippage_bps** : Kyle lambda × standard_notional depuis raw_trade_path
      - **expected_edge_bps** : edge model gouverne ou proxy forward-return bloque
      - **fee_bps** : venue metadata Bybit (BYBIT_RESEARCH_TAKER_FEE_RATE)
      - **latency_penalty_bps** : Bybit spot conservative historique

    Bornes par pair : si `apply_pair_bounds=True`, chaque champ est clampe
    dans [floor, ceiling] avec warning audit-ready, et REJETE si outlier
    extreme.

    Override caller : caller peut forcer une valeur via `*_override`. Dans
    ce cas, provenance reste `MEASURED_FROM_*` mais source = caller, donc
    bypass de bounds (caller responsable).
    """
    from local_replay_runtime.strategy_ladder_edge_model_provider import (
        estimate_forward_return_edge_bps,
    )

    warnings: list[str] = []
    expected_edge_model_status = (
        "GOVERNED_EDGE_MODEL_PENDING"
        if expected_edge_model_required
        else "EXPECTED_EDGE_MODEL_NOT_REQUESTED"
    )
    expected_edge_model_artifact_hash: str | None = None
    expected_edge_model_feature_hash: str | None = None
    bounds = get_bounds_for_pair(pair) if apply_pair_bounds and pair else DEFAULT_BOUNDS

    # ------------------------------------------------------------------
    # 0. Resolution venue (auto-detect ou caller override)
    # ------------------------------------------------------------------
    # Le venue determine fees + latency. Auto-detect depuis raw_book_path par
    # convention silver canonique (silver/{venue}/spot/...). Caller peut forcer
    # via parametre `venue=...`. En live, le caller devrait fournir venue
    # explicitement ET passer fee_bps_override depuis BinanceAccountSnapshot.taker_commission.
    # Audit 2026-05-13 W1 fix : `silver_exchange` (depuis silver_index canonique
    # `entries[i].exchange`) prend precedence sur l'auto-detect path. Sur le run
    # backtest, `raw_book_path` pointe vers les raw_windows extraits
    # (`...\raw_windows\{pair}\{candidate_id}\orderbook_snapshot.jsonl`), donc
    # l'ancien auto-detect echouait silencieusement → DEGRADED_FALLBACK_UNKNOWN_VENUE.
    venue_id, venue_metadata, venue_resolution = resolve_venue(
        venue_override=venue,
        silver_exchange=silver_exchange,
        silver_market_type=silver_market_type,
        raw_path_for_detection=str(raw_book_path) if raw_book_path else None,
    )
    if venue_resolution == "VENUE_UNKNOWN":
        warnings.append("VENUE_UNKNOWN_USING_FALLBACK_METADATA")
    elif venue_resolution == "VENUE_OVERRIDE_UNKNOWN":
        warnings.append(f"VENUE_OVERRIDE_UNKNOWN:{venue}")
    elif venue_resolution == "VENUE_FROM_SILVER_INDEX":
        warnings.append(f"VENUE_FROM_SILVER_INDEX:{venue_id}")

    # ------------------------------------------------------------------
    # 1. SPREAD — mesure depuis book snapshot
    # ------------------------------------------------------------------
    measured_spread, spread_status = measure_spread_bps_from_book_snapshot(
        raw_book_path=raw_book_path,
        timestamp_ms=timestamp_ms,
        tolerance_ms=spread_tolerance_ms,
    )
    if measured_spread is not None and measured_spread >= 0.0:
        if apply_pair_bounds:
            spread_bps, w, _rejected = clamp_with_warning(
                measured_spread,
                field_name="spread_bps",
                pair=pair,
                bounds=bounds.spread_bps,
                reject_threshold=bounds.reject_threshold_multiplier,
            )
            if w:
                warnings.append(w)
        else:
            spread_bps = measured_spread
        # Audit 2026-05-14 W2 fix : preserver le tier returne par la fonction
        # `measure_spread_bps_from_book_snapshot` au lieu d'aplatir vers
        # "MEASURED_FROM_BOOK_SNAPSHOT". Cela rend visible en telemetrie le
        # tier-2 (MEASURED_FROM_BOOK_RECONSTRUCTION) et tier-3
        # (MEASURED_FROM_BOOK_SNAPSHOT_STALE) — important pour distinguer
        # une mesure dense (silver dense) d'une mesure stale 24h sur
        # raw_windows B2. Tous les tiers restent "MEASURED_*" donc
        # downstream traite ces valeurs comme mesurees (pas REPLAY_PROXY).
        spread_provenance = spread_status
        if spread_status == "MEASURED_FROM_BOOK_SNAPSHOT_STALE":
            warnings.append(f"SPREAD_MEASURED_STALE:{spread_status}")
        elif spread_status == "MEASURED_FROM_BOOK_RECONSTRUCTION":
            warnings.append(f"SPREAD_MEASURED_RECONSTRUCTED:{spread_status}")
    else:
        spread_bps = DEFAULT_SPREAD_BPS_BY_BOOK_STATUS.get(book_status, 0.0)
        spread_provenance = "DEFAULT_BY_BOOK_STATUS"
        warnings.append(f"SPREAD_FALLBACK:{spread_status}")

    # ------------------------------------------------------------------
    # 2. EXPECTED EDGE — gouverne si edge model/override, proxy sinon.
    # ------------------------------------------------------------------
    if expected_edge_bps_override is not None and expected_edge_bps_override >= 0.0:
        expected_edge_bps = expected_edge_bps_override
        expected_edge_provenance = "MEASURED_FROM_EDGE_MODEL_OVERRIDE"
        expected_edge_model_status = "EXPECTED_EDGE_MODEL_OVERRIDE"
    elif expected_edge_model is not None:
        try:
            edge_estimate = expected_edge_model.estimate_expected_edge_bps(
                pair=pair,
                timeframe=timeframe,
                timestamp_ms=timestamp_ms,
                feature_values=expected_edge_feature_values,
                route_features=expected_edge_route_features,
            )
        except Exception as exc:  # noqa: BLE001 - governed rail must fail closed.
            expected_edge_bps = 0.0
            expected_edge_provenance = f"EDGE_MODEL_BLOCKED:ESTIMATE_FAILED_{type(exc).__name__}"
            expected_edge_model_status = "GOVERNED_EDGE_MODEL_BLOCKED"
            warnings.append(f"EDGE_MODEL_ESTIMATE_FAILED:{type(exc).__name__}")
        else:
            raw_edge = float(getattr(edge_estimate, "edge_bps", 0.0) or 0.0)
            edge_status = str(getattr(edge_estimate, "detector_status", "") or "")
            expected_edge_model_status = str(
                getattr(edge_estimate, "model_status", "") or edge_status or "GOVERNED_EDGE_MODEL_EVALUATED"
            )
            expected_edge_model_artifact_hash = getattr(edge_estimate, "artifact_hash", None)
            expected_edge_model_feature_hash = getattr(edge_estimate, "feature_hash", None)
            if expected_edge_model_artifact_hash is None:
                expected_edge_model_artifact_hash = getattr(
                    expected_edge_model, "artifact_hash", None
                )
            if expected_edge_model_feature_hash is None:
                expected_edge_model_feature_hash = getattr(
                    expected_edge_model, "feature_hash", None
                )
            warnings.extend(tuple(getattr(edge_estimate, "warnings", ()) or ()))
            if edge_status == "GOVERNED_EDGE_MODEL_READY":
                if apply_pair_bounds:
                    expected_edge_bps, w, _rejected = clamp_with_warning(
                        raw_edge,
                        field_name="edge_bps",
                        pair=pair,
                        bounds=bounds.edge_bps,
                        reject_threshold=bounds.reject_threshold_multiplier,
                    )
                    if w:
                        warnings.append(w)
                else:
                    expected_edge_bps = raw_edge
                expected_edge_provenance = str(
                    getattr(edge_estimate, "provenance", "")
                    or "GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH"
                )
            else:
                expected_edge_bps = 0.0
                expected_edge_provenance = (
                    str(getattr(edge_estimate, "provenance", "") or "")
                    or f"EDGE_MODEL_BLOCKED:{edge_status or 'UNKNOWN'}"
                )
                warnings.append(f"EDGE_MODEL_BLOCKED:{edge_status or 'UNKNOWN'}")
        if not is_expected_edge_backtest_truth(expected_edge_provenance):
            warnings.append(f"EDGE_MODEL_NOT_BACKTEST_TRUTH:{expected_edge_provenance}")
    elif expected_edge_model_required:
        expected_edge_model_status = (
            expected_edge_model_load_status or "GOVERNED_EDGE_MODEL_NOT_LOADED"
        )
        warnings.append(f"EDGE_MODEL_BLOCKED:{expected_edge_model_status}")
        if raw_ohlcv_path is not None:
            edge_estimate = estimate_forward_return_edge_bps(
                raw_ohlcv_path=raw_ohlcv_path,
                timestamp_ms=timestamp_ms,
                lookback_ms=edge_lookback_ms,
            )
            if edge_estimate.detector_status == "MEASURED":
                raw_edge = edge_estimate.edge_bps
                if apply_pair_bounds:
                    expected_edge_bps, w, _rejected = clamp_with_warning(
                        raw_edge,
                        field_name="edge_bps",
                        pair=pair,
                        bounds=bounds.edge_bps,
                        reject_threshold=bounds.reject_threshold_multiplier,
                    )
                    if w:
                        warnings.append(w)
                else:
                    expected_edge_bps = raw_edge
                expected_edge_provenance = edge_estimate.provenance
                warnings.append(f"EDGE_PROXY_BLOCKED:{expected_edge_provenance}")
            else:
                expected_edge_bps = DEFAULT_EXPECTED_EDGE_BPS
                expected_edge_provenance = "DEFAULT_TO_CALIBRATE"
                warnings.append(f"EDGE_FALLBACK:{edge_estimate.detector_status}")
        else:
            expected_edge_bps = DEFAULT_EXPECTED_EDGE_BPS
            expected_edge_provenance = "DEFAULT_TO_CALIBRATE"
            warnings.append("EDGE_FALLBACK:OHLCV_PATH_MISSING")
    elif raw_ohlcv_path is not None:
        edge_estimate = estimate_forward_return_edge_bps(
            raw_ohlcv_path=raw_ohlcv_path,
            timestamp_ms=timestamp_ms,
            lookback_ms=edge_lookback_ms,
        )
        if edge_estimate.detector_status == "MEASURED":
            raw_edge = edge_estimate.edge_bps
            if apply_pair_bounds:
                expected_edge_bps, w, _rejected = clamp_with_warning(
                    raw_edge,
                    field_name="edge_bps",
                    pair=pair,
                    bounds=bounds.edge_bps,
                    reject_threshold=bounds.reject_threshold_multiplier,
                )
                if w:
                    warnings.append(w)
            else:
                expected_edge_bps = raw_edge
            expected_edge_provenance = edge_estimate.provenance
            if not is_expected_edge_backtest_truth(expected_edge_provenance):
                warnings.append(f"EDGE_PROXY_BLOCKED:{expected_edge_provenance}")
        else:
            expected_edge_bps = DEFAULT_EXPECTED_EDGE_BPS
            expected_edge_provenance = "DEFAULT_TO_CALIBRATE"
            warnings.append(f"EDGE_FALLBACK:{edge_estimate.detector_status}")
    else:
        expected_edge_bps = DEFAULT_EXPECTED_EDGE_BPS
        expected_edge_provenance = "DEFAULT_TO_CALIBRATE"
        warnings.append("EDGE_FALLBACK:OHLCV_PATH_MISSING")

    # ------------------------------------------------------------------
    # 3. SLIPPAGE — Kyle lambda × standard notional depuis trades
    # ------------------------------------------------------------------
    if slippage_bps_override is not None and slippage_bps_override >= 0.0:
        slippage_bps = slippage_bps_override
        slippage_provenance = "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE"
    elif raw_trade_path is not None and measure_slippage_from_trades:
        kyle_slippage, kyle_status = _measure_slippage_from_kyle_lambda(
            raw_trade_path=raw_trade_path,
            timestamp_ms=timestamp_ms,
            pair=pair or "UNKNOWN",
            lookback_ms=slippage_lookback_ms,
            standard_notional_usdt=standard_notional_usdt,
        )
        if kyle_slippage is not None:
            if apply_pair_bounds:
                slippage_bps, w, _rejected = clamp_with_warning(
                    kyle_slippage,
                    field_name="slippage_bps",
                    pair=pair,
                    bounds=bounds.slippage_bps,
                    reject_threshold=bounds.reject_threshold_multiplier,
                )
                if w:
                    warnings.append(w)
            else:
                slippage_bps = kyle_slippage
            slippage_provenance = "MEASURED_FROM_KYLE_LAMBDA"
        else:
            slippage_bps = DEFAULT_SLIPPAGE_BPS
            slippage_provenance = "DEFAULT_TO_CALIBRATE"
            warnings.append(f"SLIPPAGE_FALLBACK:{kyle_status}")
    elif raw_trade_path is not None:
        slippage_bps = DEFAULT_SLIPPAGE_BPS
        slippage_provenance = "DEFAULT_TO_CALIBRATE"
        warnings.append("SLIPPAGE_DEFERRED_TO_RAW_WINDOW_REPLAY")
    else:
        slippage_bps = DEFAULT_SLIPPAGE_BPS
        slippage_provenance = "DEFAULT_TO_CALIBRATE"
        warnings.append("SLIPPAGE_FALLBACK:TRADE_PATH_MISSING")

    # ------------------------------------------------------------------
    # 4. LATENCY — venue-aware via venue_metadata_registry
    # ------------------------------------------------------------------
    if (
        latency_penalty_bps_override is not None
        and latency_penalty_bps_override >= 0.0
    ):
        latency_penalty_bps = latency_penalty_bps_override
        latency_provenance = "MEASURED_FROM_VENUE_MODEL_OVERRIDE"
    else:
        latency_penalty_bps = venue_metadata.latency_bps_conservative
        latency_provenance = venue_metadata.latency_provenance
        if apply_pair_bounds:
            latency_penalty_bps, w, _rejected = clamp_with_warning(
                latency_penalty_bps,
                field_name="latency_bps",
                pair=pair,
                bounds=bounds.latency_bps,
                reject_threshold=bounds.reject_threshold_multiplier,
            )
            if w:
                warnings.append(w)

    # ------------------------------------------------------------------
    # 5. FEE — venue-aware via venue_metadata_registry
    # ------------------------------------------------------------------
    # En live, le caller doit privilegier `fee_bps_override` depuis
    # BinanceAccountSnapshot.taker_commission (live API account dynamique).
    # Sans override, on utilise les fees publishes du venue resolved.
    if fee_bps_override is not None and fee_bps_override >= 0.0:
        fee_bps = fee_bps_override
        fee_provenance = "MEASURED_FROM_VENUE_API_OVERRIDE"
    else:
        fee_bps = (
            venue_metadata.taker_fee_bps
            if use_taker_fee
            else venue_metadata.maker_fee_bps
        )
        fee_provenance = venue_metadata.fee_provenance
        if apply_pair_bounds:
            fee_bps, w, _rejected = clamp_with_warning(
                fee_bps,
                field_name="fee_bps",
                pair=pair,
                bounds=bounds.fee_bps,
                reject_threshold=bounds.reject_threshold_multiplier,
            )
            if w:
                warnings.append(w)

    return EconomicProvenance(
        expected_edge_bps=expected_edge_bps,
        expected_edge_provenance=expected_edge_provenance,
        spread_bps=spread_bps,
        spread_provenance=spread_provenance,
        slippage_bps=slippage_bps,
        slippage_provenance=slippage_provenance,
        latency_penalty_bps=latency_penalty_bps,
        latency_provenance=latency_provenance,
        fee_bps=fee_bps,
        fee_provenance=fee_provenance,
        measurement_warnings=tuple(warnings),
        expected_edge_model_status=expected_edge_model_status,
        expected_edge_model_artifact_hash=expected_edge_model_artifact_hash,
        expected_edge_model_feature_hash=expected_edge_model_feature_hash,
    )


__all__ = [
    "DEFAULT_EXPECTED_EDGE_BPS",
    "DEFAULT_LATENCY_PENALTY_BPS",
    "DEFAULT_SLIPPAGE_BPS",
    "DEFAULT_SPREAD_BPS_BY_BOOK_STATUS",
    "EconomicProvenance",
    "ExpectedEdgeModelProtocol",
    "compute_economic_provenance",
    "expected_edge_backtest_truth_status",
    "is_expected_edge_backtest_truth",
    "measure_spread_bps_from_book_snapshot",
]
