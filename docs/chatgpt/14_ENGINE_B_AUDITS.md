# 14_ENGINE_B_AUDITS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-17_engine_b_toxic_flow_fade_local_subsignal.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_b_hardening_from_cartography_audit.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md
- docs/production_deployment_plan/update_audit/2026-04-17_engine_b_prompt1_explicit_status_and_forecast_proofs.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_b_toxic_flow_fade_local_subsignal.md

## Objective

Implement the B-local `toxic_flow_fade` sub-signal using existing Engine B files only, without creating a new engine and without inventing a new excess formula.

## Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`

## Current Code Seam

Engine B already contains:

- `excess_detector_b.py`
- `engine_b_runner.py`
- `engine_b_runner_support.py`
- `engine_b_runtime_support.py`

Docs say S1 VPIN-fade is a B sub-signal, but the current code had no explicit local semantic surface for it.

## Placement

No new `.py` was created in `src/engines/engine_b/`. The sub-signal is wired into the existing excess stage and propagated via existing output/runtime paths.

## Files Changed

- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented

1. `toxic_flow_fade` is now an explicit B-local semantic tag.
2. The sub-signal activates only when:
   - `vpin_current >= 0.35`
   - `z_score < 0`
   - `abs(z_score) >= z_marginal`
3. The sub-signal is explicitly suppressed when `toxic_flow_correlation > 0.7`.
4. The core excess formula is unchanged.
5. Runtime forecast reason codes now propagate `b.toxic_flow_fade` when active.

## Tests and Proof

- New excess-detector tests cover activation and correlation suppression.
- Runner test covers emit-path propagation.
- Runtime test covers forecast reason-code propagation.
- `python -m py_compile src/engines/engine_b/excess_detector_b.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> pass
- `python -m pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q` -> `88 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No new scoring bonus formula was introduced for `toxic_flow_fade`.
- No calibration seam provider was added yet for the 0.35 / 0.7 thresholds; they remain documented local defaults in the current B slice.

## Risks / Open Questions

- This slice makes the B sub-signal explicit and auditable, but does not yet promote it to a dedicated scored block.
- If later required, any scoring effect should come through a calibrated local B seam, not a shared seam.

## Completion Status

`PARTIAL`

## Next Safe Step

Promote the hardcoded B-local `vpin_toxic` / `max_intra_family_correlation` defaults into a proper calibration seam if and only if the current Engine B local semantics are accepted in shadow.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_b_hardening_from_cartography_audit.md

# Engine B Hardening From Cartography Audit

Date: 2026-04-17
Status: COMPLETE

## Governing Inputs
- `E:/claude  v5.3/modernisation de v5.3/V53_CARTOGRAPHIE_ALIGNMENT_ET_AUDIT_ENGINE_B.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_b/cost_feasibility_b.py`
- `src/engines/engine_b/conviction_builder_b.py`
- `src/engines/engine_b/signal_reporter_b.py`
- `src/engines/engine_b/invalidation_mapper_b.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented
- Zero or invalid candidate sizing no longer reaches emit paths.
- `LOW` conviction is no longer emittable in Engine B.
- Engine B no-trade outcomes now distinguish `INVALID_INPUT`, `COST_MARGINAL`, `CONVICTION_LOW`, and `INVALID_INVALIDATION`.
- Invalidation mapping rejects economically absurd inputs instead of silently emitting malformed stop/target contracts.
- `EngineBInput` now bounds normalized score-like fields and core economic inputs.
- `EngineBRuntimeInput` now rejects impossible numeric runtime contracts such as zero size, zero equity, negative peak equity, or zero max selections.

## Fail-First Evidence
- `test_candidate_size_zero_is_not_emittable`
- `test_low_conviction`
- `test_candidate_size_zero_rejected_before_emit`
- `test_current_price_zero_rejected_before_emit`
- `test_runtime_input_rejects_zero_projected_size`

These cases reflected permissive legacy behavior before the hardening patch and now pass under the guarded contract.

## Tests And Proof
- `python -m py_compile src/engines/engine_b/cost_feasibility_b.py src/engines/engine_b/conviction_builder_b.py src/engines/engine_b/signal_reporter_b.py src/engines/engine_b/invalidation_mapper_b.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> `113 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Remaining Calibration Gaps
- Conviction thresholds remain heuristically governed and still need shadow evidence before promotion.
- Breakout, excess, and toxic-flow thresholds remain local to Engine B and need later calibration packs if promoted beyond shadow.
- Engine B is materially safer and more auditable now, but still not promoted to live by this slice alone.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md

# Engine B Re-audit Residual Fixes

Date: 2026-04-17
Status: COMPLETE

## Governing Inputs
- `E:/claude  v5.3/modernisation de v5.3/V53_REAUDIT_ENGINE_B_CODE_REEL_ET_PROMPT.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/anti_breakout_filter_b.py`
- `src/engines/engine_b/local_mean_estimator_b.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented
- Engine B now emits stable structured `reason_codes` for the surviving no-trade branches:
  - invalid dispersion
  - non-long direction
  - no excess
  - breakout blocked
