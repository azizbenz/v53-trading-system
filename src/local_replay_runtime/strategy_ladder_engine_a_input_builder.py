"""Strategy Ladder engine_a input builder — comble la limitation P3a pour
engine_a (Audit 2026-05-07).

Construit un `EngineAInput` COMPLET (incluant les 5 champs structurels REQUIRED)
depuis un raw_window backtest, sans toucher au code des engines.

PHILOSOPHIE ENGINE A (selon doc 20 §13.1) :
  > A = Premium Trend / Initial Expansion : "capter les expansions de tendance
  > premium et les premieres sorties de range nettes."

Engine A vise l'EVENEMENT de premiere mise en mouvement (vs C qui prend la
continuation post-breakout). Les 5 champs structurels REQUIRED sont
documentes dans `engines/engine_a/structure_detector_a.py:25-33` (verbatim
Pydantic comments) :

  direction_score   : [-1, 1] — dominant local direction quality
  continuation_score: [0, 1]  — quality of continuation
  structure_quality : [0, 1]  — overall structure readability
  zone_proximity    : [0, 1]  — proximity to relevant zones (higher = closer)
  trend_stability   : [0, 1]  — stability of the trend

`detect_structure` calcule un score pondere :
  structure_score = 0.30·|direction| + 0.25·continuation + 0.20·quality
                  + 0.10·zone_proximity + 0.15·stability

PHILOSOPHIE PRESERVEE :
- AUCUN fichier dans `src/engines/engine_a/` modifie
- Builder vit dans `local_replay_runtime/` cote caller
- 5 heuristiques OHLCV documentees champ par champ avec leur semantique
- Provenance flag : `engine_a_input_provenance="BUILDER_OHLCV_HEURISTIC_TO_CALIBRATE"`
- Tant que provenance != "ENGINE_A_STRUCTURE_DETECTOR_CANONICAL", la promotion
  doit rester bloquee (audit-ready)

LIMITATION : ce builder n'invente pas de doctrine. Il calcule des aggregats
geometriques OHLCV qui se rapportent strictement aux concepts du detector
existant (direction, continuation, structure_quality, zone_proximity,
trend_stability). Toute autre semantique (regime favorability, pair_health,
flow_coherence) suit ses defaults canoniques.
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass, field
from pathlib import Path


_NS_PER_MS = 1_000_000
_DEFAULT_LOOKBACK_MS = 60 * 60 * 1000  # 1h par defaut, comme engine_c
_ENGINE_A_RECENT_STRUCTURE_MIN_BARS = 3
_ENGINE_A_RECENT_DIRECTION_WEIGHT = 0.70
_ENGINE_A_RECENT_CONTINUATION_WEIGHT = 0.70
_ENGINE_A_RECENT_STRUCTURE_QUALITY_WEIGHT = 0.50
_ENGINE_A_RECENT_TREND_STABILITY_WEIGHT = 0.60


@dataclass(frozen=True)
class EngineAStructureSummary:
    """Resultat heuristique des 5 champs structurels engine_a depuis OHLCV.

    Tous les champs respectent la semantique Pydantic du detector existant.
    """

    direction_score: float  # [-1, 1]
    continuation_score: float  # [0, 1]
    structure_quality: float  # [0, 1]
    zone_proximity: float  # [0, 1]
    trend_stability: float  # [0, 1]
    n_lookback_bars_used: int
    n_in_window_bars_used: int
    detector_status: str  # "DETECTED" / "INSUFFICIENT_BARS" / etc.
    detector_version: str = "engine_a_builder.heuristic.v1"


@dataclass(frozen=True)
class EngineAInputBuilderResult:
    """Resultat audit-ready du builder engine_a."""

    candidate_id: str
    pair: str
    builder_status: str
    structure_summary: EngineAStructureSummary | None
    engine_a_input_payload: dict[str, object] = field(default_factory=dict)
    builder_warnings: tuple[str, ...] = ()
    engine_a_input_provenance: str = "BUILDER_OHLCV_HEURISTIC_TO_CALIBRATE"


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _clamp_signed(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(-1.0, min(1.0, value))


def _cost_preference_score(*, expected_gain: float, expected_cost: float) -> float:
    if not math.isfinite(expected_gain) or expected_gain <= 0.0:
        return 0.0
    if not math.isfinite(expected_cost) or expected_cost < 0.0:
        return 0.0
    return _clamp01((expected_gain - expected_cost) / max(expected_gain, 1e-6))


def _load_ohlcv_in_window(
    raw_ohlcv_path: Path,
    *,
    window_start_ms: int,
    window_end_ms: int,
    lookback_ms: int,
) -> list[dict[str, object]]:
    if not raw_ohlcv_path.exists():
        return []
    rows: list[dict[str, object]] = []
    extended_start = window_start_ms - lookback_ms
    handle_cm = (
        gzip.open(raw_ohlcv_path, "rt", encoding="utf-8-sig")
        if str(raw_ohlcv_path).endswith(".gz")
        else raw_ohlcv_path.open("r", encoding="utf-8-sig")
    )
    with handle_cm as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
                ts = int(row.get("timestamp_ms") or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if extended_start <= ts <= window_end_ms:
                rows.append(row)
    rows.sort(key=lambda r: int(r.get("timestamp_ms") or 0))
    return rows


def _bar_close(row: dict[str, object]) -> float:
    try:
        return float(row.get("close") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bar_open(row: dict[str, object]) -> float:
    try:
        return float(row.get("open") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bar_high(row: dict[str, object]) -> float:
    try:
        return float(row.get("high") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bar_low(row: dict[str, object]) -> float:
    try:
        return float(row.get("low") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _compute_direction_score(bars: list[dict[str, object]]) -> float:
    """direction_score [-1, 1] — dominant local direction quality.

    Heuristique : moyenne des (close - open) / (high - low) sur la fenetre
    consideree. Bars haussiers donnent positif, baissiers negatif. Resultat
    clampe [-1, 1].

    Cela respecte la semantique Pydantic : "dominant local direction quality"
    — direction dominante des bars, normalisee par leur range interne.
    """
    if not bars:
        return 0.0
    contributions: list[float] = []
    for bar in bars:
        o = _bar_open(bar)
        c = _bar_close(bar)
        h = _bar_high(bar)
        low = _bar_low(bar)
        bar_range = max(h - low, 1e-9)
        if o > 0.0:
            contributions.append((c - o) / bar_range)
    if not contributions:
        return 0.0
    return _clamp_signed(sum(contributions) / len(contributions))


def _compute_continuation_score(bars: list[dict[str, object]]) -> float:
    """continuation_score [0, 1] — quality of continuation.

    Heuristique : fraction de bars qui suivent la direction du bar precedent
    (autocorrelation directionnelle). Une suite parfaite de bars dans la
    meme direction donne 1.0 ; 50/50 donne 0.0.

    Semantique alignee : "quality of continuation" = persistance directionnelle.
    """
    if len(bars) < 2:
        return 0.0
    directions: list[int] = []
    for bar in bars:
        c = _bar_close(bar)
        o = _bar_open(bar)
        if c > o:
            directions.append(1)
        elif c < o:
            directions.append(-1)
        else:
            directions.append(0)
    same_direction = 0
    transitions = 0
    for prev, curr in zip(directions, directions[1:]):
        if prev == 0 or curr == 0:
            continue
        transitions += 1
        if prev == curr:
            same_direction += 1
    if transitions == 0:
        return 0.0
    # Map [0, 1] : 50% same = 0.0, 100% same = 1.0
    fraction_same = same_direction / transitions
    return _clamp01(2.0 * (fraction_same - 0.5))


def _compute_structure_quality(bars: list[dict[str, object]]) -> float:
    """structure_quality [0, 1] — overall structure readability.

    Heuristique : 1 - mean_wick_ratio. Un bar "lisible" a peu de mecher (body
    domine). Un bar avec grosses mecher (indecision/noise) baisse la quality.

    wick_ratio = (high - max(open, close)) + (min(open, close) - low)
                / (high - low)

    Semantique alignee : "structure readability" = lisibilite des bars
    individuels (clean directional moves vs noisy choppy bars).
    """
    if not bars:
        return 0.0
    wick_ratios: list[float] = []
    for bar in bars:
        o = _bar_open(bar)
        c = _bar_close(bar)
        h = _bar_high(bar)
        low = _bar_low(bar)
        bar_range = max(h - low, 1e-9)
        body_top = max(o, c)
        body_bottom = min(o, c)
        wick = (h - body_top) + (body_bottom - low)
        wick_ratios.append(wick / bar_range)
    mean_wick = sum(wick_ratios) / len(wick_ratios)
    return _clamp01(1.0 - mean_wick)


def _compute_zone_proximity(
    bars: list[dict[str, object]],
    *,
    last_close: float,
) -> float:
    """zone_proximity [0, 1] — proximity to relevant zones (higher = closer).

    Heuristique : 1 - min(distance_to_local_max, distance_to_local_min) /
                          range_size, clampe [0, 1].

    Une zone "relevant" est un swing high ou swing low recent. Plus on est
    proche d'un de ces extremes, plus zone_proximity est haut.

    Semantique alignee : "proximity to relevant zones" = distance aux niveaux
    structurels (S/R) les plus proches.
    """
    if not bars or last_close <= 0.0:
        return 0.0
    high_max = max(_bar_high(bar) for bar in bars)
    low_min = min(_bar_low(bar) for bar in bars)
    range_size = max(high_max - low_min, 1e-9)
    dist_to_high = abs(high_max - last_close)
    dist_to_low = abs(last_close - low_min)
    closest_dist = min(dist_to_high, dist_to_low)
    proximity = 1.0 - closest_dist / range_size
    return _clamp01(proximity)


def _compute_trend_stability(bars: list[dict[str, object]]) -> float:
    """trend_stability [0, 1] — stability of the trend.

    Heuristique : R² d'une regression lineaire OLS des closes sur l'index
    temporel. R² eleve = trend stable lineaire ; R² faible = chaos.

    Semantique alignee : "stability of the trend" = un trend stable produit
    une serie temporelle des prix bien fittee par une droite.
    """
    if len(bars) < 3:
        return 0.0
    closes = [_bar_close(bar) for bar in bars]
    closes = [c for c in closes if c > 0.0]
    n = len(closes)
    if n < 3:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(closes) / n
    sum_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, closes))
    sum_xx = sum((x - mean_x) ** 2 for x in xs)
    sum_yy = sum((y - mean_y) ** 2 for y in closes)
    if sum_xx <= 0.0 or sum_yy <= 0.0:
        return 0.0
    # Pearson r squared
    r = sum_xy / math.sqrt(sum_xx * sum_yy)
    return _clamp01(r * r)


def derive_engine_a_structure_summary(
    *,
    bars_full: list[dict[str, object]],
    window_start_ms: int,
    window_end_ms: int,
) -> EngineAStructureSummary:
    """Derive les 5 champs structurels engine_a depuis OHLCV bars."""
    lookback_bars = [
        row
        for row in bars_full
        if int(row.get("timestamp_ms") or 0) < window_start_ms
    ]
    in_window_bars = [
        row
        for row in bars_full
        if window_start_ms <= int(row.get("timestamp_ms") or 0) <= window_end_ms
    ]
    # Pour engine A (premium trend), on regarde la combinaison lookback+window
    # comme contexte de detection (le trend doit etre present dans la fenetre
    # et stable).
    combined_bars = lookback_bars + in_window_bars
    if len(combined_bars) < 3:
        return EngineAStructureSummary(
            direction_score=0.0,
            continuation_score=0.0,
            structure_quality=0.0,
            zone_proximity=0.0,
            trend_stability=0.0,
            n_lookback_bars_used=len(lookback_bars),
            n_in_window_bars_used=len(in_window_bars),
            detector_status="INSUFFICIENT_BARS",
        )

    combined_direction = _compute_direction_score(combined_bars)
    combined_continuation = _compute_continuation_score(combined_bars)
    combined_structure_quality = _compute_structure_quality(combined_bars)
    combined_trend_stability = _compute_trend_stability(combined_bars)
    direction_score = combined_direction
    continuation_score = combined_continuation
    structure_quality = combined_structure_quality
    trend_stability = combined_trend_stability

    if len(in_window_bars) >= _ENGINE_A_RECENT_STRUCTURE_MIN_BARS:
        # Engine A cherche la toute premiere expansion propre. Le lookback doit
        # fournir le contexte, mais il ne doit pas noyer un breakout recent
        # lisible dans une moyenne d'une heure potentiellement choppy.
        in_window_direction = _compute_direction_score(in_window_bars)
        in_window_continuation = _compute_continuation_score(in_window_bars)
        in_window_structure_quality = _compute_structure_quality(in_window_bars)
        in_window_trend_stability = _compute_trend_stability(in_window_bars)
        direction_score = _clamp_signed(
            (
                (1.0 - _ENGINE_A_RECENT_DIRECTION_WEIGHT) * combined_direction
                + _ENGINE_A_RECENT_DIRECTION_WEIGHT * in_window_direction
            )
        )
        continuation_score = _clamp01(
            (
                (1.0 - _ENGINE_A_RECENT_CONTINUATION_WEIGHT) * combined_continuation
                + _ENGINE_A_RECENT_CONTINUATION_WEIGHT * in_window_continuation
            )
        )
        structure_quality = _clamp01(
            (
                (1.0 - _ENGINE_A_RECENT_STRUCTURE_QUALITY_WEIGHT)
                * combined_structure_quality
                + _ENGINE_A_RECENT_STRUCTURE_QUALITY_WEIGHT
                * in_window_structure_quality
            )
        )
        trend_stability = _clamp01(
            (
                (1.0 - _ENGINE_A_RECENT_TREND_STABILITY_WEIGHT)
                * combined_trend_stability
                + _ENGINE_A_RECENT_TREND_STABILITY_WEIGHT
                * in_window_trend_stability
            )
        )

    last_close = _bar_close(combined_bars[-1])

    summary = EngineAStructureSummary(
        direction_score=direction_score,
        continuation_score=continuation_score,
        structure_quality=structure_quality,
        zone_proximity=_compute_zone_proximity(combined_bars, last_close=last_close),
        trend_stability=trend_stability,
        n_lookback_bars_used=len(lookback_bars),
        n_in_window_bars_used=len(in_window_bars),
        detector_status="DETECTED",
    )
    return summary


def build_engine_a_input_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_ohlcv_path: Path | str | None,
    microstructure_updates: dict[str, float | None] | None = None,
    expected_gain: float = 0.0,
    expected_cost: float = 0.0,
    candidate_size: float = 0.0,
    lookback_ms: int = _DEFAULT_LOOKBACK_MS,
    scoring_version: str = "engine_a.builder.v1",
) -> EngineAInputBuilderResult:
    """Construit un EngineAInput.model_validate-compatible depuis raw_window.

    Combine :
      - Heuristique OHLCV pour les 5 champs structurels REQUIRED
      - Microstructure additif (depuis le pont engine_a) :
        ofi_flow_score, realized_kernel_vol_scale, realized_vol_current,
        kyle_lambda_cost_uplift
      - Defaults canoniques pour regime/health/freshness/coherence (0.5)

    Le caller peut alors faire `run_engine_a(EngineAInput(**payload))`.
    """
    warnings: list[str] = []

    if raw_ohlcv_path is None:
        warnings.append("OHLCV_PATH_MISSING")
        return EngineAInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_A_INPUT_BUILDER_FAILED_NO_OHLCV",
            structure_summary=None,
            engine_a_input_payload={},
            builder_warnings=tuple(warnings),
        )

    ohlcv_path = Path(raw_ohlcv_path)
    if not ohlcv_path.exists():
        warnings.append(f"OHLCV_PATH_NOT_FOUND:{ohlcv_path}")
        return EngineAInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_A_INPUT_BUILDER_FAILED_NO_OHLCV",
            structure_summary=None,
            engine_a_input_payload={},
            builder_warnings=tuple(warnings),
        )

    try:
        bars = _load_ohlcv_in_window(
            ohlcv_path,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            lookback_ms=lookback_ms,
        )
    except OSError as exc:
        warnings.append(f"OHLCV_LOAD_FAILED:{type(exc).__name__}")
        return EngineAInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_A_INPUT_BUILDER_FAILED_OHLCV_IO",
            structure_summary=None,
            engine_a_input_payload={},
            builder_warnings=tuple(warnings),
        )

    summary = derive_engine_a_structure_summary(
        bars_full=bars,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
    )
    if summary.detector_status != "DETECTED":
        warnings.append(f"STRUCTURE_NOT_DETECTED:{summary.detector_status}")

    last_close = 0.0
    if bars:
        last_close = _bar_close(bars[-1])

    # Construction du payload EngineAInput.model_validate-compatible
    payload: dict[str, object] = {
        "pair": pair,
        # 5 champs structurels REQUIRED
        "direction_score": summary.direction_score,
        "continuation_score": summary.continuation_score,
        "structure_quality": summary.structure_quality,
        "zone_proximity": summary.zone_proximity,
        "trend_stability": summary.trend_stability,
        # Defaults canoniques (regime/health/freshness/coherence)
        "regime": "",
        "regime_favorability": 0.5,
        "regime_confidence": 0.5,
        "pair_health": 0.5,
        "data_freshness": 0.5,
        "flow_coherence": 0.5,
        "flow_score": 0.0,
        # Cost/economics — caller fournit ou defaults
        "expected_gain": expected_gain,
        "expected_cost": expected_cost,
        "cost_preference_score": _cost_preference_score(
            expected_gain=expected_gain,
            expected_cost=expected_cost,
        ),
        "candidate_size": candidate_size,
        # Prix
        "entry_price": last_close,
        "atr": 0.0,
        "scoring_version": scoring_version,
    }

    # Merge microstructure additive seam (depuis le pont engine_a)
    if microstructure_updates:
        for key in (
            "flow_score",
            "ofi_flow_score",
            "realized_kernel_vol_scale",
            "realized_vol_current",
            "kyle_lambda_cost_uplift",
        ):
            value = microstructure_updates.get(key)
            if value is not None:
                payload[key] = value

    if summary.detector_status == "DETECTED":
        builder_status = "ENGINE_A_INPUT_BUILDER_READY"
    else:
        builder_status = "ENGINE_A_INPUT_BUILDER_INSUFFICIENT_BARS"

    return EngineAInputBuilderResult(
        candidate_id=candidate_id,
        pair=pair,
        builder_status=builder_status,
        structure_summary=summary,
        engine_a_input_payload=payload,
        builder_warnings=tuple(warnings),
    )


__all__ = [
    "EngineAInputBuilderResult",
    "EngineAStructureSummary",
    "build_engine_a_input_from_window",
    "derive_engine_a_structure_summary",
]
