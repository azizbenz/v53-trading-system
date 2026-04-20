# Objective

Add an allowed upstream signed-threshold resolver for the Engine B excess seam without changing Engine B excess logic or toxic-flow semantics.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine B excess threshold ownership had already been prepared locally in `excess_detector_b.py`, but there was no allowed upstream signed-calibration resolver for the excess threshold family.

# Placement

The resolver lives in `src/scoring_backbone/engine_b_excess_thresholds.py`, following the same dependency-safe pattern already used for Engine B cost and breakout threshold seams.

# Files Changed

- `src/scoring_backbone/engine_b_excess_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_scoring_backbone/test_engine_b_excess_thresholds.py`

# Claims Implemented

1. Added `EngineBExcessThresholdResolverConfig`.
2. Added `EngineBExcessThresholdResolution`.
3. Added `resolve_engine_b_excess_thresholds(...)`.
4. Added `build_engine_b_excess_threshold_updates(...)`.
5. Enforced signed-threshold validation for:
   - positive numeric `z_marginal`, `z_star`, `z_max`
   - unit-interval numeric `vpin_toxic`, `max_intra_family_correlation`
   - hard-cap discipline
   - strict ordering `z_marginal < z_star < z_max`
6. No Engine B excess verdict logic or `toxic_flow_fade` semantics changed.

# Tests and Proof

- `python -m py_compile src/scoring_backbone/engine_b_excess_thresholds.py src/scoring_backbone/__init__.py tests/test_scoring_backbone/test_engine_b_excess_thresholds.py src/engines/engine_b/excess_detector_b.py tests/test_engines/test_engine_b/test_engine_b.py`
  - `pass`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_b_excess_thresholds.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py --basetemp=.test_tmp/pytest`
  - `138 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - `FAIL`, unchanged repo-global baseline `9` violations outside this slice

# Deferred / Not Done

- No broader `src/` caller adopts `build_engine_b_excess_threshold_updates(...)` yet.
- No signed resolver was added for `range_bonus` / `expansion_penalty`; those remain under local typed ownership only.
- No direct loader wiring was added to `engine_b`.

# Risks / Open Questions

- The resolver exists, but operational adoption still depends on a real broader Engine B input-assembly owner or an intentionally introduced governed orchestration surface.
- Future calibration governance may also need an upstream seam for the excess adjustment parameters if those are promoted beyond local ownership.

# Completion Status

`PARTIAL`

The resolver slice itself is implemented and proven, but adoption remains deferred.

# Next Safe Step

Stay on local Engine B governance slices and add the next allowed upstream signed-threshold resolver, with the invalidation seam as the best next candidate.
