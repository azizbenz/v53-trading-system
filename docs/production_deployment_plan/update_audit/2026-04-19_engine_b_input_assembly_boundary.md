# Objective

Verify whether the new Engine B upstream cost-threshold resolver has a truthful broader `src/` adoption site, or whether the codebase is currently at an input-assembly boundary.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine B now has an allowed upstream resolver in `src/scoring_backbone/engine_b_cost_thresholds.py`, but adoption depends on a real broader caller that assembles Engine B inputs outside the `engine_b` package.

# Placement

This audit records a boundary finding only. No runtime or runner code was changed.

# Files Changed

- `docs/production_deployment_plan/update_audit/2026-04-19_engine_b_input_assembly_boundary.md`

# Claims Implemented

1. A repo-wide check confirmed that `EngineBInput`, `EngineBRuntimeInput`, `run_engine_b(...)`, and `EngineBRuntime(...)` are still referenced only inside `src/engines/engine_b/*`.
2. The new upstream resolver surface is currently exported only from `src/scoring_backbone/*` and has no broader `src/` adoption site yet.
3. No synthetic caller was created.

# Tests and Proof

- `rtk grep "EngineBInput\\(|EngineBRuntimeInput\\(|run_engine_b\\(|EngineBRuntime\\(" src`
  - matches stayed inside `src/engines/engine_b/*`
- `rtk grep "build_engine_b_cost_threshold_updates|resolve_engine_b_cost_thresholds|EngineBCostThresholdResolverConfig" src`
  - matches stayed inside `src/scoring_backbone/*`

# Deferred / Not Done

- No broader `src/` caller adopts `build_engine_b_cost_threshold_updates(...)`.
- No new Engine B orchestration surface was created.

# Risks / Open Questions

- Signed threshold governance for Engine B cost is prepared but not yet operationally adopted by a broader real caller.
- Forcing adoption now would require inventing a new input-assembly surface, which would be a new governed architecture step rather than an adoption patch.

# Completion Status

`PARTIAL`

The boundary is now explicit. The next adoption step should happen only when a real broader caller exists, or when a new orchestration surface is intentionally requested.

# Next Safe Step

Wait for a real broader Engine B input-assembly owner to appear, or explicitly request a new governed orchestration surface if Engine B adoption must continue before that.
