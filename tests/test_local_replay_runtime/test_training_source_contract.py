from __future__ import annotations

from pathlib import Path

from local_replay_runtime.training_source_contract import (
    ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED,
    TRAINING_SOURCE_CONTRACT_OK,
    TRAIN_EVAL_OVERLAP_BLOCKED,
    build_training_source_contract_report,
)


def test_training_source_contract_allows_sequential_windows(tmp_path: Path) -> None:
    report = build_training_source_contract_report(
        manifest_root_or_path=tmp_path / "missing_manifest_root",
        source_type="B2_REPLAY_GROUNDED_LABEL_STORE",
        train_start="2025-02-02",
        train_end="2025-06-02",
        validation_start="2025-06-03",
        validation_end="2025-07-02",
        backtest_start="2025-07-03",
        backtest_end="2025-08-01",
    )

    assert report.status == TRAINING_SOURCE_CONTRACT_OK
    assert report.overlap_status == TRAINING_SOURCE_CONTRACT_OK
    assert report.blocker_reasons == ()


def test_training_source_contract_blocks_train_eval_overlap(tmp_path: Path) -> None:
    report = build_training_source_contract_report(
        manifest_root_or_path=tmp_path / "missing_manifest_root",
        source_type="B2_REPLAY_GROUNDED_LABEL_STORE",
        train_start="2025-07-18",
        train_end="2025-08-01",
        validation_start="2025-07-18",
        validation_end="2025-08-01",
        backtest_start="2025-07-18",
        backtest_end="2025-08-01",
    )

    assert report.status == TRAIN_EVAL_OVERLAP_BLOCKED
    assert ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED in report.blocker_reasons


def test_training_source_manifest_allowed_backtest_start_after(tmp_path: Path) -> None:
    manifest_root = tmp_path / "ml_dataset_B2_train_2025-02-02_to_2025-06-02"
    manifest_root.mkdir()
    (manifest_root / "manifest.json").write_text(
        """
{
  "dataset_role": "ML_TRAINING_SOURCE",
  "source_type": "B2_REPLAY_GROUNDED_LABEL_STORE",
  "dataset_name": "ml_dataset_B2_train_2025-02-02_to_2025-06-02",
  "train_start": "2025-02-02",
  "train_end": "2025-06-02",
  "validation_start": "2025-06-03",
  "validation_end": "2025-07-02",
  "allowed_backtest_start_after": "2025-07-03",
  "forbidden_eval_overlap": true
}
""".strip(),
        encoding="utf-8",
    )

    report = build_training_source_contract_report(
        manifest_root_or_path=manifest_root,
        backtest_start="2025-07-02",
        backtest_end="2025-08-01",
    )

    assert report.status == TRAIN_EVAL_OVERLAP_BLOCKED
    assert ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED in report.blocker_reasons
