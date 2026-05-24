"""Strategy Ladder engine-native bridge — pont microstructure (Audit 2026-05-06 P3a).

Ce module est le pont entre les artefacts raw_windows produits par le rail
Strategy Ladder et le seam canonique microstructure
(`data_backbone.microstructure`). Il lit les fichiers JSONL bruts (trades,
orderbook snapshots + deltas, OHLCV) et calcule les 5 records canoniques
utilises par les engine runners A/B/C/D.

ARCHITECTURE BOOK (2026-05-07 fix) : OFI et QueuePressure exigent une serie
d'etats de book consecutifs. Les fichiers `orderbook_snapshot/` ne contiennent
que ~2 snapshots/jour (sparse), donc une fenetre 5min y attrape rarement
plus d'un snapshot. La solution canonique est de :
  1. Identifier le snapshot le plus recent <= window_start_ms
  2. Charger les deltas applicables (update_id > snapshot.update_id) jusqu'a window_end_ms
  3. Appliquer les deltas sequentiellement pour reconstruire l'etat book event-par-event
  4. A chaque delta dans la fenetre, capturer l'etat top-of-book / top-k

Le pont produit ainsi N etats book consecutifs (typiquement 100-1000+) au lieu
d'un unique snapshot, debloquant le calcul OFI et donnant une mesure robuste
de QueuePressure sur la fenetre.

LIMITATION P3a : ce module ne fait pas l'invocation finale `run_engine_c`,
parce qu'EngineCInput requiert 7 champs structurels (breakout_strength,
range_quality, compression_quality, volume_confirmation, followthrough_room,
extension_pct, retrace_risk) qui n'ont pas encore de structure-resolver
canonique cote caller. Le pont produit donc seulement :
  - les 5 records microstructure
  - une composition partielle d'input via compose_engine_c_input_payload

Le call final `run_engine_c(EngineCInput.model_validate(payload))` reste
bloque tant que le structure-resolver n'est pas livre (session future).
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path

from data_backbone.microstructure.engine_input_provenance import (
    build_engine_a_runner_microstructure_updates,
    compose_engine_c_input_payload,
    compose_engine_d_input_payload,
)
from data_backbone.microstructure.kyle_lambda import (
    KyleLambdaRecord,
    KyleTradePoint,
    compute_kyle_lambda,
)
from data_backbone.microstructure.order_flow_imbalance import (
    OrderBookTopLevelPoint,
    OrderFlowImbalanceRecord,
    compute_order_flow_imbalance,
)
from data_backbone.microstructure.queue_pressure import (
    QueuePressureBookPoint,
    QueuePressureRecord,
    compute_queue_pressure,
)
from data_backbone.microstructure.realized_kernel_vol import (
    RealizedKernelPricePoint,
    RealizedKernelVolRecord,
    compute_realized_kernel_vol,
)
from data_backbone.microstructure.vpin import (
    VpinRecord,
    VpinTradePoint,
    compute_vpin,
)


_NS_PER_MS = 1_000_000
_DEFAULT_VPIN_BUCKETS_PER_DAY = 50  # TO_CALIBRATE: pair-specific buckets/day
# Si window etroit, on charge aussi les snapshots juste avant pour fournir au
# moins 2 points consecutifs a OFI (sinon OFI_INSUFFICIENT_BOOK).
_OFI_PREWINDOW_LOOKBACK_MS = 60_000

_MICROSTRUCTURE_RECORD_CACHE: dict[tuple[object, ...], tuple[object, ...]] = {}


def _path_cache_signature(path_like: Path | str | None) -> tuple[str, int | None, int | None]:
    if path_like is None:
        return ("", None, None)
    path = Path(path_like)
    try:
        resolved = path.resolve()
        stat = resolved.stat()
    except OSError:
        return (str(path), None, None)
    return (str(resolved), stat.st_mtime_ns, stat.st_size)


@dataclass(frozen=True)
class EngineNativeBridgeResult:
    """Résultat audit-ready du pont microstructure pour un raw_window."""

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    # Audit 2026-05-07 fix : decompose la statistique book pour montrer la
    # reconstruction sequentielle (snapshots + deltas → states).
    n_book_snapshots_loaded: int = 0  # snapshots disponibles dans le fichier
    n_book_deltas_loaded: int = 0  # deltas charges depuis update_id du base snap
    n_book_states_reconstructed: int = 0  # etats produits dans la fenetre
    kyle_lambda_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_vol_record: RealizedKernelVolRecord | None = None
    engine_c_partial_input_payload: dict[str, object] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        return sum(
            1
            for record in (
                self.kyle_lambda_record,
                self.vpin_record,
                self.ofi_record,
                self.queue_pressure_record,
                self.realized_kernel_vol_record,
            )
            if record is not None
        )


def _iter_jsonl(path: Path) -> list[dict[str, object]]:
    """Charge un JSONL ligne par ligne en ignorant les lignes vides."""
    if not path.exists():
        return []
    out: list[dict[str, object]] = []
    opener = (
        lambda: gzip.open(path, "rt", encoding="utf-8-sig")
        if str(path).endswith(".gz")
        else path.open("r", encoding="utf-8-sig")
    )
    with opener() as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                out.append(json.loads(stripped))
            except json.JSONDecodeError:
                continue
    return out


def _load_trades_in_window(
    raw_trade_path: Path,
    *,
    window_start_ms: int,
    window_end_ms: int,
) -> list[dict[str, object]]:
    """Charge les trades dont le timestamp_ms tombe dans [window_start_ms, window_end_ms]."""
    rows = _iter_jsonl(raw_trade_path)
    in_window: list[dict[str, object]] = []
    for row in rows:
        ts = row.get("timestamp_ms")
        if not isinstance(ts, (int, float)):
            continue
        if window_start_ms <= int(ts) <= window_end_ms:
            in_window.append(row)
    return in_window


def _trade_flow_score_from_window(trades: list[dict[str, object]]) -> float | None:
    buy_qty = 0.0
    sell_qty = 0.0
    for row in trades:
        side = str(row.get("side") or "").strip().lower()
        try:
            qty = float(row.get("qty") or row.get("quantity") or 0.0)
        except (TypeError, ValueError):
            continue
        if qty <= 0.0:
            continue
        if side == "buy":
            buy_qty += qty
        elif side == "sell":
            sell_qty += qty
    total_qty = buy_qty + sell_qty
    if total_qty <= 0.0:
        return None
    imbalance = (buy_qty - sell_qty) / total_qty
    return max(0.0, min(1.0, 0.5 + 0.5 * imbalance))


def _resolve_book_delta_path(
    raw_book_path: Path | str,
    raw_book_delta_path: Path | str | None,
) -> Path | None:
    """Retourne le chemin vers le fichier deltas orderbook.

    Si `raw_book_delta_path` est fourni, l'utilise directement. Sinon, le derive
    depuis `raw_book_path` selon la convention silver canonique (remplacer
    `orderbook_snapshot` par `orderbook_delta` dans le path). Retourne None si
    aucune derivation n'est possible.
    """
    if raw_book_delta_path:
        return Path(raw_book_delta_path)
    if not raw_book_path:
        return None
    snap_str = str(raw_book_path)
    if "orderbook_snapshot" not in snap_str:
        return None
    derived = snap_str.replace("orderbook_snapshot", "orderbook_delta")
    return Path(derived)


def _select_base_snapshot(
    snapshots: list[dict[str, object]],
    *,
    window_start_ms: int,
) -> dict[str, object] | None:
    """Selectionne le snapshot le plus recent dont timestamp_ms <= window_start_ms.

    Si aucun snapshot avant la fenetre, retourne le plus recent disponible
    (fallback degrade) — la reconstruction reste possible mais part d'un etat
    posterieur a la fenetre, ce qui donnera des resultats partiels.
    """
    if not snapshots:
        return None
    eligible = [
        snap
        for snap in snapshots
        if isinstance(snap.get("timestamp_ms"), (int, float))
        and int(snap["timestamp_ms"]) <= window_start_ms
    ]
    if eligible:
        return max(eligible, key=lambda s: int(s["timestamp_ms"]))
    # Fallback : tous les snapshots sont apres window_start_ms
    return min(
        snapshots,
        key=lambda s: int(s.get("timestamp_ms") or 0),
    )


@dataclass(frozen=True)
class _BookState:
    """Etat instantane top-of-book + top-k apres application d'un delta."""

    timestamp_ms: int
    update_id: int
    bid_levels: tuple[tuple[float, float], ...]  # (price, size) tries desc par price
    ask_levels: tuple[tuple[float, float], ...]  # (price, size) tries asc par price


