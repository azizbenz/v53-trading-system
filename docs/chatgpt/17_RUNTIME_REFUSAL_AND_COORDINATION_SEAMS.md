# 17_RUNTIME_REFUSAL_AND_COORDINATION_SEAMS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-17_doc20_phase_c_ab_runtime_refusal_seam.md
- docs/production_deployment_plan/update_audit/2026-04-17_doc20_phase_d_engine_coordination_rules.md
- docs/production_deployment_plan/update_audit/2026-04-17_doc20_phase_d_cd_runtime_coordination_and_refusal.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_doc20_phase_c_ab_runtime_refusal_seam.md

"""Doc20 native migration - Phase C refusal seam for Engine A/B runtimes."""

Date: 2026-04-17
Status: COMPLETE

Docs gouvernants:
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

Code seam reel:
- `src/interface_contracts/refusal_records.py`
- `src/meta_minimal/refusal_journal/refusal_journal.py`
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`

Claims implemented:
- Engine A runtime can now emit governed `RefusalRecord` objects on:
  - `NO_TRADE`
  - `CIRCUIT_BREAKER_BLOCKED`
  - `HOOK_BLOCKED`
  - `HARD_BLOCKED`
  - `REJECTED_RANKING`
  - `REJECTED_PORTFOLIO`
  - `RISK_REJECTED`
- Engine B runtime now exposes the same refusal-native behavior.
- The refusal seam is additive:
  - no widening of the historical canonical `SignalCandidate`
  - no fake trade emission
  - no runner rewrite
- Runtime results now expose `refusal_record` explicitly.
- Runtime constructors accept an optional governed refusal sink compatible with `RefusalJournalSink`.

Category mapping applied:
- `NO_TRADE` -> `RefusalCategory.NO_TRADE`
- `CIRCUIT_BREAKER_BLOCKED` -> `RefusalCategory.HARD_BLOCK`
- `HOOK_BLOCKED` -> `RefusalCategory.HARD_BLOCK`
- `HARD_BLOCKED` -> `RefusalCategory.HARD_BLOCK`
- `REJECTED_RANKING` -> `RefusalCategory.NO_TRADE`
- `REJECTED_PORTFOLIO` -> `RefusalCategory.PORTFOLIO_REJECTED`
- `RISK_REJECTED` -> `RefusalCategory.HARD_BLOCK`

Reason-code policy:
- prefer existing engine/runtime machine reason codes
- prefer hard-block encoded codes from Build-5 when available
- prefer Build-4 risk dominant/detail codes when available
- fall back only to stable runtime-scoped codes such as:
  - `engine_a.runtime.rejected_portfolio`
  - `engine_b.runtime.rejected_ranking`

Files changed:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`

Tests and proof:
- `python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py src/engines/engine_b/engine_b_runtime.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
- `rtk pytest -q tests/test_meta_minimal/test_refusal_journal.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
  - `70 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Deferred / not done:
- refusal conditioning summaries for non-emitted runtime paths
- wiring refusal-native behavior into Engine C/D runtimes
- promotion/shadow aggregation on refusal journals
- coordination-layer consumption of refusal records

Next safe step:
- keep doc20 Phase C additive and wire refusal-native behavior into shared reporting/aggregation,
  or open Phase D with `protocols/engine_coordination_rules.py`


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_doc20_phase_d_engine_coordination_rules.md

"""Doc20 native migration - Phase D engine coordination rules seam."""

Date: 2026-04-17
Status: PARTIAL

Docs gouvernants:
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

Code seam reel:
- `src/protocols/engine_coordination_rules.py`
- `src/protocols/closed_episode_journal.py`
- `src/interface_contracts/forecast_contracts.py`
- `src/interface_contracts/refusal_records.py`

Claims implemented:
- Added a native typed coordination seam in the mandated package:
  - `EngineCoordinationInput`
  - `EngineCoordinationThresholds`
  - `EngineCoordinationOutcome`
  - `evaluate_engine_coordination`
- Implemented the additive rule surface for:
  - `R-AC-1` A holding -> C hard block
  - `R-AC-2` recent A fire on same setup -> C hard block
  - `R-D-1` missing or mismatched historical linkage -> D hard block
  - `R-D-2` consecutive D stops reset-required -> D hard block
  - `R-D-3` explicit failsafe override after expiry -> D permit
  - `R-D-4` D size multiplier -> `0.5`
- Hard-block outcomes emit:
  - `ConditioningRecord(family=HARD_BLOCK, ...)`
  - `RefusalRecord(category=HARD_BLOCK, ...)`
- Permit outcomes do not create fake refusals.

Design boundary:
- The seam does **not** infer “same structural setup”.
- The seam does **not** infer whether the failsafe override was already consumed once.
- Both judgments remain explicit inputs:
  - `recent_a_fire_same_setup_at_ns`
  - `d_failsafe_override_available`

This keeps the module additive and honest instead of freezing hidden state logic in the wrong layer.

Files changed:
- `src/protocols/engine_coordination_rules.py`
- `src/protocols/__init__.py`
- `tests/test_protocols/test_engine_coordination_rules.py`

Tests and proof:
- `python -m py_compile` with `PYTHONPYCACHEPREFIX=.test_tmp/pycache`
- `rtk pytest -q tests/test_protocols/test_closed_episode_journal.py tests/test_protocols/test_engine_coordination_rules.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
  - `65 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Deferred / not done:
- direct runtime wiring into C and D
- persistent one-shot tracking for `R-D-3` override consumption
- A/C setup-hash resolution upstream
- portfolio arbitration record integration

Next safe step:
- wire `engine_coordination_rules` into C/D runtime support with refusal journaling and no fake candidate emission,
  only after explicit upstream inputs for setup identity and failsafe-slot state are available


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_doc20_phase_d_cd_runtime_coordination_and_refusal.md

# 2026-04-17 - Doc20 Phase D - Engine C/D runtime coordination and refusal wiring

## Governing docs
- doc 28: arbitration law
- doc 24: real placement map
- doc 20: doctrinal coordination target
- doc 25/26: audit protocol and pack template

## Scope
- additive runtime-only wiring for Engine C and Engine D
- no runner rewrite
- no fake blocked trades
- no inferred setup identity

## Files changed
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## Claims implemented
- Engine C runtime accepts optional `coordination_input` and evaluates native coordination before hook/scoring.
- Engine D runtime accepts optional `coordination_input` and applies native coordination before hook/scoring.
- C/D hard-block coordination produces `HARD_BLOCKED` without emitting a fake trade.
- C/D runtime results now expose `coordination_outcome` and `refusal_record`.
- C/D runtimes accept an optional `refusal_sink` and write governed `RefusalRecord`s on blocked/no-trade statuses.
- Engine D coordination size reduction propagates into the effective runtime size used by risk evaluation.

## Explicit boundary
- The runtime does not infer “same setup”.
- The runtime does not infer D failsafe one-shot consumption.
- These remain explicit upstream inputs inside `EngineCoordinationInput`.

## Tests added
- Engine C: coordination hard-block refusal journaling
- Engine C: coordination engine-id mismatch validation
- Engine D: coordination hard-block refusal journaling
- Engine D: coordination size reduction reaches the risk candidate

## Proof checklist
- targeted pytest on Engine C/D runtime
- `py_compile`
- guardrails

## Status
- `PARTIAL_COMPLETE`
- next safe step: if needed, expose the same coordination/native refusal seam to forecast-facing C/D runtime artifacts without widening the canonical decision contract


