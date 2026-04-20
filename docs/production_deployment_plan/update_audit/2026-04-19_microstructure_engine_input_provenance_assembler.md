## Objective

Add a bounded, typed provenance assembler for Engine A / Engine C microstructure input seams under the canonical `src/data_backbone/microstructure/` package, without inventing calibrated scalar transforms or moving score math into engines.

## Docs Governants

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

Canonical microstructure calculators already exist, and Engine A / Engine C still consume scalar seam fields on their runner inputs. The missing additive layer was a typed provenance bundle that could package canonical records together with those current scalar seams, while keeping Engine A scalar mapping explicit and letting Engine C reuse canonical record values directly where the seam already matches.

## Placement

The assembler is placed in `src/data_backbone/microstructure/engine_input_provenance.py`, exported through the canonical package surface:

- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`

This keeps the provenance seam upstream and shared, instead of pushing record-to-scalar packaging logic into engine runners.

## Files Changed

- `src/data_backbone/microstructure/engine_input_provenance.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`

## Claims Implemented

1. `EngineAMicrostructureProvenance` and `EngineCMicrostructureProvenance` remain frozen, typed provenance bundles.
2. `build_engine_a_microstructure_provenance(...)` packages explicit caller-governed Engine A scalar seam values alongside canonical records without inventing score mappings.
3. `build_engine_c_microstructure_provenance(...)` truthfully populates Engine C scalar seams directly from canonical record values.
4. `build_engine_a_runner_microstructure_updates(...)` and `build_engine_c_runner_microstructure_updates(...)` expose caller-facing adapter payloads for upstream runtime/replay code without importing engine modules.
5. `compose_engine_c_input_payload(...)` is the first governed upstream caller surface for Engine C input assembly: it merges caller-owned base payloads with canonical microstructure updates, enforces pair consistency, and rejects conflicting ownership.
6. Pair alignment and required-record validation remain enforced.
7. The new builder helpers are exported from the canonical microstructure package surface.

## Tests and Proof

- `python -m py_compile src/data_backbone/microstructure/engine_input_provenance.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
  - pass
- `rtk pytest -q tests/test_data_backbone/microstructure/test_engine_input_provenance.py tests/test_data_backbone/microstructure/test_feature_provenance_seams.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_c/test_engine_c.py`
  - `33 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - fails on pre-existing repo-global DAG/import-policy issues outside this slice:
    - cycle `execution_backbone -> venue_adapters -> execution_backbone`
    - unauthorized imports involving `engine_a`, `engine_b`, `engine_c`, `engine_d`, `execution_backbone`, and `protocols`

## Deferred / Not Done

- No calibrated auto-mapping from canonical raw records into Engine A scalar seam values such as `ofi_flow_score`, `realized_kernel_vol_scale`, or `kyle_lambda_cost_uplift`.
- No runtime/replay production caller wiring yet populating these bundles from live canonical calculator outputs.
- The new Engine C caller surface is package-level and test-proven, but not yet consumed by a live `src/` orchestrator because no such Engine C input assembler exists in the current codebase.
- No Engine B / Engine D provenance bundles in this slice.

## Risks / Open Questions

- Engine A still needs a governed calibration seam before canonical raw record values can be transformed into its current scalar microstructure inputs.
- Repo-global DAG/import-policy failures remain unresolved and prevent full repo-level completion status.

## Completion Status

`PARTIAL`

The typed assembler exists, is package-exported, and is covered by targeted tests. The slice is not `COMPLETE` because live caller wiring and Engine A calibrated transforms remain deferred, and repo-global DAG proof still fails outside scope.

## Next Safe Step

Integrate `compose_engine_c_input_payload(...)` into the first truthful `src/` Engine C orchestration site once that caller surface exists, while keeping Engine A scalar mapping explicit until calibration governance is in place.
