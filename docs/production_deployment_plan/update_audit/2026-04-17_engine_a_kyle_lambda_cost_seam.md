# 2026-04-17 - Engine A Kyle lambda cost seam

## Governing Inputs
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_a/cost_feasibility_a.py`
- `src/engines/engine_a/engine_a_runner.py`
- `tests/test_engines/test_engine_a/test_engine_a.py`

## Claims Implemented
- Engine A now exposes an explicit local cost seam for Kyle lambda through:
  - `EngineAInput.kyle_lambda_cost_uplift`
  - `CostInput.kyle_lambda_cost_uplift`
- No new Kyle formula was introduced inside Engine A.
- Engine A consumes an already-normalized cost uplift derived upstream from Kyle lambda and adds it to effective expected cost:
  - `effective_expected_cost = expected_cost + kyle_lambda_cost_uplift`
- Audit surfaces are explicit:
  - `CostResult.base_expected_cost`
  - `CostResult.kyle_lambda_cost_uplift`
  - `CostResult.expected_cost` as effective cost after uplift
  - runner cost log includes `kyle_lambda_cost_uplift=...` when present

## Fail-First Evidence
- Before this slice, Engine A had no explicit local seam for Kyle lambda despite doc 23 naming Engine A cost feasibility as a consumer.
- Before this slice, there was no way for Engine A cost logic to represent a Kyle-derived slippage uplift without silently mutating `expected_cost`.
- The new tests would fail on prior code because:
  - `CostInput` had no `kyle_lambda_cost_uplift`
  - `EngineAInput` had no `kyle_lambda_cost_uplift`
  - there was no explicit audit split between base cost and effective cost

## Tests And Proof
- `python -m py_compile src/engines/engine_a/cost_feasibility_a.py src/engines/engine_a/engine_a_runner.py tests/test_engines/test_engine_a/test_engine_a.py`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- This slice does not convert raw `KyleLambdaRecord.value` or `normalized_value` into cost uplift inside Engine A.
- The remaining local-richness frontier for A is realized-kernel-driven vol scaling / structure truth.
