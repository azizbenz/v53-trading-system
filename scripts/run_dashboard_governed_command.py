#!/usr/bin/env python3
"""Write one governed Build-17 dashboard command request into the typed queue."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts import (  # noqa: E402
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DashboardSecretEnvironment,
    DashboardSecretKind,
    DashboardSecretTransferManifest,
    RuntimeMode,
)
from protocols import (  # noqa: E402
    initialize_dashboard_command_queue,
    write_dashboard_command_request,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write one governed dashboard command request into the typed file queue. "
            "This script never mutates VPS state directly."
        ),
    )
    parser.add_argument(
        "--queue-root",
        type=Path,
        default=REPO_ROOT / "build" / "dashboard_command_queue",
        help="Typed dashboard command queue root.",
    )
    parser.add_argument(
        "--command-kind",
        required=True,
        choices=[kind.value for kind in DashboardGovernedCommandKind],
        help="Governed command kind to enqueue.",
    )
    parser.add_argument(
        "--operator-reason",
        default="",
        help="Operator reason. Required for halt/rollback/suspend/resume actions.",
    )
    parser.add_argument("--target-pair", default="", help="Canonical pair target when required.")
    parser.add_argument("--target-engine", default="", help="Canonical engine target when required.")
    parser.add_argument(
        "--target-secret-profile",
        default="",
        help="Credential profile id for activate/deactivate requests.",
    )
    parser.add_argument(
        "--requested-by",
        default="grafana_operator",
        help="Operator/source label recorded in the request.",
    )
    parser.add_argument("--request-id", default="", help="Optional stable request id.")
    parser.add_argument("--correlation-id", default="", help="Optional stable correlation id.")
    parser.add_argument(
        "--source-runtime-mode",
        default=RuntimeMode.LOCAL_REPLAY.value,
        choices=[mode.value for mode in RuntimeMode],
        help="Source runtime mode recorded in the request.",
    )
    parser.add_argument(
        "--target-runtime-mode",
        default=RuntimeMode.LIVE.value,
        choices=[mode.value for mode in RuntimeMode],
        help="Target runtime mode recorded in the request.",
    )
    parser.add_argument("--artifact-hash", default="", help="Artifact hash for upload commands.")
    parser.add_argument("--artifact-id", default="", help="Artifact id for upload commands.")
    parser.add_argument("--feature-set-version", default="", help="Artifact feature set version.")
    parser.add_argument("--feature-profile", default="", help="Artifact feature profile.")
    parser.add_argument("--lineage-version", default="", help="Artifact lineage/version ref.")
    parser.add_argument("--review-state", default="", help="Artifact review state.")
    parser.add_argument("--validation-status", default="", help="Artifact validation state.")
    parser.add_argument("--source-ref", default="", help="Artifact source/export ref.")
    parser.add_argument("--secret-hash", default="", help="Sealed credential bundle hash.")
    parser.add_argument("--secret-profile-id", default="", help="Sealed credential profile id.")
    parser.add_argument(
        "--secret-environment",
        default=DashboardSecretEnvironment.TESTNET.value,
        choices=[environment.value for environment in DashboardSecretEnvironment],
        help="Credential environment carried as metadata only.",
    )
    parser.add_argument(
        "--secret-sealed-ref",
        default="",
        help="Reference to the sealed credential bundle. Never pass plaintext secrets.",
    )
    parser.add_argument(
        "--secret-backend",
        default="",
        help="Non-sensitive sealed secret backend label.",
    )
    parser.add_argument(
        "--payload-ref",
        action="append",
        default=[],
        help="Repeatable payload ref carried by the artifact manifest.",
    )
    return parser


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


def _build_artifact_manifest(
    args: argparse.Namespace,
    command_kind: DashboardGovernedCommandKind,
) -> DashboardArtifactTransferManifest | None:
    if command_kind == DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT:
        artifact_kind = DashboardArtifactKind.ML_MODEL_ARTIFACT
    elif command_kind == DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT:
        artifact_kind = DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT
    else:
        return None
    return DashboardArtifactTransferManifest(
        artifact_hash=args.artifact_hash,
        artifact_kind=artifact_kind,
        artifact_id=args.artifact_id,
        feature_set_version=args.feature_set_version,
        feature_profile=args.feature_profile,
        lineage_version=args.lineage_version,
        review_state=args.review_state,
        validation_status=args.validation_status,
        source_ref=args.source_ref,
        payload_refs=tuple(args.payload_ref),
    )


def _build_secret_manifest(
    args: argparse.Namespace,
    command_kind: DashboardGovernedCommandKind,
) -> DashboardSecretTransferManifest | None:
    if (
        command_kind
        != DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE
    ):
        return None
    return DashboardSecretTransferManifest(
        secret_hash=args.secret_hash,
        secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
        profile_id=args.secret_profile_id or args.target_secret_profile,
        environment=DashboardSecretEnvironment(args.secret_environment),
        sealed_ref=args.secret_sealed_ref,
        backend=args.secret_backend,
        lineage_version=args.lineage_version,
        review_state=args.review_state,
        validation_status=args.validation_status,
        source_ref=args.source_ref,
        payload_refs=tuple(args.payload_ref),
        created_at_ms=_timestamp_ms(),
    )


def _build_request(args: argparse.Namespace) -> DashboardGovernedCommandRequest:
    timestamp_ms = _timestamp_ms()
    command_kind = DashboardGovernedCommandKind(args.command_kind)
    request_id = args.request_id or f"grafana-{command_kind.value}-{timestamp_ms}"
    correlation_id = args.correlation_id or f"grafana-queue-{timestamp_ms}"
    return DashboardGovernedCommandRequest(
        timestamp_ms=timestamp_ms,
        correlation_id=correlation_id,
        request_id=request_id,
        command_kind=command_kind,
        source_runtime_mode=RuntimeMode(args.source_runtime_mode),
        target_runtime_mode=RuntimeMode(args.target_runtime_mode),
        requested_by=args.requested_by,
        operator_reason=args.operator_reason,
        target_pair=args.target_pair,
        target_engine=args.target_engine,
        target_secret_profile=args.target_secret_profile,
        artifact_manifest=_build_artifact_manifest(args, command_kind),
        secret_manifest=_build_secret_manifest(args, command_kind),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        request = _build_request(args)
    except (ValueError, ValidationError) as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")

    initialize_dashboard_command_queue(args.queue_root)
    request_path = write_dashboard_command_request(args.queue_root, request)
    sys.stdout.write(f"Dashboard governed command request: {request_path}\n")
    sys.stdout.write(f"Request id: {request.request_id}\n")
    sys.stdout.write(f"Command kind: {request.command_kind.value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