- Engine B emit paths now expose richer engine-level `reason_codes` instead of depending only on excess-local active codes.
- Runtime risk logs now align with the final status:
  - `engine_b_risk_rejected`
  - `engine_b_risk_reduced`
  - `engine_b_risk_observe_only`
- Reusable helpers now enforce bounded or positive contracts instead of relying only on runner-level protection:
  - `ExcessInput`
  - `BreakoutInput`
  - `LocalMeanInput`

## Fail-First Evidence
- direct repro before patch showed `reason_codes=()` for:
  - invalid dispersion
  - non-long direction
  - no excess
  - breakout blocked
- runtime support previously logged `engine_b_risk_rejected` even when final status was `RISK_REDUCED` or `RISK_OBSERVE_ONLY`
- helper inputs previously accepted out-of-range normalized values or non-positive prices/means

## Tests And Proof
- `python -m py_compile src/engines/engine_b/excess_detector_b.py src/engines/engine_b/anti_breakout_filter_b.py src/engines/engine_b/local_mean_estimator_b.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> `119 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Residual Calibration Gaps
- Engine B thresholds remain heuristically governed and still require shadow evidence before promotion.
- `signal_reporter_b.py` remains a secondary helper surface; this slice does not reclassify or deprecate it.
- Forecast conditioning / reason-code richness is improved indirectly through richer emit reason-codes, but no broader enriched-contract redesign was done here.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_engine_b_prompt1_explicit_status_and_forecast_proofs.md

# 2026-04-17 - Engine B prompt(1) closure slice

## Governing Inputs
- `E:/claude  v5.3/modernisation de v5.3/V53_REAUDIT_ENGINE_B_CODE_REEL_ET_PROMPT (1).md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `CODEX_PROMPT.md`

## Files Changed
- `src/engines/engine_b/signal_reporter_b.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

## Claims Implemented
- `signal_reporter_b.py` now has an explicit module-status contract:
  - `NoTradeReasonB` is canonical and consumed by `engine_b_runner`
  - `SignalCandidateB`, `SignalStatsB`, and `SignalReporterB` are secondary audit helpers outside the canonical runner/runtime path
- Explicit forecast proof tests now cover:
  - `expected_break_even`
  - forecast reason codes with scoring penalties
  - conditioning-state families and scoring records
  - versions non-regression

## Fail-First Evidence
- Before this slice, Engine B had no explicit code-level status marker for `signal_reporter_b.py`; the ambiguity lived in code, not just docs.
- The forecast behavior already existed, but the proof surface was only partial and indirect. The new tests make these expectations explicit and replayable.

## Tests And Proof
- `python -m py_compile src/engines/engine_b/signal_reporter_b.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `python scripts/run_engineering_guardrails.py`

## Completion Status
- `COMPLETE`

## Residual Gaps
- Engine B still remains `NEEDS_MORE_CALIBRATION` on thresholds and broader shadow/promotion evidence.


