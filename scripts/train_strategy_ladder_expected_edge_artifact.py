"""CLI for governed Strategy Ladder expected-edge artifact training."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_expected_edge_training import (  # noqa: E402
    StrategyLadderExpectedEdgeTrainingRequest,
    train_strategy_ladder_expected_edge_artifact,
)


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a governed Strategy Ladder expected-edge MlModelArtifact.",
    )
    parser.add_argument("--artifact-id", required=True, help="Stable artifact id.")
    parser.add_argument(
        "--calibration-version",
        default="strategy_ladder_expected_edge.v1",
        help="Calibration version carried by the artifact.",
    )
    parser.add_argument("--kline-root", default="", help="Root containing <pair>/<tf>/<year> klines.")
    parser.add_argument(
        "--b2-run-root",
        default="",
        help="Optional B2 workflow run root used to build replay-grounded labels.",
    )
    parser.add_argument(
        "--label-store-dataset-path",
        default="",
        help="Optional prebuilt replay-grounded label-store dataset JSONL path.",
    )
    parser.add_argument("--output-dir", required=True, help="Directory for artifact and training report.")
    parser.add_argument("--pair", default="BTCUSDT", help="Pair to train.")
    parser.add_argument("--timeframe", default="1m", help="Kline timeframe, for example 1m.")
    parser.add_argument("--train-start", required=True, help="Inclusive training data start date.")
    parser.add_argument("--train-end", required=True, help="Inclusive training data end date.")
    parser.add_argument(
        "--sample-stride-minutes",
        type=int,
        default=60,
        help="Deterministic sampling stride in minutes.",
    )
    parser.add_argument(
        "--target-horizon-minutes",
        type=int,
        default=1,
        help="Forward close-return horizon in minutes.",
    )
    parser.add_argument("--training-seed", type=int, default=5307, help="Deterministic trainer seed.")
    parser.add_argument(
        "--max-optuna-trials",
        type=int,
        default=0,
        help="Optuna trial budget. Default 0 keeps the run bounded.",
    )
    parser.add_argument(
        "--min-training-rows",
        type=int,
        default=210,
        help="Fail-closed minimum projected training rows.",
    )
    parser.add_argument(
        "--feature-names",
        default="close_return,high_low_range,volume",
        help="Comma-separated gold-store features to use.",
    )
    parser.add_argument("--shap-summary-ref", default="", help="Optional SHAP summary reference.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id=args.artifact_id,
            calibration_version=args.calibration_version,
            kline_root=Path(args.kline_root) if args.kline_root else None,
            b2_run_root=Path(args.b2_run_root) if args.b2_run_root else None,
            label_store_dataset_path=(
                Path(args.label_store_dataset_path) if args.label_store_dataset_path else None
            ),
            output_dir=Path(args.output_dir),
            pair=args.pair,
            timeframe=args.timeframe,
            train_start=args.train_start,
            train_end=args.train_end,
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
