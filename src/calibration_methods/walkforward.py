"""Shared Local IA Lab purged walk-forward helpers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PurgedWalkForwardError(ValueError):
    """Raised when walk-forward geometry is invalid."""


class PurgedWalkForwardConfig(BaseModel, frozen=True):
    """Bounded configuration for purged walk-forward folds."""

    fold_count: int = Field(..., ge=1)
    validation_window_size: int = Field(..., ge=1)
    embargo_size: int = Field(default=0, ge=0)
    label_horizon_size: int = Field(default=0, ge=0)
    min_train_size: int = Field(default=1, ge=1)


class PurgedWalkForwardFold(BaseModel, frozen=True):
    """Single purged walk-forward fold over integer-ordered observations."""

    fold_index: int = Field(..., ge=0)
    train_indices: tuple[int, ...]
    embargo_indices: tuple[int, ...]
    validation_indices: tuple[int, ...]
    train_start: int | None = None
    train_end: int | None = None
    embargo_start: int | None = None
    embargo_end: int | None = None
    validation_start: int = Field(..., ge=0)
    validation_end: int = Field(..., ge=0)
    purged_train_count: int = Field(default=0, ge=0)
    train_count: int = Field(..., ge=0)
    embargo_count: int = Field(..., ge=0)
    validation_count: int = Field(..., ge=1)


class PurgedWalkForwardPlan(BaseModel, frozen=True):
    """Audit-ready walk-forward plan before any human approval gate."""

    method_version: str = "purged_walk_forward_v1"
    observation_count: int = Field(..., ge=1)
    fold_count: int = Field(..., ge=1)
    validation_window_size: int = Field(..., ge=1)
    embargo_size: int = Field(..., ge=0)
    label_horizon_size: int = Field(..., ge=0)
    folds: tuple[PurgedWalkForwardFold, ...]


def build_purged_walk_forward_plan(
    observation_count: int,
    *,
    config: PurgedWalkForwardConfig,
) -> PurgedWalkForwardPlan:
    """Build non-overlapping purged walk-forward folds over ordered indices."""

    if observation_count <= 0:
        raise PurgedWalkForwardError("observation_count must be > 0")

    total_validation_width = config.fold_count * config.validation_window_size
    first_validation_start = observation_count - total_validation_width
    if first_validation_start < config.min_train_size + config.embargo_size:
        raise PurgedWalkForwardError(
            "observation_count is too small for the requested walk-forward geometry"
        )

    folds: list[PurgedWalkForwardFold] = []
    for fold_index in range(config.fold_count):
        validation_start = first_validation_start + fold_index * config.validation_window_size
        validation_end = validation_start + config.validation_window_size - 1
        embargo_start = max(0, validation_start - config.embargo_size)
        purge_start = max(0, validation_start - config.label_horizon_size)
        train_end_exclusive = min(embargo_start, purge_start)

        train_indices = tuple(range(0, train_end_exclusive))
        embargo_indices = tuple(range(embargo_start, validation_start))
        validation_indices = tuple(range(validation_start, validation_end + 1))

        if len(train_indices) < config.min_train_size:
            raise PurgedWalkForwardError(
                f"fold {fold_index} does not preserve min_train_size={config.min_train_size}"
            )

        purged_train_count = max(0, embargo_start - train_end_exclusive)
        folds.append(
            PurgedWalkForwardFold(
                fold_index=fold_index,
                train_indices=train_indices,
                embargo_indices=embargo_indices,
                validation_indices=validation_indices,
                train_start=train_indices[0] if train_indices else None,
                train_end=train_indices[-1] if train_indices else None,
                embargo_start=embargo_indices[0] if embargo_indices else None,
                embargo_end=embargo_indices[-1] if embargo_indices else None,
                validation_start=validation_start,
                validation_end=validation_end,
                purged_train_count=purged_train_count,
                train_count=len(train_indices),
                embargo_count=len(embargo_indices),
                validation_count=len(validation_indices),
            )
        )

    return PurgedWalkForwardPlan(
        observation_count=observation_count,
        fold_count=config.fold_count,
        validation_window_size=config.validation_window_size,
        embargo_size=config.embargo_size,
        label_horizon_size=config.label_horizon_size,
        folds=tuple(folds),
    )


__all__ = [
    "PurgedWalkForwardConfig",
    "PurgedWalkForwardError",
    "PurgedWalkForwardFold",
    "PurgedWalkForwardPlan",
    "build_purged_walk_forward_plan",
]
