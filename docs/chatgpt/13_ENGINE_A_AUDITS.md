# 13_ENGINE_A_AUDITS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-17_engine_a_runtime_risk_event_alignment.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_a_ofi_first_local_conviction_seam.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_a_kyle_lambda_cost_seam.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_a_realized_kernel_structure_seam.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md
- docs/production_deployment_plan/update_audit/2026-04-18_doc20_phase_b1_engine_a_additive_economics_wiring.md
- docs/production_deployment_plan/update_audit/2026-04-18_engine_a_runtime_downstream_truthfulness.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_a_runtime_risk_event_alignment.md

# 2026-04-17 - Engine A runtime risk event alignment

## Governing Inputs
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_a/engine_a_runtime.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`

## Claims Implemented
- Engine A runtime risk observability is now aligned with final status:
  - `engine_a_risk_rejected`
  - `engine_a_risk_reduced`
  - `engine_a_risk_observe_only`
- Trade logic is unchanged; only runtime event naming and proof coverage were tightened.

## Fail-First Evidence
- Before this patch, `RISK_REDUCED` and `RISK_OBSERVE_ONLY` still logged `engine_a_risk_rejected`.
- The new tests would have failed on the previous code because they require status-specific event names and absence of the rejected event in the reduced/observe-only branches.

## Tests And Proof
- `python -m py_compile src/engines/engine_a/engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- Engine A still needs a broader local-richness review against docs 20/23/24, especially around A-specific structure/cost/microstructure semantics rather than just runtime guardrails.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_a_ofi_first_local_conviction_seam.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_a_kyle_lambda_cost_seam.md

# 2026-04-17 - Engine A Kyle lambda cost seam

## Governing Inputs
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_a/cost_feasibility_a.py`
- `src/engines/engine_a/engine_a_runner.py`
- `tests/test_engines/test_engine_a/test_engine_a.py`

## Claims Implemented
- Engine A now exposes an explicit local cost seam for Kyle lambda through:
  - `EngineAInput.kyle_lambda_cost_uplift`
  - `CostInput.kyle_lambda_cost_uplift`
- No new Kyle formula was introduced inside Engine A.
- Engine A consumes an already-normalized cost uplift derived upstream from Kyle lambda and adds it to effective expected cost:
  - `effective_expected_cost = expected_cost + kyle_lambda_cost_uplift`
- Audit surfaces are explicit:
  - `CostResult.base_expected_cost`
  - `CostResult.kyle_lambda_cost_uplift`
  - `CostResult.expected_cost` as effective cost after uplift
  - runner cost log includes `kyle_lambda_cost_uplift=...` when present

## Fail-First Evidence
- Before this slice, Engine A had no explicit local seam for Kyle lambda despite doc 23 naming Engine A cost feasibility as a consumer.
- Before this slice, there was no way for Engine A cost logic to represent a Kyle-derived slippage uplift without silently mutating `expected_cost`.
- The new tests would fail on prior code because:
  - `CostInput` had no `kyle_lambda_cost_uplift`
  - `EngineAInput` had no `kyle_lambda_cost_uplift`
  - there was no explicit audit split between base cost and effective cost

## Tests And Proof
- `python -m py_compile src/engines/engine_a/cost_feasibility_a.py src/engines/engine_a/engine_a_runner.py tests/test_engines/test_engine_a/test_engine_a.py`
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- This slice does not convert raw `KyleLambdaRecord.value` or `normalized_value` into cost uplift inside Engine A.
- The remaining local-richness frontier for A is realized-kernel-driven vol scaling / structure truth.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_a_realized_kernel_structure_seam.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md

# 2026-04-17 Engine A Prompt Correction Hardening

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>)
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>)
- [25_UPDATE_AUDIT_PROTOCOL.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md>)
- [26_UPDATE_AUDIT_PACK_TEMPLATE.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md>)
- [28_ARBITRATION_PROTOCOL_OPUS_CODEX.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md>)
- [V53_PROMPT_CORRECTION_ENGINE_A.md](</E:/claude  v5.3/modernisation de v5.3/V53_PROMPT_CORRECTION_ENGINE_A.md>)

## Current Code Seam

- Engine A canonical runner/runtime rail remains:
  `runner -> scoring -> ranking -> risk`
- Existing non-regression guards were preserved:
  - `direction_score <= 0`
  - `candidate_size <= 0`
  - `holding_period <= 0`
  - `entry_price <= 0`
  - `atr < 0`
  - `LOW conviction` non-emittable
  - blank `scoring_version` rejected in runtime

## Files Changed

- [cost_feasibility_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/cost_feasibility_a.py>)
- [context_validator_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/context_validator_a.py>)
- [conviction_builder_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/conviction_builder_a.py>)
- [structure_detector_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/structure_detector_a.py>)
- [invalidation_mapper_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/invalidation_mapper_a.py>)
- [signal_reporter_a.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/signal_reporter_a.py>)
- [engine_a_runner_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runner_support.py>)
- [engine_a_runner.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runner.py>)
- [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)
- [test_engine_a.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a.py>)
- [test_engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a_runtime.py>)

## Claims Implemented

- `CostVerdict.MARGINAL` remains distinct, but is now explicitly non-emittable through `CostResult.is_emittable=False` and runner blocking.
- `engine_a.cost.non_positive_ev_net` exists as an explicit guarded path when `delta_safe == 0` and EV is not positive.
- Score-like input contracts are now bounded in:
  - `EngineAInput`
  - `StructureInput`
  - `ContextInput`
  - `ConvictionInput`
- `EngineARuntimeInput` now defends:
  - `projected_size > 0`
  - `projected_loss >= 0`
  - `current_equity > 0`
  - `session_peak_equity > 0`
  - `max_selections >= 1`
- `build_invalidation()` now rejects invalid isolated helper inputs and documents the `atr == 0` no-price-level policy explicitly.
- Engine A output now carries stable `reason_codes` for no-trade and emit paths.
- Forecast additive contract is richer:
  - conditioning state now includes structure/context/cost/tier/invalidation presence
  - forecast reason codes now include engine verdicts plus scoring penalties
- `signal_reporter_a.py` status is explicit and aligned with the Engine B pattern.
- `engine_a_runner.py` was reduced below the guardrail limit by extracting pure tuple/log helpers into `engine_a_runner_support.py`, with no behavioral bypass.

## Tests and Proof

- `python -m py_compile src/engines/engine_a/cost_feasibility_a.py src/engines/engine_a/context_validator_a.py src/engines/engine_a/conviction_builder_a.py src/engines/engine_a/structure_detector_a.py src/engines/engine_a/invalidation_mapper_a.py src/engines/engine_a/signal_reporter_a.py src/engines/engine_a/engine_a_runner_support.py src/engines/engine_a/engine_a_runner.py src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py` -> pass
- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py` -> `130 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No `forecast_normalizer.py` inserted yet.
- No `break_even_filter.py` inserted yet.
- No `RefusalRecord / RefusalJournal` seam inserted yet.
- No upstream microstructure assembler added in this slice; the focus stayed on internal Engine A hardening from the correction brief.

## Completion Status

`COMPLETE`

## Next Safe Step

Next safe step is no longer another blind A-local tweak. It is either:

1. formalize the doc 20 shared economic seams (`forecast_normalizer`, `break_even_filter`, refusal record rail), then land them additively on A;
2. or run the same fail-first hardening pass on the next engine with a correction brief, without inventing new theory.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_doc20_phase_b1_engine_a_additive_economics_wiring.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_engine_a_runtime_downstream_truthfulness.md

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


