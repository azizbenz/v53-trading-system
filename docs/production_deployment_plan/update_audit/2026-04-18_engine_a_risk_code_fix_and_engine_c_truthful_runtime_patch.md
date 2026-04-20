## Scope

- Engine A targeted safety fix in `engine_a_runtime_support.py`
- Engine C additive truthfulness patch on runner/runtime/forecast/refusal

## Governing docs

- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Files changed

- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`

## Claims implemented

- Engine A runtime risk reason extraction now tolerates `dominant_reason_code=None` or blank without unsafe `.strip()`.
- Engine C output now carries stable structured `reason_codes`.
- Engine C forecast enriched rail now carries truthful `reason_codes`, `conditioning_state`, and a stable `invalidation_ref`.
- Engine C downstream runtime states are explicit on the enriched rail for:
  - `HARD_BLOCKED`
  - `REJECTED_RANKING`
  - `REJECTED_PORTFOLIO`
  - `RISK_REJECTED`
  - `RISK_REDUCED`
  - `RISK_OBSERVE_ONLY`
- `HOOK_BLOCKED` now prefers stable structured runtime codes over free-text fallback.
- No canonical `SignalCandidate` change.
- No fake blocked trade.
- No `side="flat"`.

## Boundary kept

- `break_even_filter` was not turned into a second hard gate on the canonical decision contract.
- local duplication policy remains in the runner for pre-emit local economics
- native cross-engine coordination remains in runtime via `engine_coordination_rules`

## Verification

- `python -m pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_c/test_invalidation_mapper_c.py tests/test_engines/test_engine_c/test_output_payload_builder_c.py`
- result: `58 passed`
- `python -m py_compile ...targeted files...`
- result: pass
- `python scripts/run_engineering_guardrails.py`
- result: `new_violations=0`

## Deferred

- no economics seam harmonization for Engine C beyond additive truthfulness
- no canonical contract widening
- no coordination redesign

## Status

- `DONE`
