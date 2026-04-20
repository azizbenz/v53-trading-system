# Objective

Prepare Engine B anti-breakout threshold ownership for future calibration governance without changing Engine B trading semantics.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

`anti_breakout_filter_b.py` already grouped breakout weights and thresholds in module-level dictionaries, but ownership was still informal. This slice promotes those values into typed single-source surfaces while preserving the current public constants and evaluation logic.

# Placement

The ownership prep remains local to `src/engines/engine_b/anti_breakout_filter_b.py`. No caller or runtime wiring changed.

# Files Changed

- `src/engines/engine_b/anti_breakout_filter_b.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`

# Claims Implemented

1. Engine B anti-breakout weights now have a typed ownership surface: `EngineBBreakoutFilterWeights`.
2. Engine B anti-breakout thresholds now have a typed ownership surface: `EngineBBreakoutFilterThresholds`.
3. Threshold ids were made explicit:
   - `THR-B03` for warning
   - `THR-B04` for blocked
4. Existing dictionary constants remain available as compatibility mirrors derived from the typed ownership surface.
5. `evaluate_breakout_risk(...)` now reads from the typed single-source surfaces instead of raw literals or raw dicts.
6. No breakout logic, scoring, or reason-code semantics were changed.

# Tests and Proof

- `python -m py_compile src/engines/engine_b/anti_breakout_filter_b.py tests/test_engines/test_engine_b/test_engine_b.py`
  - `pass`
- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py --basetemp=.test_tmp/pytest`
  - `135 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - `FAIL`, unchanged repo-global baseline `9` violations outside this slice

# Deferred / Not Done

- No signed-threshold resolver exists yet for `THR-B03` / `THR-B04`.
- No broader calibration-loader adoption exists for the anti-breakout seam.
- No broader Engine B threshold families beyond this anti-breakout slice were touched here.

# Risks / Open Questions

- This slice closes ownership only. Future signed-threshold adoption still needs an allowed upstream seam if direct loader wiring remains disallowed by DAG policy.
- `ENGINE_B_BREAKOUT_FILTER_WEIGHTS` and `ENGINE_B_BREAKOUT_FILTER_THRESHOLDS` remain for compatibility, so future work should avoid letting them drift away from the typed ownership surface.

# Completion Status

`PARTIAL`

Ownership prep is complete and proven for this anti-breakout seam, but signed calibration adoption is still deferred.

# Next Safe Step

Continue Step 6 on another local Engine B threshold family that does not depend on a broader caller, with the next best candidate being `excess_detector_b.py`.
