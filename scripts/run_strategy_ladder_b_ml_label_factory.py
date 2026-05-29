"""Run the V5.3 B_ML counterfactual label factory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_b_ml_label_factory import (
    BML_TARGET_POLICY,
    BmlLabelFactoryRequest,
    run_bml_label_factory,
)


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in str(raw_value or "").split(",") if item.strip())


def _int_csv_tuple(raw_value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in str(raw_value or "").split(",") if item.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build B_ML ex-ante feature / post-decision label rows from A2 gold artifacts."
    )
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--a2-run-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--pairs", required=True, help="Comma-separated pair list, e.g. BTCUSDT,BNBUSDT")
    parser.add_argument("--timeframes", required=True, help="Comma-separated timeframe list, e.g. 1m,5m")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--label-horizons", default="5m,15m,1h")
    parser.add_argument("--capital-buckets", default="400,500,1500,4000")
    parser.add_argument("--feature-names", default="close_return,high_low_range,volume")
    parser.add_argument("--candidate-sampler-mode", default="TEMPORAL_STRATIFIED_BACKGROUND_GRID")
    parser.add_argument("--b1-candidate-events-path", type=Path, default=None)
    parser.add_argument("--existing-b1-candidates-root", type=Path, default=None)
    parser.add_argument("--existing-b2-raw-windows-root", type=Path, default=None)
    parser.add_argument("--allow-reuse-existing-raw-windows", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-generate-new-raw-windows", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max-candidates-per-day", type=int, default=0)
    parser.add_argument("--train-start", default="")
    parser.add_argument("--train-end", default="")
    parser.add_argument("--validation-start", default="")
    parser.add_argument("--validation-end", default="")
    parser.add_argument("--allowed-backtest-start-after", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id=args.workflow_run_id,
            a2_run_root=args.a2_run_root,
            output_root=args.output_root,
            pair_list=_csv_tuple(args.pairs),
            timeframes=_csv_tuple(args.timeframes),
            start=args.start,
            end=args.end,
            label_horizons=_csv_tuple(args.label_horizons),
            capital_buckets=_int_csv_tuple(args.capital_buckets),
            candidate_sampler_mode=args.candidate_sampler_mode,
            b1_candidate_events_path=args.b1_candidate_events_path,
            existing_b1_candidates_root=args.existing_b1_candidates_root,
            existing_b2_raw_windows_root=args.existing_b2_raw_windows_root,
            allow_reuse_existing_raw_windows=args.allow_reuse_existing_raw_windows,
            allow_generate_new_raw_windows=args.allow_generate_new_raw_windows,
            feature_names=_csv_tuple(args.feature_names),
            target_policy=BML_TARGET_POLICY,
            max_candidates_per_day=args.max_candidates_per_day,
            train_start=args.train_start,
            train_end=args.train_end,
            validation_start=args.validation_start,
            validation_end=args.validation_end,
            allowed_backtest_start_after=args.allowed_backtest_start_after,
        )
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
