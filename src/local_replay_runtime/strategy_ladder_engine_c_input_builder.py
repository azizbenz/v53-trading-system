"""Strategy Ladder engine_c input builder — comble la limitation du pont
microstructure (Audit 2026-05-07 P3a-fix).

Ce module construit un `EngineCInput` COMPLET (incluant les 7 champs
structurels REQUIRED) depuis un raw_window backtest, sans toucher au code
des engines. Il s'aligne strictement sur la spec doctrinale doc 21
(`docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`)
qui prescrit :

  Stage 1 — `structure_detector_c.py` :
    Detecte un BreakoutReference dans une trailing window (default 1h, cap 4h)
    Long  : close >= upper_range_high + k × realized_vol_at_break
    Short : mirror

  Stage 2 — `continuation_validator_c.py` (existant dans engines/engine_c/) :
    Valide la continuation depuis OFI / Queue / VPIN

  Les 7 champs structurels d'EngineCInput sont des SCORES AGREGES derives de
  ces stages. Doc 21 §3 ne donne pas de formule explicite scalaire pour
  chacun ; l'agregation reste calibrable via THR-C_* (calibration land via
  risk_runtime_drawdown_calibration.py).

PHILOSOPHIE PRESERVEE : ce module n'invente PAS de doctrine de trading. Il
calcule des aggregats geometriques OHLCV+vol qui se rapportent directement
aux concepts doc 21 :
  - breakout_strength = (close - breakout_level) / (breakout_level × realized_vol_at_break)
    clampe [0, 1]. Magnitude relative du break, normalisee par la vol au break.
  - range_quality = compression_ratio_pre_break (BB squeeze)
  - compression_quality = (vol_pre_break_window - vol_lookback) / vol_lookback ratio inverse
  - volume_confirmation = volume_at_break / mean_volume_lookback
  - followthrough_room = (next_resistance - close) / range_size
  - extension_pct = (close - breakout_level) / range_size
  - retrace_risk = max_pullback_post_break / range_size

Chaque champ est marque dans le payload avec :
  `engine_c_input_provenance` : "BUILDER_DOC21_HEURISTIC_TO_CALIBRATE"

Cela permet au caller de distinguer un EngineCInput construit ici d'un
EngineCInput construit par un structure_detector_c.py canonique futur dans
engines/engine_c/.

Tant que `engine_c_input_provenance != "ENGINE_C_STRUCTURE_DETECTOR_CANONICAL"`,
le manifest doit refuser la promotion (audit-ready).
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from data_backbone.microstructure.realized_kernel_vol import (
    RealizedKernelPricePoint,
    RealizedKernelVolRecord,
    compute_realized_kernel_vol,
)
# Patch 2026-05-30 — V5.3 doctrine microstructure-aware override
from data_backbone.microstructure.breakout_microstructure_features import (
    BreakoutMicrostructureInputs,
    FRESHNESS_FRESH,
    FRESHNESS_NOT_PROVEN,
    resolve_breakout_microstructure_features,
)
from engines.engine_c.structure_resolver_c import (
    build_engine_c_input_from_breakout_features,
)


_MICROSTRUCTURE_AWARE_PROVENANCE = "MICROSTRUCTURE_AWARE_RESOLVER_V1"
_LEGACY_DOC21_HEURISTIC_PROVENANCE = "BUILDER_DOC21_HEURISTIC_TO_CALIBRATE"


_NS_PER_MS = 1_000_000
# k dans la formule doc 21 §3 Stage 1 : close >= range_high + k × realized_vol.
# Pas de valeur calibree dans la spec ; defaut conservateur k=1.0 (1 deviation).
_DEFAULT_BREAKOUT_K_VOL_MULTIPLIER = 1.0
# Lookback par defaut THR-C_LOOKBACK = 1h (doc 21 §5)
_DEFAULT_BREAKOUT_LOOKBACK_MS = 60 * 60 * 1000


@dataclass(frozen=True)
class BreakoutReference:
    """Reference de breakout selon doc 21 §3 Stage 1.

    Output canonique : (t_break, level, direction, realized_vol_at_break,
    queue_state_at_break). Le queue_state_at_break n'est pas calcule ici (il
    requiert un snapshot orderbook au timestamp t_break) ; le caller doit le
    fournir si besoin.
    """

    t_break_ms: int
    level: float
    direction: str  # "long" ou "short"
    realized_vol_at_break: float
    range_high_lookback: float
    range_low_lookback: float
    range_size: float
    breakout_strength_raw: float  # (close - level) / level avant clamp
    detector_status: str  # "DETECTED" ou "NO_BREAKOUT_IN_LOOKBACK" ou "INSUFFICIENT_OHLCV"
    detector_version: str = "doc21_stage1.heuristic.v1"


@dataclass(frozen=True)
class EngineCInputBuilderResult:
    """Resultat audit-ready du builder engine_c."""

    candidate_id: str
    pair: str
    builder_status: str
    breakout_reference: BreakoutReference | None
    engine_c_input_payload: dict[str, object] = field(default_factory=dict)
    builder_warnings: tuple[str, ...] = ()
    engine_c_input_provenance: str = "BUILDER_DOC21_HEURISTIC_TO_CALIBRATE"


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _load_ohlcv_in_window(
    raw_ohlcv_path: Path,
    *,
    window_start_ms: int,
    window_end_ms: int,
    lookback_ms: int,
) -> list[dict[str, object]]:
    """Charge les bars OHLCV dans [window_start_ms - lookback_ms, window_end_ms]."""
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


def _compute_realized_vol_at_break(
    *,
    pair: str,
    raw_trade_path: Path,
    t_break_ms: int,
    lookback_ms: int = _DEFAULT_BREAKOUT_LOOKBACK_MS,
) -> RealizedKernelVolRecord | None:
    """Calcule realized_kernel_vol sur la fenetre [t_break - lookback, t_break]."""
    if not raw_trade_path.exists():
        return None
    points: list[RealizedKernelPricePoint] = []
    handle_cm = (
        gzip.open(raw_trade_path, "rt", encoding="utf-8-sig")
        if str(raw_trade_path).endswith(".gz")
        else raw_trade_path.open("r", encoding="utf-8-sig")
    )
    with handle_cm as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
                ts = int(row.get("timestamp_ms") or 0)
                price = float(row.get("price") or 0.0)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            if price <= 0.0:
                continue
            if t_break_ms - lookback_ms <= ts <= t_break_ms:
                points.append(
                    RealizedKernelPricePoint(timestamp_ns=ts * _NS_PER_MS, price=price)
                )
    if len(points) < 2:
        return None
    try:
        return compute_realized_kernel_vol(points, pair=pair)
    except Exception:  # noqa: BLE001
        return None


def detect_breakout_reference_doc21(
    *,
    pair: str,
    ohlcv_rows: list[dict[str, object]],
    raw_trade_path: Path | None,
    window_start_ms: int,
    window_end_ms: int,
    k_vol_multiplier: float = _DEFAULT_BREAKOUT_K_VOL_MULTIPLIER,
    lookback_ms: int = _DEFAULT_BREAKOUT_LOOKBACK_MS,
) -> BreakoutReference:
    """Stage 1 selon spec doc 21 §3.

    Detecte le bar dans la fenetre dont le close depasse upper_range_high +
    k × realized_vol_at_break (long) ou symmetrique pour short. La range est
    calculee sur la fenetre lookback PRECEDANT le candidat.
    """
    if len(ohlcv_rows) < 2:
        return BreakoutReference(
            t_break_ms=0,
            level=0.0,
            direction="",
            realized_vol_at_break=0.0,
            range_high_lookback=0.0,
            range_low_lookback=0.0,
            range_size=0.0,
            breakout_strength_raw=0.0,
            detector_status="INSUFFICIENT_OHLCV",
        )

    # Separer bars lookback (avant window_start) et bars dans la fenetre
    lookback_bars = [
        row
        for row in ohlcv_rows
        if int(row.get("timestamp_ms") or 0) < window_start_ms
    ]
    in_window_bars = [
        row
        for row in ohlcv_rows
        if window_start_ms <= int(row.get("timestamp_ms") or 0) <= window_end_ms
    ]

    # Fallback : si pas de lookback bars (ex: fenetre cross-day), on utilise
    # les premiers bars in-window comme proxy pour le range pre-break. C'est
    # une degradation acceptable pour le mode replay backtest ; le statut
    # le signale via "DETECTED_FALLBACK_INWINDOW_RANGE".
    used_fallback_range = False
    if len(lookback_bars) < 1:
        if len(in_window_bars) < 3:
            return BreakoutReference(
                t_break_ms=0,
                level=0.0,
                direction="",
                realized_vol_at_break=0.0,
                range_high_lookback=0.0,
                range_low_lookback=0.0,
                range_size=0.0,
                breakout_strength_raw=0.0,
                detector_status="NO_LOOKBACK_BARS_AND_INSUFFICIENT_INWINDOW",
            )
        # Premier 1/3 de la fenetre = range pre-break, reste = test break
        split_idx = max(1, len(in_window_bars) // 3)
        lookback_bars = in_window_bars[:split_idx]
        in_window_bars = in_window_bars[split_idx:]
        used_fallback_range = True

    range_high = max(float(row.get("high") or 0.0) for row in lookback_bars)
    range_low = min(float(row.get("low") or 0.0) for row in lookback_bars)
    if range_high <= range_low or range_high <= 0.0:
        return BreakoutReference(
            t_break_ms=0,
            level=0.0,
            direction="",
            realized_vol_at_break=0.0,
            range_high_lookback=range_high,
            range_low_lookback=range_low,
            range_size=0.0,
            breakout_strength_raw=0.0,
            detector_status="DEGENERATE_RANGE",
        )

    range_size = range_high - range_low

    # Cherche le premier bar in-window qui ferme au-dessus de range_high + k×vol
    for bar in in_window_bars:
        try:
            close = float(bar.get("close") or 0.0)
            ts_ms = int(bar.get("timestamp_ms") or 0)
        except (TypeError, ValueError):
            continue
        if close <= 0.0:
            continue

        # Calcule realized_vol AT this bar (lookback se termine au bar)
        rk_record: RealizedKernelVolRecord | None = None
        if raw_trade_path is not None:
            rk_record = _compute_realized_vol_at_break(
                pair=pair,
                raw_trade_path=raw_trade_path,
                t_break_ms=ts_ms,
                lookback_ms=lookback_ms,
            )
        # Fallback heuristique : range_size / range_high (vol relative implicite)
        realized_vol = (
            rk_record.value
            if rk_record is not None and rk_record.value > 0.0
            else range_size / range_high
        )

        # Threshold long : range_high + k × range_high × realized_vol
        # (realized_vol est sans unite pour la kernel, donc on multiplie par range_high)
        long_threshold = range_high + k_vol_multiplier * range_high * realized_vol
        short_threshold = range_low - k_vol_multiplier * range_high * realized_vol

        if close >= long_threshold:
            return BreakoutReference(
                t_break_ms=ts_ms,
                level=range_high,
                direction="long",
                realized_vol_at_break=realized_vol,
                range_high_lookback=range_high,
                range_low_lookback=range_low,
                range_size=range_size,
                breakout_strength_raw=(close - range_high) / max(range_high, 1e-9),
                detector_status=(
                    "DETECTED_FALLBACK_INWINDOW_RANGE"
                    if used_fallback_range
                    else "DETECTED"
                ),
            )
        if close <= short_threshold:
            return BreakoutReference(
                t_break_ms=ts_ms,
                level=range_low,
                direction="short",
                realized_vol_at_break=realized_vol,
                range_high_lookback=range_high,
                range_low_lookback=range_low,
                range_size=range_size,
                breakout_strength_raw=(range_low - close) / max(range_high, 1e-9),
                detector_status=(
                    "DETECTED_FALLBACK_INWINDOW_RANGE"
                    if used_fallback_range
                    else "DETECTED"
                ),
            )

    # Pas de breakout detecte : on retourne le contexte avec status explicite
    return BreakoutReference(
        t_break_ms=0,
        level=range_high,
        direction="",
        realized_vol_at_break=range_size / max(range_high, 1e-9),
        range_high_lookback=range_high,
        range_low_lookback=range_low,
        range_size=range_size,
        breakout_strength_raw=0.0,
        detector_status="NO_BREAKOUT_IN_LOOKBACK",
    )


def _derive_seven_structural_fields_from_doc21(
    *,
    breakout: BreakoutReference,
    in_window_bars: list[dict[str, object]],
    lookback_bars: list[dict[str, object]],
) -> dict[str, float]:
    """Derive les 7 champs structurels EngineCInput selon semantique doc 21.

    - breakout_strength : magnitude du break normalisee par realized_vol_at_break
    - range_quality : 1 - dispersion(range)/range_size (range tight = quality haut)
    - compression_quality : 1 - vol_pre_break/vol_lookback_full (squeeze pre-break)
    - volume_confirmation : volume_at_break / mean(volume_lookback)
    - followthrough_room : (next_resistance - close) / range_size, default 1.0 si pas de resistance
    - extension_pct : (close - breakout_level) / range_size
    - retrace_risk : max_pullback_post_break / range_size
    """
    if breakout.detector_status not in {
        "DETECTED",
        "DETECTED_FALLBACK_INWINDOW_RANGE",
    } or not in_window_bars:
        # Retour zero values si pas de break detecte. EngineCInput rejettera
        # avec breakout_strength=0 (cf engine_c_runner.py:341).
        return {
            "breakout_strength": 0.0,
            "range_quality": 0.0,
            "compression_quality": 0.0,
            "volume_confirmation": 0.0,
            "followthrough_room": 0.0,
            "extension_pct": 0.0,
            "retrace_risk": 0.0,
        }

    # Last bar in window = "current" bar pour engine evaluation
    last_bar = in_window_bars[-1]
    try:
        last_close = float(last_bar.get("close") or 0.0)
    except (TypeError, ValueError):
        last_close = 0.0

    # 1. breakout_strength : magnitude normalisee par realized_vol_at_break
    if breakout.realized_vol_at_break > 0.0 and breakout.level > 0.0:
        if breakout.direction == "long":
            magnitude = (last_close - breakout.level) / (
                breakout.level * breakout.realized_vol_at_break
            )
        else:  # short
            magnitude = (breakout.level - last_close) / (
                breakout.level * breakout.realized_vol_at_break
            )
        breakout_strength = _clamp01(magnitude)
    else:
        breakout_strength = 0.0

    # 2. range_quality : 1 - mean_dispersion / range_size
    # Mesure la "tightness" du range avant break (range tight = quality haut)
    if lookback_bars and breakout.range_size > 0.0:
        closes_lookback = [
            float(row.get("close") or 0.0) for row in lookback_bars
        ]
        closes_lookback = [c for c in closes_lookback if c > 0.0]
        if len(closes_lookback) >= 2:
            mean_close = sum(closes_lookback) / len(closes_lookback)
            mean_abs_dev = sum(abs(c - mean_close) for c in closes_lookback) / len(
                closes_lookback
            )
            range_quality = _clamp01(1.0 - (mean_abs_dev / breakout.range_size) * 2.0)
        else:
            range_quality = 0.5
    else:
        range_quality = 0.0

    # 3. compression_quality : 1 - vol_recente_pre_break / vol_lookback_full
    # Mesure le squeeze de volatilite avant le break (compression = quality haut)
    if lookback_bars and len(lookback_bars) >= 4:
        # Split lookback en moitie : recent vs ancien
        midpoint = len(lookback_bars) // 2
        ancien_bars = lookback_bars[:midpoint]
        recent_bars = lookback_bars[midpoint:]

        def _bar_range(row: dict[str, object]) -> float:
            try:
                h = float(row.get("high") or 0.0)
                low = float(row.get("low") or 0.0)
                return max(0.0, h - low)
            except (TypeError, ValueError):
                return 0.0

        ancien_vol = (
            sum(_bar_range(b) for b in ancien_bars) / max(len(ancien_bars), 1)
        )
        recent_vol = (
            sum(_bar_range(b) for b in recent_bars) / max(len(recent_bars), 1)
        )
        if ancien_vol > 0.0:
            compression_quality = _clamp01(1.0 - recent_vol / ancien_vol)
        else:
            compression_quality = 0.0
    else:
        compression_quality = 0.0

    # 4. volume_confirmation : volume_at_break / mean(volume_lookback)
    if lookback_bars:
        volumes_lookback = [float(row.get("volume") or 0.0) for row in lookback_bars]
        volumes_lookback = [v for v in volumes_lookback if v >= 0.0]
        mean_volume = (
            sum(volumes_lookback) / len(volumes_lookback) if volumes_lookback else 0.0
        )
        # Volume at break = volume of the breakout bar
        break_bar_volume = 0.0
        for bar in in_window_bars:
            try:
                if int(bar.get("timestamp_ms") or 0) == breakout.t_break_ms:
                    break_bar_volume = float(bar.get("volume") or 0.0)
                    break
            except (TypeError, ValueError):
                continue
        if mean_volume > 0.0:
            volume_confirmation = _clamp01(break_bar_volume / (2.0 * mean_volume))
        else:
            volume_confirmation = 0.0
    else:
        volume_confirmation = 0.0

    # 5. followthrough_room : place restante avant prochaine resistance
    # Heuristique : on prend range_size comme proxy de la prochaine resistance
    # distance, donc followthrough_room = 1.0 si extension est faible et 0 si
    # extension >= range_size.
    if breakout.range_size > 0.0:
        if breakout.direction == "long":
            extension_abs = max(0.0, last_close - breakout.level)
        else:
            extension_abs = max(0.0, breakout.level - last_close)
        followthrough_room = _clamp01(1.0 - extension_abs / breakout.range_size)
    else:
        followthrough_room = 0.0

    # 6. extension_pct : extension actuelle / range_size
    if breakout.range_size > 0.0:
        if breakout.direction == "long":
            extension_abs = max(0.0, last_close - breakout.level)
        else:
            extension_abs = max(0.0, breakout.level - last_close)
        extension_pct = _clamp01(extension_abs / breakout.range_size)
    else:
        extension_pct = 0.0

    # 7. retrace_risk : max pullback post-break / range_size
    # Pullback = distance entre le local extremum post-break et le close actuel
    post_break_bars = [
        bar
        for bar in in_window_bars
        if int(bar.get("timestamp_ms") or 0) > breakout.t_break_ms
    ]
    if post_break_bars and breakout.range_size > 0.0:
        if breakout.direction == "long":
            local_extremum = max(
                float(bar.get("high") or 0.0) for bar in post_break_bars
            )
            pullback = max(0.0, local_extremum - last_close)
        else:
            local_extremum = min(
                float(bar.get("low") or 0.0) for bar in post_break_bars
                if float(bar.get("low") or 0.0) > 0.0
            )
            pullback = max(0.0, last_close - local_extremum)
        retrace_risk = _clamp01(pullback / breakout.range_size)
    else:
        retrace_risk = 0.0

    return {
        "breakout_strength": breakout_strength,
        "range_quality": range_quality,
        "compression_quality": compression_quality,
        "volume_confirmation": volume_confirmation,
        "followthrough_room": followthrough_room,
        "extension_pct": extension_pct,
        "retrace_risk": retrace_risk,
    }


def build_engine_c_input_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_ohlcv_path: Path | str | None,
    microstructure_partial_payload: dict[str, object] | None = None,
    expected_gain: float = 0.0,
    expected_cost: float = 0.0,
    candidate_size: float = 0.0,
    holding_period: float | None = None,
    k_vol_multiplier: float = _DEFAULT_BREAKOUT_K_VOL_MULTIPLIER,
    lookback_ms: int = _DEFAULT_BREAKOUT_LOOKBACK_MS,
    scoring_version: str = "engine_c.builder_doc21.v1",
) -> EngineCInputBuilderResult:
    """Construit un EngineCInput.model_validate-compatible depuis raw_window.

    Combine :
      - Stage 1 doc 21 : detection BreakoutReference depuis OHLCV+trades
      - Derivation des 7 champs structurels (semantique doc 21)
      - Microstructure seam additif depuis le pont engine_c (cumulative_ofi,
        queue_pressure, vpin, kyle_lambda, realized_vol_current,
        realized_vol_at_break)

    Le payload retourne est `EngineCInput.model_validate()`-compatible. Le
    caller peut directement faire `run_engine_c(EngineCInput(**payload))`.
    """
    warnings: list[str] = []

    if raw_ohlcv_path is None:
        warnings.append("OHLCV_PATH_MISSING")
        return EngineCInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_C_INPUT_BUILDER_FAILED_NO_OHLCV",
            breakout_reference=None,
            engine_c_input_payload={},
            builder_warnings=tuple(warnings),
        )

    ohlcv_path = Path(raw_ohlcv_path)
    if not ohlcv_path.exists():
        warnings.append(f"OHLCV_PATH_NOT_FOUND:{ohlcv_path}")
        return EngineCInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_C_INPUT_BUILDER_FAILED_NO_OHLCV",
            breakout_reference=None,
            engine_c_input_payload={},
            builder_warnings=tuple(warnings),
        )

    try:
        ohlcv_rows = _load_ohlcv_in_window(
            ohlcv_path,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            lookback_ms=lookback_ms,
        )
    except OSError as exc:
        warnings.append(f"OHLCV_LOAD_FAILED:{type(exc).__name__}")
        return EngineCInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_C_INPUT_BUILDER_FAILED_OHLCV_IO",
            breakout_reference=None,
            engine_c_input_payload={},
            builder_warnings=tuple(warnings),
        )

    if not ohlcv_rows:
        warnings.append("OHLCV_NO_BARS_IN_WINDOW")
        return EngineCInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_C_INPUT_BUILDER_FAILED_NO_OHLCV_BARS",
            breakout_reference=None,
            engine_c_input_payload={},
            builder_warnings=tuple(warnings),
        )

    # Stage 1 : detection breakout reference doc 21
    breakout = detect_breakout_reference_doc21(
        pair=pair,
        ohlcv_rows=ohlcv_rows,
        raw_trade_path=Path(raw_trade_path) if raw_trade_path else None,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        k_vol_multiplier=k_vol_multiplier,
        lookback_ms=lookback_ms,
    )
    if breakout.detector_status != "DETECTED":
        warnings.append(f"BREAKOUT_NOT_DETECTED:{breakout.detector_status}")

    # Derivation des 7 champs structurels
    lookback_bars = [
        row
        for row in ohlcv_rows
        if int(row.get("timestamp_ms") or 0) < window_start_ms
    ]
    in_window_bars = [
        row
        for row in ohlcv_rows
        if window_start_ms <= int(row.get("timestamp_ms") or 0) <= window_end_ms
    ]
    structural_fields = _derive_seven_structural_fields_from_doc21(
        breakout=breakout,
        in_window_bars=in_window_bars,
        lookback_bars=lookback_bars,
    )

    # Last close = entry_price candidate
    entry_price = 0.0
    if in_window_bars:
        try:
            entry_price = float(in_window_bars[-1].get("close") or 0.0)
        except (TypeError, ValueError):
            entry_price = 0.0

    # Patch 2026-05-30 — V5.3 microstructure-aware override per user doctrine.
    # Legacy `_derive_seven_structural_fields_from_doc21` uses Bollinger
    # squeeze / volume MA / OHLCV-only formulas that are explicitly forbidden
    # as primary signal. When microstructure_partial_payload carries OFI /
    # VPIN / queue_pressure / kyle_lambda (5 records bridge), recompute the
    # 7 structural floats using `resolve_breakout_microstructure_features`
    # (neutral primitives) + `build_engine_c_input_from_breakout_features`
    # (engine-c-specific mapping). Fall back to legacy when no microstructure
    # scalars are available (research-only mode preserved).
    engine_c_input_provenance = _LEGACY_DOC21_HEURISTIC_PROVENANCE
    if microstructure_partial_payload:
        msp = microstructure_partial_payload
        has_any_micro = any(
            msp.get(k) is not None
            for k in ("cumulative_ofi", "queue_pressure", "vpin", "kyle_lambda")
        )
        if has_any_micro:
            try:
                kyle_value = msp.get("kyle_lambda")
                kyle_float = float(kyle_value) if kyle_value is not None else None
            except (TypeError, ValueError):
                kyle_float = None

            breakout_inputs = BreakoutMicrostructureInputs(
                breakout_price=breakout.level if breakout.level > 0.0 else None,
                entry_price=entry_price if entry_price > 0.0 else None,
                range_high=(
                    breakout.range_high_lookback
                    if breakout.range_high_lookback > 0.0
                    else None
                ),
                range_low=(
                    breakout.range_low_lookback
                    if breakout.range_low_lookback > 0.0
                    else None
                ),
                recent_range_width=(
                    breakout.range_size if breakout.range_size > 0.0 else None
                ),
                realized_vol_current=(
                    msp.get("realized_vol_current")
                    or (
                        breakout.realized_vol_at_break
                        if breakout.realized_vol_at_break > 0.0
                        else None
                    )
                ),
                realized_vol_at_break=(
                    breakout.realized_vol_at_break
                    if breakout.realized_vol_at_break > 0.0
                    else None
                ),
                ofi_normalized=msp.get("cumulative_ofi"),
                cumulative_ofi=msp.get("cumulative_ofi"),
                queue_pressure=msp.get("queue_pressure"),
                vpin=msp.get("vpin"),
                expected_slippage_bps=(
                    kyle_float * 100.0
                    if kyle_float is not None and kyle_float >= 0.0
                    else None
                ),
                inputs_freshness_status=FRESHNESS_FRESH,
            )
            try:
                resolution = resolve_breakout_microstructure_features(breakout_inputs)
                microstructure_floats = build_engine_c_input_from_breakout_features(
                    resolution
                )
                # Override legacy 7 floats with microstructure-aware values
                structural_fields = microstructure_floats
                # Provenance flag: research-only if any field used fallback
                engine_c_input_provenance = (
                    _MICROSTRUCTURE_AWARE_PROVENANCE
                    if not resolution.any_research_only_fallback
                    else f"{_MICROSTRUCTURE_AWARE_PROVENANCE}_PARTIAL_FALLBACK"
                )
            except Exception as exc:  # noqa: BLE001 - keep legacy values on failure
                warnings.append(
                    f"MICROSTRUCTURE_RESOLVER_FAILED:{type(exc).__name__}:{exc}"
                )

    # Construction du payload EngineCInput.model_validate-compatible
    payload: dict[str, object] = {
        "pair": pair,
        # 7 champs structurels
        **structural_fields,
        "rejection_wick_ratio": 0.0,  # default — wick analysis non implementee ici
        # Contexte regime/health (defaults)
        "regime": "",
        "regime_favorability": 0.5,
        "pair_health": 0.5,
        "data_freshness": 0.5,
        "flow_coherence": 0.5,
        # Prix / niveau
        "entry_price": entry_price,
        "breakout_level": breakout.level if breakout.level > 0.0 else entry_price,
        "range_low": breakout.range_low_lookback,
        "range_high": breakout.range_high_lookback,
        # Realized vol (doc 21 §3 Stage 1)
        "realized_vol_current": breakout.realized_vol_at_break
        if breakout.realized_vol_at_break > 0.0
        else None,
        "realized_vol_at_break": breakout.realized_vol_at_break
        if breakout.realized_vol_at_break > 0.0
        else None,
        "expected_gain": expected_gain,
        "expected_cost": expected_cost,
        "candidate_size": candidate_size,
        # Scoring version
        "scoring_version": scoring_version,
        "atr": 0.0,
    }
    if holding_period is not None:
        payload["holding_period"] = holding_period

    # Merge microstructure additive seam si fourni (depuis le pont engine_c)
    if microstructure_partial_payload:
        for key in (
            "cumulative_ofi",
            "queue_pressure",
            "vpin",
            "kyle_lambda",
            "realized_vol_current",
            "realized_vol_at_break",
        ):
            if (
                key in microstructure_partial_payload
                and microstructure_partial_payload[key] is not None
            ):
                # Le seam canonique ne doit jamais ecraser realized_vol_at_break si
                # le builder l'a mesure depuis le breakout (c'est plus precis)
                if key in {"realized_vol_at_break", "realized_vol_current"} and payload.get(
                    key
                ) is not None:
                    continue
                payload[key] = microstructure_partial_payload[key]

    if breakout.detector_status == "DETECTED":
        builder_status = "ENGINE_C_INPUT_BUILDER_READY"
    elif breakout.detector_status == "DETECTED_FALLBACK_INWINDOW_RANGE":
        builder_status = "ENGINE_C_INPUT_BUILDER_READY_FALLBACK_INWINDOW_RANGE"
    else:
        builder_status = "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT"

    return EngineCInputBuilderResult(
        candidate_id=candidate_id,
        pair=pair,
        builder_status=builder_status,
        breakout_reference=breakout,
        engine_c_input_payload=payload,
        builder_warnings=tuple(warnings),
        engine_c_input_provenance=engine_c_input_provenance,
    )


__all__ = [
    "BreakoutReference",
    "EngineCInputBuilderResult",
    "build_engine_c_input_from_window",
    "detect_breakout_reference_doc21",
]
