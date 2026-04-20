# 2026-04-17 - Engine A runtime risk event alignment

## Governing Inputs
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_a/engine_a_runtime.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`

## Claims Implemented
- Engine A runtime risk observability is now aligned with final status:
  - `engine_a_risk_rejected`
  - `engine_a_risk_reduced`
  - `engine_a_risk_observe_only`
- Trade logic is unchanged; only runtime event naming and proof coverage were tightened.

## Fail-First Evidence
- Before this patch, `RISK_REDUCED` and `RISK_OBSERVE_ONLY` still logged `engine_a_risk_rejected`.
- The new tests would have failed on the previous code because they require status-specific event names and absence of the rejected event in the reduced/observe-only branches.

## Tests And Proof
- `python -m py_compile src/engines/engine_a/engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- Engine A still needs a broader local-richness review against docs 20/23/24, especially around A-specific structure/cost/microstructure semantics rather than just runtime guardrails.