def _reconstruct_book_states(
    *,
    base_snapshot: dict[str, object],
    deltas: list[dict[str, object]],
    window_start_ms: int,
    window_end_ms: int,
    top_k: int = 20,
) -> list[_BookState]:
    """Reconstruit la sequence d'etats book par application sequentielle des deltas.

    Convention orderbook (Bybit/standard) :
      - delta[price, size] avec size > 0 : level mis a jour ou ajoute
      - delta[price, "0"] ou size == 0 : level supprime
      - update_id strictement croissant ; on ne traite que les deltas dont
        update_id > base_snapshot.update_id

    Emet un _BookState seulement pour les deltas dont timestamp_ms est dans
    [window_start_ms, window_end_ms], mais APPLIQUE tous les deltas posterieurs
    au snapshot (y compris pre-fenetre) pour rester aligne sur l'etat reel.
    """
    bid_book: dict[float, float] = {}
    ask_book: dict[float, float] = {}
    base_update_id = int(base_snapshot.get("update_id") or 0)

    # Charger l'etat initial depuis le snapshot
    for level in base_snapshot.get("bids") or []:
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if size > 0.0:
            bid_book[price] = size
    for level in base_snapshot.get("asks") or []:
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if size > 0.0:
            ask_book[price] = size

    # Trier les deltas par update_id croissant
    def _delta_update_id(d: dict[str, object]) -> int:
        try:
            return int(d.get("update_id") or 0)
        except (TypeError, ValueError):
            return 0

    sorted_deltas = sorted(deltas, key=_delta_update_id)
    states: list[_BookState] = []

    for delta in sorted_deltas:
        delta_update_id = _delta_update_id(delta)
        if delta_update_id <= base_update_id:
            continue
        ts = delta.get("timestamp_ms")
        if not isinstance(ts, (int, float)):
            continue
        delta_ts_ms = int(ts)
        if delta_ts_ms > window_end_ms:
            break

        # Appliquer le delta
        for level in delta.get("bids") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                bid_book.pop(price, None)
            else:
                bid_book[price] = size
        for level in delta.get("asks") or []:
            try:
                price = float(level[0])
                size = float(level[1])
            except (TypeError, ValueError, IndexError):
                continue
            if size <= 0.0:
                ask_book.pop(price, None)
            else:
                ask_book[price] = size

        # Capturer un etat seulement si le delta est dans la fenetre
        if delta_ts_ms < window_start_ms:
            continue

        # Top-k ordonne (bids desc, asks asc)
        sorted_bids = sorted(bid_book.items(), key=lambda x: -x[0])[:top_k]
        sorted_asks = sorted(ask_book.items(), key=lambda x: x[0])[:top_k]
        if not sorted_bids or not sorted_asks:
            continue
        states.append(
            _BookState(
                timestamp_ms=delta_ts_ms,
                update_id=delta_update_id,
                bid_levels=tuple(sorted_bids),
                ask_levels=tuple(sorted_asks),
            )
        )

    return states


