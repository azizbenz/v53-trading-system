# Objective

Add an allowed upstream signed-threshold resolver for the Engine B anti-breakout threshold seam without changing Engine B breakout logic.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine B anti-breakout threshold ownership had already been prepared locally in `anti_breakout_filter_b.py`, but there was no allowed upstream signed-calibration resolver comparable to the existing cost-threshold seam.

# Placement

The resolver lives in `src/scoring_backbone/engine_b_breakout_thresholds.py`, following the same dependency-safe pattern as `engine_b_cost_thresholds.py`.

# Files Changed

- `src/scoring_backbone/engine_b_breakout_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_scoring_backbone/test_engine_b_breakout_thresholds.py`

# Claims Implemented

1. Added `EngineBBreakoutThresholdResolverConfig`.
2. Added `EngineBBreakoutThresholdResolution`.
3. Added `resolve_engine_b_breakout_thresholds(...)`.
4. Added `build_engine_b_breakout_threshold_updates(...)`.
5. Enforced signed-threshold validation for:
   - unit-interval numeric values
   - hard-cap discipline
   - strict ordering `warning < blocked`
6. No Engine B breakout runtime logic changed.

# Tests and Proof

- `python -m py_compile src/scoring_backbone/engine_b_breakout_thresholds.py src/scoring_backbone/__init__.py tests/test_scoring_backbone/test_engine_b_breakout_thresholds.py src/engines/engine_b/anti_breakout_filter_b.py tests/test_engines/test_engine_b/test_engine_b.py`
  - `pass`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_b_breakout_thresholds.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py --basetemp=.test_tmp/pytest`
  - `138 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - `FAIL`, unchanged repo-global baseline `9` violations outside this slice

# Deferred / Not Done

- No broader `src/` caller adopts `build_engine_b_breakout_threshold_updates(...)` yet.
- No direct loader wiring was added to `engine_b`.

# Risks / Open Questions

- The resolver exists, but operational adoption still depends on a real broader Engine B input-assembly owner or a consciously introduced governed orchestration surface.

# Completion Status

`PARTIAL`

The resolver slice itself is implemented and proven, but adoption remains deferred.

# Next Safe Step

Either add the same allowed upstream signed-threshold resolver pattern for the Engine B excess seam, or explicitly document the broader Engine B adoption boundary if no real caller exists yet.
