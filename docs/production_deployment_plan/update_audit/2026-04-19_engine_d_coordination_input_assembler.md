## Objective

Add the first governed Engine D coordination-input assembler that resolves historical linkage from the closed-episode journal and explicit stop state, without inventing a second coordination rule engine or synthetic runtime state.

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

The previous slice landed explicit Engine D historical-linkage helpers:

- first-episode resolution
- consecutive-stop state helpers
- D historical-linkage guard wrapper

But there was still no governed assembler that took those helper seams and produced a caller-ready `EngineCoordinationInput`.

## Placement

The assembler is placed in:

- `src/engines/engine_d/coordination_input_assembler_d.py`

It stays protocol-agnostic by taking a caller-supplied `coordination_input_factory`, while using:

- `resolve_first_episode(...)`
- `ConsecutiveStopStateD`
- `build_engine_d_coordination_input(...)`

## Files Changed

- `src/engines/engine_d/coordination_input_assembler_d.py`
- `src/engines/engine_d/__init__.py`
- `tests/test_engines/test_engine_d/test_coordination_input_assembler_d.py`

## Claims Implemented

1. `assemble_engine_d_coordination_input(...)` resolves the most recent D-eligible A/C episode from the journal.
2. The assembler carries explicit `ConsecutiveStopStateD` into the coordination-input payload.
3. The assembler returns a typed assembly object containing:
   - the historical resolution result
   - the stop state
   - the caller-ready coordination input
4. The assembler does not re-implement protocol rules; canonical evaluation still happens in `evaluate_engine_coordination(...)`.
5. The new assembler is test-proven to work end-to-end with `EngineDRuntime`.

## Tests and Proof

- `$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile ...`
  - pass
- `rtk pytest -q tests/test_engines/test_engine_d/test_coordination_input_assembler_d.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py tests/test_engines/test_engine_d/test_historical_linkage_guard_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_protocols/test_closed_episode_journal.py tests/test_protocols/test_engine_coordination_rules.py`
  - `55 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - fails on the same pre-existing repo-global cycle/import-policy issues:
    - cycle `execution_backbone -> venue_adapters -> execution_backbone`
    - unauthorized imports involving `engine_a`, `engine_b`, `engine_c`, `engine_d`, `execution_backbone`, and `protocols`
  - DAG violation count stayed at the known `9`-violation baseline

## Deferred / Not Done

- No production runtime/orchestrator caller in `src/` wires this assembler yet.
- No strategy-beta or inherited-field deepening in this slice.
- No auto-persistence of `ConsecutiveStopStateD` in this slice.

## Risks / Open Questions

- Repo-global DAG/import-policy failures remain an external blocker until separately addressed.
- The assembler is now governed and end-to-end testable, but still needs adoption by a real caller surface outside tests.

## Completion Status

`PARTIAL`

Targeted proofs passed, guardrails stayed clean, and the DAG report remained at the pre-existing baseline. The slice stays `PARTIAL` because the assembler is now governed and end-to-end testable, but no production runtime/orchestrator caller in `src/` adopts it yet.

## Next Safe Step

Adopt `assemble_engine_d_coordination_input(...)` in the first truthful D orchestration surface that currently hand-builds `EngineCoordinationInput`, without changing runner semantics.
