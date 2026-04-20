## Objective

Adopt the governed Engine D coordination-input assembler on real public runtime surfaces by:

- adding a runtime-input assembler that produces `EngineDRuntimeInput` with historical coordination already populated
- adding an additive `EngineDRuntime` entrypoint that consumes that assembler directly

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

The previous Step 4 slices added:

- explicit first-episode resolution
- explicit D stop-state helpers
- a governed coordination-input assembler

The previous sub-slice introduced the first actual caller surface in `src/engines/engine_d/`:

- `assemble_engine_d_runtime_input(...)`

This follow-up adopts that assembler on the public `EngineDRuntime` surface itself.

## Placement

The adopted caller surfaces are:

- `src/engines/engine_d/runtime_input_assembler_d.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`

It stays additive and protocol-rule-agnostic:

- it uses `assemble_engine_d_coordination_input(...)`
- it assembles `EngineDRuntimeInput`
- `EngineDRuntime.evaluate_from_historical_state(...)` delegates to the governed assembler, then evaluates the canonical runtime rail
- it does not create a second coordination rule engine

## Files Changed

- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`
- `tests/test_engines/test_engine_d/test_coordination_input_assembler_d.py`
- `docs/production_deployment_plan/update_audit/2026-04-19_engine_d_runtime_input_assembler.md`

## Claims Implemented

1. `assemble_engine_d_runtime_input(...)` remains the first governed `src/` caller surface that adopts the D coordination-input assembler.
2. `EngineDRuntime.evaluate_from_historical_state(...)` provides an additive public path that assembles historical linkage evidence and then evaluates the canonical runtime rail.
3. The public entrypoint is hosted in a dedicated mixin file so `engine_d_runtime.py` stays under the file-length guardrail without changing runtime semantics.
4. The assembly path resolves historical linkage from the journal and merges explicit stop-state into the runtime input.
5. It returns both:
   - the coordination assembly
   - the fully assembled `EngineDRuntimeInput`
6. It is end-to-end testable through `EngineDRuntime`.
7. It does not introduce a second coordination rule engine or widen canonical public contracts.

## Tests and Proof

- `$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile src/engines/engine_d/engine_d_runtime.py src/engines/engine_d/engine_d_runtime_history_entry_mixin.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_engines/test_engine_d/test_coordination_input_assembler_d.py`
  - pass
- `python -m pytest -q tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_engines/test_engine_d/test_coordination_input_assembler_d.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py tests/test_engines/test_engine_d/test_historical_linkage_guard_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_protocols/test_closed_episode_journal.py tests/test_protocols/test_engine_coordination_rules.py --basetemp=.test_tmp/pytest`
  - `61 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - fails on the same pre-existing repo-global cycle/import-policy issues:
    - cycle `execution_backbone -> venue_adapters -> execution_backbone`
    - unauthorized imports involving `engine_a`, `engine_b`, `engine_c`, `engine_d`, `execution_backbone`, and `protocols`
  - DAG violation count remained at the known `9`-violation baseline

## Deferred / Not Done

- No external orchestrator outside `src/engines/engine_d/` adopts the runtime-input assembler yet.
- No strategy-beta or inherited-field deepening in this slice.
- No state persistence for `ConsecutiveStopStateD` in this slice.

## Risks / Open Questions

- Repo-global DAG/import-policy failures remain an external blocker until separately addressed.
- This closes the "no real src caller" gap at the engine package public-runtime level, but not yet at a broader protocol/orchestration layer.

## Completion Status

`PARTIAL`

Targeted proofs passed, guardrails stayed clean, and the DAG report remained on the pre-existing baseline. The slice stays `PARTIAL` because the runtime class now adopts the assembler, but no broader orchestration or replay surface outside `src/engines/engine_d` adopts that public seam yet.

## Next Safe Step

If a broader orchestration or replay surface for Engine D appears in `src/`, adopt `EngineDRuntime.evaluate_from_historical_state(...)` there instead of hand-building runtime inputs. Otherwise, stay inside Step 4 and make the D reset/failsafe state more explicitly inspectable without inventing a synthetic caller.
