from __future__ import annotations

import pytest

from calibration_methods import (
    PurgedWalkForwardConfig,
    PurgedWalkForwardError,
    build_purged_walk_forward_plan,
)


def test_build_purged_walk_forward_plan_creates_non_overlapping_folds():
    plan = build_purged_walk_forward_plan(
        120,
        config=PurgedWalkForwardConfig(
            fold_count=5,
            validation_window_size=10,
            embargo_size=4,
            label_horizon_size=6,
            min_train_size=20,
        ),
    )

    assert plan.fold_count == 5
    assert len(plan.folds) == 5

    for fold in plan.folds:
        train = set(fold.train_indices)
        embargo = set(fold.embargo_indices)
        validation = set(fold.validation_indices)
        assert train.isdisjoint(embargo)
        assert train.isdisjoint(validation)
        assert embargo.isdisjoint(validation)
        assert fold.validation_start == fold.validation_indices[0]
        assert fold.validation_end == fold.validation_indices[-1]
        assert fold.train_count >= 20


def test_walk_forward_plan_exposes_label_purging_when_horizon_exceeds_embargo():
    plan = build_purged_walk_forward_plan(
        80,
        config=PurgedWalkForwardConfig(
            fold_count=3,
            validation_window_size=10,
            embargo_size=2,
            label_horizon_size=5,
            min_train_size=15,
        ),
    )

    assert any(fold.purged_train_count > 0 for fold in plan.folds)


def test_walk_forward_rejects_insufficient_training_history():
    with pytest.raises(PurgedWalkForwardError, match="too small"):
        build_purged_walk_forward_plan(
            25,
            config=PurgedWalkForwardConfig(
                fold_count=2,
                validation_window_size=10,
                embargo_size=4,
                min_train_size=10,
            ),
        )
