# 2026-04-17 - Engine A OFI-first local conviction seam

## Governing Inputs
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_a/conviction_builder_a.py`
- `src/engines/engine_a/engine_a_runner.py`
- `tests/test_engines/test_engine_a/test_engine_a.py`

## Claims Implemented
- Engine A now exposes an explicit OFI-first local seam through:
  - `EngineAInput.ofi_flow_score`
  - `ConvictionInput.ofi_flow_score`
- No new conviction equation was introduced.
- OFI is landed as an explicit source for the existing `flow` channel in Engine A conviction:
  - if `ofi_flow_score` is absent, legacy `flow_score` is preserved
  - if `ofi_flow_score` is provided, it becomes the effective `flow` component used by the existing conviction weights
- Audit traces are explicit in `block_scores`:
  - `flow`
  - `flow_legacy_score`
  - `flow_source_is_ofi`
  - `ofi_flow_score` when provided

## Fail-First Evidence
- Before this slice, Engine A had no explicit local OFI seam despite doc 23 naming Engine A conviction as a consumer.
- Before this slice, there was no way to prove in the runner output whether the flow channel came from a generic legacy score or an OFI-derived score.
- The new tests would fail on prior code because:
  - `ConvictionInput` had no `ofi_flow_score`
  - `EngineAInput` had no `ofi_flow_score`
  - `block_scores` had no OFI-source trace

## Tests And Proof
- `python -m py_compile src/engines/engine_a/conviction_builder_a.py src/engines/engine_a/engine_a_runner.py tests/test_engines/test_engine_a/test_engine_a.py`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- This slice does not normalize raw OFI inside Engine A; it lands a bounded OFI-derived seam only.
- Engine A still needs later local-richness work for:
  - Kyle lambda -> cost feasibility
  - realized kernel vol -> vol scaling / structure truth
