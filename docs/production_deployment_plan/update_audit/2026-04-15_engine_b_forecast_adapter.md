# 2026-04-15 Engine B Forecast Adapter

## Objective

Wire the second additive forecast adapter on Engine B without replacing the canonical decision signal contract and without inventing a `strategy_id`.

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§3.1`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) `§3.3`, `§5`
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R22`, `R23`, `R24`, `R26`, `Bloc 10`

## Current Code Seam

- Canonical file today: [decision_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/decision_contracts.py>)
- Engine runtime seam: [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- Forbidden shortcut for this slice: no canonical contract replacement, no fake `strategy_id`, no `side="flat"`

## Placement

- Target runtime files: [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>) and [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- Actual landing decision: keep the forecast mapping in the existing Engine B support module because file size remains below guardrail thresholds and the helper seam already lives there

## Files Changed

- [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- [test_engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b_runtime.py>)

## Claims Implemented

- `EngineBRuntimeInput` accepts optional `strategy_id` and rejects blank values -> [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- `EngineBRuntimeResult` exposes optional `forecast_signal_candidate` while preserving the canonical `signal_candidate` -> [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- Engine B maps its canonical signal into an additive `ForecastSignalCandidate` only when `strategy_id` is explicitly provided -> [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- Engine B forecast mapping uses `BetStructure.MEAN_REVERT`, real cost/gain fields, real invalidation text, and runtime scoring penalties -> [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- Test harness is normalized to `repo_tmp_path` to stay executable in this repo sandbox -> [test_engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b_runtime.py>)

## Tests and Proof

- `python -m py_compile src/engines/engine_b/engine_b_runtime.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> pass
- `python -m pytest tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_interface_contracts/test_forecast_contracts.py -q` -> `32 passed`
- `python -m pytest tests/test_interface_contracts/test_all_contracts.py tests/test_interface_contracts/test_forecast_contracts.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q` -> `95 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`, `total_violations=3537`

## Deferred / Not Done

- No Engine C adapter yet
- No Engine D adapter yet
- No cross-repo canonical `strategy_identity` seam yet

## Risks / Open Questions

- `strategy_id` still enters at runtime input level, not yet through a broader canonical contract
- Future adapters should continue reusing the existing forecast contract seam rather than creating engine-local variants

## Completion Status

`COMPLETE`

Reason:

`Targeted engine tests, broader interface/runtime proof, and guardrails are all green with no new violations.`

## Next Safe Step

`Proceed to Engine C only if a real strategy_id seam is available there too; otherwise formalize strategy identity before wider propagation.`
