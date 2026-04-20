# 2026-04-17 Engine A Prompt Correction Hardening

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>)
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>)
- [25_UPDATE_AUDIT_PROTOCOL.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md>)
- [26_UPDATE_AUDIT_PACK_TEMPLATE.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md>)
- [28_ARBITRATION_PROTOCOL_OPUS_CODEX.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md>)
- [V53_PROMPT_CORRECTION_ENGINE_A.md](</E:/claude  v5.3/modernisation de v5.3/V53_PROMPT_CORRECTION_ENGINE_A.md>)

## Current Code Seam

- Engine A canonical runner/runtime rail remains:
  `runner -> scoring -> ranking -> risk`
- Existing non-regression guards were preserved:
  - `direction_score <= 0`
  - `candidate_size <= 0`
  - `holding_period <= 0`
  - `entry_price <= 0`
  - `atr < 0`
  - `LOW conviction` non-emittable
  - blank `scoring_version` rejected in runtime

## Files Changed

- [cost_feasibility_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/cost_feasibility_a.py>)
- [context_validator_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/context_validator_a.py>)
- [conviction_builder_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/conviction_builder_a.py>)
- [structure_detector_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/structure_detector_a.py>)
- [invalidation_mapper_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/invalidation_mapper_a.py>)
- [signal_reporter_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/signal_reporter_a.py>)
- [engine_a_runner_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runner_support.py>)
- [engine_a_runner.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runner.py>)
- [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)
- [test_engine_a.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a.py>)
- [test_engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a_runtime.py>)

## Claims Implemented

- `CostVerdict.MARGINAL` remains distinct, but is now explicitly non-emittable through `CostResult.is_emittable=False` and runner blocking.
- `engine_a.cost.non_positive_ev_net` exists as an explicit guarded path when `delta_safe == 0` and EV is not positive.
- Score-like input contracts are now bounded in:
  - `EngineAInput`
  - `StructureInput`
  - `ContextInput`
  - `ConvictionInput`
- `EngineARuntimeInput` now defends:
  - `projected_size > 0`
  - `projected_loss >= 0`
  - `current_equity > 0`
  - `session_peak_equity > 0`
  - `max_selections >= 1`
- `build_invalidation()` now rejects invalid isolated helper inputs and documents the `atr == 0` no-price-level policy explicitly.
- Engine A output now carries stable `reason_codes` for no-trade and emit paths.
- Forecast additive contract is richer:
  - conditioning state now includes structure/context/cost/tier/invalidation presence
  - forecast reason codes now include engine verdicts plus scoring penalties
- `signal_reporter_a.py` status is explicit and aligned with the Engine B pattern.
- `engine_a_runner.py` was reduced below the guardrail limit by extracting pure tuple/log helpers into `engine_a_runner_support.py`, with no behavioral bypass.

## Tests and Proof

- `python -m py_compile src/engines/engine_a/cost_feasibility_a.py src/engines/engine_a/context_validator_a.py src/engines/engine_a/conviction_builder_a.py src/engines/engine_a/structure_detector_a.py src/engines/engine_a/invalidation_mapper_a.py src/engines/engine_a/signal_reporter_a.py src/engines/engine_a/engine_a_runner_support.py src/engines/engine_a/engine_a_runner.py src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py` -> pass
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py` -> `130 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No `forecast_normalizer.py` inserted yet.
- No `break_even_filter.py` inserted yet.
- No `RefusalRecord / RefusalJournal` seam inserted yet.
- No upstream microstructure assembler added in this slice; the focus stayed on internal Engine A hardening from the correction brief.

## Completion Status

`COMPLETE`

## Next Safe Step

Next safe step is no longer another blind A-local tweak. It is either:

1. formalize the doc 20 shared economic seams (`forecast_normalizer`, `break_even_filter`, refusal record rail), then land them additively on A;
2. or run the same fail-first hardening pass on the next engine with a correction brief, without inventing new theory.
