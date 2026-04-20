## Objective

Implement the B-local `toxic_flow_fade` sub-signal using existing Engine B files only, without creating a new engine and without inventing a new excess formula.

## Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`

## Current Code Seam

Engine B already contains:

- `excess_detector_b.py`
- `engine_b_runner.py`
- `engine_b_runner_support.py`
- `engine_b_runtime_support.py`

Docs say S1 VPIN-fade is a B sub-signal, but the current code had no explicit local semantic surface for it.

## Placement

No new `.py` was created in `src/engines/engine_b/`. The sub-signal is wired into the existing excess stage and propagated via existing output/runtime paths.

## Files Changed

- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented

1. `toxic_flow_fade` is now an explicit B-local semantic tag.
2. The sub-signal activates only when:
   - `vpin_current >= 0.35`
   - `z_score < 0`
   - `abs(z_score) >= z_marginal`
3. The sub-signal is explicitly suppressed when `toxic_flow_correlation > 0.7`.
4. The core excess formula is unchanged.
5. Runtime forecast reason codes now propagate `b.toxic_flow_fade` when active.

## Tests and Proof

- New excess-detector tests cover activation and correlation suppression.
- Runner test covers emit-path propagation.
- Runtime test covers forecast reason-code propagation.
- `python -m py_compile src/engines/engine_b/excess_detector_b.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> pass
- `python -m pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q` -> `88 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No new scoring bonus formula was introduced for `toxic_flow_fade`.
- No calibration seam provider was added yet for the 0.35 / 0.7 thresholds; they remain documented local defaults in the current B slice.

## Risks / Open Questions

- This slice makes the B sub-signal explicit and auditable, but does not yet promote it to a dedicated scored block.
- If later required, any scoring effect should come through a calibrated local B seam, not a shared seam.

## Completion Status

`PARTIAL`

## Next Safe Step

Promote the hardcoded B-local `vpin_toxic` / `max_intra_family_correlation` defaults into a proper calibration seam if and only if the current Engine B local semantics are accepted in shadow.
