# 2026-04-17 - Engine A realized-kernel structure seam

## Governing Inputs
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_a/structure_detector_a.py`
- `src/engines/engine_a/engine_a_runner.py`
- `tests/test_engines/test_engine_a/test_engine_a.py`

## Claims Implemented
- Engine A now exposes an explicit local seam for realized-kernel-driven structure truth through:
  - `EngineAInput.realized_kernel_vol_scale`
  - `StructureInput.realized_kernel_vol_scale`
- No new structure equation was introduced.
- Engine A lands realized-kernel volatility as an explicit source for the existing `trend_stability` channel:
  - if absent, legacy `trend_stability` is preserved
  - if present, `realized_kernel_vol_scale` becomes the effective `trend_stability` used by the existing structure weights
- Audit surfaces are explicit:
  - `StructureResult.block_scores`
  - `trend_stability`
  - `trend_stability_legacy_score`
  - `trend_stability_source_is_realized_kernel`
  - `realized_kernel_vol_scale` when present
- Runner structure logs now carry the structure block scores.

## Fail-First Evidence
- Before this slice, Engine A had no explicit realized-kernel landing despite doc 23 naming Engine A as a consumer for vol scaling.
- Before this slice, there was no way to prove whether Engine A structure truth came from a legacy trend-stability score or a realized-kernel-derived scale.
- The new tests would fail on prior code because:
  - `StructureInput` had no `realized_kernel_vol_scale`
  - `EngineAInput` had no `realized_kernel_vol_scale`
  - `StructureResult` had no structure-level block-score trace

## Tests And Proof
- `python -m py_compile src/engines/engine_a/structure_detector_a.py src/engines/engine_a/engine_a_runner.py tests/test_engines/test_engine_a/test_engine_a.py`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- This slice does not derive `realized_kernel_vol_scale` from raw `RealizedKernelVolRecord.value` inside Engine A.
- Engine A now has explicit local seams for:
  - OFI -> conviction flow
  - Kyle lambda -> cost uplift
  - realized kernel -> structure truth / vol-aware stability
