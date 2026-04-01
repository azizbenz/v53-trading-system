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


class ReplayArtifactExportResult(BaseModel, frozen=True):
    """Stable paths emitted by the governed LOCAL_REPLAY artifact exporter."""

    export_dir: Path
    run_manifest_path: Path
    review_export_path: Path
    feature_bridge_path: Path
    parity_diagnostics_path: Path
    replay_metrics_path: Path
    replay_dtr_path: Path

    @property
    def payload_refs(self) -> tuple[str, ...]:
        return (
            str(self.review_export_path.resolve()),
            str(self.feature_bridge_path.resolve()),
            str(self.parity_diagnostics_path.resolve()),
            str(self.replay_metrics_path.resolve()),
            str(self.replay_dtr_path.resolve()),
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

    return ReplayArtifactExportResult(
        export_dir=output_dir,
        run_manifest_path=run_manifest_path,
        review_export_path=review_export_path,
        feature_bridge_path=feature_bridge_path,
        parity_diagnostics_path=parity_diagnostics_path,
        replay_metrics_path=replay_metrics_path,
        replay_dtr_path=replay_dtr_path,
    )


__all__ = [
    "ReplayArtifactExportRequest",
    "ReplayArtifactExportResult",
    "export_local_replay_artifact",
]
