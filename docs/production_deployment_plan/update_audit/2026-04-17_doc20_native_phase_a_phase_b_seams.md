# 2026-04-17 — doc20 native migration — Phase A/B seams

## Governing docs
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

## Current code seam
- Canonical historical runtime contract remains `src/interface_contracts/decision_contracts.py`
- Additive enriched seam remains `src/interface_contracts/forecast_contracts.py`
- A/B runtime adapters remain in:
  - `src/engines/engine_a/engine_a_runtime_support.py`
  - `src/engines/engine_b/engine_b_runtime_support.py`
- New economics seams landed in:
  - `src/scoring_backbone/forecast_normalizer.py`
  - `src/scoring_backbone/break_even_filter.py`

## Files changed
- `src/interface_contracts/forecast_contracts.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `src/scoring_backbone/__init__.py`
- `src/scoring_backbone/forecast_normalizer.py`
- `src/scoring_backbone/break_even_filter.py`
- `tests/test_interface_contracts/test_forecast_contracts.py`
- `tests/test_scoring_backbone/test_forecast_normalizer.py`
- `tests/test_scoring_backbone/test_break_even_filter.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims implemented
1. The additive forecast seam is more native and less divergent:
   - shared helper for additive forecast version map
   - shared helper for scoring conditioning records
   - shared helper for normalized/deduplicated reason codes
2. `ForecastSignalCandidate` is more defensive:
   - `expected_ce` must be finite
   - `expected_gain` must be finite
3. doc20 economics seams now exist in the real repo paths mandated by doc24:
   - `forecast_normalizer.py`
   - `break_even_filter.py`
4. `scoring_backbone/__init__.py` exports those seams without introducing a parallel stack.

## Explicit non-claims
- `decision_contracts.SignalCandidate` was not widened.
- No fake `side="flat"` path was added.
- No blocked emission was modeled as a fake trade.
- No `meta_engine/*` path was created.
- `break_even_filter` was **not** wired into A/B runtime adapters on this cut.

## Why `break_even_filter` was not wired yet
Fail-first check showed that the naive wiring simply duplicated the existing engine cost verdict and did not create a distinct governed behavior on the current A/B rails. That would have been decorative, not native.

Current boundary:
- seam exists and is tested
- engine wiring is deferred until:
  - refusal/native no-emit observability is wired, or
  - a distinct economics decision boundary exists beyond the current engine-local cost verdict

## Tests and proof
- `python -m py_compile src/interface_contracts/forecast_contracts.py src/scoring_backbone/forecast_normalizer.py src/scoring_backbone/break_even_filter.py src/scoring_backbone/__init__.py src/engines/engine_a/engine_a_runtime_support.py src/engines/engine_b/engine_b_runtime_support.py tests/test_interface_contracts/test_forecast_contracts.py tests/test_scoring_backbone/test_forecast_normalizer.py tests/test_scoring_backbone/test_break_even_filter.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `rtk pytest -q tests/test_interface_contracts/test_forecast_contracts.py tests/test_interface_contracts/test_strategy_identity.py tests/test_scoring_backbone/test_forecast_normalizer.py tests/test_scoring_backbone/test_break_even_filter.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
  - result: `71 passed`
- `python scripts/run_engineering_guardrails.py`
  - result: `new_violations=0`

## Residual / deferred
- A runtime regression tests were not extended in this slice because the current worktree has deleted `tests/test_engines/test_engine_a/*` sources; no re-creation was done to avoid clashing with concurrent work.
- C/D enriched forecast migration remains deferred.
- Refusal-native propagation from engine no-trade/no-emit remains deferred.
- `engine_coordination_rules.py` remains deferred.

## Completion status
- `PARTIAL`

## Next safe step
1. Wire `RefusalRecord` / `RefusalJournal` from engine/runtime no-trade and no-emit surfaces.
2. After refusal-native observability exists, re-open A/B economics wiring for the additive forecast rail only if it creates a distinct, auditable boundary.
3. Then land `engine_coordination_rules.py` in `src/protocols/`.
