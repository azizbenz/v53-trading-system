## Engine C additive economics / coordination / duplication governance

### Docs governants
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

### Current code seam
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/structure_resolver_c.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/invalidation_mapper_c.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/cost_feasibility_c.py`
- `src/engines/engine_c/continuation_validator_c.py`

### Files changed
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/structure_resolver_c.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/invalidation_mapper_c.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/cost_feasibility_c.py`
- `src/engines/engine_c/continuation_validator_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_invalidation_mapper_c.py`

### Claims implemented
- Forecast strength no longer uses `penalized_score * 20`; Engine C forecast uses the additive normalizer seam and is clipped by config to `[0, 15]`.
- Additive break-even semantics are wired into Engine C forecast via `break_even_filter`, including conditioning and structured reason codes.
- Engine C forecast now distinguishes local engine score from downstream runtime score in conditioning state.
- Local duplication heuristics remain visible, but no longer act as a runner-side substitute for doctrinal A/C hard-blocks.
- Canonical A/C hard-block semantics remain in `engine_coordination_rules` at runtime.
- Engine C invalidation is now explicitly marked as a transitional ATR-proxy seam, not a falsely claimed realized-vol final model.
- Invalidation failures now carry finer structured reason codes; `INVALID_BREAKOUT_LEVEL` is no longer the only catch-all path.
- Threshold defaults are grouped into `TO_CALIBRATE` blocks instead of staying fully scattered.

### Tests and proof
- `rtk pytest -q tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_c/test_structure_resolver_c.py tests/test_engines/test_engine_c/test_invalidation_mapper_c.py tests/test_engines/test_engine_c/test_output_payload_builder_c.py tests/test_protocols/test_engine_coordination_rules.py`
  - `63 passed`
- `python -m py_compile src/engines/engine_c/engine_c_runtime_forecast_support.py src/engines/engine_c/engine_c_runtime.py src/engines/engine_c/engine_c_runtime_support.py src/engines/engine_c/structure_resolver_c.py src/engines/engine_c/engine_c_runner_support.py src/engines/engine_c/invalidation_mapper_c.py src/engines/engine_c/engine_c_runner.py src/engines/engine_c/cost_feasibility_c.py src/engines/engine_c/continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_c/test_structure_resolver_c.py tests/test_engines/test_engine_c/test_invalidation_mapper_c.py tests/test_engines/test_engine_c/test_output_payload_builder_c.py`
  - pass
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

### Deferred / not done
- Final realized-vol-at-break invalidation model is not implemented because the upstream input does not exist yet.
- Runtime coordination is still input-driven; this patch removes doctrinal ambiguity, but does not invent a new upstream coordination source.
- CalibrationLoader wiring is not implemented here; thresholds are only regrouped and marked `TO_CALIBRATE`.

### Completion status
- `DONE`

### Next safe step
- Wire a governed upstream evidence path for Engine C volatility / coordination inputs, then replace the transitional ATR invalidation seam with the final realized-vol-at-break contract.
