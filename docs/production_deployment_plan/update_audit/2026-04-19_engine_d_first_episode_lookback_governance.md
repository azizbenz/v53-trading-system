## 1. Objective

Advance Engine D first-episode linkage governance on the next safe local seam by:

- replacing unowned `lookback_ns` usage with a typed caller-threshold surface
- adding an allowed upstream signed resolver for `THR-D_LOOKBACK`
- proving that the existing public Engine D runtime seam can consume the governed lookback without inventing a broader caller

This slice does **not** attempt `THR-D_MIN_GAP`, because that seam is not yet present in the current Engine D runtime path.

## 2. Docs Governants

- `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`
- `11_DYNAMIC_THRESHOLDS_CATALOG.md`
- `13_CALIBRATION_METHODS.md`

## 3. Current Code Seam

Before this slice:

- `first_episode_resolver_d.py` accepted `lookback_ns`, but no typed threshold ownership surface existed
- no upstream signed resolver existed for `THR-D_LOOKBACK`
- the public runtime seam `EngineDRuntime.evaluate_from_historical_state(...)` accepted `lookback_ns`, but had no governed default path

Existing truthful public seams already present:

- `src/engines/engine_d/first_episode_resolver_d.py`
- `src/engines/engine_d/coordination_input_assembler_d.py`
- `src/engines/engine_d/runtime_input_assembler_d.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`

## 4. Placement

This slice stays additive:

- local ownership lands in `src/engines/engine_d/first_episode_resolver_d.py`
- public runtime adoption lands in `src/engines/engine_d/engine_d_runtime.py` and `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- the allowed signed resolver lands in `src/scoring_backbone/engine_d_first_episode_thresholds.py`

No broader orchestration surface was created.

## 5. Files Changed

- `src/engines/engine_d/first_episode_resolver_d.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- `src/engines/engine_d/__init__.py`
- `src/scoring_backbone/engine_d_first_episode_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_engines/test_engine_d/test_first_episode_resolver_d.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`
- `tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`

## 6. Claims Implemented

- Added `EngineDFirstEpisodeCallerThresholds` as the single local ownership surface for `THR-D_LOOKBACK`.
- Added explicit doctrinal threshold id:
  - `THR-D_LOOKBACK`
- Added `ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE`.
- Added upstream signed resolver seam:
  - `EngineDFirstEpisodeThresholdResolverConfig`
  - `EngineDFirstEpisodeThresholdResolution`
  - `resolve_engine_d_first_episode_thresholds(...)`
  - `build_engine_d_first_episode_threshold_updates(...)`
- Added additive public runtime adoption:
  - `EngineDRuntime` now accepts `first_episode_lookback_ns`
  - `EngineDRuntime.evaluate_from_historical_state(...)` uses that governed lookback when the caller does not pass `lookback_ns`
- Proved that a 12h governed lookback blocks D historical linkage when the only candidate episode is 13h old.
- Added a one-line `from __future__ import annotations` fix to an empty unrelated test file so the mandatory guardrail proof stayed honest and green.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_d/first_episode_resolver_d.py src/engines/engine_d/engine_d_runtime.py src/engines/engine_d/engine_d_runtime_history_entry_mixin.py src/engines/engine_d/__init__.py src/scoring_backbone/engine_d_first_episode_thresholds.py src/scoring_backbone/__init__.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py --basetemp=.test_tmp/pytest`
  - `47 passed`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
  - `124 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No broader caller outside `engine_d` adopts `build_engine_d_first_episode_threshold_updates(...)` yet.
- No `THR-D_MIN_GAP` resolver or runtime adoption in this slice.
- No broader orchestration/input-assembly surface was created.

## 9. Risks / Open Questions

- The current resolver governs `THR-D_LOOKBACK` only; `THR-D_MIN_GAP` remains separate work.
- Final production calibration discipline still depends on a broader caller adopting the signed resolver instead of leaving lookback injection local.
- Repo-global DAG/import-policy failures remain an external blocker.

## 10. Completion Status

`PARTIAL`

Local ownership, upstream signed resolution, and public runtime adoption are implemented and tested, but broader caller adoption is still absent and `THR-D_MIN_GAP` remains deferred.

## 11. Next Safe Step

Continue on `THR-D_MIN_GAP` only if a truthful runtime seam for gap enforcement exists. Otherwise, stop pushing synthetic D history controls and wait for the first broader caller outside `engine_d` to adopt the new lookback resolver.
