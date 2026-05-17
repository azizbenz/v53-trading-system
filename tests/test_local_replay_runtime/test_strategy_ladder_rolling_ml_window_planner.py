from datetime import date, timedelta
from pathlib import Path

from local_replay_runtime.strategy_ladder_rolling_ml_window_planner import (
    CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY,
    CHUNK_READY,
    ROLLING_ML_WINDOW_PLAN_JSON_FILENAME,
    ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME,
    ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY,
    ROLLING_PLAN_READY,
    StrategyLadderRollingMlWindowPlannerRequest,
    build_strategy_ladder_rolling_ml_window_plan,
    write_strategy_ladder_rolling_ml_window_plan,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("strategy_ladder_rolling_ml_planner_tests", label)


def test_rolling_planner_30_day_backtest_produces_one_chunk() -> None:
    plan = build_strategy_ladder_rolling_ml_window_plan(
        StrategyLadderRollingMlWindowPlannerRequest(
            backtest_start_date="2025-05-01",
            backtest_days=30,
        )
    )

    assert plan.status == ROLLING_PLAN_READY
    assert plan.required_artifact_count == 1
    assert len(plan.chunks) == 1
    chunk = plan.chunks[0]
    assert chunk.status == CHUNK_READY
    assert chunk.backtest_chunk_start == "2025-05-01"
    assert chunk.backtest_chunk_end == "2025-05-30"
    assert chunk.validation_end == "2025-04-30"
    assert chunk.artifact_stale_after == "2025-05-30"
    assert chunk.max_valid_backtest_end == "2025-05-30"


def test_rolling_planner_130_day_backtest_produces_five_chunks() -> None:
    plan = build_strategy_ladder_rolling_ml_window_plan(
        StrategyLadderRollingMlWindowPlannerRequest(
            backtest_start_date="2025-05-01",
            backtest_days=130,
        )
    )

    assert plan.status == "ROLLING_PLAN_REQUIRES_5_ARTIFACTS"
    assert plan.required_artifact_count == 5
    assert len(plan.chunks) == 5
    assert plan.chunks[-1].backtest_chunk_end == "2025-09-07"
    assert plan.chunks[-1].status == CHUNK_READY


def test_rolling_planner_chunks_are_contiguous_and_respect_freshness() -> None:
    plan = build_strategy_ladder_rolling_ml_window_plan(
        StrategyLadderRollingMlWindowPlannerRequest(
            backtest_start_date="2025-05-01",
            backtest_days=130,
        )
    )

    previous_end = None
    for chunk in plan.chunks:
        chunk_start = date.fromisoformat(chunk.backtest_chunk_start)
        chunk_end = date.fromisoformat(chunk.backtest_chunk_end)
        train_end = date.fromisoformat(chunk.train_end)
        validation_start = date.fromisoformat(chunk.validation_start)
        validation_end = date.fromisoformat(chunk.validation_end)
        max_valid_backtest_end = date.fromisoformat(chunk.max_valid_backtest_end)
        if previous_end is not None:
            assert chunk_start == previous_end + timedelta(days=1)
        assert chunk_end <= max_valid_backtest_end
        assert train_end < validation_start
        assert validation_end < chunk_start
        previous_end = chunk_end


def test_rolling_planner_blocks_insufficient_history() -> None:
    plan = build_strategy_ladder_rolling_ml_window_plan(
        StrategyLadderRollingMlWindowPlannerRequest(
            backtest_start_date="2025-05-01",
            backtest_days=30,
            available_history_start_date="2025-01-01",
        )
    )

    assert plan.status == ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY
    assert plan.blocker_codes == (
        CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY,
        ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY,
    )
    assert plan.chunks[0].status == CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY


def test_rolling_planner_writes_json_and_markdown() -> None:
    scratch = _scratch_dir("write_plan")
    plan = write_strategy_ladder_rolling_ml_window_plan(
        scratch,
        StrategyLadderRollingMlWindowPlannerRequest(
            backtest_start_date="2025-05-01",
            backtest_days=30,
        ),
    )

    assert plan.json_ref == str((scratch / ROLLING_ML_WINDOW_PLAN_JSON_FILENAME).resolve())
    assert plan.markdown_ref == str(
        (scratch / ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME).resolve()
    )
    assert Path(plan.json_ref).is_file()
    assert Path(plan.markdown_ref).is_file()
