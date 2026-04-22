from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import ArtifactActionKind, HookId, RUNTIME_OPEN_HOOK_IDS
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    build_execution_no_trade_bridge_projection,
    build_execution_runtime_projection_bridge_projection,
    build_runtime_hook_bridge_projections,
)
from tests.support_paths import repo_build_path


def _publish_execution_no_trade_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/execution_no_trade.json",
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
                    artifact_ids=("artifact-1",),
                    action_kinds=(ArtifactActionKind.NO_TRADE,),
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _write_execution_runtime_projection(
    path: Path,
    *,
    projection_status: str = "ready",
    ready_count: int = 3,
    partial_count: int = 0,
    blocked_count: int = 0,
) -> None:
    atomic_write_json(
        path,
        {
            "correlation_id": "corr-exec-runtime",
            "export_dir": "build/local_lab",
            "run_id": "local-lab-run-1",
            "projection_status": projection_status,
            "projection_ready": projection_status == "ready",
            "execution_review_status": "ready",
            "execution_review_ready": True,
            "consumer_count": 3,
            "ready_consumer_count": ready_count,
            "partial_consumer_count": partial_count,
            "blocked_consumer_count": blocked_count,
            "blocking_reasons": ["rate limit evidence missing"]
            if projection_status == "blocked"
            else [],
            "caution_flags": ["THR-X05_ACCEPTED_EVENTS_ONLY"]
            if projection_status != "blocked"
            else [],
            "consumers": [
                {
                    "consumer_id": "rate_limiter",
                    "consumer_interface": "quota_ratio_ceiling",
                    "threshold_id": "THR-X03",
                    "target_runtime_mode": "shadow",
                    "projection_status": "ready" if projection_status == "ready" else projection_status,
                    "projection_ready": projection_status == "ready",
                    "threshold_review_status": "ready" if projection_status == "ready" else projection_status,
                    "threshold_fit_ready": projection_status == "ready",
                    "method": "quota_ratio_ceiling_v1",
                    "unit": "quota_ratio",
                    "projection_value": 0.8 if projection_status == "ready" else None,
                    "projection_value_semantics": "max_observed_quota_ratio_before_throttle",
                    "hard_cap_human": 0.8,
                    "hard_cap_binding": False,
                    "blocking_reasons": ["rate limit evidence missing"]
                    if projection_status == "blocked"
                    else [],
                    "caution_flags": [],
                },
                {
                    "consumer_id": "spread_guard",
                    "consumer_interface": "spread_bps_ceiling",
                    "threshold_id": "THR-X04",
                    "target_runtime_mode": "shadow",
                    "projection_status": "ready" if projection_status == "ready" else projection_status,
                    "projection_ready": projection_status == "ready",
                    "threshold_review_status": "ready" if projection_status == "ready" else projection_status,
                    "threshold_fit_ready": projection_status == "ready",
                    "method": "lognormal_mu_plus_2sigma_capped",
                    "unit": "bps",
                    "projection_value": 24.0 if projection_status == "ready" else None,
                    "projection_value_semantics": "max_observed_spread_bps_before_no_trade",
                    "hard_cap_human": 50.0,
                    "hard_cap_binding": False,
                    "blocking_reasons": ["spread evidence missing"]
                    if projection_status == "blocked"
                    else [],
                    "caution_flags": [],
                },
                {
                    "consumer_id": "slippage_model",
                    "consumer_interface": "sqrt_size_slippage_predictor",
                    "threshold_id": "THR-X05",
                    "target_runtime_mode": "shadow",
                    "projection_status": "ready" if projection_status == "ready" else projection_status,
                    "projection_ready": projection_status == "ready",
                    "threshold_review_status": "ready" if projection_status == "ready" else projection_status,
                    "threshold_fit_ready": projection_status == "ready",
                    "method": "size_slippage_huber_v1",
                    "unit": "bps",
                    "projection_value": 18.0 if projection_status == "ready" else None,
                    "projection_value_semantics": "reference_slippage_bps_at_q95_size",
                    "reference_size": 4.0 if projection_status == "ready" else None,
                    "size_proxy": "final_size" if projection_status == "ready" else "",
                    "intercept_bps": 2.0 if projection_status == "ready" else None,
                    "sqrt_size_coefficient": 8.0 if projection_status == "ready" else None,
                    "r_squared": 0.55 if projection_status == "ready" else None,
                    "mean_absolute_error_bps": 1.5 if projection_status == "ready" else None,
                    "blocking_reasons": [],
                    "caution_flags": ["THR-X05_ACCEPTED_EVENTS_ONLY"]
                    if projection_status == "ready"
                    else [],
                },
            ],
        },
    )


def test_build_execution_no_trade_bridge_projection_returns_planned_when_unconfigured():
    projection = build_execution_no_trade_bridge_projection()

    assert projection.status == "planned"
    assert projection.configured is False
    assert projection.selection_status == "no_snapshot"


