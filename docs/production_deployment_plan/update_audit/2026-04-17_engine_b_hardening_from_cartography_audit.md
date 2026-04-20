# Engine B Hardening From Cartography Audit

Date: 2026-04-17
Status: COMPLETE

## Governing Inputs
- `E:/claude  v5.3/modernisation de v5.3/V53_CARTOGRAPHIE_ALIGNMENT_ET_AUDIT_ENGINE_B.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_b/cost_feasibility_b.py`
- `src/engines/engine_b/conviction_builder_b.py`
- `src/engines/engine_b/signal_reporter_b.py`
- `src/engines/engine_b/invalidation_mapper_b.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented
- Zero or invalid candidate sizing no longer reaches emit paths.
- `LOW` conviction is no longer emittable in Engine B.
- Engine B no-trade outcomes now distinguish `INVALID_INPUT`, `COST_MARGINAL`, `CONVICTION_LOW`, and `INVALID_INVALIDATION`.
- Invalidation mapping rejects economically absurd inputs instead of silently emitting malformed stop/target contracts.
- `EngineBInput` now bounds normalized score-like fields and core economic inputs.
- `EngineBRuntimeInput` now rejects impossible numeric runtime contracts such as zero size, zero equity, negative peak equity, or zero max selections.

## Fail-First Evidence
- `test_candidate_size_zero_is_not_emittable`
- `test_low_conviction`
- `test_candidate_size_zero_rejected_before_emit`
- `test_current_price_zero_rejected_before_emit`
- `test_runtime_input_rejects_zero_projected_size`

These cases reflected permissive legacy behavior before the hardening patch and now pass under the guarded contract.

## Tests And Proof
- `python -m py_compile src/engines/engine_b/cost_feasibility_b.py src/engines/engine_b/conviction_builder_b.py src/engines/engine_b/signal_reporter_b.py src/engines/engine_b/invalidation_mapper_b.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> `113 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Remaining Calibration Gaps
- Conviction thresholds remain heuristically governed and still need shadow evidence before promotion.
- Breakout, excess, and toxic-flow thresholds remain local to Engine B and need later calibration packs if promoted beyond shadow.
- Engine B is materially safer and more auditable now, but still not promoted to live by this slice alone.
