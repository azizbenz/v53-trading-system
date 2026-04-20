## Engine C coordination-required and score-parity slice

**Date**: 2026-04-19  
**Scope**: Engine C runtime / forecast / refusal truthfulness, additive only

### Docs Governants

- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

### Current Code Seam

- Canonical decision rail unchanged:
  - `src/engines/engine_c/engine_c_runner.py`
  - `src/engines/engine_c/engine_c_runtime.py`
- Additive runtime/forecast seams:
  - `src/engines/engine_c/engine_c_runtime_support.py`
  - `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- Local duplication observability:
  - `src/engines/engine_c/structure_resolver_c.py`
  - `src/engines/engine_c/output_payload_builder_c.py`

### Files Changed

- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/structure_resolver_c.py`
- `src/engines/engine_c/output_payload_builder_c.py`
- `src/engines/engine_c/cost_feasibility_c.py`
- `src/engines/engine_c/continuation_validator_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py`
- `tests/test_engines/test_engine_c/test_structure_resolver_c.py`
- `tests/test_engines/test_engine_c/test_output_payload_builder_c.py`

### Claims Implemented

- Engine C runtime now treats missing `coordination_input` on the emit rail as a governed hard block, not a silent best-effort bypass.
- Canonical A/C hard-block remains runtime-only through `engine_coordination_rules`; local duplication stays observability-only.
- Runtime reason codes now distinguish:
  - `engine_c.runtime.coordination_input_missing`
  - `engine_c.runtime.coordination_required`
  - `engine_c.runtime.coordination_blocked`
  - `engine_c.duplication.local_policy_triggered`
- Score truth is now closed on the correct local surface:
  - `scoring_audit.raw_score_result.base_raw_score`
  - matches `engine_output.penalized_score`
  - not the pre-penalty `engine_output.raw_score`
- Engine C emit block scores now expose the runner score components needed for parity:
  - `breakout`
  - `continuation`
  - `context`
  - `ce_component`
  - `fake_breakout_risk`
- `local_duplication_policy_triggered` is now the truthful field; `duplication_blocked` remains as backward-compatible alias.
- Calibration hygiene was tightened only additively via `TO_CALIBRATE` naming; no `CalibrationLoader` wiring was introduced.

### Tests and Proof

```text
rtk pytest -q tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_c/test_structure_resolver_c.py tests/test_engines/test_engine_c/test_output_payload_builder_c.py tests/test_protocols/test_engine_coordination_rules.py
-> Pytest: 59 passed

rtk pytest -q tests/test_engines/test_engine_c
-> Pytest: 87 passed

rtk pytest -q tests/test_protocols/test_engine_coordination_rules.py
-> Pytest: 8 passed

$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile src/engines/engine_c/cost_feasibility_c.py src/engines/engine_c/conviction_builder_c.py src/engines/engine_c/invalidation_mapper_c.py src/engines/engine_c/output_payload_builder_c.py src/engines/engine_c/structure_resolver_c.py src/engines/engine_c/continuation_validator_c.py src/engines/engine_c/engine_c_runner.py src/engines/engine_c/engine_c_runner_support.py src/engines/engine_c/engine_c_runtime.py src/engines/engine_c/engine_c_runtime_support.py src/engines/engine_c/engine_c_runtime_forecast_support.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py tests/test_engines/test_engine_c/test_structure_resolver_c.py tests/test_engines/test_engine_c/test_output_payload_builder_c.py
-> pass

python scripts/run_engineering_guardrails.py
-> new_violations=0
```

### Deferred / Not Done

- No auto-population of `coordination_input` was introduced. The runtime now blocks when it is missing; the caller still owns supplying the governed coordination fact set.
- No final `realized_vol_at_break` invalidation model was introduced.
- No `CalibrationLoader` wiring was introduced.
- `duplication_blocked` is still present as compatibility alias and has not yet been fully removed from the public payload.

### Completion Status

`DONE`

Reason:

`The runtime now enforces governed coordination on the emit rail, score parity is closed against the true local Engine C score surface, local duplication is demoted to observability, and the targeted Engine C verification suite is green with guardrails unchanged.`

### Next Safe Step

`Move to the next Engine C slice only if upstream orchestration is ready to provide coordination facts everywhere on governed rails; otherwise the next highest-value work is the separate CalibrationLoader migration for the TO_CALIBRATE threshold bundles.`