def _load_book_snapshots(raw_book_path: Path) -> list[dict[str, object]]:
    """Charge tous les snapshots du fichier (n'est pas filtre par fenetre :
    on a besoin du snapshot le plus recent <= window_start_ms)."""
    return _iter_jsonl(raw_book_path)


def _load_book_deltas_in_window_with_lookback(
    raw_book_delta_path: Path,
    *,
    base_update_id: int,
    window_end_ms: int,
) -> list[dict[str, object]]:
    """Charge les deltas dont update_id > base_update_id et timestamp_ms <= window_end_ms."""
    out: list[dict[str, object]] = []
    if not raw_book_delta_path.exists():
        return out
    opener = (
        lambda: gzip.open(raw_book_delta_path, "rt", encoding="utf-8-sig")
        if str(raw_book_delta_path).endswith(".gz")
        else raw_book_delta_path.open("r", encoding="utf-8-sig")
    )
    with opener() as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
                uid = int(row.get("update_id") or 0)
                ts = row.get("timestamp_ms")
                if not isinstance(ts, (int, float)):
                    continue
                ts_ms = int(ts)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if ts_ms > window_end_ms:
                break
            if uid > base_update_id:
                out.append(row)
    return out


def _build_kyle_trade_points(
    trades: list[dict[str, object]],
) -> list[KyleTradePoint]:
    points: list[KyleTradePoint] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
            volume = float(row.get("qty") or row.get("volume") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0 or volume <= 0.0:
            continue
        points.append(
            KyleTradePoint(
                timestamp_ns=ts_ms * _NS_PER_MS,
                price=price,
                volume=volume,
                mid_price=None,
            )
        )
    return points


def _build_vpin_trade_points(
    trades: list[dict[str, object]],
) -> list[VpinTradePoint]:
    points: list[VpinTradePoint] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
            volume = float(row.get("qty") or row.get("volume") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0 or volume <= 0.0:
            continue
        points.append(
            VpinTradePoint(
                timestamp_ns=ts_ms * _NS_PER_MS,
                price=price,
                volume=volume,
            )
        )
    return points


def _book_state_to_ofi_point(state: _BookState) -> OrderBookTopLevelPoint | None:
    """Extrait le top-of-book d'un _BookState reconstruit pour OFI."""
    if not state.bid_levels or not state.ask_levels:
        return None
    bid_price, bid_size = state.bid_levels[0]
    ask_price, ask_size = state.ask_levels[0]
    if bid_price <= 0.0 or ask_price <= 0.0 or ask_price < bid_price:
        return None
    try:
        return OrderBookTopLevelPoint(
            timestamp_ns=state.timestamp_ms * _NS_PER_MS,
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
        )
    except Exception:  # noqa: BLE001
        return None


def _book_state_to_queue_pressure_point(
    state: _BookState,
    *,
    top_k: int = 5,
) -> QueuePressureBookPoint | None:
    """Extrait top-k bid/ask sizes d'un _BookState pour QueuePressure."""
    if not state.bid_levels or not state.ask_levels:
        return None
    try:
        bid_sizes = tuple(size for _, size in state.bid_levels[:top_k])
        ask_sizes = tuple(size for _, size in state.ask_levels[:top_k])
    except (TypeError, ValueError):
        return None
    if not bid_sizes or not ask_sizes:
        return None
    return QueuePressureBookPoint(
        timestamp_ns=state.timestamp_ms * _NS_PER_MS,
        bid_sizes=bid_sizes,
        ask_sizes=ask_sizes,
    )


def _build_realized_kernel_price_points(
    trades: list[dict[str, object]],
) -> list[RealizedKernelPricePoint]:
    points: list[RealizedKernelPricePoint] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0:
            continue
        points.append(
            RealizedKernelPricePoint(
                timestamp_ns=ts_ms * _NS_PER_MS,
                price=price,
            )
        )
    return points


def build_engine_c_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None = None,
    base_payload: dict[str, object] | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> EngineNativeBridgeResult:
    """Pont microstructure pour engine_c sur une fenêtre raw_window.

    Calcule les 5 records canoniques (Kyle, VPIN, OFI, QueuePressure,
    RealizedKernelVol) puis compose un input PARTIEL engine_c via
    `compose_engine_c_input_payload`. L'input final n'est pas
    `EngineCInput.model_validate()`-compatible tant que les 7 champs
    structurels (breakout_strength, range_quality, ...) ne sont pas
    fournis par un structure-resolver canonique.

    Tous les records sont None individuellement si leurs inputs sont
    insuffisants (window vide, pas de trades, pas de book, etc.).
    Le `bridge_status` documente le statut global.
    """

    warnings: list[str] = []
    trades_raw: list[dict[str, object]] = []
    book_states: list[_BookState] = []
    book_snapshots_count = 0
    book_deltas_count = 0

    # Étape 1a : trades dans la fenêtre
    if raw_trade_path:
        try:
            trades_raw = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    # Étape 1b : reconstruction séquentielle du book via snapshot + deltas.
    # On utilise raw_book_delta_path explicite si fourni, sinon on derive depuis
    # raw_book_path par convention silver canonique (orderbook_snapshot →
    # orderbook_delta dans le path).
    if raw_book_path:
        try:
            snapshots = _load_book_snapshots(Path(raw_book_path))
            book_snapshots_count = len(snapshots)
            base_snap = _select_base_snapshot(
                snapshots, window_start_ms=window_start_ms
            )
            if base_snap is None:
                warnings.append("BOOK_NO_SNAPSHOT_AVAILABLE")
            else:
                base_uid = int(base_snap.get("update_id") or 0)
                delta_path = _resolve_book_delta_path(
                    raw_book_path, raw_book_delta_path
                )
                if delta_path is None or not delta_path.exists():
                    warnings.append(
                        f"BOOK_DELTA_PATH_MISSING:{delta_path}"
                    )
                else:
                    deltas = _load_book_deltas_in_window_with_lookback(
                        delta_path,
                        base_update_id=base_uid,
                        window_end_ms=window_end_ms,
                    )
                    book_deltas_count = len(deltas)
                    book_states = _reconstruct_book_states(
                        base_snapshot=base_snap,
                        deltas=deltas,
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        top_k=20,
                    )
        except OSError as exc:
            warnings.append(f"BOOK_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("BOOK_PATH_MISSING")

    # Étape 2 : calcule les 5 records (chaque échec → record=None + warning)
    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_record: RealizedKernelVolRecord | None = None

    kyle_points = _build_kyle_trade_points(trades_raw)
    if len(kyle_points) >= 2:
        try:
            window_seconds = max(1.0, (window_end_ms - window_start_ms) / 1000.0)
            kyle_record = compute_kyle_lambda(
                kyle_points,
                pair=pair,
                window_seconds=window_seconds,
                bucket_seconds=min(60.0, window_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"KYLE_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"KYLE_INSUFFICIENT_TRADES:{len(kyle_points)}")

    vpin_points = _build_vpin_trade_points(trades_raw)
    if len(vpin_points) >= 1:
        try:
            vpin_record = compute_vpin(
                vpin_points,
                pair=pair,
                buckets_per_day=vpin_buckets_per_day,
                allow_derived_daily_volume=True,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"VPIN_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append("VPIN_NO_TRADES")

    # OFI sur la sequence d'etats reconstruits (top-of-book event-par-event).
    ofi_points: list[OrderBookTopLevelPoint] = []
    for state in book_states:
        point = _book_state_to_ofi_point(state)
        if point is not None:
            ofi_points.append(point)
    if len(ofi_points) >= 2:
        try:
            ofi_record = compute_order_flow_imbalance(
                ofi_points,
                pair=pair,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"OFI_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(
            f"OFI_INSUFFICIENT_BOOK_STATES:{len(ofi_points)}/"
            f"states={len(book_states)}/snaps={book_snapshots_count}/"
            f"deltas={book_deltas_count}"
        )

    # QueuePressure sur le dernier etat reconstruit dans la fenetre
    if book_states:
        latest_state = book_states[-1]
        queue_point = _book_state_to_queue_pressure_point(latest_state, top_k=5)
        if queue_point is not None:
            try:
                queue_pressure_record = compute_queue_pressure(
                    queue_point,
                    pair=pair,
                    top_k=5,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"QUEUE_PRESSURE_FAILED:{type(exc).__name__}:{exc}")
        else:
            warnings.append("QUEUE_PRESSURE_BOOK_STATE_BUILD_FAILED")
    else:
        warnings.append("QUEUE_PRESSURE_NO_BOOK_STATES")

    rk_points = _build_realized_kernel_price_points(trades_raw)
    if len(rk_points) >= 2:
        try:
            realized_kernel_record = compute_realized_kernel_vol(
                rk_points,
                pair=pair,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"REALIZED_KERNEL_VOL_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"REALIZED_KERNEL_VOL_INSUFFICIENT_PRICES:{len(rk_points)}")

    # Étape 3 : composition partielle de l'input engine_c.
    # Note : EngineCMicrostructureProvenance.kyle_lambda exige ge=0.0, donc un
    # kyle_record stale avec value <= 0 (non_positive_lambda, slope OLS negatif)
    # ne peut pas etre passe directement. On le filtre avec un warning explicite.
    kyle_for_engine_c: KyleLambdaRecord | None = kyle_record
    if kyle_for_engine_c is not None and (
        kyle_for_engine_c.is_stale or kyle_for_engine_c.value < 0.0
    ):
        warnings.append(
            f"KYLE_FILTERED_FOR_ENGINE_C:stale={kyle_for_engine_c.is_stale}"
            f":value={kyle_for_engine_c.value}"
        )
        kyle_for_engine_c = None

    base = dict(base_payload or {})
    base.setdefault("pair", pair)
    partial_payload: dict[str, object] = {}
    try:
        partial_payload = compose_engine_c_input_payload(
            base,
            pair=pair,
            ofi_record=ofi_record,
            queue_pressure_record=queue_pressure_record,
            vpin_record=vpin_record,
            kyle_lambda_record=kyle_for_engine_c,
            realized_vol_current_record=realized_kernel_record,
            realized_vol_at_break_record=None,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"COMPOSE_ENGINE_C_FAILED:{type(exc).__name__}:{exc}")

    # Statut final
    n_built = sum(
        1
        for r in (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_kernel_record,
        )
        if r is not None
    )
    if n_built == 5:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_built > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineNativeBridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=len(trades_raw),
        n_book_snapshots_loaded=book_snapshots_count,
        n_book_deltas_loaded=book_deltas_count,
        n_book_states_reconstructed=len(book_states),
        kyle_lambda_record=kyle_record,
        vpin_record=vpin_record,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        realized_kernel_vol_record=realized_kernel_record,
        engine_c_partial_input_payload=partial_payload,
        bridge_warnings=tuple(warnings),
    )


# ----------------------------------------------------------------------------
# Helpers internes communs (calcul des records depuis raw_window)
# ----------------------------------------------------------------------------


def _compute_microstructure_records_from_window(
    *,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> tuple[
    KyleLambdaRecord | None,
    VpinRecord | None,
    OrderFlowImbalanceRecord | None,
    QueuePressureRecord | None,
    RealizedKernelVolRecord | None,
    int,  # n_trades_loaded
    int,  # n_book_snapshots_loaded
    int,  # n_book_deltas_loaded
    int,  # n_book_states_reconstructed
    list[str],  # warnings
]:
    """Calcule les 5 records canoniques. Helper partage entre tous les engines."""
    cache_key = (
        pair.strip().upper(),
        int(window_start_ms),
        int(window_end_ms),
        _path_cache_signature(raw_trade_path),
        _path_cache_signature(raw_book_path),
        _path_cache_signature(raw_book_delta_path),
        int(vpin_buckets_per_day),
    )
    cached = _MICROSTRUCTURE_RECORD_CACHE.get(cache_key)
    if cached is not None:
        return (
            cached[0],
            cached[1],
            cached[2],
            cached[3],
            cached[4],
            int(cached[5]),
            int(cached[6]),
            int(cached[7]),
            int(cached[8]),
            list(cached[9]),
        )
    warnings: list[str] = []
    trades_raw: list[dict[str, object]] = []
    book_states: list[_BookState] = []
    book_snapshots_count = 0
    book_deltas_count = 0

    if raw_trade_path:
        try:
            trades_raw = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    if raw_book_path:
        try:
            snapshots = _load_book_snapshots(Path(raw_book_path))
            book_snapshots_count = len(snapshots)
            base_snap = _select_base_snapshot(
                snapshots, window_start_ms=window_start_ms
            )
            if base_snap is None:
                warnings.append("BOOK_NO_SNAPSHOT_AVAILABLE")
            else:
                base_uid = int(base_snap.get("update_id") or 0)
                delta_path = _resolve_book_delta_path(
                    raw_book_path, raw_book_delta_path
                )
                if delta_path is None or not delta_path.exists():
                    warnings.append(f"BOOK_DELTA_PATH_MISSING:{delta_path}")
                else:
                    deltas = _load_book_deltas_in_window_with_lookback(
                        delta_path,
                        base_update_id=base_uid,
                        window_end_ms=window_end_ms,
                    )
                    book_deltas_count = len(deltas)
                    book_states = _reconstruct_book_states(
                        base_snapshot=base_snap,
                        deltas=deltas,
                        window_start_ms=window_start_ms,
                        window_end_ms=window_end_ms,
                        top_k=20,
                    )
        except OSError as exc:
            warnings.append(f"BOOK_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("BOOK_PATH_MISSING")

    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_record: RealizedKernelVolRecord | None = None

    kyle_points = _build_kyle_trade_points(trades_raw)
    if len(kyle_points) >= 2:
        try:
            window_seconds = max(1.0, (window_end_ms - window_start_ms) / 1000.0)
            kyle_record = compute_kyle_lambda(
                kyle_points,
                pair=pair,
                window_seconds=window_seconds,
                bucket_seconds=min(60.0, window_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"KYLE_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"KYLE_INSUFFICIENT_TRADES:{len(kyle_points)}")

    vpin_points = _build_vpin_trade_points(trades_raw)
    if len(vpin_points) >= 1:
        try:
            vpin_record = compute_vpin(
                vpin_points,
                pair=pair,
                buckets_per_day=vpin_buckets_per_day,
                allow_derived_daily_volume=True,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"VPIN_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append("VPIN_NO_TRADES")

    ofi_points: list[OrderBookTopLevelPoint] = []
    for state in book_states:
        point = _book_state_to_ofi_point(state)
        if point is not None:
            ofi_points.append(point)
    if len(ofi_points) >= 2:
        try:
            ofi_record = compute_order_flow_imbalance(ofi_points, pair=pair)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"OFI_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(
            f"OFI_INSUFFICIENT_BOOK_STATES:{len(ofi_points)}/"
            f"states={len(book_states)}/snaps={book_snapshots_count}/"
            f"deltas={book_deltas_count}"
        )

    if book_states:
        latest_state = book_states[-1]
        queue_point = _book_state_to_queue_pressure_point(latest_state, top_k=5)
        if queue_point is not None:
            try:
                queue_pressure_record = compute_queue_pressure(
                    queue_point, pair=pair, top_k=5
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"QUEUE_PRESSURE_FAILED:{type(exc).__name__}:{exc}")
        else:
            warnings.append("QUEUE_PRESSURE_BOOK_STATE_BUILD_FAILED")
    else:
        warnings.append("QUEUE_PRESSURE_NO_BOOK_STATES")

    rk_points = _build_realized_kernel_price_points(trades_raw)
    if len(rk_points) >= 2:
        try:
            realized_kernel_record = compute_realized_kernel_vol(rk_points, pair=pair)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"REALIZED_KERNEL_VOL_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(f"REALIZED_KERNEL_VOL_INSUFFICIENT_PRICES:{len(rk_points)}")

    result = (
        kyle_record,
        vpin_record,
        ofi_record,
        queue_pressure_record,
        realized_kernel_record,
        len(trades_raw),
        book_snapshots_count,
        book_deltas_count,
        len(book_states),
        warnings,
    )
    _MICROSTRUCTURE_RECORD_CACHE[cache_key] = (
        kyle_record,
        vpin_record,
        ofi_record,
        queue_pressure_record,
        realized_kernel_record,
        len(trades_raw),
        book_snapshots_count,
        book_deltas_count,
        len(book_states),
        tuple(warnings),
    )
    return result


# ----------------------------------------------------------------------------
# Engine D — bridge realized_vol_current + realized_vol_post_close
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineDBridgeResult:
    """Resultat audit-ready du pont microstructure pour engine_d.

    LIMITATION : EngineDInput requiert 8 champs structurels engine-d-specifiques
    (prior_trade_quality, reformation_quality, pullback_quality, continuation_room,
    concentration_headroom, marginal_edge, reentry_lateness, + champs context
    de re-entree). Ces champs n'ont pas de structure-resolver canonique, donc
    `run_engine_d(EngineDInput)` n'est pas invoque ici.
    """

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    n_book_snapshots_loaded: int = 0
    n_book_deltas_loaded: int = 0
    n_book_states_reconstructed: int = 0
    kyle_lambda_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_vol_current_record: RealizedKernelVolRecord | None = None
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None
    engine_d_partial_input_payload: dict[str, object] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        return sum(
            1
            for r in (
                self.kyle_lambda_record,
                self.vpin_record,
                self.ofi_record,
                self.queue_pressure_record,
                self.realized_vol_current_record,
                self.realized_vol_post_close_record,
            )
            if r is not None
        )


def build_engine_d_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None = None,
    raw_book_delta_path: Path | str | None = None,
    post_close_window_end_ms: int | None = None,
    base_payload: dict[str, object] | None = None,
) -> EngineDBridgeResult:
    """Pont microstructure engine_d.

    Calcule realized_vol_current depuis les trades dans [window_start_ms, window_end_ms]
    et realized_vol_post_close depuis les trades dans [window_end_ms,
    post_close_window_end_ms] (si fourni). Compose un input partiel engine_d via
    compose_engine_d_input_payload.
    """
    warnings: list[str] = []
    trades_in_window: list[dict[str, object]] = []
    trades_post_close: list[dict[str, object]] = []

    if raw_trade_path:
        try:
            trades_in_window = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
            if post_close_window_end_ms is not None and post_close_window_end_ms > window_end_ms:
                trades_post_close = _load_trades_in_window(
                    Path(raw_trade_path),
                    window_start_ms=window_end_ms,
                    window_end_ms=post_close_window_end_ms,
                )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    realized_vol_current_record: RealizedKernelVolRecord | None = None
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None
    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    n_book_snapshots = 0
    n_book_deltas = 0
    n_book_states = 0

    rk_current_points = _build_realized_kernel_price_points(trades_in_window)
    if len(rk_current_points) >= 2:
        try:
            realized_vol_current_record = compute_realized_kernel_vol(
                rk_current_points, pair=pair
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"REALIZED_VOL_CURRENT_FAILED:{type(exc).__name__}:{exc}")
    else:
        warnings.append(
            f"REALIZED_VOL_CURRENT_INSUFFICIENT_PRICES:{len(rk_current_points)}"
        )

    if post_close_window_end_ms is not None:
        rk_post_close_points = _build_realized_kernel_price_points(trades_post_close)
        if len(rk_post_close_points) >= 2:
            try:
                realized_vol_post_close_record = compute_realized_kernel_vol(
                    rk_post_close_points, pair=pair
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(
                    f"REALIZED_VOL_POST_CLOSE_FAILED:{type(exc).__name__}:{exc}"
                )
        else:
            warnings.append(
                f"REALIZED_VOL_POST_CLOSE_INSUFFICIENT_PRICES:"
                f"{len(rk_post_close_points)}"
            )
    else:
        warnings.append("REALIZED_VOL_POST_CLOSE_WINDOW_NOT_PROVIDED")

    if raw_book_path is not None or raw_book_delta_path is not None:
        (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            common_realized_record,
            _n_trades,
            n_book_snapshots,
            n_book_deltas,
            n_book_states,
            common_warnings,
        ) = _compute_microstructure_records_from_window(
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            raw_trade_path=raw_trade_path,
            raw_book_path=raw_book_path,
            raw_book_delta_path=raw_book_delta_path,
        )
        if realized_vol_current_record is None:
            realized_vol_current_record = common_realized_record
        warnings.extend(common_warnings)

    base = dict(base_payload or {})
    base.setdefault("pair", pair)
    partial_payload: dict[str, object] = {}
    try:
        partial_payload = compose_engine_d_input_payload(
            base,
            pair=pair,
            realized_vol_current_record=realized_vol_current_record,
            realized_vol_post_close_record=realized_vol_post_close_record,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"COMPOSE_ENGINE_D_FAILED:{type(exc).__name__}:{exc}")

    n_built = sum(
        1
        for r in (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_vol_current_record,
            realized_vol_post_close_record,
        )
        if r is not None
    )
    vol_built = sum(
        1
        for r in (realized_vol_current_record, realized_vol_post_close_record)
        if r is not None
    )
    if vol_built == 2:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_built > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineDBridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=len(trades_in_window),
        n_book_snapshots_loaded=n_book_snapshots,
        n_book_deltas_loaded=n_book_deltas,
        n_book_states_reconstructed=n_book_states,
        kyle_lambda_record=kyle_record,
        vpin_record=vpin_record,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_post_close_record=realized_vol_post_close_record,
        engine_d_partial_input_payload=partial_payload,
        bridge_warnings=tuple(warnings),
    )


# ----------------------------------------------------------------------------
# Engine A — bridge ofi_flow_score + realized_kernel_vol_scale +
#                realized_vol_current + kyle_lambda_cost_uplift
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineABridgeResult:
    """Resultat audit-ready du pont microstructure pour engine_a.

    LIMITATION : EngineAInput requiert ~5 champs structurels REQUIRED
    (direction_score, continuation_score, structure_quality, zone_proximity,
    trend_stability) sans structure-resolver canonique. `run_engine_a()` n'est
    pas invoque ici.
    """

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    n_book_snapshots_loaded: int = 0
    n_book_deltas_loaded: int = 0
    n_book_states_reconstructed: int = 0
    ofi_record: OrderFlowImbalanceRecord | None = None
    vpin_record: VpinRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_vol_record: RealizedKernelVolRecord | None = None
    kyle_lambda_record: KyleLambdaRecord | None = None
    engine_a_microstructure_updates: dict[str, float | None] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        return sum(
            1
            for r in (
                self.ofi_record,
                self.vpin_record,
                self.queue_pressure_record,
                self.realized_kernel_vol_record,
                self.kyle_lambda_record,
            )
            if r is not None
        )


def build_engine_a_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None,
    raw_book_delta_path: Path | str | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> EngineABridgeResult:
    """Pont microstructure engine_a.

    Reutilise les helpers communs pour calculer les records canoniques, puis
    appelle `build_engine_a_runner_microstructure_updates` du seam
    `data_backbone.microstructure.engine_input_provenance` pour produire les
    additive updates aux scalar inputs Engine A :
      - ofi_flow_score, realized_kernel_vol_scale, realized_vol_current,
        kyle_lambda_cost_uplift

    Note : ces additive updates s'appliquent SUR un EngineAInput de base que le
    caller doit construire (avec direction_score, continuation_score, etc.).
    """
    (
        kyle_record,
        vpin_record,
        ofi_record,
        queue_pressure_record,
        realized_kernel_record,
        n_trades,
        n_snaps,
        n_deltas,
        n_states,
        warnings,
    ) = _compute_microstructure_records_from_window(
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=raw_trade_path,
        raw_book_path=raw_book_path,
        raw_book_delta_path=raw_book_delta_path,
        vpin_buckets_per_day=vpin_buckets_per_day,
    )

    # Engine A additive seam updates via le pont canonique. Filtrer Kyle stale
    # comme pour engine_c (EngineAMicrostructureProvenance.kyle_lambda_cost_uplift
    # exige ge=0.0).
    kyle_for_engine_a: KyleLambdaRecord | None = kyle_record
    if kyle_for_engine_a is not None and (
        kyle_for_engine_a.is_stale or kyle_for_engine_a.value < 0.0
    ):
        warnings.append(
            f"KYLE_FILTERED_FOR_ENGINE_A:stale={kyle_for_engine_a.is_stale}"
            f":value={kyle_for_engine_a.value}"
        )
        kyle_for_engine_a = None

    updates: dict[str, float | None] = {}
    try:
        updates = build_engine_a_runner_microstructure_updates(
            pair=pair,
            ofi_record=ofi_record,
            realized_kernel_record=realized_kernel_record,
            kyle_lambda_record=kyle_for_engine_a,
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"BUILD_ENGINE_A_UPDATES_FAILED:{type(exc).__name__}:{exc}")
    if updates.get("ofi_flow_score") is None and raw_trade_path is not None:
        try:
            flow_score = _trade_flow_score_from_window(
                _load_trades_in_window(
                    Path(raw_trade_path),
                    window_start_ms=window_start_ms,
                    window_end_ms=window_end_ms,
                )
            )
        except OSError as exc:
            warnings.append(f"ENGINE_A_TRADE_FLOW_FALLBACK_FAILED:{type(exc).__name__}")
            flow_score = None
        if flow_score is not None:
            updates["flow_score"] = flow_score
            warnings.append("ENGINE_A_FLOW_SCORE_FROM_TRADE_IMBALANCE")

    n_built = sum(
        1
        for r in (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_kernel_record,
        )
        if r is not None
    )
    if n_built == 5:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_built > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineABridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=n_trades,
        n_book_snapshots_loaded=n_snaps,
        n_book_deltas_loaded=n_deltas,
        n_book_states_reconstructed=n_states,
        ofi_record=ofi_record,
        vpin_record=vpin_record,
        queue_pressure_record=queue_pressure_record,
        realized_kernel_vol_record=realized_kernel_record,
        kyle_lambda_record=kyle_record,
        engine_a_microstructure_updates=updates,
        bridge_warnings=tuple(warnings),
    )


# ----------------------------------------------------------------------------
# Engine B — bridge local_mean + local_std + vpin
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineBBridgeResult:
    """Resultat audit-ready du pont engine_b.

    EngineBInput requiert 4 champs : pair, current_price, local_mean, local_std.
    Le bridge calcule current_price (= dernier prix de la fenetre), local_mean
    (= moyenne arithmetique des prix) et local_std (= ecart-type empirique) depuis
    les trades dans la fenetre. VPIN partage le pipeline microstructure commun.

    LIMITATION : les autres champs sweep_score / absorption_score /
    poc_reversion_score / false_breakout_score / execution_fragility /
    market_toxicity / etc. necessitent d'autres modules microstructure
    (walls_and_spoofing, etc.) non cables ici. `run_engine_b()` n'est pas
    invoque ici.
    """

    candidate_id: str
    pair: str
    window_start_ms: int
    window_end_ms: int
    bridge_status: str
    n_trades_loaded: int = 0
    n_book_snapshots_loaded: int = 0
    n_book_deltas_loaded: int = 0
    n_book_states_reconstructed: int = 0
    current_price: float | None = None
    local_mean: float | None = None
    local_std: float | None = None
    kyle_lambda_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_vol_record: RealizedKernelVolRecord | None = None
    engine_b_partial_input_payload: dict[str, object] = field(default_factory=dict)
    bridge_warnings: tuple[str, ...] = ()

    @property
    def n_records_built(self) -> int:
        # Compte les composantes critiques disponibles (price, mean, std, vpin)
        return sum(
            1
            for v in (
                self.current_price,
                self.local_mean,
                self.local_std,
                self.kyle_lambda_record,
                self.vpin_record,
                self.ofi_record,
                self.queue_pressure_record,
                self.realized_kernel_vol_record,
            )
            if v is not None
        )


def _compute_local_mean_std_from_trades(
    trades: list[dict[str, object]],
) -> tuple[float | None, float | None, float | None]:
    """Retourne (current_price, local_mean, local_std) depuis trades dans la fenetre.

    - current_price : prix du dernier trade (par timestamp_ms)
    - local_mean    : moyenne arithmetique des prix (volume-weighted serait
                       preferable mais demande calibration ; ici simple mean)
    - local_std     : ecart-type empirique non-biaise (N-1 denominator)

    Retourne (None, None, None) si moins de 2 trades exploitables.
    """
    prices: list[tuple[int, float]] = []
    for row in trades:
        try:
            ts_ms = int(row["timestamp_ms"])
            price = float(row["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0.0:
            continue
        prices.append((ts_ms, price))
    if len(prices) < 2:
        return None, None, None
    prices.sort(key=lambda x: x[0])
    values = [p for _, p in prices]
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = variance ** 0.5
    current = values[-1]
    return current, mean, std


def build_engine_b_microstructure_inputs_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_book_path: Path | str | None = None,
    raw_book_delta_path: Path | str | None = None,
    base_payload: dict[str, object] | None = None,
    vpin_buckets_per_day: int = _DEFAULT_VPIN_BUCKETS_PER_DAY,
) -> EngineBBridgeResult:
    """Pont microstructure engine_b.

    Calcule current_price, local_mean, local_std depuis les trades dans la fenetre
    et VPIN via le pipeline microstructure commun. Compose un input partiel
    engine_b en respectant les defaults TO_CALIBRATE pour les autres champs.
    """
    warnings: list[str] = []
    trades_in_window: list[dict[str, object]] = []

    if raw_trade_path:
        try:
            trades_in_window = _load_trades_in_window(
                Path(raw_trade_path),
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        except OSError as exc:
            warnings.append(f"TRADE_LOAD_FAILED:{type(exc).__name__}")
    else:
        warnings.append("TRADE_PATH_MISSING")

    current_price, local_mean, local_std = _compute_local_mean_std_from_trades(
        trades_in_window
    )
    if current_price is None:
        warnings.append(
            f"LOCAL_MEAN_STD_INSUFFICIENT_TRADES:{len(trades_in_window)}"
        )

    # VPIN via le pipeline commun (re-utilise sans book — book est optionnel
    # pour engine_b car local_mean/std sont les inputs critiques)
    kyle_record: KyleLambdaRecord | None = None
    vpin_record: VpinRecord | None = None
    ofi_record: OrderFlowImbalanceRecord | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    realized_kernel_record: RealizedKernelVolRecord | None = None
    n_book_snapshots = 0
    n_book_deltas = 0
    n_book_states = 0

    if raw_book_path is not None or raw_book_delta_path is not None:
        (
            kyle_record,
            vpin_record,
            ofi_record,
            queue_pressure_record,
            realized_kernel_record,
            _n_trades,
            n_book_snapshots,
            n_book_deltas,
            n_book_states,
            common_warnings,
        ) = _compute_microstructure_records_from_window(
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            raw_trade_path=raw_trade_path,
            raw_book_path=raw_book_path,
            raw_book_delta_path=raw_book_delta_path,
            vpin_buckets_per_day=vpin_buckets_per_day,
        )
        warnings.extend(common_warnings)
    else:
        vpin_points = _build_vpin_trade_points(trades_in_window)
        if len(vpin_points) >= 1:
            try:
                vpin_record = compute_vpin(
                    vpin_points,
                    pair=pair,
                    buckets_per_day=vpin_buckets_per_day,
                    allow_derived_daily_volume=True,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"VPIN_FAILED:{type(exc).__name__}:{exc}")
        else:
            warnings.append("VPIN_NO_TRADES")

    # Compose payload partiel engine_b (pas de compose_engine_b dans le seam,
    # on construit manuellement en respectant les contraintes Pydantic
    # EngineBInput : pair, current_price>0, local_mean>0, local_std>=0).
    base = dict(base_payload or {})
    base.setdefault("pair", pair)
    if current_price is not None and current_price > 0.0:
        base.setdefault("current_price", current_price)
    if local_mean is not None and local_mean > 0.0:
        base.setdefault("local_mean", local_mean)
    if local_std is not None and local_std >= 0.0:
        base.setdefault("local_std", local_std)
    if vpin_record is not None:
        # EngineBInput.vpin_current : Field(default=None, ge=0.0, le=1.0)
        base.setdefault("vpin_current", vpin_record.value)

    n_critical = sum(
        1
        for v in (current_price, local_mean, local_std, vpin_record)
        if v is not None
    )
    if n_critical == 4:
        bridge_status = "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    elif n_critical > 0:
        bridge_status = "ENGINE_NATIVE_BRIDGE_PARTIAL"
    else:
        bridge_status = "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"

    return EngineBBridgeResult(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        bridge_status=bridge_status,
        n_trades_loaded=len(trades_in_window),
        n_book_snapshots_loaded=n_book_snapshots,
        n_book_deltas_loaded=n_book_deltas,
        n_book_states_reconstructed=n_book_states,
        current_price=current_price,
        local_mean=local_mean,
        local_std=local_std,
        kyle_lambda_record=kyle_record,
        vpin_record=vpin_record,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        realized_kernel_vol_record=realized_kernel_record,
        engine_b_partial_input_payload=base,
        bridge_warnings=tuple(warnings),
    )


__all__ = [
    "EngineNativeBridgeResult",
    "EngineDBridgeResult",
    "EngineABridgeResult",
    "EngineBBridgeResult",
    "build_engine_c_microstructure_inputs_from_window",
    "build_engine_d_microstructure_inputs_from_window",
    "build_engine_a_microstructure_inputs_from_window",
    "build_engine_b_microstructure_inputs_from_window",
]
