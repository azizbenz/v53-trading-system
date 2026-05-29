"""CLI for IA Lab -> Strategy Ladder backtest ML handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_ml_lab_handoff import (  # noqa: E402
    DEFAULT_STRATEGY_LADDER_BACKTEST_OOS_DAYS,
    StrategyLadderMlLabHandoffRequest,
    run_strategy_ladder_ml_lab_handoff,
)
from local_replay_runtime.strategy_ladder_rolling_ml_window_planner import (  # noqa: E402
    DEFAULT_ROLLING_CHUNK_DAYS,
    DEFAULT_ROLLING_FRESHNESS_DAYS,
    DEFAULT_ROLLING_TRAIN_DAYS,
    DEFAULT_ROLLING_VALIDATION_DAYS,
)


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train/export a governed Strategy Ladder expected-edge artifact for backtest.",
    )
    parser.add_argument("--artifact-id", required=True, help="Stable artifact id.")
    parser.add_argument(
        "--calibration-version",
        default="strategy_ladder_expected_edge.v1",
        help="Calibration version carried by the artifact.",
    )
    parser.add_argument("--kline-root", required=True, help="Root containing <pair>/<tf>/<year> klines.")
    parser.add_argument(
        "--b2-run-root",
        default="",
        help="Optional B2 workflow run root used to build replay-grounded labels.",
    )
    parser.add_argument(
        "--label-store-dataset-path",
        default="",
        help="Optional direct replay-grounded label-store dataset path, for example B_ML labels\\b_ml_label_store.jsonl.",
    )
    parser.add_argument("--export-dir", required=True, help="Handoff export directory.")
    parser.add_argument("--pair", default="BTCUSDT", help="Pair to train.")
    # Patch P2b (2026-05-22) — optional multi-pair tuple. When provided with ≥ 2
    # pairs, the handoff emits an additional MULTI_PAIR_C1_EXPECTED_EDGE manifest.
    parser.add_argument(
        "--selected-pairs",
        default="",
        help="Optional CSV of pair names. When ≥ 2, triggers MULTI_PAIR_C1 manifest emission.",
    )
    parser.add_argument(
        "--timeframe",
        default="1m",
        help="Kline timeframe or timeframe CSV, for example 1m or 1m,5m,10m.",
    )
    parser.add_argument("--train-start", required=True, help="Inclusive training data start date.")
    parser.add_argument("--train-end", required=True, help="Inclusive training data end date.")
    parser.add_argument(
        "--requested-backtest-start",
        default="",
        help="Optional first backtest date. Defaults to after artifact validation guard.",
    )
    parser.add_argument(
        "--requested-backtest-days",
        type=int,
        default=DEFAULT_STRATEGY_LADDER_BACKTEST_OOS_DAYS,
        help="Requested OOS backtest days. Defaults to 130 and may fail closed for one artifact.",
    )
    parser.add_argument(
        "--guard-days-after-validation",
        type=int,
        default=1,
        help="Conservative date guard after artifact validation before backtest starts; minimum 1.",
    )
    parser.add_argument("--train-days", type=int, default=DEFAULT_ROLLING_TRAIN_DAYS)
    parser.add_argument(
        "--validation-days",
        type=int,
        default=DEFAULT_ROLLING_VALIDATION_DAYS,
    )
    parser.add_argument(
        "--freshness-days",
        type=int,
        default=DEFAULT_ROLLING_FRESHNESS_DAYS,
    )
    parser.add_argument("--chunk-days", type=int, default=DEFAULT_ROLLING_CHUNK_DAYS)
    parser.add_argument("--sample-stride-minutes", type=int, default=60)
    parser.add_argument("--target-horizon-minutes", type=int, default=1)
    parser.add_argument("--training-seed", type=int, default=5307)
    parser.add_argument("--max-optuna-trials", type=int, default=0)
    parser.add_argument("--min-training-rows", type=int, default=210)
    parser.add_argument(
        "--feature-names",
        default="close_return,high_low_range,volume",
        help=(
            "Comma-separated expected-edge feature names to use. "
            "Supported names are governed by "
            "local_replay_runtime.strategy_ladder_expected_edge_training."
        ),
    )
    parser.add_argument("--shap-summary-ref", default="", help="Optional SHAP summary reference.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_strategy_ladder_ml_lab_handoff(
        StrategyLadderMlLabHandoffRequest(
            artifact_id=args.artifact_id,
            calibration_version=args.calibration_version,
            kline_root=Path(args.kline_root),
            b2_run_root=Path(args.b2_run_root) if args.b2_run_root else None,
            label_store_dataset_path=(
                Path(args.label_store_dataset_path)
                if args.label_store_dataset_path
                else None
            ),
            export_dir=Path(args.export_dir),
            pair=args.pair,
            selected_pairs=_csv_tuple(args.selected_pairs),
            timeframe=args.timeframe,
            train_start=args.train_start,
            train_end=args.train_end,
            requested_backtest_start=args.requested_backtest_start or None,
            requested_backtest_days=args.requested_backtest_days,
            guard_days_after_validation=args.guard_days_after_validation,
            train_days=args.train_days,
            validation_days=args.validation_days,
            freshness_days=args.freshness_days,
            chunk_days=args.chunk_days,
            sample_stride_minutes=args.sample_stride_minutes,
            target_horizon_minutes=args.target_horizon_minutes,
            training_seed=args.training_seed,
            max_optuna_trials=args.max_optuna_trials,
            min_training_rows=args.min_training_rows,
            feature_names=_csv_tuple(args.feature_names),
            shap_summary_ref=args.shap_summary_ref or None,
        )
    )
    print(report.model_dump_json(indent=2))
    return 0 if report.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
