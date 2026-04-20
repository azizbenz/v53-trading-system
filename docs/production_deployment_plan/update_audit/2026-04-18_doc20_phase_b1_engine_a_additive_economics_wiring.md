# 2026-04-18 - doc20 Phase B1 - Engine A additive economics wiring

## Docs governants
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

## Current code seam
- Canonical historical contract unchanged: `src/interface_contracts/decision_contracts.py`
- Additive enriched seam preserved: `src/interface_contracts/forecast_contracts.py`
- Economics seams reused:
  - `src/scoring_backbone/forecast_normalizer.py`
  - `src/scoring_backbone/break_even_filter.py`
- Engine A runtime adapter seam:
  - `src/engines/engine_a/engine_a_runtime_support.py`
  - `src/engines/engine_a/engine_a_runtime.py`

## Files changed
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`

## Claims implemented
1. `forecast_normalizer.py` is now genuinely wired into the additive Engine A forecast contract.
   - `forecast_strength` no longer uses the prior `raw_score * 20` heuristic.
   - normalization uses additive economics only:
     - expected return = `expected_gain - expected_cost`
     - volatility proxy priority:
       - `realized_kernel_vol_scale`
       - else `atr / entry_price`
       - else `delta_safe` fallback
2. `break_even_filter.py` is wired additively, not as a second hard gate.
   - it enriches:
     - `conditioning_state`
     - `reason_codes`
     - `refusal_record.reason_codes` when economics context is real
   - it does not block or rewrite the canonical `SignalCandidate`
3. Runtime refusal semantics are now downstream-aware of additive economics.
   - cost-based no-trade refusals can carry both:
     - engine-local cost reason codes
     - additive economics break-even reason codes
4. `risk_reduced` and `risk_observe_only` remain explicit runtime statuses.
   - the historical runtime contract is unchanged
   - when `strategy_id` is present, the additive forecast contract still propagates on those paths

## Explicit non-claims
- no widening of `decision_contracts.SignalCandidate`
- no fake blocked trade
- no `side="flat"`
- no new shared helper extracted in Phase C
- no runner rewrite

## Fail-first evidence
- before this patch, `tests/test_engines/test_engine_a/test_engine_a_runtime.py` failed with:
  - `_build_runtime_refusal_record() missing 1 required keyword-only argument: 'engine_inputs'`
  - `reason_codes must not contain blank values`

## Tests and proof
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - result: `24 passed`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - result: `37 passed`
- `python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - result: pass
- `python scripts/run_engineering_guardrails.py`
  - result: `new_violations=0`

## Deferred / not done
- Engine B equivalent Phase B wiring
- any shared forecast adapter helper
- any shared refusal builder helper
- additive economics wiring for C/D

## Completion status
- `DONE`

## Next safe step
1. apply the same bounded wiring to `engine_b_runtime_support.py`
2. only after A/B are both stable, measure real duplication
3. extract a shared helper only if duplication is concrete and useful
