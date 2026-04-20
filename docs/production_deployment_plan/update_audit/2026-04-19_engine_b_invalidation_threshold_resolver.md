# Objective

Add an allowed upstream signed-threshold resolver for the Engine B invalidation seam without changing Engine B invalidation grammar or runtime behavior.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine B invalidation threshold ownership had already been prepared locally in `invalidation_mapper_b.py`, but there was no allowed upstream signed-calibration resolver for the invalidation threshold family.

# Placement

The resolver lives in `src/scoring_backbone/engine_b_invalidation_thresholds.py`, following the same dependency-safe pattern already used for Engine B cost, breakout, and excess threshold seams.

# Files Changed

- `src/scoring_backbone/engine_b_invalidation_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_scoring_backbone/test_engine_b_invalidation_thresholds.py`

# Claims Implemented

1. Added `EngineBInvalidationThresholdResolverConfig`.
2. Added `EngineBInvalidationThresholdResolution`.
3. Added `resolve_engine_b_invalidation_thresholds(...)`.
4. Added `build_engine_b_invalidation_threshold_updates(...)`.
5. Enforced signed-threshold validation for:
   - positive numeric `max_holding_hours`
   - positive numeric `stop_multiplier`
   - open-unit-interval numeric `fallback_stop_ratio`
   - hard-cap discipline
6. No Engine B invalidation mapping logic, error-code grammar, or fallback semantics changed.

# Tests and Proof

- `python -m py_compile src/scoring_backbone/engine_b_invalidation_thresholds.py src/scoring_backbone/__init__.py tests/test_scoring_backbone/test_engine_b_invalidation_thresholds.py src/engines/engine_b/invalidation_mapper_b.py tests/test_engines/test_engine_b/test_engine_b.py`
  - `pass`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_b_invalidation_thresholds.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py --basetemp=.test_tmp/pytest`
  - `138 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - `FAIL`, unchanged repo-global baseline `9` violations outside this slice

# Deferred / Not Done

- No broader `src/` caller adopts `build_engine_b_invalidation_threshold_updates(...)` yet.
- No direct loader wiring was added to `engine_b`.
- The compatibility seam `ENGINE_B_INVALIDATION_DEFAULTS` remains intentionally preserved.

# Risks / Open Questions

- The resolver exists, but operational adoption still depends on a real broader Engine B input-assembly owner or an intentionally introduced governed orchestration surface.
- Future work must preserve the compatibility seam until a real caller migration is ready.

# Completion Status

`PARTIAL`

The resolver slice itself is implemented and proven, but adoption remains deferred.

# Next Safe Step

At this point, the main local Engine B threshold families have upstream resolver seams. The next safe step is to assess the broader Engine B adoption boundary rather than invent a synthetic caller.