def test_build_execution_no_trade_bridge_projection_returns_healthy_when_loaded():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_dashboard_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_EXECUTION_BLOCK"],
                    "detail": "artifact veto at execution boundary",
                },
            },
        )

        projection = build_execution_no_trade_bridge_projection(
            compiled_registry_state_dir=state_dir
        )

        assert projection.status == "healthy"
        assert projection.configured is True
        assert projection.selection_status == "loaded"
        assert projection.loaded is True
        assert projection.artifact_count == 1
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_no_trade_bridge_projection_returns_warning_on_invalid_plan():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_dashboard_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )

        projection = build_execution_no_trade_bridge_projection(
            compiled_registry_state_dir=state_dir
        )

        assert projection.status == "warning"
        assert projection.selection_status == "load_error"
        assert projection.failure_mode == "fail_open_baseline_skip_artifact"
        assert projection.error_stage == "plan_selection"
        assert projection.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_runtime_hook_bridge_projections_returns_all_runtime_open_hooks_when_unconfigured():
    projections = build_runtime_hook_bridge_projections()

    assert tuple(projection.hook_id for projection in projections) == RUNTIME_OPEN_HOOK_IDS
    assert all(projection.status == "planned" for projection in projections)
    assert all(projection.selection_status == "not_configured" for projection in projections)


def test_build_runtime_hook_bridge_projections_projects_loaded_engine_b_and_execution_hooks():
    state_dir = repo_build_path("build/test_protocols_execution_runtime_dashboard_runtime_hooks")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        store.publish(
            CompiledArtifactRegistrySnapshot(
                snapshot_id="snap-1",
                generated_at_ms=1000,
                artifact_ids=("artifact-1", "artifact-2"),
                hook_bindings=(
                    CompiledArtifactHookBinding(
                        hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
                        artifact_ids=("artifact-1",),
                        action_kinds=(ArtifactActionKind.NO_TRADE,),
                        compiled_plan_ref="compiled/snap-1/execution_no_trade.json",
                    ),
                    CompiledArtifactHookBinding(
                        hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                        artifact_ids=("artifact-2",),
                        action_kinds=(ArtifactActionKind.SOFT_REDUCE,),
                        compiled_plan_ref="compiled/snap-1/engine_b_sweep.json",
                    ),
                ),
            )
        )
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_b_sweep.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_B_SWEEP_VALIDATION.value,
                "artifact_ids": ["artifact-2"],
                "action_kinds": [ArtifactActionKind.SOFT_REDUCE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"raw_score_add": -0.1},
            },
        )

        projections = build_runtime_hook_bridge_projections(
            compiled_registry_state_dir=state_dir
        )

        execution = next(
            projection
            for projection in projections
            if projection.hook_id == HookId.EXECUTION_NO_TRADE_FILTER
        )
        engine_b = next(
            projection
            for projection in projections
            if projection.hook_id == HookId.ENGINE_B_SWEEP_VALIDATION
        )

        assert execution.status == "healthy"
        assert execution.loaded is True
        assert execution.artifact_count == 1
        assert engine_b.status == "healthy"
        assert engine_b.loaded is True
        assert engine_b.artifact_count == 1
        assert engine_b.action_kinds == ("soft_reduce",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_runtime_projection_bridge_projection_returns_planned_when_unconfigured():
    projection = build_execution_runtime_projection_bridge_projection()

    assert projection.status == "planned"
    assert projection.configured is False
    assert projection.projection_loaded is False


def test_build_execution_runtime_projection_bridge_projection_returns_healthy_when_models_load():
    path = repo_build_path("build/test_protocols_execution_runtime_projection_bridge_ready.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_execution_runtime_projection(path)

        projection = build_execution_runtime_projection_bridge_projection(
            execution_runtime_projection_path=path
        )

        assert projection.status == "healthy"
        assert projection.configured is True
        assert projection.projection_found is True
        assert projection.projection_loaded is True
        assert projection.ready_consumer_count == 3
        assert projection.rate_limit_model_loaded is True
        assert projection.spread_guard_model_loaded is True
        assert projection.slippage_model_loaded is True
    finally:
        path.unlink(missing_ok=True)


def test_build_execution_runtime_projection_bridge_projection_returns_critical_when_blocked():
    path = repo_build_path("build/test_protocols_execution_runtime_projection_bridge_blocked.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_execution_runtime_projection(
            path,
            projection_status="blocked",
            ready_count=0,
            blocked_count=3,
        )

        projection = build_execution_runtime_projection_bridge_projection(
            execution_runtime_projection_path=path
        )

        assert projection.status == "critical"
        assert projection.blocked_consumer_count == 3
        assert "blocked runtime consumers" in projection.detail
    finally:
        path.unlink(missing_ok=True)
