"""Atomic snapshot store for governed compiled artifact registry publication."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    ArtifactActionKind,
    ArtifactConflictPolicy,
    CANONICAL_ARTIFACT_CONFLICT_POLICY,
    CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY,
    CompiledArtifactRegistryPolicy,
    HookId,
)
from interface_contracts.atomic_io import atomic_write_json


class CompiledArtifactHookBinding(BaseModel, frozen=True):
    """Published compiled-binding metadata for a single canonical hook."""

    hook_id: HookId
    artifact_ids: tuple[str, ...] = ()
    action_kinds: tuple[ArtifactActionKind, ...] = ()
    compiled_plan_ref: str = ""

    @model_validator(mode="after")
    def validate_binding(self) -> "CompiledArtifactHookBinding":
        if len(set(self.artifact_ids)) != len(self.artifact_ids):
            raise ValueError("CompiledArtifactHookBinding artifact_ids must be unique")
        if len(set(self.action_kinds)) != len(self.action_kinds):
            raise ValueError("CompiledArtifactHookBinding action_kinds must be unique")
        return self


class CompiledArtifactRegistrySnapshot(BaseModel, frozen=True):
    """Immutable snapshot published by the future compiled artifact registry."""

    snapshot_id: str = Field(..., min_length=1)
    generated_at_ms: int = Field(..., ge=0)
    artifact_ids: tuple[str, ...] = ()
    hook_bindings: tuple[CompiledArtifactHookBinding, ...] = ()
    conflict_policy: ArtifactConflictPolicy = Field(
        default_factory=lambda: CANONICAL_ARTIFACT_CONFLICT_POLICY
    )
    registry_policy: CompiledArtifactRegistryPolicy = Field(
        default_factory=lambda: CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY
    )

    @model_validator(mode="after")
    def validate_snapshot(self) -> "CompiledArtifactRegistrySnapshot":
        if len(set(self.artifact_ids)) != len(self.artifact_ids):
            raise ValueError("CompiledArtifactRegistrySnapshot artifact_ids must be unique")
        hook_ids = tuple(binding.hook_id for binding in self.hook_bindings)
        if len(set(hook_ids)) != len(hook_ids):
            raise ValueError("CompiledArtifactRegistrySnapshot hook_bindings must be unique per hook")
        declared_artifacts = set(self.artifact_ids)
        for binding in self.hook_bindings:
            missing = set(binding.artifact_ids) - declared_artifacts
            if missing:
                raise ValueError(
                    "CompiledArtifactRegistrySnapshot hook binding references unknown artifact_ids"
                )
        return self


class CompiledArtifactRegistryPointer(BaseModel):
    """Atomic pointer to the published compiled-registry snapshot set."""

    current_snapshot_id: str = ""
    previous_snapshot_id: str = ""
    last_known_good_snapshot_id: str = ""
    published_at_ms: int | None = Field(default=None, ge=0)
    last_good_marked_at_ms: int | None = Field(default=None, ge=0)
    last_rollback_at_ms: int | None = Field(default=None, ge=0)


class CompiledArtifactPublishResult(BaseModel, frozen=True):
    """Stable result of a compiled-registry publication or rollback operation."""

    current_snapshot_id: str = Field(..., min_length=1)
    previous_snapshot_id: str = ""
    last_known_good_snapshot_id: str = ""
    pointer_path: Path
    snapshot_path: Path
    rolled_back: bool = False


class CompiledArtifactRegistryStore:
    """Atomic snapshot/pointer store aligned with the canonical registry policy."""

    def __init__(
        self,
        state_dir: Path,
        *,
        pointer_filename: str = "compiled_artifact_registry_pointer.json",
        snapshot_dirname: str = "compiled_artifact_registry_snapshots",
    ) -> None:
        self._state_dir = state_dir
        self._pointer_path = state_dir / pointer_filename
        self._snapshot_dir = state_dir / snapshot_dirname
        self._pointer = self._load_pointer()

    @property
    def pointer_path(self) -> Path:
        return self._pointer_path

    @property
    def state_dir(self) -> Path:
        return self._state_dir

    @property
    def snapshot_dir(self) -> Path:
        return self._snapshot_dir

    def publish(
        self,
        snapshot: CompiledArtifactRegistrySnapshot,
    ) -> CompiledArtifactPublishResult:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self._snapshot_path(snapshot.snapshot_id)
        atomic_write_json(snapshot_path, snapshot.model_dump(mode="json"))

        previous_snapshot_id = self._pointer.current_snapshot_id
        self._pointer.previous_snapshot_id = previous_snapshot_id
        self._pointer.current_snapshot_id = snapshot.snapshot_id
        self._pointer.published_at_ms = snapshot.generated_at_ms
        self._persist_pointer()
        return CompiledArtifactPublishResult(
            current_snapshot_id=snapshot.snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            last_known_good_snapshot_id=self._pointer.last_known_good_snapshot_id,
            pointer_path=self._pointer_path,
            snapshot_path=snapshot_path,
        )

    def mark_last_known_good(
        self,
        snapshot_id: str,
        *,
        marked_at_ms: int,
    ) -> None:
        self._load_snapshot(snapshot_id)
        self._pointer.last_known_good_snapshot_id = snapshot_id
        self._pointer.last_good_marked_at_ms = marked_at_ms
        self._persist_pointer()

    def rollback_to_last_known_good(
        self,
        *,
        rollback_at_ms: int,
    ) -> CompiledArtifactPublishResult:
        snapshot_id = self._pointer.last_known_good_snapshot_id
        if not snapshot_id:
            raise ValueError("CompiledArtifactRegistryStore requires a last-known-good snapshot before rollback")
        snapshot = self._load_snapshot(snapshot_id)
        previous_snapshot_id = self._pointer.current_snapshot_id
        self._pointer.previous_snapshot_id = previous_snapshot_id
        self._pointer.current_snapshot_id = snapshot.snapshot_id
        self._pointer.last_rollback_at_ms = rollback_at_ms
        self._pointer.published_at_ms = rollback_at_ms
        self._persist_pointer()
        return CompiledArtifactPublishResult(
            current_snapshot_id=snapshot.snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            last_known_good_snapshot_id=self._pointer.last_known_good_snapshot_id,
            pointer_path=self._pointer_path,
            snapshot_path=self._snapshot_path(snapshot.snapshot_id),
            rolled_back=True,
        )

    def load_current_snapshot(self) -> CompiledArtifactRegistrySnapshot | None:
        snapshot_id = self._pointer.current_snapshot_id
        if not snapshot_id:
            return None
        return self._load_snapshot(snapshot_id)

    def load_pointer(self) -> CompiledArtifactRegistryPointer:
        return CompiledArtifactRegistryPointer.model_validate(
            self._pointer.model_dump(mode="json")
        )

    def _load_pointer(self) -> CompiledArtifactRegistryPointer:
        if self._pointer_path.exists():
            try:
                data = json.loads(self._pointer_path.read_text(encoding="utf-8"))
                return CompiledArtifactRegistryPointer.model_validate(data)
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        return CompiledArtifactRegistryPointer()

    def _persist_pointer(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._pointer_path, self._pointer.model_dump(mode="json"))

    def _snapshot_path(self, snapshot_id: str) -> Path:
        return self._snapshot_dir / f"{snapshot_id}.json"

    def _load_snapshot(self, snapshot_id: str) -> CompiledArtifactRegistrySnapshot:
        snapshot_path = self._snapshot_path(snapshot_id)
        if not snapshot_path.exists():
            raise FileNotFoundError(
                f"Compiled artifact registry snapshot '{snapshot_id}' was not found"
            )
        return CompiledArtifactRegistrySnapshot.model_validate_json(
            snapshot_path.read_text(encoding="utf-8")
        )


__all__ = [
    "CompiledArtifactHookBinding",
    "CompiledArtifactRegistrySnapshot",
    "CompiledArtifactRegistryPointer",
    "CompiledArtifactPublishResult",
    "CompiledArtifactRegistryStore",
]
