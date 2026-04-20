# 2026-04-18 - Engine A runtime downstream truthfulness

## Docs governants
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current code seam
- Canonical contract unchanged: `src/interface_contracts/decision_contracts.py`
- Additive forecast contract unchanged: `src/interface_contracts/forecast_contracts.py`
- Engine A runtime seam:
  - `src/engines/engine_a/engine_a_runtime.py`
  - `src/engines/engine_a/engine_a_runtime_support.py`

## Files changed
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py`

## Claims implemented
1. Downstream runtime statuses now annotate the additive forecast contract truthfully.
   - `HARD_BLOCKED`
   - `REJECTED_RANKING`
   - `REJECTED_PORTFOLIO`
   - `RISK_REJECTED`
   - `RISK_REDUCED`
   - `RISK_OBSERVE_ONLY`
2. The historical `SignalCandidate` is unchanged.
3. No fake blocked trade path was introduced.
4. No `side="flat"` path was introduced.
5. `HOOK_BLOCKED` now prefers stable reason codes over free-text detail fallback.
6. No fake blocked trade path and no fake flat-side path were reintroduced in the covered runtime branches.

## Policy decisions
- `RISK_REDUCED` and `RISK_OBSERVE_ONLY` remain governed non-refusal statuses.
- They do not emit `RefusalRecord`.
- They do enrich `forecast_signal_candidate.reason_codes` and `conditioning_state`.
- `RISK_REJECTED` remains a refusal-producing hard block.

## Tests and proof
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - result: `26 passed`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - result: `39 passed`
- `python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - result: pass
- `python scripts/run_engineering_guardrails.py`
  - result: `new_violations=0`

## Deferred / not done
- no shared helper extraction yet
- no Engine B/C/D changes
- no widening of the canonical decision contract
- no runtime-native coordination changes

## Completion status
- `DONE`
