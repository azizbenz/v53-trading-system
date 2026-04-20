## 1. Objective

Adopt the shared realized-vol engine-facing adapter in the first truthful existing Engine D caller surface instead of leaving the D realized-vol seam unused outside tests.

## 2. Docs Governants

- `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## 3. Current Code Seam

Before this slice:

- `src/data_backbone/microstructure/engine_input_provenance.py`
  - already exposed `build_engine_d_runner_microstructure_updates(...)`
  - but no real `src/` caller consumed it
- `src/engines/engine_d/runtime_input_assembler_d.py`
  - assembled `EngineDRuntimeInput`
  - but accepted only already-populated `EngineDInput`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
  - exposed the public historical-entry runtime seam
  - but did not accept canonical realized-vol records

## 4. Placement

The shared microstructure layer remains the only place that translates canonical realized-kernel records into Engine D input fields. Adoption is performed by the existing D runtime-input assembler and public historical-entry seam; no new orchestrator or bridge was created.

## 5. Files Changed

- `src/data_backbone/microstructure/engine_input_provenance.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `src/data_backbone/microstructure/feature_registry.py`
- `src/engines/engine_d/runtime_input_assembler_d.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`

## 6. Claims Implemented

- Added `compose_engine_d_input_payload(...)` to the shared microstructure provenance seam.
- `compose_engine_d_input_payload(...)` merges canonical realized-vol records into a caller-owned Engine D payload and rejects conflicting ownership.
- `assemble_engine_d_runtime_input(...)` now adopts the shared D compose seam before constructing `EngineDRuntimeInput`.
- `EngineDRuntime.evaluate_from_historical_state(...)` now exposes the same adoption path through its public historical-entry seam.
- The canonical feature registry now records `engines.engine_d.runtime_input_assembler_d` as a realized-kernel consumer surface.

## 7. Tests and Proof

- `python -m py_compile ...` on touched shared and D files/tests: pass
- `rtk pytest -q tests/test_data_backbone/microstructure/test_engine_input_provenance.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_data_backbone/microstructure/test_feature_registry.py --basetemp=.test_tmp/pytest`
  - pass
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline fail outside this slice

## 8. Deferred / Not Done

- No analogous truthful caller adoption exists yet for Engine A.
- No analogous truthful caller adoption exists yet for Engine C.
- No broader production orchestrator outside `src/engines/engine_d/` consumes this seam yet.

## 9. Risks / Open Questions

- This closes the first real D adoption site, not full A/C/D end-to-end adoption.
- Caller conflict rejection is deliberate; upstream owners must not pass contradictory realized-vol values and records.

## 10. Completion Status

PARTIAL

The first truthful Engine D caller now consumes the shared realized-vol seam, but A and C still do not have equivalent real caller adoption and repo-global DAG proof remains outside-slice red.

## 11. Next Safe Step

Inventory whether Engine C has any truthful input-assembly seam beyond `compose_engine_c_input_payload(...)`; if not, stop there honestly and wait for a real caller rather than creating a synthetic one.
