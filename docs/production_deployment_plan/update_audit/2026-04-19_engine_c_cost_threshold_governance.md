## 1. Objective

Advance Engine C cost-threshold governance on the next safe local seam by:

- replacing tuple-only local ownership with a typed caller-threshold surface
- adding an allowed upstream signed resolver in `scoring_backbone`

without changing Engine C trading semantics or inventing a broader caller.

## 2. Docs Governants

- `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `11_DYNAMIC_THRESHOLDS_CATALOG.md`
- `13_CALIBRATION_METHODS.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Before this slice:

- Engine C cost thresholds on the local seam were represented by a tuple only
- `EngineCInput` defaults still read raw `ce_min` / `delta_safe` values
- no upstream signed resolver existed for Engine C cost thresholds

## 4. Placement

This slice stays additive:

- local ownership lands in `src/engines/engine_c/cost_feasibility_c.py`
- runner defaults reuse that ownership surface in `src/engines/engine_c/engine_c_runner.py`
- the allowed signed resolver lands in `src/scoring_backbone/engine_c_cost_thresholds.py`

No broader orchestration surface was added.

## 5. Files Changed

- `src/engines/engine_c/cost_feasibility_c.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/__init__.py`
- `src/scoring_backbone/engine_c_cost_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_engines/test_engine_c/test_cost_feasibility_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_scoring_backbone/test_engine_c_cost_thresholds.py`

## 6. Claims Implemented

- Added `EngineCCostCallerThresholds` as the single local ownership surface for:
  - `delta_safe`
  - `ce_min`
- Added explicit doctrinal family ids:
  - `THR-E04` for `delta_safe`
  - `THR-E03` for `ce_min`
- Added `ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE`.
- Wired `EngineCInput` defaults to the typed local cost threshold surface.
- Added upstream signed resolver seam:
  - `EngineCCostThresholdResolverConfig`
  - `EngineCCostThresholdResolution`
  - `resolve_engine_c_cost_thresholds(...)`
  - `build_engine_c_cost_threshold_updates(...)`
- Kept resolver threshold ids caller-specified because the current doctrine pins threshold families (`THR-E03` / `THR-E04`) but does not force one concrete artifact id naming convention for Engine C.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_c/cost_feasibility_c.py src/engines/engine_c/engine_c_runner.py src/engines/engine_c/__init__.py src/scoring_backbone/engine_c_cost_thresholds.py src/scoring_backbone/__init__.py tests/test_engines/test_engine_c/test_cost_feasibility_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_scoring_backbone/test_engine_c_cost_thresholds.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_c_cost_thresholds.py tests/test_engines/test_engine_c/test_cost_feasibility_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py --basetemp=.test_tmp/pytest`
  - `46 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No broader caller outside `engine_c` adopts `build_engine_c_cost_threshold_updates(...)` yet.
- No new orchestration/input-assembly surface was created.
- No claim that Engine C cost thresholds are fully promoted end-to-end.

## 9. Risks / Open Questions

- The current resolver uses caller-specified signed threshold ids because doctrine freezes the threshold families, not one canonical Engine C artifact naming convention.
- Hard caps remain sanity caps at resolver level; final production calibration discipline still depends on broader adoption and signed artifacts.

## 10. Completion Status

`PARTIAL`

Local ownership and the allowed upstream resolver are implemented and tested, but broader caller adoption is still absent.

## 11. Next Safe Step

Continue Step 7 on another local Engine C family that does not require a broader caller, or stop and wait for a real Engine C input owner outside `engine_c` before adopting the new cost resolver.
