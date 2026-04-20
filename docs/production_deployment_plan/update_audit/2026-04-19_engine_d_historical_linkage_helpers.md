## Objective

Land the first explicit Step 4 Engine D historical-linkage helpers without rewriting the runner or inventing a second coordination canon.

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

The canonical rule already existed in `src/protocols/engine_coordination_rules.py`, and the append-only A/C evidence rail already existed in `src/protocols/closed_episode_journal.py`. Engine D runtime consumed `EngineCoordinationInput` directly, but there were no explicit Engine D helper surfaces for:

- resolving the first eligible closed A/C episode
- representing/resetting consecutive stop state
- invoking the D historical-linkage rule through a D-specific helper

## Placement

Helpers were added under `src/engines/engine_d/`:

- `first_episode_resolver_d.py`
- `consecutive_stop_counter_d.py`
- `historical_linkage_guard_d.py`

Runtime wiring remains additive: `engine_d_runtime.py` now uses `evaluate_engine_d_historical_linkage(...)`, which delegates to the existing protocol canon instead of re-implementing it.

## Files Changed

- `src/engines/engine_d/first_episode_resolver_d.py`
- `src/engines/engine_d/consecutive_stop_counter_d.py`
- `src/engines/engine_d/historical_linkage_guard_d.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/__init__.py`
- `tests/test_engines/test_engine_d/test_first_episode_resolver_d.py`
- `tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py`
- `tests/test_engines/test_engine_d/test_historical_linkage_guard_d.py`

## Claims Implemented

1. `resolve_first_episode_ref(...)` and `resolve_first_episode(...)` expose explicit first-episode resolution from the closed-episode journal.
2. `ConsecutiveStopStateD` plus `record_engine_d_stop(...)` / `record_fresh_a_detection(...)` expose explicit D reset-state transitions.
3. `build_engine_d_coordination_input(...)` composes D historical state into the canonical coordination input shape through a caller-supplied factory, avoiding new static `protocols` imports in helper modules.
4. `evaluate_engine_d_historical_linkage(...)` wraps the existing canonical coordination rule without creating a second rule engine.
5. `EngineDRuntime` now routes D coordination through the D-specific helper surface.

## Tests and Proof

- `$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile src/engines/engine_d/first_episode_resolver_d.py src/engines/engine_d/consecutive_stop_counter_d.py src/engines/engine_d/historical_linkage_guard_d.py src/engines/engine_d/engine_d_runtime.py src/engines/engine_d/__init__.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py tests/test_engines/test_engine_d/test_historical_linkage_guard_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_protocols/test_closed_episode_journal.py tests/test_protocols/test_engine_coordination_rules.py`
  - pass
- `rtk pytest -q tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py tests/test_engines/test_engine_d/test_historical_linkage_guard_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_protocols/test_closed_episode_journal.py tests/test_protocols/test_engine_coordination_rules.py`
  - `53 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - fails on the same pre-existing repo-global cycle/import-policy issues:
    - cycle `execution_backbone -> venue_adapters -> execution_backbone`
    - unauthorized imports involving `engine_a`, `engine_b`, `engine_c`, `engine_d`, `execution_backbone`, and `protocols`
  - no new DAG violation count introduced by this slice; report returned to the known `9`-violation baseline after removing new static helper imports

## Deferred / Not Done

- No automatic runtime caller yet constructs `EngineCoordinationInput` from the new helpers.
- No `first_episode_ref` auto-resolution is wired into a D orchestrator surface.
- No strategy-beta or inherited-field deepening in this slice.

## Risks / Open Questions

- Repo-global DAG/import-policy failures remain an expected external blocker until separately addressed.
- The new helpers make the D historical rail explicit, but they do not yet replace caller-owned assembly of `EngineCoordinationInput`.

## Completion Status

`PARTIAL`

Targeted proofs passed and the repo-global DAG result returned to the known pre-existing baseline. The slice remains `PARTIAL` because there is still no governed caller assembling `EngineCoordinationInput` from the new helpers, and no deeper D strategy-beta / inherited-field wiring in this slice.

## Next Safe Step

Wire `resolve_first_episode(...)` and `ConsecutiveStopStateD` into the first governed D coordination-input assembler, without changing runner semantics or inventing a second coordination path.
