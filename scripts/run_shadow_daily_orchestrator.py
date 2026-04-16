#!/usr/bin/env python3
"""Orchestrate one governed Build-11 Shadow day per invocation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from protocols import (  # noqa: E402
    ShadowDailyExecutionRecord,
    ShadowDailyOrchestrator,
    ShadowDailyPlanSlot,
    build_execution_runtime_projection_bridge_projection,
)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _load_shadow_runner_module() -> ModuleType:
    script_path = REPO_ROOT / "scripts" / "run_local_replay_shadow.py"
    module_name = "shadow_daily_orchestrator_runner"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_local_replay_shadow.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _resolve_slot(
    *,
    orchestrator: ShadowDailyOrchestrator,
    exports_root: Path | None,
    export_dir: Path | None,
    session_date: str | None,
) -> ShadowDailyPlanSlot | None:
    if export_dir is not None:
        discovered_slot = orchestrator.build_slot_from_export_dir(export_dir)
        if session_date is None:
            if discovered_slot is None:
                raise ValueError(
                    "--session-date is required when the export directory does not expose governed session metadata"
                )
            return discovered_slot
        if discovered_slot is not None and discovered_slot.session_date != session_date:
            raise ValueError(
                "Explicit --session-date does not match governed export metadata: "
                f"{session_date} != {discovered_slot.session_date}"
            )
        return ShadowDailyPlanSlot(
            session_date=session_date,
            export_dir_ref=str(export_dir.resolve()),
        )

    if exports_root is not None:
        if session_date is not None:
            for slot in orchestrator.discover_slots(exports_root):
                if slot.session_date == session_date:
                    return slot
            raise FileNotFoundError(
                "Missing export directory with governed session_date="
                f"{session_date} under {exports_root}"
            )
        return orchestrator.select_next_slot(exports_root)

    return orchestrator.next_demo_slot(start_date=session_date)


def _read_execution_runtime_projection_summary(path: Path | None) -> dict[str, object]:
    projection = build_execution_runtime_projection_bridge_projection(
        execution_runtime_projection_path=path
    )
    projection_status = projection.projection_status
    if not projection.configured:
        projection_status = "not_configured"
    elif not projection.projection_found and not projection_status:
        projection_status = "invalid"
    bridge_ready = (
        projection.projection_loaded
        and projection.projection_status == "ready"
        and projection.partial_consumer_count == 0
        and projection.blocked_consumer_count == 0
        and projection.rate_limit_model_loaded
        and projection.spread_guard_model_loaded
        and projection.slippage_model_loaded
    )
    return {
        "execution_runtime_projection_status": projection_status,
        "execution_runtime_projection_ready": bridge_ready,
        "execution_runtime_projection_consumer_count": projection.consumer_count,
        "execution_runtime_projection_ready_consumer_count": (
            projection.ready_consumer_count
        ),
        "execution_runtime_projection_partial_consumer_count": (
            projection.partial_consumer_count
        ),
        "execution_runtime_projection_blocked_consumer_count": (
            projection.blocked_consumer_count
        ),
        "execution_runtime_projection_bridge_status": projection.status,
        "execution_runtime_projection_bridge_loaded": projection.projection_loaded,
        "execution_runtime_projection_rate_limit_model_loaded": (
            projection.rate_limit_model_loaded
        ),
        "execution_runtime_projection_spread_guard_model_loaded": (
            projection.spread_guard_model_loaded
        ),
        "execution_runtime_projection_slippage_model_loaded": (
            projection.slippage_model_loaded
        ),
    }


def _read_regime_lite_governance_summary(
    shadow_summary: dict[str, object],
) -> dict[str, object]:
    governance = shadow_summary.get("regime_lite_governance", {})
    if not isinstance(governance, dict):
        governance = {}
    return {
        "regime_lite_governance_status": str(
            governance.get("status", "not_configured") or "not_configured"
        ),
        "regime_lite_state": str(
            governance.get("state", "not_configured") or "not_configured"
        ),
        "regime_lite_candidate_state": str(
            governance.get("candidate_state", "not_configured")
            or "not_configured"
        ),
        "regime_lite_state_changed": bool(
            governance.get("state_changed", False)
        ),
        "regime_lite_entries_blocked": bool(
            governance.get("entries_blocked", False)
        ),
        "regime_lite_sudden_event": bool(governance.get("sudden_event", False)),
        "regime_lite_safing_severity": str(
            governance.get("safing_severity", "not_configured")
            or "not_configured"
        ),
        "regime_lite_safing_should_block_new_entries": bool(
            governance.get("should_block_new_entries", False)
        ),
        "regime_lite_safing_should_exit_all": bool(
            governance.get("should_exit_all", False)
        ),
        "regime_lite_safing_recommended_operator_action": str(
            governance.get("recommended_operator_action", "")
        ),
        "regime_lite_safing_operator_safing_request_action": str(
            governance.get("operator_safing_request_action", "")
        ),
        "regime_lite_safing_operator_safing_request_source_runtime_mode": str(
            governance.get("operator_safing_request_source_runtime_mode", "")
        ),
        "regime_lite_safing_reason_codes": tuple(
            str(value) for value in governance.get("reason_codes", ())
        ),
        "regime_lite_safing_detail": str(governance.get("detail", "")),
    }


def _read_info_stress_governance_summary(
    shadow_summary: dict[str, object],
) -> dict[str, object]:
    governance = shadow_summary.get("info_stress_governance", {})
    if not isinstance(governance, dict):
        governance = {}
    return {
        "info_stress_governance_status": str(
            governance.get("status", "not_configured") or "not_configured"
        ),
        "info_stress_level": str(
            governance.get("level", "not_configured") or "not_configured"
        ),
        "info_stress_alert_count": int(governance.get("alert_count", 0) or 0),
        "info_stress_entries_blocked": bool(
            governance.get("entries_blocked", False)
        ),
        "info_stress_entries_blocked_until_ts": int(
            governance.get("entries_blocked_until_ts", 0) or 0
        ),
        "info_stress_reason_codes": tuple(
            str(value) for value in governance.get("reason_codes", ())
        ),
        "info_stress_detail": str(governance.get("detail", "")),
    }


def _emit_output_lines(lines: tuple[str, ...]) -> None:
    if not lines:
        return
    sys.stdout.write("\n".join(lines) + "\n")


def _build_last_run_payload(
    *,
    slot: ShadowDailyPlanSlot,
    orchestrator: ShadowDailyOrchestrator,
    resolved_shadow_output_dir: Path,
    artifacts: object,
    execution_runtime_projection_summary: dict[str, object],
    regime_lite_governance_summary: dict[str, object],
    info_stress_governance_summary: dict[str, object],
    record: ShadowDailyExecutionRecord,
) -> dict[str, object]:
    return {
        "session_date": slot.session_date,
        "export_dir_ref": slot.export_dir_ref,
        "state_path": str(orchestrator.state_path.resolve()),
        "shadow_output_dir_ref": str(resolved_shadow_output_dir.resolve()),
        "local_replay_evidence_ref": str(
            artifacts.local_replay_evidence_json_path.resolve()
        ),
        "shadow_runtime_evidence_ref": str(
            artifacts.shadow_runtime_evidence_json_path.resolve()
        ),
        "shadow_summary_ref": str(artifacts.shadow_summary_json_path.resolve()),
        "shadow_report_ref": str(artifacts.shadow_report_json_path.resolve()),
        "shadow_session_summary_ref": str(
            artifacts.shadow_session_summary_json_path.resolve()
        ),
        "shadow_session_registry_ref": str(
            artifacts.shadow_session_registry_json_path.resolve()
        ),
        "execution_runtime_projection_ref": (
            str(artifacts.execution_runtime_projection_json_path.resolve())
            if artifacts.execution_runtime_projection_json_path is not None
            else ""
        ),
        **execution_runtime_projection_summary,
        **regime_lite_governance_summary,
        **info_stress_governance_summary,
        "shadow_day_recorded": record.shadow_day_recorded,
        "accepted": record.accepted,
        "consecutive_days": record.consecutive_days,
        "remaining_days": record.remaining_days,
    }


def _orchestrator_output_lines(
    *,
    slot: ShadowDailyPlanSlot,
    orchestrator: ShadowDailyOrchestrator,
    last_run_path: Path,
    resolved_shadow_output_dir: Path,
    artifacts: object,
) -> tuple[str, ...]:
    return (
        f"Orchestrated session date: {slot.session_date}",
        f"Orchestrator state JSON: {orchestrator.state_path}",
        f"Last run JSON: {last_run_path}",
        f"Shadow output dir: {resolved_shadow_output_dir}",
        f"Local replay evidence JSON: {artifacts.local_replay_evidence_json_path}",
        f"Shadow runtime evidence JSON: {artifacts.shadow_runtime_evidence_json_path}",
        f"Shadow summary JSON: {artifacts.shadow_summary_json_path}",
        f"Shadow report JSON: {artifacts.shadow_report_json_path}",
    )


def orchestrate_one_shadow_day(
    output_dir: Path,
    *,
    shadow_output_dir: Path | None = None,
    exports_root: Path | None = None,
    export_dir: Path | None = None,
    session_date: str | None = None,
    execution_runtime_projection_path: Path | None = None,
    regime_lite_assessment_path: Path | None = None,
    regime_lite_safing_recommendation_path: Path | None = None,
    info_stress_assessment_path: Path | None = None,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_shadow_output_dir = shadow_output_dir or (output_dir / "shadow_session")
    orchestrator = ShadowDailyOrchestrator(output_dir)
    slot = _resolve_slot(
        orchestrator=orchestrator,
        exports_root=exports_root,
        export_dir=export_dir,
        session_date=session_date,
    )
    if slot is None:
        _emit_output_lines(("No pending dated Shadow export directory was found.",))
        return 0
    if slot.session_date in set(orchestrator.completed_session_dates()):
        _emit_output_lines(
            (
                "Shadow daily orchestrator already completed "
                f"session_date={slot.session_date}.",
            )
        )
        return 0

    runner = _load_shadow_runner_module()
    artifacts = runner.export_local_replay_shadow_run(
        resolved_shadow_output_dir,
        export_dir=Path(slot.export_dir_ref) if slot.export_dir_ref else None,
        shadow_days=1,
        session_date=slot.session_date,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=(
            regime_lite_safing_recommendation_path
        ),
        info_stress_assessment_path=info_stress_assessment_path,
    )
    shadow_summary = json.loads(
        artifacts.shadow_summary_json_path.read_text(encoding="utf-8")
    )
    shadow_day_record = json.loads(
        artifacts.shadow_day_record_json_path.read_text(encoding="utf-8")
    )
    shadow_session_summary = json.loads(
        artifacts.shadow_session_summary_json_path.read_text(encoding="utf-8")
    )
    execution_runtime_projection_summary = _read_execution_runtime_projection_summary(
        artifacts.execution_runtime_projection_json_path
    )
    regime_lite_governance_summary = _read_regime_lite_governance_summary(
        shadow_summary
    )
    info_stress_governance_summary = _read_info_stress_governance_summary(
        shadow_summary
    )
    record = ShadowDailyExecutionRecord(
        session_date=slot.session_date,
        export_dir_ref=slot.export_dir_ref,
        shadow_output_dir_ref=str(resolved_shadow_output_dir.resolve()),
        local_replay_evidence_ref=str(artifacts.local_replay_evidence_json_path.resolve()),
        shadow_runtime_evidence_ref=str(artifacts.shadow_runtime_evidence_json_path.resolve()),
        shadow_summary_ref=str(artifacts.shadow_summary_json_path.resolve()),
        shadow_report_ref=str(artifacts.shadow_report_json_path.resolve()),
        shadow_session_summary_ref=str(
            artifacts.shadow_session_summary_json_path.resolve()
        ),
        shadow_session_registry_ref=str(
            artifacts.shadow_session_registry_json_path.resolve()
        ),
        shadow_day_recorded=bool(shadow_day_record.get("passed_all_gates", False)),
        accepted=bool(shadow_summary["decision"]["accepted"]),
        consecutive_days=int(shadow_session_summary["consecutive_days"]),
        remaining_days=int(shadow_session_summary["remaining_days"]),
    )
    orchestrator.record_execution(record)

    last_run_path = output_dir / "shadow_daily_orchestrator.last_run.json"
    last_run_path.write_text(
        json.dumps(
            _build_last_run_payload(
                slot=slot,
                orchestrator=orchestrator,
                resolved_shadow_output_dir=resolved_shadow_output_dir,
                artifacts=artifacts,
                execution_runtime_projection_summary=(
                    execution_runtime_projection_summary
                ),
                regime_lite_governance_summary=regime_lite_governance_summary,
                info_stress_governance_summary=info_stress_governance_summary,
                record=record,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    _emit_output_lines(
        _orchestrator_output_lines(
            slot=slot,
            orchestrator=orchestrator,
            last_run_path=last_run_path,
            resolved_shadow_output_dir=resolved_shadow_output_dir,
            artifacts=artifacts,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        description=(
            "Execute one governed Build-11 Shadow day per invocation from dated local exports."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "shadow_daily_orchestrator",
        help="Directory used to persist orchestrator state and last-run sidecars.",
    )
    parser.add_argument(
        "--shadow-output-dir",
        type=Path,
        default=None,
        help=(
            "Optional directory holding the long-lived Shadow session state. "
            "Defaults to <output-dir>/shadow_session."
        ),
    )
    parser.add_argument(
        "--exports-root",
        type=Path,
        default=None,
        help="Optional root containing daily export directories named YYYY-MM-DD.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Optional explicit export directory for a single orchestrated day.",
    )
    parser.add_argument(
        "--session-date",
        type=str,
        default=None,
        help=(
            "Optional ISO date (YYYY-MM-DD). With --exports-root it targets a specific "
            "dated subdirectory. With --export-dir it pins the governed session date."
        ),
    )
    parser.add_argument(
        "--execution-runtime-projection-path",
        type=Path,
        default=None,
        help=(
            "Optional Local IA Lab execution runtime projection artifact forwarded to "
            "the governed local replay shadow runner."
        ),
    )
    parser.add_argument(
        "--regime-lite-assessment-path",
        type=Path,
        default=None,
        help=(
            "Optional typed regime_lite assessment JSON forwarded to the governed "
            "local replay shadow runner."
        ),
    )
    parser.add_argument(
        "--regime-lite-safing-recommendation-path",
        type=Path,
        default=None,
        help=(
            "Optional typed regime_lite safing recommendation JSON forwarded to the "
            "governed local replay shadow runner."
        ),
    )
    parser.add_argument(
        "--info-stress-assessment-path",
        type=Path,
        default=None,
        help=(
            "Optional typed info_stress assessment JSON forwarded to the governed "
            "local replay shadow runner."
        ),
    )
    args = parser.parse_args(argv)
    if args.exports_root is not None and args.export_dir is not None:
        parser.error("--exports-root and --export-dir are mutually exclusive")

    return orchestrate_one_shadow_day(
        args.output_dir,
        shadow_output_dir=args.shadow_output_dir,
        exports_root=args.exports_root,
        export_dir=args.export_dir,
        session_date=args.session_date,
        execution_runtime_projection_path=args.execution_runtime_projection_path,
        regime_lite_assessment_path=args.regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=(
            args.regime_lite_safing_recommendation_path
        ),
        info_stress_assessment_path=args.info_stress_assessment_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
