# Engine B score parity and truthfulness patch

**Date**: 2026-04-19  
**Scope**: Engine B runner/runtime parity, reason-code hardening, invalidation guards

## Docs Governants

- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

- canonical runner: `src/engines/engine_b/engine_b_runner.py`
- runtime scoring bridge: `src/engines/engine_b/engine_b_runtime_support.py`
- additive forecast seam: `src/engines/engine_b/engine_b_runtime_forecast_support.py`
- invalidation seam: `src/engines/engine_b/invalidation_mapper_b.py`

## Files Changed

- `src/engines/engine_b/engine_b_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime_forecast_support.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/invalidation_mapper_b.py`
- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/anti_breakout_filter_b.py`
- `src/engines/engine_b/cost_feasibility_b.py`
- `src/engines/engine_b/local_mean_estimator_b.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented

- runtime scoring now reconstructs the full Engine B runner feature space instead of the legacy 4-feature subset
- breakout warning penalty duplication is documented as intentional audit alignment, not hidden double logic
- forecast parity conditioning now treats runner-equivalent raw score as the nominal parity surface
- runner no-trade logs now prefer stable reason codes over generic human summaries
- invalidation builder now carries stable fallback reason codes and explicit defensive guards
- runner-facing default thresholds are more clearly consolidated for later calibration-loader migration

## Tests and Proof

- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
  - `139 passed`
- `rtk pytest -q tests/test_engines/test_engine_b`
  - `141 passed`
- `python -m py_compile src/engines/engine_b/engine_b_runtime_support.py src/engines/engine_b/engine_b_runtime_forecast_support.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/excess_detector_b.py src/engines/engine_b/anti_breakout_filter_b.py src/engines/engine_b/cost_feasibility_b.py src/engines/engine_b/invalidation_mapper_b.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
  - `pass`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

## Deferred / Not Done

- signed `CalibrationLoader` wiring for Engine B thresholds
- any change to the canonical `SignalCandidate`
- any runtime hard gate beyond the existing runner/risk/scoring rail

## Completion Status

`DONE`

## Next Safe Step

Patch the remaining Engine B calibration seam:

1. branch runner-facing defaults to a signed loader
2. keep the runtime parity tests fixed as non-regression proof
3. avoid changing the canonical runner/risk contract while doing so
