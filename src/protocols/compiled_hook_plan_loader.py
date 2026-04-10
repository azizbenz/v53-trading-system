"""Bounded selection/loading semantics for compiled hook plans."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import json

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ArtifactActionKind, HookId

from .compiled_artifact_registry_store import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistryStore,
)


class CompiledHookPlanLoadStatus(StrEnum):
    NO_SNAPSHOT = "no_snapshot"
    NO_BINDING = "no_binding"
    BINDING_ONLY = "binding_only"
    LOAD_ERROR = "load_error"
    LOADED = "loaded"


class CompiledHookPlanDocument(BaseModel, frozen=True):
    """Typed compiled plan document loaded from a published compiled-plan ref."""

    snapshot_id: str = Field(..., min_length=1)
    hook_id: HookId
    artifact_ids: tuple[str, ...] = ()
    action_kinds: tuple[ArtifactActionKind, ...] = ()
    generated_at_ms: int = Field(..., ge=0)
    plan_format: str = Field(default="compiled_hook_plan.v1", min_length=1)
    compiler_version: str = Field(default="v1", min_length=1)
    compiled_action_count: int = Field(default=0, ge=0)
    opaque_plan_payload: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_document(self) -> "CompiledHookPlanDocument":
        if len(set(self.artifact_ids)) != len(self.artifact_ids):
            raise ValueError("CompiledHookPlanDocument artifact_ids must be unique")
        if len(set(self.action_kinds)) != len(self.action_kinds):
            raise ValueError("CompiledHookPlanDocument action_kinds must be unique")
        return self


class CompiledHookPlanSelection(BaseModel, frozen=True):
    """Selection result for one canonical hook against the current registry snapshot."""

    hook_id: HookId
    snapshot_id: str = ""
    status: CompiledHookPlanLoadStatus
    binding: CompiledArtifactHookBinding | None = None
    compiled_plan_path: Path | None = None
    plan: CompiledHookPlanDocument | None = None
    error_type: str = ""
    error_detail: str = ""


def load_compiled_hook_plan(path: Path) -> CompiledHookPlanDocument:
    """Load a compiled hook plan document from JSON."""

    data = json.loads(path.read_text(encoding="utf-8"))
    return CompiledHookPlanDocument.model_validate(data)


def select_current_compiled_hook_plan(
    store: CompiledArtifactRegistryStore,
    hook_id: HookId,
) -> CompiledHookPlanSelection:
    """Select and, when present, load the compiled plan for one canonical hook."""

    snapshot = store.load_current_snapshot()
    if snapshot is None:
        return CompiledHookPlanSelection(
            hook_id=hook_id,
            status=CompiledHookPlanLoadStatus.NO_SNAPSHOT,
        )

    binding = next(
        (item for item in snapshot.hook_bindings if item.hook_id == hook_id),
        None,
    )
    if binding is None:
        return CompiledHookPlanSelection(
            hook_id=hook_id,
            snapshot_id=snapshot.snapshot_id,
            status=CompiledHookPlanLoadStatus.NO_BINDING,
        )

    if not binding.compiled_plan_ref:
        return CompiledHookPlanSelection(
            hook_id=hook_id,
            snapshot_id=snapshot.snapshot_id,
            status=CompiledHookPlanLoadStatus.BINDING_ONLY,
            binding=binding,
        )

    compiled_plan_path = _resolve_compiled_plan_path(store.state_dir, binding.compiled_plan_ref)
    try:
        plan = load_compiled_hook_plan(compiled_plan_path)
        _validate_plan_matches_binding(
            snapshot_id=snapshot.snapshot_id,
            hook_id=hook_id,
            binding=binding,
            plan=plan,
        )
    except Exception as exc:
        return CompiledHookPlanSelection(
            hook_id=hook_id,
            snapshot_id=snapshot.snapshot_id,
            status=CompiledHookPlanLoadStatus.LOAD_ERROR,
            binding=binding,
            compiled_plan_path=compiled_plan_path,
            error_type=type(exc).__name__,
            error_detail=str(exc),
        )
    return CompiledHookPlanSelection(
        hook_id=hook_id,
        snapshot_id=snapshot.snapshot_id,
        status=CompiledHookPlanLoadStatus.LOADED,
        binding=binding,
        compiled_plan_path=compiled_plan_path,
        plan=plan,
    )


def _resolve_compiled_plan_path(state_dir: Path, compiled_plan_ref: str) -> Path:
    plan_path = Path(compiled_plan_ref)
    return plan_path if plan_path.is_absolute() else (state_dir / plan_path).resolve()


def _validate_plan_matches_binding(
    *,
    snapshot_id: str,
    hook_id: HookId,
    binding: CompiledArtifactHookBinding,
    plan: CompiledHookPlanDocument,
) -> None:
    if plan.snapshot_id != snapshot_id:
        raise ValueError("CompiledHookPlanDocument snapshot_id must match current snapshot")
    if plan.hook_id != hook_id:
        raise ValueError("CompiledHookPlanDocument hook_id must match selected binding hook_id")
    if plan.artifact_ids != binding.artifact_ids:
        raise ValueError("CompiledHookPlanDocument artifact_ids must match binding artifact_ids")
    if plan.action_kinds != binding.action_kinds:
        raise ValueError("CompiledHookPlanDocument action_kinds must match binding action_kinds")


__all__ = [
    "CompiledHookPlanLoadStatus",
    "CompiledHookPlanDocument",
    "CompiledHookPlanSelection",
    "load_compiled_hook_plan",
    "select_current_compiled_hook_plan",
]
