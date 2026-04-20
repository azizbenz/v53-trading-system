## 1. Objective

Determine whether Engine C or Engine A has a truthful existing input-assembly caller that can adopt the shared realized-vol seam without inventing new orchestration.

## 2. Docs Governants

- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## 3. Current Code Seam

Shared realized-vol input seams already exist in:

- `src/data_backbone/microstructure/engine_input_provenance.py`
  - `build_engine_a_microstructure_provenance(...)`
  - `build_engine_a_runner_microstructure_updates(...)`
  - `build_engine_c_microstructure_provenance(...)`
  - `build_engine_c_runner_microstructure_updates(...)`
  - `compose_engine_c_input_payload(...)`

Inventory result for truthful caller adoption:

- Engine C
  - `src/engines/engine_c/engine_c_runner.py`
    - declares `EngineCInput`
  - `src/engines/engine_c/engine_c_runtime.py`
    - declares `EngineCRuntimeInput`
  - no broader `src/` caller found that assembles `EngineCInput` or `EngineCRuntimeInput`
- Engine A
  - `src/engines/engine_a/engine_a_runner.py`
    - declares `EngineAInput`
  - `src/engines/engine_a/engine_a_runtime.py`
    - declares `EngineARuntimeInput`
  - no broader `src/` caller found that assembles `EngineAInput` or `EngineARuntimeInput`

By contrast, Engine D already has a truthful caller seam:

- `src/engines/engine_d/runtime_input_assembler_d.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`

## 4. Placement

This boundary is architectural, not a missing patch. Under the no-synthetic-caller rule, A and C cannot adopt the shared realized-vol seam further until a real caller exists.

## 5. Files Changed

- `docs/production_deployment_plan/update_audit/2026-04-19_engine_ac_realized_vol_input_assembly_boundary.md`

## 6. Claims Implemented

- Verified that Engine C has no truthful existing `src/` caller beyond local type declarations.
- Verified that Engine A has no truthful existing `src/` caller beyond local type declarations.
- Confirmed that pushing further adoption for A/C right now would require creating new orchestration rather than adopting an existing surface.

## 7. Tests and Proof

Inventory proof commands:

- `rtk grep "EngineCInput\\(|EngineCRuntimeInput\\(|compose_engine_c_input_payload\\(|build_engine_c_runner_microstructure_updates\\(|build_engine_c_microstructure_provenance\\(" src`
- `rtk grep "EngineAInput\\(|EngineARuntimeInput\\(|build_engine_a_runner_microstructure_updates\\(|build_engine_a_microstructure_provenance\\(" src`
- `rtk grep "evaluate_from_historical_state\\(|assemble_engine_d_runtime_input\\(|compose_engine_d_input_payload\\(" src`

Results:

- Engine C: no truthful caller beyond declarations and shared seam
- Engine A: no truthful caller beyond declarations and shared seam
- Engine D: truthful caller seam exists and has already been adopted

## 8. Deferred / Not Done

- No new Engine C orchestrator was created.
- No new Engine A orchestrator was created.
- No synthetic public entrypoint was added just to consume realized-vol updates.

## 9. Risks / Open Questions

- Full upstream operational adoption of realized-vol remains partial until A/C obtain real caller surfaces.
- Forcing the next adoption step on A/C today would violate the no-synthetic-orchestrator constraint.

## 10. Completion Status

PARTIAL

The boundary is now explicit and evidenced, but A/C adoption cannot progress further without a real caller.

## 11. Next Safe Step

Wait for a truthful Engine C or Engine A input-assembly owner to exist, then adopt the shared realized-vol seam there. Do not create a new orchestrator solely to consume the adapter.
