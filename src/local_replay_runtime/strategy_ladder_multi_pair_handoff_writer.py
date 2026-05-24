"""Multi-pair C1 manifest writer for the Strategy Ladder ML Lab handoff.

Patch P2b (2026-05-22) — writes the `MULTI_PAIR_C1_EXPECTED_EDGE.json` manifest
consumed by the strategy-ladder backtest runner when `expected_edge_artifact_mode
== MULTI_PAIR_C1` (P1 provider). The manifest aggregates per-pair training
artifacts produced by the mono-pair handoff orchestrator into a single C1
inference entry point.

Doctrine :
- ZERO hardcoded pair names — the encoding is derived from the caller-provided
  tuple of pair names (sorted alphabetical for determinism, aligned with
  C1.3.C `_assign_pair_ids_deterministic`).
- Backward-compat strict — when `selected_pairs` is empty OR len < 2, the
  writer is NOT invoked by the handoff orchestrator (mono-pair path stays
  exactly as-is).
- Audit-ready — manifest fields mirror those required by
  `StrategyLadderMultiPairC1Manifest` (P1).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from local_replay_runtime.strategy_ladder_edge_model_provider_multi_pair import (
    MULTI_PAIR_C1_ARTIFACT_KIND,
)
from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    PAIR_ID_FEATURE_KEY,
    _assign_pair_ids_deterministic,
)


MULTI_PAIR_C1_HANDOFF_MANIFEST_FILENAME = (
    "strategy_ladder_expected_edge_multi_pair_c1_manifest.json"
)


def _hash_sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_multi_pair_c1_handoff_manifest(
    *,
    artifact_id: str,
    calibration_version: str,
    timeframe: str,
    selected_pairs: tuple[str, ...],
    feature_names: tuple[str, ...],
    model_path_ref: str,
    train_start: str,
    train_end: str,
    horizon_minutes: int = 1,
    purge_window_minutes: int = 0,
    embargo_window_minutes: int = 0,
    label_source: str = "MULTI_PAIR_C1_HANDOFF_AGGREGATE",
    label_fidelity: str = "EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
    anti_leakage_status: str = "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN",
    walkforward_status: str = "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED",
) -> dict[str, object]:
    """Build the in-memory manifest dict ready to serialize as JSON.

    Args:
        artifact_id: unique id for this multi-pair handoff artifact.
        calibration_version: opaque calibration identifier (e.g. "v1").
        timeframe: scope (e.g. "1m", "15m").
        selected_pairs: tuple of pair names selected by the admin (≥ 2 expected).
        feature_names: tuple including PAIR_ID_FEATURE_KEY (validator enforces).
        model_path_ref: path (absolute or relative) to the LightGBM `.lgb` file.
        train_start / train_end: ISO date strings of the training window.
        horizon_minutes / purge_window_minutes / embargo_window_minutes:
            governance window parameters (defaults are safe for stub manifests).

    Returns:
        dict ready to be passed to `json.dumps` and consumed by
        `StrategyLadderMultiPairC1Manifest.model_validate_json` (P1 loader).

    Raises:
        ValueError: when selected_pairs has < 1 entry or feature_names misses
            the pair_id key.
    """
    normalized_pairs = tuple(p.strip().upper() for p in selected_pairs if p.strip())
    if not normalized_pairs:
        raise ValueError(
            "DOCTRINE_MULTI_PAIR_C1_HANDOFF_EMPTY_PAIRS — at least one pair required"
        )
    normalized_features = tuple(name.strip() for name in feature_names if name.strip())
    if PAIR_ID_FEATURE_KEY not in normalized_features:
        raise ValueError(
            f"DOCTRINE_MULTI_PAIR_C1_HANDOFF_MISSING_PAIR_ID — feature_names must "
            f"include {PAIR_ID_FEATURE_KEY!r}"
        )

    pair_id_encoding = _assign_pair_ids_deterministic(normalized_pairs)
    feature_hash = _hash_sha256_hex(
        json.dumps(list(normalized_features), sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    artifact_hash_seed = {
        "artifact_id": artifact_id,
        "calibration_version": calibration_version,
        "timeframe": timeframe,
        "model_path_ref": model_path_ref,
        "feature_hash": feature_hash,
        "pair_id_encoding": pair_id_encoding,
    }
    artifact_hash = _hash_sha256_hex(
        json.dumps(artifact_hash_seed, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    )

    return {
        "artifact_kind": MULTI_PAIR_C1_ARTIFACT_KIND,
        "artifact_id": artifact_id,
        "artifact_hash": artifact_hash,
        "feature_hash": feature_hash,
        "feature_names": list(normalized_features),
        "pair_id_encoding": dict(pair_id_encoding),
        "calibration_version": calibration_version,
        "timeframe": timeframe,
        "model_path_ref": model_path_ref,
        "label_source": label_source,
        "label_fidelity": label_fidelity,
        "anti_leakage_status": anti_leakage_status,
        "walkforward_status": walkforward_status,
        "horizon_minutes": horizon_minutes,
        "purge_window_minutes": purge_window_minutes,
        "embargo_window_minutes": embargo_window_minutes,
        "training_window": {
            "train_start": train_start,
            "train_end": train_end,
        },
    }


def write_multi_pair_c1_handoff_manifest(
    *,
    export_dir: Path,
    manifest: dict[str, object],
    filename: str = MULTI_PAIR_C1_HANDOFF_MANIFEST_FILENAME,
) -> Path:
    """Persist the manifest dict as JSON in export_dir and return the Path."""
    export_dir.mkdir(parents=True, exist_ok=True)
    target = export_dir / filename
    target.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def maybe_emit_multi_pair_c1_handoff_manifest(
    *,
    selected_pairs: Iterable[str],
    artifact_id: str,
    calibration_version: str,
    timeframe: str,
    feature_names: tuple[str, ...],
    model_path_ref: str,
    train_start: str,
    train_end: str,
    export_dir: Path,
) -> Path | None:
    """Emit the manifest only when ≥ 2 pairs selected (multi-pair condition).

    Returns the written manifest path, or None if condition not met.
    The handoff orchestrator calls this after the per-timeframe mono training
    so the resulting `.lgb` reference (model_path_ref) can be reused as a stub
    booster pending a future real C1.3.C multi-pair training pass.
    """
    normalized = tuple(
        name.strip().upper() for name in selected_pairs if name and name.strip()
    )
    if len(normalized) < 2:
        return None

    features_with_pair_id = tuple(dict.fromkeys((*feature_names, PAIR_ID_FEATURE_KEY)))

    manifest = build_multi_pair_c1_handoff_manifest(
        artifact_id=artifact_id,
        calibration_version=calibration_version,
        timeframe=timeframe,
        selected_pairs=normalized,
        feature_names=features_with_pair_id,
        model_path_ref=model_path_ref,
        train_start=train_start,
        train_end=train_end,
    )
    return write_multi_pair_c1_handoff_manifest(
        export_dir=export_dir,
        manifest=manifest,
    )


__all__ = [
    "MULTI_PAIR_C1_HANDOFF_MANIFEST_FILENAME",
    "build_multi_pair_c1_handoff_manifest",
    "maybe_emit_multi_pair_c1_handoff_manifest",
    "write_multi_pair_c1_handoff_manifest",
]
