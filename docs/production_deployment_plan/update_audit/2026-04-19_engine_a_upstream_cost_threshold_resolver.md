# Objective

Add the first allowed upstream signed-threshold resolver surface for Engine A cost inputs, without creating a forbidden `engine_a -> calibration_loader` dependency.

# Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine A cannot import `calibration_loader` directly under the current dependency registry. The correct next slice is therefore an upstream resolver surface in an allowed module, not a direct loader call inside `engine_a`.

# Placement

The new resolver lives in `src/scoring_backbone/engine_a_cost_thresholds.py` because:

- `scoring_backbone -> calibration_loader` is allowed
- `engine_a -> scoring_backbone` is allowed
- this creates a truthful future path for governed threshold injection without changing Engine A runtime behavior today

# Files Changed

- `src/scoring_backbone/engine_a_cost_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_scoring_backbone/test_engine_a_cost_thresholds.py`

# Claims Implemented

- Added `EngineACostThresholdResolverConfig` with:
  - `calibration_root`
  - `calibration_version`
  - caller-specified `delta_safe_threshold_id`
  - caller-specified `ce_min_threshold_id`
  - bounded hard caps
- Added `EngineACostThresholdResolution`
- Added `resolve_engine_a_cost_thresholds(...)`
- Added `build_engine_a_cost_threshold_updates(...)`
- Kept the slice additive:
  - no Engine A behavior change
  - no direct Engine A import of `calibration_loader`
  - no synthetic caller adoption

# Tests and Proof

- `python -m py_compile src/scoring_backbone/engine_a_cost_thresholds.py src/scoring_backbone/__init__.py tests/test_scoring_backbone/test_engine_a_cost_thresholds.py`
  - pass
- `python -m pytest -q tests/test_scoring_backbone/test_engine_a_cost_thresholds.py --basetemp=.test_tmp/pytest`
  - `3 passed`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_a_cost_thresholds.py tests/test_engines/test_engine_a/test_cost_feasibility_a.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py --basetemp=.test_tmp/pytest`
  - `34 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline fail with `9` violations outside this slice

# Deferred / Not Done

- No real caller adopts the new resolver yet.
- No signed threshold ids are injected into a production Engine A input-assembly path yet.
- No microstructure provenance migration is attempted in this slice.

# Risks / Open Questions

- Hard caps in the resolver are governance rails for safe loading, not final doctrinal calibration targets.
- The next adoption step still requires a real caller surface that owns Engine A input assembly.

# Completion Status

`PARTIAL`

Reason:

The upstream allowed resolver now exists and is tested, but no real Engine A caller uses it yet.

# Next Safe Step

Identify the first truthful Engine A input assembly surface outside `engine_a` and adopt `build_engine_a_cost_threshold_updates(...)` there, or document the boundary if no real caller exists yet.
