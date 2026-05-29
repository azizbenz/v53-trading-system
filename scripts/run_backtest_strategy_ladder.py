"""Canonical CLI entrypoint for the V5.3 Backtest Strategy Ladder runner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_runner import run_backtest_strategy_ladder
from local_replay_runtime.strategy_ladder_models import StrategyLadderRequest


_COCKPIT_JOB_TERMINAL_SENTINEL_ENV = "COCKPIT_JOB_TERMINAL_SENTINEL_PATH"


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _bucket_tuple(raw_value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in (raw_value or "").split(",") if part.strip())


def _write_terminal_sentinel(payload: dict[str, object]) -> None:
    raw_path = os.environ.get(_COCKPIT_JOB_TERMINAL_SENTINEL_ENV, "").strip()
    if not raw_path:
        return
    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "written_at": payload.get("written_at"),
                "run_id": payload.get("run_id"),
                "summary_path": payload.get("summary_path"),
                "final_status": payload.get("final_status"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the canonical V5.3 Strategy Ladder pipeline.")
    parser.add_argument("--run-id", default="", help="Deterministic run id. Required for --resume and --detailed-only.")
    parser.add_argument("--input-root", required=True, help="Canonical base directory for feature-store and raw inputs.")
    parser.add_argument("--feature-store-root", default="", help="Optional override for the feature/gold-store root.")
    parser.add_argument("--raw-root", dest="raw_root_list", action="append", default=[], help="Optional raw market-data root. May be repeated.")
    parser.add_argument("--raw-roots", default="", help="Comma-separated raw market-data roots.")
    parser.add_argument("--raw-source-manifest", default="", help="Optional raw source manifest path.")
    parser.add_argument("--silver-index-path", default="", help="Optional governed silver_index.json path.")
    parser.add_argument("--output-root", default="build", help="Directory that will contain backtest_strategy_ladder/<run_id>.")
    parser.add_argument("--pairs", default="", help="Comma-separated pair filter.")
    parser.add_argument("--engines", default="", help="Comma-separated engine filter.")
    parser.add_argument("--capital-buckets", default="400,500,1500,4000", help="Comma-separated capital buckets.")
    parser.add_argument("--timeframes", default="", help="Comma-separated timeframe filter.")
    parser.add_argument(
        "--feature-names",
        default="",
        help="Comma-separated backtest feature/audit scope; independent from ML overlay mode.",
    )
    parser.add_argument("--start", default="", help="Inclusive start boundary (epoch seconds/ms or ISO date/time).")
    parser.add_argument("--end", default="", help="Inclusive end boundary (epoch seconds/ms or ISO date/time).")
    parser.add_argument("--fast-only", action="store_true", help="Stop after fast candidate export.")
    parser.add_argument("--detailed-only", action="store_true", help="Require existing candidate events and run only detailed stages.")
    parser.add_argument("--resume", action="store_true", help="Resume an existing run directory when possible.")
    parser.add_argument("--dry-run", action="store_true", help="Write only manifest/status artifacts. Do not emit measured outputs.")
    parser.add_argument("--workflow-run-id", default="", help="Parent workflow id for multi-phase diagnostics.")
    parser.add_argument("--phase-run-id", default="", help="Phase-specific run id within the parent workflow.")
    parser.add_argument("--parent-workflow-ref", default="", help="workflow_manifest.json reference for the parent workflow.")
    parser.add_argument("--ml-mode", default="ML_MODE_OFF", help="ML mode for the baseline runner. Training mode is rejected.")
    parser.add_argument("--frozen-ml-artifact-path", default="", help="Frozen ML artifact path for ML_MODE_OVERLAY_FROZEN.")
    parser.add_argument("--frozen-ml-artifact-hash", default="", help="Frozen ML artifact hash for ML_MODE_OVERLAY_FROZEN.")
    # Patch P3 (2026-05-22) — explicit mono|multi mode for the C1-aware provider.
    parser.add_argument(
        "--expected-edge-artifact-mode",
        default="MONO_PAIR_LEGACY",
        choices=("MONO_PAIR_LEGACY", "MULTI_PAIR_C1"),
        help="Expected-edge artifact loader mode (mono frozen bundle vs C1 multi-pair manifest).",
    )
    parser.add_argument(
        "--rolling-ml-window-plan-path",
        default="",
        help="Optional rolling ML window plan for long frozen-ML backtests.",
    )
    parser.add_argument(
        "--ml-artifact-freshness-days",
        default=30,
        type=int,
        help="Maximum days one frozen ML artifact may legally cover before a rolling plan is required.",
    )
    parser.add_argument(
        "--engine-native-mode",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Materialize candidates through native engine A/B/C/D runners before replay (default True; use --no-engine-native-mode for legacy proxy path).",
    )
    parser.add_argument(
        "--engine-native-sample-size",
        default=10,
        type=int,
        help="Legacy audit sample size field; full-path native materialization remains governed by the runner.",
    )
    parser.add_argument("--candidate-discovery-mode", default="SAMPLE_CAPPED_DEBUG", help="Governed candidate discovery breadth mode.")
    parser.add_argument("--candidate-sample-cap", default=10, type=int, help="Per-engine candidate cap for diagnostic discovery.")
    parser.add_argument(
        "--b1-5-policy-mode",
        default="conservative_hard_only",
        choices=(
            "conservative_hard_only",
            "strict_fail_closed",
            "diagnostic_full_replay",
        ),
        help="B1.5 engine-native preselection policy mode.",
    )
    parser.add_argument(
        "--preselected-only",
        dest="preselected_only",
        action="store_true",
        help="Replay only B1.5 engine-native preselected candidates.",
    )
    parser.add_argument(
        "--no-preselected-only",
        dest="preselected_only",
        action="store_false",
        help="Disable preselected-only replay mode.",
    )
    parser.add_argument(
        "--diagnostic-full-replay",
        action="store_true",
        help="Replay all B1 discovery pre-candidates even if B1.5 would reject them.",
    )
    parser.add_argument(
        "--raw-window-mode",
        default="MATERIALIZE",
        choices=("MATERIALIZE", "REFS_ONLY"),
        help="Raw window materialization mode. REFS_ONLY is for fast B1 discovery only.",
    )
    parser.add_argument("--candidate-events-path", default="", help="External candidate_events.jsonl path for B2 detailed replay.")
    parser.add_argument("--small-scope-enabled", action="store_true", help="Persist small-scope lineage in the run manifest.")
    parser.add_argument("--full-scan-enabled", action="store_true", help="Persist full-scan lineage in the run manifest.")
    parser.add_argument("--no-full-scan-enabled", action="store_true", help="Persist no-full-scan lineage in the run manifest.")
    parser.set_defaults(preselected_only=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    run_id = args.run_id.strip() or f"strategy-ladder-{uuid4().hex[:12]}"
    if (args.resume or args.detailed_only) and not args.run_id.strip():
        parser.error("--run-id is required for --resume and --detailed-only")
    input_root = Path(args.input_root).resolve()
    feature_store_root = Path(args.feature_store_root).resolve() if args.feature_store_root else input_root / "feature_store"
    raw_roots = tuple(
        dict.fromkeys(
            str(Path(value).resolve())
            for value in [*args.raw_root_list, *_csv_tuple(args.raw_roots)]
            if value
        )
    )
    raw_root_values = tuple(Path(value) for value in raw_roots)
    raw_root = raw_root_values[0] if raw_root_values else (input_root / "raw")
    output_root = Path(args.output_root).resolve()
    request = StrategyLadderRequest(
        run_id=run_id,
        input_root=input_root,
        feature_store_root=feature_store_root,
        raw_root=raw_root,
        raw_roots=raw_root_values,
        raw_source_manifest_path=(
            Path(args.raw_source_manifest).resolve()
            if args.raw_source_manifest
            else None
        ),
        silver_index_path=(
            Path(args.silver_index_path).resolve()
            if args.silver_index_path
            else None
        ),
        output_root=output_root,
        workflow_run_id=args.workflow_run_id.strip() or run_id,
        phase_run_id=args.phase_run_id.strip(),
        parent_workflow_ref=args.parent_workflow_ref.strip(),
        pairs=_csv_tuple(args.pairs),
        engines=_csv_tuple(args.engines),
        capital_buckets=_bucket_tuple(args.capital_buckets),
        timeframes=_csv_tuple(args.timeframes),
        feature_names=_csv_tuple(args.feature_names),
        start=args.start,
        end=args.end,
        fast_only=args.fast_only,
        detailed_only=args.detailed_only,
        resume=args.resume,
        dry_run=args.dry_run,
        ml_mode=args.ml_mode,
        frozen_ml_artifact_path=(
            Path(args.frozen_ml_artifact_path).resolve()
            if args.frozen_ml_artifact_path
            else None
        ),
        frozen_ml_artifact_hash=args.frozen_ml_artifact_hash or None,
        expected_edge_artifact_mode=args.expected_edge_artifact_mode,
        rolling_ml_window_plan_path=(
            Path(args.rolling_ml_window_plan_path).resolve()
            if args.rolling_ml_window_plan_path
            else None
        ),
        ml_artifact_freshness_days=max(int(args.ml_artifact_freshness_days), 1),
        engine_native_mode=args.engine_native_mode,
        engine_native_sample_size=args.engine_native_sample_size,
        candidate_discovery_mode=args.candidate_discovery_mode,
        candidate_sample_cap=max(int(args.candidate_sample_cap), 0),
        b1_5_policy_mode=args.b1_5_policy_mode,
        raw_window_materialization_mode=args.raw_window_mode,
        preselected_only=bool(args.preselected_only),
        diagnostic_full_replay=bool(args.diagnostic_full_replay),
        small_scope_enabled=args.small_scope_enabled,
        full_scan_enabled=args.full_scan_enabled,
        no_full_scan_enabled=args.no_full_scan_enabled,
        candidate_events_path=(
            Path(args.candidate_events_path).resolve()
            if args.candidate_events_path
            else None
        ),
    )
    result = run_backtest_strategy_ladder(request)
    payload = {
        "run_id": result.run_manifest.run_id,
        "run_manifest_path": str((request.run_dir / "run_manifest.json").resolve()),
        "summary_path": str((request.run_dir / "reports" / "strategy_ladder_summary.json").resolve()),
        "final_status": result.run_manifest.final_status,
        "candidate_count": result.run_manifest.candidate_count,
        "detailed_replay_count": result.run_manifest.detailed_replay_count,
        "capital_profile_count": result.run_manifest.capital_profile_count,
        "engine_promotion_count": result.run_manifest.engine_promotion_count,
        "pair_promotion_count": result.run_manifest.pair_promotion_count,
        "strategy_promotion_count": result.run_manifest.strategy_promotion_count,
        "written_at": result.run_manifest.updated_at.isoformat(),
    }
    print(json.dumps(payload, indent=2))
    sys.stdout.flush()
    _write_terminal_sentinel(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
