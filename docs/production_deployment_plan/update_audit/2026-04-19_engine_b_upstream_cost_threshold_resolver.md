# Objective

Prepare Engine B signed cost-threshold governance through an allowed upstream seam, without changing Engine B trading semantics or violating the repo DAG policy.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine B already had grouped cost defaults in `cost_feasibility_b.py`, but the signed-threshold resolution path did not exist yet. Direct `engine_b -> calibration_loader` wiring remains disallowed by the current dependency discipline, so the resolver had to live in an allowed upstream layer.

# Placement

The new resolver lives in `src/scoring_backbone/engine_b_cost_thresholds.py`. This keeps signed calibration lookup outside `engine_b`, while still providing additive caller-owned updates for future Engine B input assembly surfaces.

# Files Changed

- `src/engines/engine_b/engine_b_runner.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_scoring_backbone/test_engine_b_cost_thresholds.py`

# Claims Implemented

1. Engine B cost-threshold ownership is now asserted against the typed single-source surface `ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE`.
2. The upstream signed-threshold resolver for Engine B is covered by targeted tests:
   - signed load success
   - caller-facing update payload shape
   - hard-cap rejection
3. No Engine B score logic, runtime logic, or trading semantics were changed.

# Tests and Proof

- `python -m py_compile src/engines/engine_b/cost_feasibility_b.py src/engines/engine_b/engine_b_runner.py src/scoring_backbone/engine_b_cost_thresholds.py src/scoring_backbone/__init__.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_scoring_backbone/test_engine_b_cost_thresholds.py`
  - `pass`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_b_cost_thresholds.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py --basetemp=.test_tmp/pytest`
  - `138 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - `FAIL`, unchanged repo-global baseline `9` violations outside this slice

# Deferred / Not Done

- No real broader `src/` caller adopts `build_engine_b_cost_threshold_updates(...)` yet.
- No direct signed threshold injection into a production Engine B input-assembly owner was added.
- No broader Engine B threshold families beyond the cost seam were moved in this slice.

# Risks / Open Questions

- The upstream resolver exists, but adoption still depends on a real caller surface outside `engine_b`.
- Current DAG policy still prevents direct `engine_b -> calibration_loader` wiring, so future adoption must stay upstream or the dependency policy must change intentionally.

# Completion Status

`PARTIAL`

The ownership prep plus upstream resolver proof are complete for this slice, but the resolver is not yet adopted by a broader real caller.

# Next Safe Step

Identify whether a real broader `src/` Engine B input assembly surface exists. If it does, adopt `build_engine_b_cost_threshold_updates(...)` there. If it does not, document that boundary explicitly instead of creating a synthetic caller.
