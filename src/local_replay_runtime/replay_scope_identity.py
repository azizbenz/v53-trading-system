"""Typed aggregate replay scope identity for governed multi-scope sessions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from interface_contracts import EngineId

from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.replay_session_config import ReplayInputKind


class ReplayScopeIdentity(BaseModel):
    """Typed identity for a multi-engine / multi-pair replay scope."""

    dataset_id: str = Field(..., min_length=1)
    input_kind: ReplayInputKind
    performance_mode: str = Field(..., min_length=1)
    engine_scope: tuple[EngineId, ...] = Field(..., min_length=1)
    pair_scope: tuple[str, ...] = Field(..., min_length=1)
    chunk_count: int = Field(..., ge=1)
    selected_chunk_indices: tuple[int, ...] = Field(..., min_length=1)
    requested_window_start_ms: int | None = Field(default=None, ge=0)
    requested_window_end_ms: int | None = Field(default=None, ge=0)
    effective_start_timestamp_ms: int = Field(..., ge=0)
    effective_end_timestamp_ms: int = Field(..., ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("dataset_id", "performance_mode")
    @classmethod
    def _normalize_non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("pair_scope")
    @classmethod
    def _normalize_pair_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(pair.strip().upper() for pair in value)
        if any(not pair for pair in normalized):
            raise ValueError("pair_scope must not contain blank pairs")
        if len(normalized) != len(set(normalized)):
            raise ValueError("pair_scope must stay unique")
        return normalized

    @field_validator("selected_chunk_indices")
    @classmethod
    def _normalize_selected_chunk_indices(
        cls,
        value: tuple[int, ...],
    ) -> tuple[int, ...]:
        if len(value) != len(set(value)):
            raise ValueError("selected_chunk_indices must stay unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def validate_scope(self) -> "ReplayScopeIdentity":
        if len(self.engine_scope) != len(set(self.engine_scope)):
            raise ValueError("engine_scope must stay unique")
        if any(index < 1 or index > self.chunk_count for index in self.selected_chunk_indices):
            raise ValueError("selected_chunk_indices must stay within chunk_count")
        if self.requested_window_start_ms is not None and self.requested_window_end_ms is not None:
            if self.requested_window_end_ms < self.requested_window_start_ms:
                raise ValueError(
                    "requested_window_end_ms must stay >= requested_window_start_ms"
                )
        if self.effective_end_timestamp_ms < self.effective_start_timestamp_ms:
            raise ValueError(
                "effective_end_timestamp_ms must stay >= effective_start_timestamp_ms"
            )
        return self

    @property
    def canonical_key(self) -> str:
        engine_scope = ",".join(engine.value for engine in self.engine_scope)
        pair_scope = ",".join(self.pair_scope)
        selected_chunks = ",".join(str(index) for index in self.selected_chunk_indices)
        requested_window = (
            f"{self.requested_window_start_ms if self.requested_window_start_ms is not None else 'none'}-"
            f"{self.requested_window_end_ms if self.requested_window_end_ms is not None else 'none'}"
        )
        effective_window = (
            f"{self.effective_start_timestamp_ms}-{self.effective_end_timestamp_ms}"
        )
        return ":".join(
            (
                self.dataset_id,
                self.input_kind,
                self.performance_mode,
                engine_scope,
                pair_scope,
                str(self.chunk_count),
                selected_chunks,
                requested_window,
                effective_window,
            )
        )


def build_replay_scope_identity(
    *,
    datasets: tuple[HistoricalReplayDataset, ...],
    input_kind: ReplayInputKind,
    performance_mode: str,
    chunk_count: int,
    selected_chunk_indices: tuple[int, ...],
    requested_window_start_ms: int | None,
    requested_window_end_ms: int | None,
) -> ReplayScopeIdentity:
    """Build a typed aggregate replay identity from processed chunk datasets."""

    if not datasets:
        raise ValueError("ReplayScopeIdentity requires at least one processed dataset")
    dataset_ids = sorted({dataset.dataset_id for dataset in datasets})
    if len(dataset_ids) != 1:
        raise ValueError("ReplayScopeIdentity requires a single governed dataset_id")

    return ReplayScopeIdentity(
        dataset_id=dataset_ids[0],
        input_kind=input_kind,
        performance_mode=performance_mode,
        engine_scope=tuple(
            EngineId(engine_id)
            for engine_id in sorted(
                {
                    engine_id
                    for dataset in datasets
                    for engine_id in dataset.engine_scope
                }
            )
        ),
        pair_scope=tuple(
            sorted(
                {
                    pair
                    for dataset in datasets
                    for pair in dataset.pair_scope
                }
            )
        ),
        chunk_count=chunk_count,
        selected_chunk_indices=selected_chunk_indices,
        requested_window_start_ms=requested_window_start_ms,
        requested_window_end_ms=requested_window_end_ms,
        effective_start_timestamp_ms=min(dataset.start_timestamp_ms for dataset in datasets),
        effective_end_timestamp_ms=max(dataset.end_timestamp_ms for dataset in datasets),
    )


__all__ = ["ReplayScopeIdentity", "build_replay_scope_identity"]
