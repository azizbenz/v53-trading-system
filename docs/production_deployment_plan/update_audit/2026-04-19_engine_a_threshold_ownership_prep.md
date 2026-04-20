# Objective

Prepare Engine A cost-threshold governance by eliminating duplicated default ownership for `holding_period`, `delta_safe`, and `ce_min`, while keeping Engine A behavior unchanged.

# Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine A still needs governed `ce_min_A` / `delta_safe_A`, but the current DAG does not allow `engine_a -> calibration_loader`. Before this slice, Engine A also had duplicated threshold defaults:

- `EngineAInput` in `engine_a_runner.py`
- `CostInput` in `cost_feasibility_a.py`

Those duplicates would have made the future upstream governed resolver riskier.

# Placement

This slice stays inside the existing Engine A cost seam:

- `src/engines/engine_a/cost_feasibility_a.py`
- `src/engines/engine_a/engine_a_runner.py`

It does not add a direct signed-loader dependency to Engine A. It prepares a single source of truth so a later upstream resolver can feed governed values without another cleanup pass.

# Files Changed

- `src/engines/engine_a/cost_feasibility_a.py`
- `src/engines/engine_a/engine_a_runner.py`
- `tests/test_engines/test_engine_a/test_cost_feasibility_a.py`

# Claims Implemented

- Added explicit Engine A cost-threshold ids:
  - `THR-A01` for `delta_safe`
  - `THR-A02` for `ce_min`
- Added typed `EngineACostThresholds` ownership surface.
- Added `ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE` as the single threshold-default source for:
  - `holding_period`
  - `delta_safe`
  - `ce_min`
- Updated both `CostInput` and `EngineAInput` to read these defaults from the same source.
- Preserved canonical runner default `holding_period=4.0h`.

# Tests and Proof

- `python -m py_compile src/engines/engine_a/cost_feasibility_a.py src/engines/engine_a/engine_a_runner.py tests/test_engines/test_engine_a/test_cost_feasibility_a.py`
  - pass
- `rtk pytest -q tests/test_engines/test_engine_a/test_cost_feasibility_a.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py --basetemp=.test_tmp/pytest`
  - `31 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline fail with `9` violations outside this slice

# Deferred / Not Done

- No direct `CalibrationLoader` wiring inside Engine A.
- No upstream governed resolver feeds `THR-A01` / `THR-A02` yet.
- No canonical microstructure-to-Engine-A calibrated transform was added in this slice.

# Risks / Open Questions

- The dependency registry currently forbids `engine_a -> calibration_loader`. A future signed-threshold adoption must therefore happen through an allowed upstream seam or through a consciously governed architecture change.
- `holding_period` is now explicitly owned by the same cost-threshold surface as `delta_safe` / `ce_min`, but it is still a documented default, not yet a signed calibrated artifact.

# Completion Status

`PARTIAL`

Reason:

Threshold ownership cleanup is complete, but the governed signed-threshold resolver is still deferred.

# Next Safe Step

Add the first allowed upstream Engine A threshold resolver surface outside `engine_a` that can load signed `THR-A01` / `THR-A02` values and pass them into `EngineAInput` without violating the DAG.
