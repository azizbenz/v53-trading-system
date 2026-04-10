#!/usr/bin/env python3
"""Orchestrate one governed Build-11 Shadow day per invocation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from protocols import (  # noqa: E402
    ShadowDailyExecutionRecord,
    ShadowDailyOrchestrator,
    ShadowDailyPlanSlot,
)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _load_shadow_runner_module():
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


def orchestrate_one_shadow_day(
    output_dir: Path,
    *,
    shadow_output_dir: Path | None = None,
    exports_root: Path | None = None,
    export_dir: Path | None = None,
    session_date: str | None = None,
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
        print("No pending dated Shadow export directory was found.")
        return 0
    if slot.session_date in set(orchestrator.completed_session_dates()):
        print(
            f"Shadow daily orchestrator already completed session_date={slot.session_date}."
        )
        return 0

    runner = _load_shadow_runner_module()
    artifacts = runner.export_local_replay_shadow_run(
        resolved_shadow_output_dir,
        export_dir=Path(slot.export_dir_ref) if slot.export_dir_ref else None,
        shadow_days=1,
        session_date=slot.session_date,
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
            {
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
                "shadow_day_recorded": record.shadow_day_recorded,
                "accepted": record.accepted,
                "consecutive_days": record.consecutive_days,
                "remaining_days": record.remaining_days,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Orchestrated session date: {slot.session_date}")
    print(f"Orchestrator state JSON: {orchestrator.state_path}")
    print(f"Last run JSON: {last_run_path}")
    print(f"Shadow output dir: {resolved_shadow_output_dir}")
    print(f"Local replay evidence JSON: {artifacts.local_replay_evidence_json_path}")
    print(f"Shadow runtime evidence JSON: {artifacts.shadow_runtime_evidence_json_path}")
    print(f"Shadow summary JSON: {artifacts.shadow_summary_json_path}")
    print(f"Shadow report JSON: {artifacts.shadow_report_json_path}")
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
    args = parser.parse_args(argv)
    if args.exports_root is not None and args.export_dir is not None:
        parser.error("--exports-root and --export-dir are mutually exclusive")

    return orchestrate_one_shadow_day(
        args.output_dir,
        shadow_output_dir=args.shadow_output_dir,
        exports_root=args.exports_root,
        export_dir=args.export_dir,
        session_date=args.session_date,
    )


if __name__ == "__main__":
    raise SystemExit(main())
