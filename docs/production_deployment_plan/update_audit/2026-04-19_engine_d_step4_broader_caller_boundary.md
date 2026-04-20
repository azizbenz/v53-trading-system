## Objective

Resolve the next Step 4 boundary honestly: determine whether a broader real `src/` caller exists for the public Engine D historical-entry runtime seam, or whether the boundary must be explicitly deferred.

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

Step 4 now provides a truthful public Engine D historical-entry seam:

- `assemble_engine_d_coordination_input(...)`
- `assemble_engine_d_runtime_input(...)`
- `EngineDRuntime.evaluate_from_historical_state(...)`

The next planned move was broader adoption outside `src/engines/engine_d/`.

## Placement

No code placement change was made in this boundary pass.

Instead, this pass documents the architectural boundary:

- there is no broader real `src/` caller currently assembling Engine D runtime inputs
- introducing a new orchestration or protocol wrapper solely to consume the seam would be synthetic, not doctrinal

## Files Changed

- `docs/production_deployment_plan/update_audit/2026-04-19_engine_d_step4_broader_caller_boundary.md`

## Claims Implemented

1. The repo was searched for broader `src/` callers of:
   - `EngineDRuntime`
   - `EngineDRuntimeInput`
   - `assemble_engine_d_runtime_input(...)`
   - `EngineDInput` runtime assembly paths
2. No broader real caller was found outside `src/engines/engine_d/`.
3. Existing `protocols` references to Engine D are hook/bridge status surfaces only, not runtime-input assembly surfaces.
4. Creating another wrapper at this point would be synthetic architecture, not real adoption.
5. The correct Step 4 status remains `PARTIAL`.

## Tests and Proof

Search evidence run:

- `rtk grep "EngineDRuntime\\(|run_engine_d\\(|evaluate_from_historical_state\\(|assemble_engine_d_runtime_input\\(|EngineDRuntimeInput\\(" src`
  - only matched `src/engines/engine_d/*`
- `rtk grep "engine_d" src/protocols src/local_replay_runtime src/monitoring src/execution_backbone src/meta_minimal src/portfolio_minimal`
  - showed hook bridges, journal, dashboard, and enum/reporting references, but no broader runtime-input caller
- `rtk read src/protocols/engine_d_reentry_validation_bridge.py`
  - confirmed this bridge is compiled-hook execution only, not a D runtime orchestrator

No new code path was introduced in this boundary pass, so no additional compile/test/guardrail run was required beyond the already-green Step 4 slices immediately preceding it.

## Deferred / Not Done

- No broader real caller outside `src/engines/engine_d/` adopts `EngineDRuntime.evaluate_from_historical_state(...)` yet.
- No new orchestrator or protocols wrapper was introduced.

## Risks / Open Questions

- The repo may gain a broader D orchestration/replay surface later. If it does, that new real caller should adopt the public historical-entry seam instead of rebuilding D runtime inputs manually.
- Until such a caller exists, Step 4 broader adoption must remain explicitly deferred.

## Completion Status

`PARTIAL`

The correct result of this pass is a documented boundary, not a fabricated integration surface.

## Next Safe Step

Move within Step 4 only when one of these is true:

1. a broader real `src/` caller for Engine D appears and can adopt `EngineDRuntime.evaluate_from_historical_state(...)`
2. the project explicitly asks for a new orchestration surface and accepts that as new governed architecture rather than adoption of an existing caller
