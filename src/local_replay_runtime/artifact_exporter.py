"""Artifact exporter for governed LOCAL_REPLAY runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.replay_run_manifest import ReplayRunManifest


class ReplayArtifactExportRequest(BaseModel, frozen=True):
    """Canonical inputs required to export a governed LOCAL_REPLAY artifact."""

    run_manifest: ReplayRunManifest
    review_export_markdown: str = Field(..., min_length=1)
    feature_bridge_payload: dict[str, Any]
    parity_diagnostics_payload: dict[str, Any]
    replay_metrics_payload: dict[str, Any]
    replay_dtr_records: tuple[dict[str, Any], ...]
    capital_profile_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)
    engine_promotion_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pair_promotion_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)
    strategy_promotion_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sample_size_survival_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ReplayArtifactExportResult(BaseModel, frozen=True):
    """Stable paths emitted by the governed LOCAL_REPLAY artifact exporter."""

    export_dir: Path
    run_manifest_path: Path
    review_export_path: Path
    feature_bridge_path: Path
    parity_diagnostics_path: Path
    replay_metrics_path: Path
    replay_dtr_path: Path
    capital_profile_paths: tuple[Path, ...] = ()
    engine_promotion_paths: tuple[Path, ...] = ()
    pair_promotion_paths: tuple[Path, ...] = ()
    strategy_promotion_paths: tuple[Path, ...] = ()
    sample_size_survival_paths: tuple[Path, ...] = ()

    @property
    def payload_refs(self) -> tuple[str, ...]:
        return (
            str(self.review_export_path.resolve()),
            str(self.feature_bridge_path.resolve()),
            str(self.parity_diagnostics_path.resolve()),
            str(self.replay_metrics_path.resolve()),
            str(self.replay_dtr_path.resolve()),
            *(str(path.resolve()) for path in self.capital_profile_paths),
            *(str(path.resolve()) for path in self.engine_promotion_paths),
            *(str(path.resolve()) for path in self.pair_promotion_paths),
            *(str(path.resolve()) for path in self.strategy_promotion_paths),
            *(str(path.resolve()) for path in self.sample_size_survival_paths),
        )


def export_local_replay_artifact(
    output_dir: Path,
    request: ReplayArtifactExportRequest,
) -> ReplayArtifactExportResult:
    """Write the canonical LOCAL_REPLAY artifact directory structure."""

    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest_path = output_dir / "replay_run_manifest.json"
    review_export_path = output_dir / "review_export.md"
    feature_bridge_path = output_dir / "feature_bridge.json"
    parity_diagnostics_path = output_dir / "parity_diagnostics.json"
    replay_metrics_path = output_dir / "replay_metrics.json"
    replay_dtr_path = output_dir / "replay_dtr.jsonl"
    capital_profile_dir = output_dir / "capital_profiles"
    engine_promotion_dir = output_dir / "engine_promotion"
    pair_promotion_dir = output_dir / "pair_promotion"
    strategy_promotion_dir = output_dir / "strategy_promotion"
    sample_size_survival_dir = output_dir / "sample_size_survival"

    atomic_write_json(
        run_manifest_path,
        request.run_manifest.model_dump(mode="json"),
    )
    atomic_write_text(review_export_path, request.review_export_markdown)
    atomic_write_json(feature_bridge_path, request.feature_bridge_payload)
    atomic_write_json(parity_diagnostics_path, request.parity_diagnostics_payload)
    atomic_write_json(replay_metrics_path, request.replay_metrics_payload)
    atomic_write_text(
        replay_dtr_path,
        "\n".join(
            [
                json.dumps(record, ensure_ascii=False, default=str)
                for record in request.replay_dtr_records
            ]
        )
        + ("\n" if request.replay_dtr_records else ""),
    )
    capital_profile_paths: list[Path] = []
    engine_promotion_paths: list[Path] = []
    pair_promotion_paths: list[Path] = []
    strategy_promotion_paths: list[Path] = []
    sample_size_survival_paths: list[Path] = []
    if request.capital_profile_payloads:
        capital_profile_dir.mkdir(parents=True, exist_ok=True)
        for bucket, payload in sorted(
            request.capital_profile_payloads.items(),
            key=lambda item: int(item[0]),
        ):
            path = capital_profile_dir / f"{bucket}.json"
            atomic_write_json(path, payload)
            capital_profile_paths.append(path)
    if request.engine_promotion_payloads:
        engine_promotion_dir.mkdir(parents=True, exist_ok=True)
        for engine_id, payload in sorted(request.engine_promotion_payloads.items()):
            run_id = str(payload.get("run_id") or request.run_manifest.run_id)
            path = engine_promotion_dir / engine_id / f"{run_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(path, payload)
            engine_promotion_paths.append(path)
    if request.pair_promotion_payloads:
        pair_promotion_dir.mkdir(parents=True, exist_ok=True)
        for pair, payload in sorted(request.pair_promotion_payloads.items()):
            run_id = str(payload.get("run_id") or request.run_manifest.run_id)
            path = pair_promotion_dir / pair / f"{run_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(path, payload)
            pair_promotion_paths.append(path)
    if request.strategy_promotion_payloads:
        strategy_promotion_dir.mkdir(parents=True, exist_ok=True)
        for strategy_id, payload in sorted(request.strategy_promotion_payloads.items()):
            run_id = str(payload.get("run_id") or request.run_manifest.run_id)
            path = strategy_promotion_dir / strategy_id / f"{run_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(path, payload)
            strategy_promotion_paths.append(path)
    if request.sample_size_survival_payloads:
        sample_size_survival_dir.mkdir(parents=True, exist_ok=True)
        for scoped_id, payload in sorted(request.sample_size_survival_payloads.items()):
            scope = str(payload.get("scope") or "unknown")
            scope_id = str(payload.get("id") or scoped_id)
            run_id = str(payload.get("run_id") or request.run_manifest.run_id)
            path = sample_size_survival_dir / scope / scope_id / f"{run_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(path, payload)
            sample_size_survival_paths.append(path)

    return ReplayArtifactExportResult(
        export_dir=output_dir,
        run_manifest_path=run_manifest_path,
        review_export_path=review_export_path,
        feature_bridge_path=feature_bridge_path,
        parity_diagnostics_path=parity_diagnostics_path,
        replay_metrics_path=replay_metrics_path,
        replay_dtr_path=replay_dtr_path,
        capital_profile_paths=tuple(capital_profile_paths),
        engine_promotion_paths=tuple(engine_promotion_paths),
        pair_promotion_paths=tuple(pair_promotion_paths),
        strategy_promotion_paths=tuple(strategy_promotion_paths),
        sample_size_survival_paths=tuple(sample_size_survival_paths),
    )


__all__ = [
    "ReplayArtifactExportRequest",
    "ReplayArtifactExportResult",
    "export_local_replay_artifact",
]
