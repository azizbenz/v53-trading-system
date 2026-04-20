# Objective

Verify whether the new Engine B invalidation signed-threshold resolver has a truthful broader `src/` adoption site, or whether the codebase remains at an input-assembly boundary.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

# Current Code Seam

The new resolver is exported from `src/scoring_backbone/*`, but adoption depends on a broader caller that assembles Engine B inputs outside `src/engines/engine_b/*`.

# Placement

This audit records a boundary finding only. No runtime behavior changed.

# Files Changed

- `docs/production_deployment_plan/update_audit/2026-04-19_engine_b_invalidation_input_assembly_boundary.md`

# Claims Implemented

1. A repo-wide check confirmed that `EngineBInput`, `EngineBRuntimeInput`, `run_engine_b(...)`, and `EngineBRuntime(...)` are still referenced only inside `src/engines/engine_b/*`.
2. The new invalidation-threshold resolver surface is currently referenced only inside `src/scoring_backbone/*`.
3. No synthetic caller was created.

# Tests and Proof

- `rtk grep "build_engine_b_invalidation_threshold_updates|resolve_engine_b_invalidation_thresholds|EngineBInvalidationThresholdResolverConfig" src`
  - matches stayed inside `src/scoring_backbone/*`
- `rtk grep "EngineBInput\\(|EngineBRuntimeInput\\(|run_engine_b\\(|EngineBRuntime\\(" src`
  - matches stayed inside `src/engines/engine_b/*`

# Deferred / Not Done

- No broader `src/` caller adopts the invalidation-threshold resolver.
- No new Engine B orchestration surface was created.

# Risks / Open Questions

- Invalidation-threshold governance is now prepared upstream but still not operationally adopted by a real broader caller.

# Completion Status

`PARTIAL`

The boundary is explicit. Future adoption should happen only when a real broader caller exists, or when a new orchestration surface is intentionally requested.

# Next Safe Step

Stop creating more local Engine B resolver layers and assess Step 6 as a whole: either wait for a real broader Engine B input-assembly owner, or explicitly request a new governed orchestration surface if adoption must continue now.
