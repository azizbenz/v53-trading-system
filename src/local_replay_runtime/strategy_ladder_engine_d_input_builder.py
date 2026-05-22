"""Strategy Ladder engine_d input builder — comble la limitation P3a pour
engine_d (Audit 2026-05-07).

Construit un `EngineDInput` COMPLET (incluant les 8 champs structurels REQUIRED)
depuis un raw_window backtest, sans toucher au code des engines.

PHILOSOPHIE ENGINE D (selon spec doc 22) :
  > D = Re-entry / Second Chance — "reengager du capital apres un premier
  > contexte deja valide / seulement quand une nouvelle structure exploitable
  > se reforme / seulement si la valeur marginale de ce reengagement est
  > positive."

D est NEVER A PRIMARY ENTRY. Il depend d'un `first_episode_ref` (trade A ou C
clos sur la meme (pair, direction)). Dans le backtest actuel ou aucun trade
n'est execute, le first_episode_ref n'existe pas → D refusera correctement
avec `d.no_first_episode`.

Champs REQUIRED dans `engines/engine_d/engine_d_models.py:134-156` :
  pair, prior_trade_quality, reformation_quality, pullback_quality,
  continuation_room, concentration_headroom, marginal_edge, reentry_lateness

Semantique extraite des poids dans `engine_d/signal_math_d.py` :

| Champ | Poids signal_math_d | Stage scoring |
|---|---|---|
| prior_trade_quality      | 0.55 | history_score |
| reformation_quality      | 0.45 | reformation_score |
| pullback_quality         | 0.30 | reformation_score |
| continuation_room        | 0.30 | marginal_value_score |
| concentration_headroom   | 0.20 | marginal_value_score |
| marginal_edge            | 0.35 | marginal_value_score |
| reentry_lateness (inv.)  | 0.15 | marginal_value_score |

Tous les 8 champs doivent etre [0, 1] vu que `_clamp` dans signal_math_d clampe
les resultats finaux [0, 1].

PHILOSOPHIE PRESERVEE :
- AUCUN fichier dans `src/engines/engine_d/` modifie
- Builder vit dans `local_replay_runtime/` cote caller
- Heuristiques OHLCV alignees sur la semantique signal_math_d
- Provenance flag : `engine_d_input_provenance="BUILDER_NO_FIRST_EPISODE_DEFAULTS"`
  (etat normal en backtest sans trades executes)
- Quand le caller fournit `first_episode_context` via base_payload, la
  provenance bascule vers `BUILDER_WITH_FIRST_EPISODE_HEURISTIC_TO_CALIBRATE`

LIMITATION : sans un journal de closed_episodes (futur module
`first_episode_resolver_d.py`), engine_d retournera systematiquement no_trade
avec `d.no_first_episode`. C'est le comportement DOCTRINAL CORRECT — D est
dependent par design.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    EngineDBridgeResult,
    build_engine_d_microstructure_inputs_from_window,
)


@dataclass(frozen=True)
class EngineDStructureSummary:
    """Resultat heuristique des 8 champs structurels engine_d.

    Tous les champs sont [0, 1] pour respecter le clamp signal_math_d.
    """

    prior_trade_quality: float  # [0, 1] — qualite du first_episode (default 0.5 si absent)
    reformation_quality: float  # [0, 1] — force de la nouvelle structure
    pullback_quality: float  # [0, 1] — amplitude du pullback vers le niveau
    continuation_room: float  # [0, 1] — place restante
    concentration_headroom: float  # [0, 1] — marge portfolio (1 - concentration)
    marginal_edge: float  # [0, 1] — EV-net marginal au-dessus seuil
    reentry_lateness: float  # [0, 1] — delai depuis close (haut = mauvais)
    has_first_episode_context: bool
    n_lookback_bars_used: int
    n_in_window_bars_used: int
    detector_status: str
    detector_version: str = "engine_d_builder.heuristic.v1"


@dataclass(frozen=True)
class EngineDInputBuilderResult:
    """Resultat audit-ready du builder engine_d."""

    candidate_id: str
    pair: str
    builder_status: str
    structure_summary: EngineDStructureSummary | None
    bridge_result: EngineDBridgeResult | None
    engine_d_input_payload: dict[str, object] = field(default_factory=dict)
    builder_warnings: tuple[str, ...] = ()
    engine_d_input_provenance: str = "BUILDER_NO_FIRST_EPISODE_DEFAULTS"


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
    if not raw_ohlcv_path.exists():
        return []
    rows: list[dict[str, object]] = []
    extended_start = window_start_ms - lookback_ms
    with raw_ohlcv_path.open("r", encoding="utf-8-sig") as handle:
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


def _compute_reformation_quality(
    bars: list[dict[str, object]],
) -> float:
    """reformation_quality [0, 1] — force de la nouvelle structure se reformant.

    Heuristique : 1 - mean_dispersion / range_size (similar a engine_c
    range_quality). Une structure tight se reforme = quality haut.
    """
    if len(bars) < 3:
        return 0.0
    closes = [_bar_close(b) for b in bars]
    closes = [c for c in closes if c > 0.0]
    if len(closes) < 3:
        return 0.0
    high_max = max(_bar_high(b) for b in bars)
    low_min = min(_bar_low(b) for b in bars)
    range_size = max(high_max - low_min, 1e-9)
    mean_close = sum(closes) / len(closes)
    mean_abs_dev = sum(abs(c - mean_close) for c in closes) / len(closes)
    return _clamp01(1.0 - (mean_abs_dev / range_size) * 2.0)


def _compute_pullback_quality(
    bars: list[dict[str, object]],
    *,
    last_close: float,
) -> float:
    """pullback_quality [0, 1] — amplitude du pullback vers le niveau d'origine.

    Heuristique : pullback recent / range_size, clampe [0, 1].
    Un pullback significatif (vers une zone de re-entry valide) = quality haut.
    """
    if len(bars) < 3 or last_close <= 0.0:
        return 0.0
    high_max = max(_bar_high(b) for b in bars)
    low_min = min(_bar_low(b) for b in bars)
    range_size = max(high_max - low_min, 1e-9)
    # Pullback : distance entre le local extremum recent et le close actuel
    pullback_from_high = max(0.0, high_max - last_close)
    pullback_from_low = max(0.0, last_close - low_min)
    pullback = min(pullback_from_high, pullback_from_low)
    return _clamp01(pullback / range_size)


def _compute_continuation_room(
    bars: list[dict[str, object]],
    *,
    last_close: float,
) -> float:
    """continuation_room [0, 1] — place restante avant la prochaine resistance.

    Heuristique : 1 - (extension_from_mean / range_size), clampe [0, 1].
    Plus le close est proche du mean = plus de room pour continuer.
    """
    if len(bars) < 3 or last_close <= 0.0:
        return 0.0
    closes = [_bar_close(b) for b in bars if _bar_close(b) > 0.0]
    if len(closes) < 3:
        return 0.0
    mean_close = sum(closes) / len(closes)
    high_max = max(_bar_high(b) for b in bars)
    low_min = min(_bar_low(b) for b in bars)
    range_size = max(high_max - low_min, 1e-9)
    extension_from_mean = abs(last_close - mean_close)
    return _clamp01(1.0 - extension_from_mean / range_size)


def _compute_marginal_edge(
    *,
    expected_gain: float,
    expected_cost: float,
    candidate_size: float,
) -> float:
    """marginal_edge [0, 1] — EV-net marginal au-dessus du seuil.

    Heuristique : (expected_gain - expected_cost) / max(expected_cost, eps),
    clampe [0, 1]. Edge positif = marginal_edge eleve.
    """
    if expected_cost <= 0.0:
        return 0.0
    edge_ratio = (expected_gain - expected_cost) / expected_cost
    return _clamp01(edge_ratio)


def derive_engine_d_structure_summary(
    *,
    bars_full: list[dict[str, object]],
    window_start_ms: int,
    window_end_ms: int,
    has_first_episode_context: bool,
    prior_trade_quality_override: float | None = None,
    concentration_headroom_override: float | None = None,
    reentry_lateness_override: float | None = None,
    expected_gain: float = 0.0,
    expected_cost: float = 0.0,
    candidate_size: float = 0.0,
) -> EngineDStructureSummary:
    """Derive les 8 champs structurels engine_d depuis OHLCV bars + context."""
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
    combined_bars = lookback_bars + in_window_bars

    if len(combined_bars) < 3:
        return EngineDStructureSummary(
            prior_trade_quality=(
                prior_trade_quality_override
                if prior_trade_quality_override is not None
                else (0.5 if has_first_episode_context else 0.0)
            ),
            reformation_quality=0.0,
            pullback_quality=0.0,
            continuation_room=0.0,
            concentration_headroom=(
                concentration_headroom_override
                if concentration_headroom_override is not None
                else 1.0  # default : pas de concentration risk en backtest
            ),
            marginal_edge=_compute_marginal_edge(
                expected_gain=expected_gain,
                expected_cost=expected_cost,
                candidate_size=candidate_size,
            ),
            reentry_lateness=(
                reentry_lateness_override
                if reentry_lateness_override is not None
                else 1.0  # default : tres en retard sans context
            ),
            has_first_episode_context=has_first_episode_context,
            n_lookback_bars_used=len(lookback_bars),
            n_in_window_bars_used=len(in_window_bars),
            detector_status="INSUFFICIENT_BARS",
        )

    last_close = _bar_close(combined_bars[-1])

    # prior_trade_quality : sans first_episode, default 0.0 (block)
    # Avec first_episode, quality default 0.5 (neutre, override par caller)
    if prior_trade_quality_override is not None:
        prior_trade_quality = _clamp01(prior_trade_quality_override)
    elif has_first_episode_context:
        prior_trade_quality = 0.5
    else:
        prior_trade_quality = 0.0

    # concentration_headroom : default 1.0 (pas de concentration en backtest)
    # Override par le caller si portfolio context fourni
    if concentration_headroom_override is not None:
        concentration_headroom = _clamp01(concentration_headroom_override)
    else:
        concentration_headroom = 1.0

    # reentry_lateness : default 1.0 (tres en retard sans context)
    # Si first_episode fourni, le caller doit calculer (now - close_at) / lookback
    if reentry_lateness_override is not None:
        reentry_lateness = _clamp01(reentry_lateness_override)
    elif has_first_episode_context:
        reentry_lateness = 0.5
    else:
        reentry_lateness = 1.0

    return EngineDStructureSummary(
        prior_trade_quality=prior_trade_quality,
        reformation_quality=_compute_reformation_quality(combined_bars),
        pullback_quality=_compute_pullback_quality(
            combined_bars, last_close=last_close
        ),
        continuation_room=_compute_continuation_room(
            combined_bars, last_close=last_close
        ),
        concentration_headroom=concentration_headroom,
        marginal_edge=_compute_marginal_edge(
            expected_gain=expected_gain,
            expected_cost=expected_cost,
            candidate_size=candidate_size,
        ),
        reentry_lateness=reentry_lateness,
        has_first_episode_context=has_first_episode_context,
        n_lookback_bars_used=len(lookback_bars),
        n_in_window_bars_used=len(in_window_bars),
        detector_status="DETECTED",
    )


def build_engine_d_input_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    raw_ohlcv_path: Path | str | None,
    first_episode_context: dict[str, object] | None = None,
    expected_gain: float = 0.0,
    expected_cost: float = 0.0,
    candidate_size: float = 0.0,
    holding_period: float = 2.0,
    post_close_window_ms: int = 60_000,
    lookback_ms: int = 60 * 60 * 1000,
    scoring_version: str = "engine_d.builder.v1",
    base_payload: dict[str, object] | None = None,
) -> EngineDInputBuilderResult:
    """Construit un EngineDInput.model_validate-compatible depuis raw_window.

    Combine :
      - 8 heuristiques OHLCV pour les 8 champs structurels REQUIRED
      - Pont microstructure engine_d (realized_vol_current + realized_vol_post_close)
      - first_episode_context optionnel : si fourni (origin_context_id, etc.),
        la provenance change vers BUILDER_WITH_FIRST_EPISODE_*
      - Defaults canoniques pour autres champs

    Sans first_episode_context, le builder produit un EngineDInput valide
    Pydantic mais run_engine_d() refusera proprement avec d.no_first_episode
    (comportement doctrinal correct).
    """
    warnings: list[str] = []

    bridge: EngineDBridgeResult | None = None
    if raw_trade_path is not None:
        try:
            bridge = build_engine_d_microstructure_inputs_from_window(
                candidate_id=candidate_id,
                pair=pair,
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
                raw_trade_path=raw_trade_path,
                post_close_window_end_ms=window_end_ms + post_close_window_ms,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"BRIDGE_FAILED:{type(exc).__name__}:{exc}")

    if raw_ohlcv_path is None:
        warnings.append("OHLCV_PATH_MISSING")
        return EngineDInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_D_INPUT_BUILDER_FAILED_NO_OHLCV",
            structure_summary=None,
            bridge_result=bridge,
            engine_d_input_payload={},
            builder_warnings=tuple(warnings),
        )

    ohlcv_path = Path(raw_ohlcv_path)
    if not ohlcv_path.exists():
        warnings.append(f"OHLCV_PATH_NOT_FOUND:{ohlcv_path}")
        return EngineDInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_D_INPUT_BUILDER_FAILED_NO_OHLCV",
            structure_summary=None,
            bridge_result=bridge,
            engine_d_input_payload={},
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
        return EngineDInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_D_INPUT_BUILDER_FAILED_OHLCV_IO",
            structure_summary=None,
            bridge_result=bridge,
            engine_d_input_payload={},
            builder_warnings=tuple(warnings),
        )

    has_first_episode = bool(first_episode_context)
    fe_ctx = first_episode_context or {}

    summary = derive_engine_d_structure_summary(
        bars_full=bars,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        has_first_episode_context=has_first_episode,
        prior_trade_quality_override=fe_ctx.get("prior_trade_quality"),
        concentration_headroom_override=fe_ctx.get("concentration_headroom"),
        reentry_lateness_override=fe_ctx.get("reentry_lateness"),
        expected_gain=expected_gain,
        expected_cost=expected_cost,
        candidate_size=candidate_size,
    )
    if summary.detector_status != "DETECTED":
        warnings.append(f"STRUCTURE_NOT_DETECTED:{summary.detector_status}")

    last_close = 0.0
    if bars:
        last_close = _bar_close(bars[-1])

    payload: dict[str, object] = {
        "pair": pair,
        # First episode context (defaults : empty)
        "origin_context_id": str(fe_ctx.get("origin_context_id") or ""),
        "origin_trade_id": str(fe_ctx.get("origin_trade_id") or ""),
        "link_type": str(fe_ctx.get("link_type") or "prior_trade"),
        "first_episode_id": str(fe_ctx.get("first_episode_id") or ""),
        "first_episode_engine_id": str(fe_ctx.get("first_episode_engine_id") or ""),
        "first_episode_close_reason": str(
            fe_ctx.get("first_episode_close_reason") or ""
        ),
        "consecutive_stop_count": int(fe_ctx.get("consecutive_stop_count") or 0),
        "last_stop_at_ns": fe_ctx.get("last_stop_at_ns"),
        "last_fresh_a_detection_at_ns": fe_ctx.get("last_fresh_a_detection_at_ns"),
        "anti_revenge_state": str(fe_ctx.get("anti_revenge_state") or ""),
        # 8 champs structurels REQUIRED
        "prior_trade_quality": summary.prior_trade_quality,
        "reformation_quality": summary.reformation_quality,
        "pullback_quality": summary.pullback_quality,
        "continuation_room": summary.continuation_room,
        "concentration_headroom": summary.concentration_headroom,
        "marginal_edge": summary.marginal_edge,
        "reentry_lateness": summary.reentry_lateness,
        "structure_reformed_detected": bool(
            fe_ctx.get("structure_reformed_detected", True)
        ),
        "duplication_overlap_with_engine_a": float(
            fe_ctx.get("duplication_overlap_with_engine_a") or 0.0
        ),
        "marginal_portfolio_gain": float(
            fe_ctx.get("marginal_portfolio_gain") or 0.0
        ),
        "covered_share_by_engine_a": float(
            fe_ctx.get("covered_share_by_engine_a") or 0.0
        ),
        # Defaults canoniques
        "regime": "",
        "regime_favorability": 0.5,
        "pair_health": 0.5,
        "data_freshness": 0.5,
        "flow_coherence": 0.5,
        "expected_gain": expected_gain,
        "expected_cost": expected_cost,
        "candidate_size": candidate_size,
        "holding_period": holding_period,
        "entry_price": last_close,
        "reentry_anchor_price": float(fe_ctx.get("reentry_anchor_price") or last_close),
        "atr": 0.0,
        "scoring_version": scoring_version,
    }

    # Realized vol depuis le pont engine_d
    if bridge is not None:
        if bridge.realized_vol_current_record is not None:
            payload["realized_vol_current"] = bridge.realized_vol_current_record.value
        if bridge.realized_vol_post_close_record is not None:
            payload["realized_vol_post_close"] = (
                bridge.realized_vol_post_close_record.value
            )

    # Permettre au caller d'overrider via base_payload
    if base_payload:
        payload.update(base_payload)

    if summary.detector_status == "DETECTED":
        builder_status = (
            "ENGINE_D_INPUT_BUILDER_READY_WITH_FIRST_EPISODE"
            if has_first_episode
            else "ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE"
        )
    else:
        builder_status = "ENGINE_D_INPUT_BUILDER_INSUFFICIENT_BARS"

    provenance = (
        "BUILDER_WITH_FIRST_EPISODE_HEURISTIC_TO_CALIBRATE"
        if has_first_episode
        else "BUILDER_NO_FIRST_EPISODE_DEFAULTS"
    )

    return EngineDInputBuilderResult(
        candidate_id=candidate_id,
        pair=pair,
        builder_status=builder_status,
        structure_summary=summary,
        bridge_result=bridge,
        engine_d_input_payload=payload,
        builder_warnings=tuple(warnings),
        engine_d_input_provenance=provenance,
    )


__all__ = [
    "EngineDInputBuilderResult",
    "EngineDStructureSummary",
    "build_engine_d_input_from_window",
    "derive_engine_d_structure_summary",
]
