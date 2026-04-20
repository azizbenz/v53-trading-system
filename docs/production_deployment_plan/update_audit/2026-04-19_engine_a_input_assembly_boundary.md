# Objective

Document whether the new upstream Engine A cost-threshold resolver can be adopted now in a real Engine A input assembly surface, without inventing a synthetic caller.

# Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

The repo now has:

- `src/engines/engine_a/cost_feasibility_a.py` with single-source threshold ownership
- `src/scoring_backbone/engine_a_cost_thresholds.py` with a signed-threshold resolver

But adoption still requires a real caller outside `engine_a` that legitimately assembles `EngineAInput` or `EngineARuntimeInput`.

# Placement

This audit records a truthful boundary. No new orchestration surface is added.

# Files Changed

- `docs/production_deployment_plan/update_audit/2026-04-19_engine_a_input_assembly_boundary.md`

# Claims Implemented

- Verified that no broader real `src/` caller currently constructs `EngineAInput` outside `src/engines/engine_a/`.
- Verified that no broader real `src/` caller currently constructs `EngineARuntimeInput` outside `src/engines/engine_a/`.
- Verified that the newly added `build_engine_a_cost_threshold_updates(...)` resolver has no truthful adoption site yet.
- Kept the boundary honest: no synthetic Engine A orchestrator or caller was created.

# Tests and Proof

Inspection commands executed:

- `rtk grep "EngineAInput\\(|EngineARuntimeInput\\(|run_engine_a\\(|EngineARuntime\\(" src | rg -v "src\\\\engines\\\\engine_a|tests\\\\"`
- `rtk grep "direction_score|continuation_score|structure_quality|zone_proximity|trend_stability|ofi_flow_score|realized_kernel_vol_scale|kyle_lambda_cost_uplift" src | rg -v "src\\\\engines\\\\engine_a|tests\\\\"`
- `rtk grep "build_engine_a_cost_threshold_updates|resolve_engine_a_cost_thresholds|THR-A01|THR-A02" src tests`

Observed result:

- `EngineAInput` appears only in `src/engines/engine_a/` and tests.
- `EngineARuntimeInput` appears only in `src/engines/engine_a/` and tests.
- No broader runtime/orchestration surface in `src/` currently owns Engine A input assembly.

# Deferred / Not Done

- No adoption of `build_engine_a_cost_threshold_updates(...)` in a broader real caller.
- No production input assembly path for Engine A thresholds outside `engine_a`.
- No microstructure provenance caller adoption in this slice.

# Risks / Open Questions

- The signed-threshold resolver exists but remains inactive until a real Engine A input owner exists.
- Creating a new owner now would be new architecture, not adoption, and should only be done explicitly.

# Completion Status

`PARTIAL`

Reason:

The upstream resolver is ready, but there is still no real broader Engine A input assembly surface to adopt it without inventing architecture.

# Next Safe Step

Wait for a real `src/` Engine A input owner to appear and adopt `build_engine_a_cost_threshold_updates(...)` there, or request a new governed Engine A orchestration surface explicitly if architecture expansion is intended.
