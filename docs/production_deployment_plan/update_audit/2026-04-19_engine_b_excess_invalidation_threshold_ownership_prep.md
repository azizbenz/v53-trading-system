# Objective

Prepare Engine B threshold ownership on the next two local seams that do not depend on a broader caller:

- `excess_detector_b.py`
- `invalidation_mapper_b.py`

The goal is to consolidate threshold ownership into typed single-source surfaces without changing Engine B trading semantics.

# Docs Governants

- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

# Current Code Seam

Engine B already grouped excess and invalidation defaults in module-level dictionaries, but ownership was still informal. This slice moves ownership into typed surfaces while keeping the existing dictionary constants as compatibility mirrors.

# Placement

Both ownership-prep changes remain local to `src/engines/engine_b/*`. No runtime orchestration, no broader caller, and no scoring/risk semantics changed.

# Files Changed

- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/invalidation_mapper_b.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`

# Claims Implemented

1. Engine B excess thresholds now have a typed single-source surface:
   - `EngineBExcessThresholds`
   - `EngineBExcessAdjustments`
2. Explicit excess threshold ids were added:
   - `THR-B05` = `z_marginal`
   - `THR-B06` = `z_star`
   - `THR-B07` = `z_max`
   - `THR-B08` = `vpin_toxic`
   - `THR-B09` = `max_intra_family_correlation`
3. `detect_excess(...)` now reads from the typed excess ownership surface.
4. Engine B invalidation thresholds now have a typed single-source surface:
   - `EngineBInvalidationThresholds`
5. Explicit invalidation threshold ids were added:
   - `THR-B10` = `max_holding_hours`
   - `THR-B11` = `fallback_stop_ratio`
   - `THR-B12` = `stop_multiplier`
6. `ENGINE_B_INVALIDATION_DEFAULTS` remains as a compatibility seam derived from the typed ownership surface so existing monkeypatch-based tests and callers do not break.
7. No Engine B verdict logic, toxic-flow semantics, invalidation grammar, or runtime parity changed.

# Tests and Proof

- `python -m py_compile src/engines/engine_b/excess_detector_b.py src/engines/engine_b/invalidation_mapper_b.py tests/test_engines/test_engine_b/test_engine_b.py`
  - `pass`
- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py --basetemp=.test_tmp/pytest`
  - `135 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - `FAIL`, unchanged repo-global baseline `9` violations outside this slice

# Deferred / Not Done

- No signed-threshold resolver exists yet for the new excess or invalidation threshold ids.
- No broader caller adoption exists for these threshold families.
- `ENGINE_B_INVALIDATION_DEFAULTS` is intentionally retained as a compatibility seam and is not yet retired.

# Risks / Open Questions

- Future signed-threshold adoption for these families will likely need allowed upstream resolver seams similar to `engine_b_cost_thresholds.py`.
- If compatibility dictionaries are kept too long, future work must continue to ensure they remain derived from the typed ownership source and do not drift.

# Completion Status

`PARTIAL`

Ownership prep is complete and proven for these two local threshold families, but signed calibration adoption remains deferred.

# Next Safe Step

The next safe Step 6 slice is to add allowed upstream signed-threshold resolvers for the newly prepared Engine B threshold families, starting with the anti-breakout seam or the excess seam, without inventing a broader caller.
