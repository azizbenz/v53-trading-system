"""Shadow VPS service CLI helpers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from interface_contracts.shadow_vps_service_contracts import ShadowVpsServiceState
from protocols import ShadowVpsServiceStore


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent

_SERVICE_PATH_ARGUMENTS: tuple[dict[str, object], ...] = (
    {
        "name": "--service-dir",
        "type": Path,
        "default": REPO_ROOT / "build" / "shadow_vps_service",
        "help": "Directory used to persist the VPS Shadow service state and logs.",
    },
    {
        "name": "--orchestrator-output-dir",
        "type": Path,
        "default": None,
        "help": "Optional directory used for the external daily orchestrator state.",
    },
    {
        "name": "--shadow-output-dir",
        "type": Path,
        "default": None,
        "help": "Optional directory used for the long-lived Shadow session artifacts.",
    },
    {
        "name": "--exports-root",
        "type": Path,
        "default": None,
        "help": "Optional root containing daily export directories named YYYY-MM-DD.",
    },
    {
        "name": "--raw-inputs-root",
        "type": Path,
        "default": None,
        "help": (
            "Optional root containing daily raw input directories named YYYY-MM-DD. "
            "Each dated directory must contain a replay_dataset.* or snapshot_batch.* file."
        ),
    },
    {
        "name": "--websocket-streams-root",
        "type": Path,
        "default": None,
        "help": (
            "Optional root containing daily injected websocket directories named YYYY-MM-DD. "
            "Each dated directory must contain websocket_stream.json(.l) or websocket_frames.json(.l)."
        ),
    },
    {
        "name": "--live-websocket-config",
        "type": Path,
        "default": None,
        "help": (
            "Optional JSON config used to capture a bounded native live_websocket window "
            "directly from the VPS."
        ),
    },
    {
        "name": "--live-captures-root",
        "type": Path,
        "default": None,
        "help": (
            "Optional root where native live_websocket captures will be written before "
            "governed export."
        ),
    },
    {
        "name": "--auto-snapshots-root",
        "type": Path,
        "default": None,
        "help": (
            "Optional root where historical snapshot batches auto-generated from "
            "--websocket-streams-root will be written."
        ),
    },
    {
        "name": "--auto-exports-root",
        "type": Path,
        "default": None,
        "help": (
            "Optional root where governed exports auto-generated from --raw-inputs-root "
            "will be written."
        ),
    },
    {
        "name": "--dashboard-command-queue-root",
        "type": Path,
        "default": None,
        "help": (
            "Optional governed dashboard command queue root. When set, the VPS "
            "service consumes typed operator requests at the start of each cycle."
        ),
    },
)

_EXECUTION_RUNTIME_ARGUMENTS: tuple[dict[str, object], ...] = (
    {
        "name": "--execution-time-sync-offsets-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional JSON list/mapping carrying THR-X01 time-sync offsets for the current "
            "service cycle. When omitted, the service falls back to a native live-capture "
            "`live_time_sync_offsets.json` sidecar when present; otherwise the execution "
            "telemetry sidecar remains explicit partial for THR-X01."
        ),
    },
    {
        "name": "--execution-runtime-bootstrap-enabled",
        "action": "store_true",
        "help": (
            "Enable the bounded Binance execution runtime bootstrap seam at service "
            "startup. This is inspection/bootstrap only, not order submission."
        ),
    },
    {
        "name": "--execution-runtime-gatekeeper-audit-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional JSONL audit path for the bounded execution gatekeeper audit "
            "logger used by the startup bootstrap seam."
        ),
    },
    {
        "name": "--execution-runtime-projection-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional Local IA Lab execution runtime projection artifact forwarded to "
            "the governed daily Shadow orchestrator."
        ),
    },
    {
        "name": "--regime-lite-assessment-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional typed regime_lite assessment JSON forwarded to the governed "
            "daily Shadow orchestrator."
        ),
    },
    {
        "name": "--regime-lite-safing-recommendation-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional typed regime_lite safing recommendation JSON forwarded to the "
            "governed daily Shadow orchestrator."
        ),
    },
    {
        "name": "--info-stress-assessment-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional typed info_stress assessment JSON forwarded to the governed "
            "daily Shadow orchestrator."
        ),
    },
    {
        "name": "--telegram-alert-config-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional JSON/YAML or sealed Telegram bot config used to send bounded "
            "Shadow service alerts."
        ),
    },
    {
        "name": "--telegram-alert-key-path",
        "type": Path,
        "default": None,
        "help": (
            "Optional master-key path required when --telegram-alert-config-path "
            "targets a sealed secret mapping."
        ),
    },
)

_MONITORING_ARGUMENTS: tuple[dict[str, object], ...] = (
    {
        "name": "--node-exporter-textfile-dir",
        "type": Path,
        "default": None,
        "help": (
            "Optional node_exporter textfile collector directory where the compact "
            "Shadow VPS `.prom` export will be mirrored."
        ),
    },
    {
        "name": "--scrape-host",
        "default": "",
        "help": (
            "Optional reachable host or IP used to materialize a local-PC Prometheus "
            "scrape manifest for this VPS."
        ),
    },
    {
        "name": "--vps-id",
        "default": "",
        "help": "Optional stable VPS identifier written into the local scrape manifest.",
    },
    {
        "name": "--node-exporter-port",
        "type": int,
        "default": 9100,
        "help": "Port used for the node_exporter endpoint on the VPS.",
    },
    {
        "name": "--node-exporter-scheme",
        "default": "http",
        "help": "Scheme used for the node_exporter endpoint on the VPS.",
    },
    {
        "name": "--node-exporter-metrics-path",
        "default": "/metrics",
        "help": "Metrics path used for the node_exporter endpoint on the VPS.",
    },
    {
        "name": "--prometheus-job-name",
        "default": "v53_shadow_vps",
        "help": "Job label written into the Prometheus file_sd entry for this VPS.",
    },
)

_RUNTIME_LOOP_ARGUMENTS: tuple[dict[str, object], ...] = (
    {
        "name": "--poll-interval-s",
        "type": float,
        "default": 5.0,
        "help": "Sleep duration between cycles when the service stays alive.",
    },
    {
        "name": "--max-cycles",
        "type": int,
        "default": None,
        "help": "Optional maximum number of service cycles. Useful for tests and smoke runs.",
    },
    {
        "name": "--stop-on-error",
        "action": "store_true",
        "help": "Stop the service immediately on the first orchestration error.",
    },
)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _emit_output_lines(lines: tuple[str, ...]) -> None:
    for line in lines:
        sys.stdout.write(f"{line}\n")


def _base_service_output_lines(
    *,
    store: ShadowVpsServiceStore,
    service_dir: Path,
    resolved_orchestrator_output_dir: Path,
    resolved_shadow_output_dir: Path,
) -> list[str]:
    """Return the fixed set of output lines for Shadow VPS artifacts."""
    return [
        f"Shadow VPS service state JSON: {store.state_path}",
        f"Shadow VPS service events JSONL: {store.events_path}",
        (
            "Shadow daily orchestrator state JSON: "
            f"{resolved_orchestrator_output_dir / 'shadow_daily_orchestrator.state.json'}"
        ),
        (
            "Shadow session summary JSON: "
            f"{resolved_shadow_output_dir / 'local_replay_shadow.shadow_session_summary.json'}"
        ),
        (
            "Shadow VPS monitoring backend JSON: "
            f"{service_dir / 'shadow_vps_service_monitoring_backend_payload.json'}"
        ),
        (
            "Shadow VPS observability export JSON: "
            f"{service_dir / 'shadow_vps_service_observability_export.json'}"
        ),
        (
            "Shadow VPS observability text PROM: "
            f"{service_dir / 'shadow_vps_service_observability.prom'}"
        ),
        (
            "Shadow VPS recent events summary JSON: "
            f"{service_dir / 'shadow_vps_service_recent_events.json'}"
        ),
    ]


def _append_scrape_output_lines(
    *,
    lines: list[str],
    service_dir: Path,
    scrape_host: str,
    node_exporter_textfile_dir: Path | None,
) -> None:
    if scrape_host:
        lines.extend(
            [
                (
                    "Shadow VPS scrape manifest JSON: "
                    f"{service_dir / 'shadow_vps_service_scrape_manifest.json'}"
                ),
                (
                    "Shadow VPS Prometheus file_sd JSON: "
                    f"{service_dir / 'shadow_vps_service_prometheus_file_sd.json'}"
                ),
            ]
        )
    if node_exporter_textfile_dir is not None:
        lines.append(
            "Shadow VPS node_exporter textfile PROM: "
            f"{node_exporter_textfile_dir / 'v53_shadow_vps_service.prom'}"
        )


def _append_state_output_lines(
    lines: list[str],
    state: ShadowVpsServiceState,
) -> None:
    if state.last_campaign_summary_ref:
        lines.append(
            f"Shadow VPS campaign summary JSON: {state.last_campaign_summary_ref}"
        )
    if state.last_runtime_evidence_bundle_ref:
        lines.append(
            "Shadow runtime evidence bundle JSON: "
            f"{state.last_runtime_evidence_bundle_ref}"
        )
    if state.last_execution_telemetry_ref:
        lines.append(
            f"Shadow execution telemetry JSON: {state.last_execution_telemetry_ref}"
        )
    if state.last_execution_runtime_bootstrap_ref:
        lines.append(
            "Shadow execution runtime bootstrap summary JSON: "
            f"{state.last_execution_runtime_bootstrap_ref}"
        )


def _build_service_output_lines(
    *,
    store: ShadowVpsServiceStore,
    service_dir: Path,
    resolved_orchestrator_output_dir: Path,
    resolved_shadow_output_dir: Path,
    scrape_host: str,
    node_exporter_textfile_dir: Path | None,
) -> tuple[str, ...]:
    state = store.state
    lines = _base_service_output_lines(
        store=store,
        service_dir=service_dir,
        resolved_orchestrator_output_dir=resolved_orchestrator_output_dir,
        resolved_shadow_output_dir=resolved_shadow_output_dir,
    )
    _append_scrape_output_lines(
        lines=lines,
        service_dir=service_dir,
        scrape_host=scrape_host,
        node_exporter_textfile_dir=node_exporter_textfile_dir,
    )
    _append_state_output_lines(lines, state)
    return tuple(lines)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the autonomous VPS Shadow service that keeps polling and processing governed Shadow days."
        ),
    )
    _add_service_path_arguments(parser)
    _add_execution_runtime_arguments(parser)
    _add_monitoring_arguments(parser)
    _add_runtime_loop_arguments(parser)
    return parser


def _add_argument_specs(
    parser: argparse.ArgumentParser,
    specs: tuple[dict[str, object], ...],
) -> None:
    for spec in specs:
        name = spec["name"]
        kwargs = {key: value for key, value in spec.items() if key != "name"}
        parser.add_argument(name, **kwargs)


def _add_service_path_arguments(parser: argparse.ArgumentParser) -> None:
    _add_argument_specs(parser, _SERVICE_PATH_ARGUMENTS)


def _add_execution_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    _add_argument_specs(parser, _EXECUTION_RUNTIME_ARGUMENTS)


def _add_monitoring_arguments(parser: argparse.ArgumentParser) -> None:
    _add_argument_specs(parser, _MONITORING_ARGUMENTS)


def _add_runtime_loop_arguments(parser: argparse.ArgumentParser) -> None:
    _add_argument_specs(parser, _RUNTIME_LOOP_ARGUMENTS)


def _validate_input_root_selection(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    selected_input_roots = (
        int(args.exports_root is not None)
        + int(args.raw_inputs_root is not None)
        + int(args.websocket_streams_root is not None)
        + int(args.live_websocket_config is not None)
    )
    if selected_input_roots > 1:
        parser.error(
            "--exports-root, --raw-inputs-root, --websocket-streams-root, and --live-websocket-config are mutually exclusive"
        )
