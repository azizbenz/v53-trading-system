## 1. Objective

Advance Engine D cost-threshold governance on the next safe local seam by:

- replacing inline local ownership with a typed caller-threshold surface
- adding an allowed upstream signed resolver in `scoring_backbone`

without changing Engine D trading semantics or inventing a broader caller.

## 2. Docs Governants

- `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `11_DYNAMIC_THRESHOLDS_CATALOG.md`
- `13_CALIBRATION_METHODS.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Before this slice:

- Engine D cost thresholds were only implicit defaults in `EngineDInput`
- no typed local ownership surface existed for `ce_min` / `delta_safe`
- no upstream signed resolver existed for Engine D cost thresholds

The cost logic itself already lived in:

- `src/engines/engine_d/cost_feasibility_d.py`
- `src/engines/engine_d/engine_d_models.py`
- `src/engines/engine_d/engine_d_runner.py`

## 4. Placement

This slice stays additive:

- local ownership lands in `src/engines/engine_d/cost_feasibility_d.py`
- `EngineDInput` defaults reuse that ownership surface in `src/engines/engine_d/engine_d_models.py`
- the allowed signed resolver lands in `src/scoring_backbone/engine_d_cost_thresholds.py`

No broader orchestration surface was added.

## 5. Files Changed

- `src/engines/engine_d/cost_feasibility_d.py`
- `src/engines/engine_d/engine_d_models.py`
- `src/engines/engine_d/__init__.py`
- `src/scoring_backbone/engine_d_cost_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_engines/test_engine_d/test_cost_feasibility_d.py`
- `tests/test_engines/test_engine_d/test_engine_d.py`
- `tests/test_scoring_backbone/test_engine_d_cost_thresholds.py`

## 6. Claims Implemented

- Added `EngineDCostCallerThresholds` as the single local ownership surface for:
  - `delta_safe`
  - `ce_min`
- Added explicit doctrinal family ids:
  - `THR-E04` for `delta_safe`
  - `THR-E03` for `ce_min`
- Added `ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE`.
- Wired `EngineDInput` defaults to the typed local cost threshold surface.
- Added upstream signed resolver seam:
  - `EngineDCostThresholdResolverConfig`
  - `EngineDCostThresholdResolution`
  - `resolve_engine_d_cost_thresholds(...)`
  - `build_engine_d_cost_threshold_updates(...)`
- Kept resolver threshold ids caller-specified because the current doctrine pins threshold families (`THR-E03` / `THR-E04`) but does not force one concrete artifact id naming convention for Engine D.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_d/cost_feasibility_d.py src/engines/engine_d/engine_d_models.py src/engines/engine_d/__init__.py src/scoring_backbone/engine_d_cost_thresholds.py src/scoring_backbone/__init__.py tests/test_engines/test_engine_d/test_cost_feasibility_d.py tests/test_engines/test_engine_d/test_engine_d.py tests/test_scoring_backbone/test_engine_d_cost_thresholds.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_d_cost_thresholds.py tests/test_engines/test_engine_d/test_cost_feasibility_d.py tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py --basetemp=.test_tmp/pytest`
  - `55 passed`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
  - `122 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No broader caller outside `engine_d` adopts `build_engine_d_cost_threshold_updates(...)` yet.
- No new orchestration/input-assembly surface was created.
- No claim that Engine D cost thresholds are fully promoted end-to-end.

## 9. Risks / Open Questions

- The current resolver uses caller-specified signed threshold ids because doctrine freezes the threshold families, not one canonical Engine D artifact naming convention.
- Hard caps remain sanity caps at resolver level; final production calibration discipline still depends on broader adoption and signed artifacts.
- Repo-global DAG/import-policy failures remain an external blocker.

## 10. Completion Status

`PARTIAL`

Local ownership and the allowed upstream resolver are implemented and tested, but broader caller adoption is still absent.

## 11. Next Safe Step

If a truthful Engine D input owner outside `engine_d` appears, adopt `build_engine_d_cost_threshold_updates(...)` there instead of keeping threshold injection local. Otherwise, continue the plan on another real local Engine D seam that does not require a broader caller.
