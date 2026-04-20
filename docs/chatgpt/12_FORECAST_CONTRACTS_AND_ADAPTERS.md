# 12_FORECAST_CONTRACTS_AND_ADAPTERS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-15_forecast_contract_engine_a_adapter.md
- docs/production_deployment_plan/update_audit/2026-04-15_engine_b_forecast_adapter.md
- docs/production_deployment_plan/update_audit/2026-04-17_doc20_native_phase_a_phase_b_seams.md
- docs/production_deployment_plan/update_audit/2026-04-18_doc20_cd_additive_forecast_runtime_seam.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_forecast_contract_engine_a_adapter.md

# 2026-04-15 Forecast Contract + Engine A Adapter

## Objective

Create an auditable additive forecast contract seam, then wire the first real engine adapter on Engine A without replacing the canonical decision signal contract.

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§3.1`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) `§3.3`, `§5`
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R22`, `R23`, `R24`, `R26`

## Current Code Seam

- Canonical file today: [decision_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/decision_contracts.py>)
- First engine runtime consumer: [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- Forbidden shortcut for this slice: no canonical contract replacement, no invented `strategy_id`, no `side="flat"`

## Placement

- Target file: [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- First engine adapter landing: [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>) + [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)
- Actual landing decision: additive sibling contract plus optional runtime adapter, preserving `decision_contracts.SignalCandidate` as the package canon

## Files Changed

- [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- [__init__.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/__init__.py>)
- [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)
- [test_forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/tests/test_interface_contracts/test_forecast_contracts.py>)
- [test_engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a_runtime.py>)

## Claims Implemented

- Additive forecast enums + conditioning contract exist -> [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- Package-level canonical `SignalCandidate` remains unchanged while `ForecastSignalCandidate` is exported separately -> [__init__.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/__init__.py>)
- Engine A can emit `forecast_signal_candidate` only when `strategy_id` is explicitly provided -> [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- Engine A forecast mapping uses only real data already present in the runtime seam -> [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)

## Tests and Proof

- `python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py tests/test_engines/test_engine_a/test_engine_a_runtime.py src/interface_contracts/forecast_contracts.py` -> pass
- `python -m pytest tests/test_interface_contracts/test_all_contracts.py tests/test_interface_contracts/test_forecast_contracts.py tests/test_engines/test_engine_a/test_engine_a_runtime.py -q` -> `95 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`, `total_violations=3549`

## Deferred / Not Done

- Engine B adapter not wired yet
- No canonical `strategy_identity` contract yet
- No propagation yet into C/D, scoring, portfolio, or execution

## Risks / Open Questions

- `strategy_id` is currently an optional runtime seam, not yet a cross-repo canonical contract
- Future engines should reuse the same pattern rather than creating a second competing forecast canon

## Completion Status

`COMPLETE`

Reason:

`The additive contract seam exists, the first real engine adapter exists, proof commands are green, and no new guardrail violations were introduced.`

## Next Safe Step

`Replicate the same optional strategy_id -> forecast_signal_candidate pattern on Engine B, or formalize strategy identity before wider propagation.`


---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_engine_b_forecast_adapter.md

# 2026-04-15 Engine B Forecast Adapter

## Objective

Wire the second additive forecast adapter on Engine B without replacing the canonical decision signal contract and without inventing a `strategy_id`.

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§3.1`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) `§3.3`, `§5`
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R22`, `R23`, `R24`, `R26`, `Bloc 10`

## Current Code Seam

- Canonical file today: [decision_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/decision_contracts.py>)
- Engine runtime seam: [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- Forbidden shortcut for this slice: no canonical contract replacement, no fake `strategy_id`, no `side="flat"`

## Placement

- Target runtime files: [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>) and [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- Actual landing decision: keep the forecast mapping in the existing Engine B support module because file size remains below guardrail thresholds and the helper seam already lives there

## Files Changed

- [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- [test_engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b_runtime.py>)

## Claims Implemented

- `EngineBRuntimeInput` accepts optional `strategy_id` and rejects blank values -> [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- `EngineBRuntimeResult` exposes optional `forecast_signal_candidate` while preserving the canonical `signal_candidate` -> [engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime.py>)
- Engine B maps its canonical signal into an additive `ForecastSignalCandidate` only when `strategy_id` is explicitly provided -> [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- Engine B forecast mapping uses `BetStructure.MEAN_REVERT`, real cost/gain fields, real invalidation text, and runtime scoring penalties -> [engine_b_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py>)
- Test harness is normalized to `repo_tmp_path` to stay executable in this repo sandbox -> [test_engine_b_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b_runtime.py>)

## Tests and Proof

- `python -m py_compile src/engines/engine_b/engine_b_runtime.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_b/test_engine_b_runtime.py` -> pass
- `python -m pytest tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_interface_contracts/test_forecast_contracts.py -q` -> `32 passed`
- `python -m pytest tests/test_interface_contracts/test_all_contracts.py tests/test_interface_contracts/test_forecast_contracts.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q` -> `95 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`, `total_violations=3537`

## Deferred / Not Done

- No Engine C adapter yet
- No Engine D adapter yet
- No cross-repo canonical `strategy_identity` seam yet

## Risks / Open Questions

- `strategy_id` still enters at runtime input level, not yet through a broader canonical contract
- Future adapters should continue reusing the existing forecast contract seam rather than creating engine-local variants

## Completion Status

`COMPLETE`

Reason:

`Targeted engine tests, broader interface/runtime proof, and guardrails are all green with no new violations.`

## Next Safe Step

`Proceed to Engine C only if a real strategy_id seam is available there too; otherwise formalize strategy identity before wider propagation.`


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_doc20_native_phase_a_phase_b_seams.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_doc20_cd_additive_forecast_runtime_seam.md

# 2026-04-18 - Doc20 additive forecast runtime seam for Engine C/D

## Governing docs
- doc 28: arbitration law
- doc 24: real placement map
- doc 19: migration order
- doc 20: enriched forecast doctrine
- doc 25/26: audit protocol and pack template

## Scope
- additive forecast-facing runtime seam for Engine C and Engine D
- no runner rewrite
- no widening of `decision_contracts.SignalCandidate`
- no fake blocked trades

## Files changed
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## Claims implemented
- Engine C runtime input now accepts optional `strategy_id`.
- Engine D runtime input now accepts optional `strategy_id`.
- C/D runtime results now expose additive `forecast_signal_candidate`.
- Historical `signal_candidate` remains unchanged and still drives the canonical runtime path.
- Forecast construction is done only inside runtime support seams.
- Engine C forecast candidate carries additive breakout/continuation/microstructure reason codes.
- Engine D forecast candidate carries additive conviction/link-type/anti-revenge reason codes.
- Engine D forecast candidate reuses `first_episode_ref.bet_structure` when coordination input provides it.

## Explicit boundary
- `invalidation_ref` remains `None` for C/D because the current runner outputs do not expose a canonical invalidation reference string.
- Version maps are truthful but minimal:
  - `scoring_version`
  - `runtime_adapter_version`
- No calibration profile IDs were invented for C/D runtime adapters.

## Tests added
- C runtime emits additive forecast signal when `strategy_id` is provided.
- C forecast reason codes include engine and scoring penalties.
- C conditioning state includes engine-internal and scoring records.
- C forecast versions remain stable.
- C runtime input rejects blank `strategy_id`.
- D runtime emits additive forecast signal when `strategy_id` is provided.
- D forecast reason codes include engine and scoring penalties.
- D conditioning state includes engine-internal and scoring records.
- D forecast versions remain stable.
- D runtime input rejects blank `strategy_id`.

## Proof checklist
- targeted `py_compile` with workspace pycache prefix
- targeted pytest on Engine C/D runtime
- targeted pytest on C/D runtime regression packs
- guardrails

## Completion status
- `PARTIAL_COMPLETE`
- next safe step: if required, harmonize A/B/C/D forecast adapter evidence through a shared audit utility without changing the runtime decision canon


