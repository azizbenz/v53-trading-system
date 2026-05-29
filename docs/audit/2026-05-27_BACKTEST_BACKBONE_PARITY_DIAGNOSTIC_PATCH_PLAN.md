# V5.3 - Backtest Backbone Parity Diagnostic And Patch Plan

Date: 2026-05-27  
Reference run: `L:\output backtest\runs\strategy_ladder_workflow-2df91d9d5c48dfbf`  
Mode: `READ_ONLY_THEN_PATCH`  
Scope: diagnostic + reporting/taxonomy/count semantics only

## 1. Objective

This document is the working witness for the Backbone Parity tranche.

The question to answer is:

> Does the V5.3 backtest test the same logical system as the future VPS/shadow/live runtime, or is it still testing a parallel `local_replay_runtime` rail?

The work is split into two phases:

1. Read-only diagnostic.
2. Minimal patch limited to truth-of-state, reason-code taxonomy, count semantics, and backbone-parity reporting.

This tranche must not make the strategy more permissive and must not attempt to produce profit.

## 2. Non-Negotiable Invariants

Do not modify:

- Engine A/B/C/D logic.
- `SignalCandidate`.
- Engine thresholds.
- Hard gates.
- Expected-edge proxy blockers.
- Sharia / spot-only / long-only rules.
- Live/shadow/VPS policy.
- Trade selection or execution decisions.

Do not:

- Force `selected_count` or `executed_count`.
- Create fake trades.
- Create fake labels.
- Promote proxy labels as truth.
- Train ML.
- Import the full live/VPS runtime into B2.
- Refactor the full strategy in this tranche.

Allowed changes only:

- Diagnostic-only reports.
- Reporting-only summaries.
- Reason-code classification.
- Count semantics clarification.
- Adapter/contract truth-state labels.
- Wording safety for single-pair/single-timeframe reports.

## 3. Known Trigger From Run `2df91`

Observed state:

- `candidate_count=200`
- `b2_replay_candidates=97`
- `replay_records=388`
- matrix-level `selected_count=4`
- matrix-level `executed_count=4`

Actual semantic interpretation:

- 1 unique Engine A signal.
- Expanded over 4 capital buckets.
- Therefore `4` bucket execution records, not 4 independent trading signals.

Critical issue:

`candidate_id=ae5c57f5197f33fcab27b346` has:

- `engine_id=engine_a`
- `engine_a.emit.valid`
- `execution_state=executed`
- but reason codes still include `ENGINE_NATIVE_RUNNER_NOT_INVOKED`

This is not acceptable as a final blocking reason on an executed record. It must be reclassified as previous-stage/diagnostic, renamed, or flagged as inconsistent.

Second issue:

`B2_COST_MEASUREMENT_BLOCKED` is too coarse. It currently hides component-level causes:

- depth20 missing;
- fill realism missing;
- spread proxy;
- slippage proxy;
- fee missing;
- adverse selection proxy;
- live parity telemetry missing;
- partial measurement not promotion-grade.

## 4. Phase 1 - Read-Only Diagnostic

### 4.1 Main Diagnostic Artifacts

Create under the active run `reports/` directory:

- `backtest_backbone_parity_audit.json`
- `backtest_decision_source_matrix.json`
- `backbone_module_usage_matrix.json`
- `backtest_local_replay_dependency_audit.json`
- `parallel_logic_and_proxy_surface_audit.json`
- `count_semantics_deep_audit.json`
- `reason_code_taxonomy_audit.json`
- `executed_reason_code_consistency_audit.json`
- `engine_native_runner_invocation_audit.json`
- `b2_cost_blocker_component_audit.json`
- `engine_a_executed_candidate_autopsy.json`
- `backtest_backbone_parity_final_report.json`

Create repo docs:

- `docs/audit/BACKTEST_BACKBONE_PARITY_AUDIT.md`
- `docs/audit/ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY.md`
- `docs/audit/BACKTEST_BACKBONE_PARITY_FINAL_REPORT.md`

### 4.2 Module Usage Matrix

For each module:

- `src/data_backbone`
- `src/execution_backbone`
- `src/meta_learning`
- `src/portfolio_minimal`
- `src/protocols`
- `src/complete_enablers`
- `src/risk_backbone`
- `src/regime_classifier`
- `src/scoring_backbone`
- `src/local_replay_runtime`

Report:

```json
{
  "module": "src/execution_backbone",
  "used_by_backtest": true,
  "usage_level": "direct|adapter|manifest_only|shadow_only|not_used",
  "used_in_phase": ["A2", "B1", "B2", "B_ML", "DecisionReport"],
  "entrypoints": [],
  "decision_authority": "canonical|partial|proxy|none",
  "gaps": [],
  "patch_needed": true
}
```

Initial expected status from code reconnaissance:

- `data_backbone`: used directly for A2 and microstructure.
- `execution_backbone`: used partially through `shadow_execution_simulator.py` and replay contracts.
- `portfolio_minimal`: used partially for capital viability/buckets.
- `complete_enablers`: used partially through Strategy Ladder C/D support.
- `meta_learning`: mostly IA Lab/research, not B2 decision authority.
- `protocols`: mostly shadow/live scripts, not B2 core.
- `risk_backbone`: mostly shadow/live scripts, weak B2 parity.
- `regime_classifier`: weak/missing in B2 reports.
- `scoring_backbone`: weak/missing in B2 decision authority; some manifest references.
- `local_replay_runtime`: dominant rail.

### 4.3 Decision Source Matrix

Audit the source of truth for:

- `data_loading`
- `feature_computation`
- `candidate_generation`
- `engine_decision`
- `scoring`
- `break_even`
- `risk_filtering`
- `execution_intent`
- `spread_measurement`
- `slippage_measurement`
- `fee_measurement`
- `partial_fill`
- `adverse_selection`
- `portfolio_update`
- `regime_classification`
- `refusal_logging`
- `promotion_verdict`

For each surface:

```json
{
  "surface": "slippage_measurement",
  "current_source": "local_replay_runtime|execution_backbone|proxy|unknown",
  "canonical_expected_source": "execution_backbone",
  "actual_status": "canonical|partial_canonical|adapter|proxy|missing",
  "evidence_files": [],
  "reason_codes": [],
  "parity_status": "PARITY_OK|PARITY_PARTIAL|PARITY_MISSING|PARITY_CONFLICT"
}
```

### 4.4 Parallel Logic And Proxy Surface Audit

Search and report double logic for:

- engine cost feasibility vs replay cost feasibility;
- engine break-even vs `scoring_backbone`;
- A2 spread/slippage research features vs B2 truth measurements;
- B1/B1.5/B2 reason-code mixing;
- candidate count vs bucket record count;
- expected-edge proxy vs expected-edge artifact;
- `shadow_execution_simulator.py` as partial truth path.

Verdicts:

- `NO_PARALLEL_LOGIC_FOUND`
- `PARALLEL_LOGIC_REPORTING_ONLY`
- `PARALLEL_LOGIC_DECISION_CONFLICT`
- `PARALLEL_LOGIC_PATCH_REQUIRED`

## 5. Diagnostic - Count Semantics

Create `reports/count_semantics_deep_audit.json`.

Required fields:

- `candidate_count`
- `unique_candidate_count`
- `selected_candidate_count`
- `selected_bucket_record_count`
- `executed_candidate_count`
- `executed_bucket_record_count`
- `independent_signal_count`
- `capital_bucket_expansion_factor`

Expected for run `2df91`:

- `independent_executed_signal_count=1`
- `executed_bucket_record_count=4`
- explanation: `4 bucket execution records, not 4 independent trading signals`

Verdicts:

- `COUNT_SEMANTICS_OK`
- `COUNT_SEMANTICS_BUCKET_EXPANSION_CONFUSING`
- `COUNT_SEMANTICS_INCONSISTENT`
- `COUNT_SEMANTICS_PATCH_REQUIRED`

## 6. Diagnostic - Reason-Code Taxonomy

Create:

- `reports/reason_code_taxonomy_audit.json`
- `reports/executed_reason_code_consistency_audit.json`

Reason-code classes:

- `blocking_reason_codes`
- `diagnostic_reason_codes`
- `advisory_reason_codes`
- `historical_reason_codes`
- `previous_stage_reason_codes`

Executed record invariant:

If `execution_state=executed`, these codes cannot appear as final blocking reasons:

- `ENGINE_NATIVE_RUNNER_NOT_INVOKED`
- `ENGINE_NATIVE_NO_TRADE`
- `B2_COST_MEASUREMENT_BLOCKED`
- `cost_infeasible`
- `break_even_not_cleared`
- `non_long_direction`

If present, they must be:

- moved to diagnostic/previous-stage;
- renamed;
- or record flagged `INCONSISTENT_EXECUTION_RECORD`.

Verdicts:

- `REASON_CODE_TAXONOMY_OK`
- `ENGINE_NATIVE_RUNNER_NOT_INVOKED_MISNAMED`
- `EXECUTED_RECORD_HAS_CONTRADICTORY_BLOCKERS`
- `REASON_CODE_CLASSES_MISSING`
- `REASON_CODE_PATCH_REQUIRED`

## 7. Diagnostic - `ENGINE_NATIVE_RUNNER_NOT_INVOKED`

Create `reports/engine_native_runner_invocation_audit.json`.

Questions:

- Does B2 actually re-invoke engines?
- Does B2 reuse B1/B1.5 decision?
- If B2 reuses B1, why is the code named `ENGINE_NATIVE_RUNNER_NOT_INVOKED`?
- Is it blocker, advisory, diagnostic, or previous-stage?
- Why does executed Engine A carry both `engine_a.emit.valid` and `ENGINE_NATIVE_RUNNER_NOT_INVOKED`?

Candidate replacement names:

- `B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1`
- `B2_ENGINE_NATIVE_REEVALUATION_NOT_REQUESTED`
- `ENGINE_NATIVE_RUNNER_INVOCATION_MISSING_BUG`

Verdicts:

- `ENGINE_NATIVE_RUNNER_NOT_INVOKED_LEGITIMATE_BLOCKER`
- `ENGINE_NATIVE_RUNNER_NOT_INVOKED_MISNAMED_DIAGNOSTIC`
- `ENGINE_NATIVE_RUNNER_NOT_INVOKED_WIRING_BUG`
- `ENGINE_NATIVE_RUNNER_REASON_CODE_TOO_COARSE`

## 8. Diagnostic - B2 Cost Blocker Components

Create `reports/b2_cost_blocker_component_audit.json`.

For each replay/bucket record:

```json
{
  "candidate_id": "...",
  "engine_id": "...",
  "capital_bucket": 400,
  "execution_state": "...",
  "book_depth20_status": "...",
  "fill_realism_status": "...",
  "spread_status": "MEASURED|PROXY|MISSING|UNKNOWN",
  "slippage_status": "MEASURED|PROXY|MISSING|UNKNOWN",
  "fee_status": "MEASURED|PROXY|MISSING|UNKNOWN",
  "partial_fill_status": "MEASURED|PROXY|MISSING|UNKNOWN",
  "adverse_selection_status": "MEASURED|PROXY|MISSING|UNKNOWN",
  "live_parity_status": "PROVEN|BLOCKED|MISSING",
  "cost_blocker_components": [],
  "final_cost_truth_status": "FULLY_MEASURED|PARTIAL_MEASURED|PROXY|MISSING",
  "blocker_legitimate": true
}
```

Component codes:

- `B2_COST_BLOCKED_BY_DEPTH20_MISSING`
- `B2_COST_BLOCKED_BY_FILL_REALISM_MISSING`
- `B2_COST_BLOCKED_BY_SPREAD_PROXY`
- `B2_COST_BLOCKED_BY_SLIPPAGE_PROXY`
- `B2_COST_BLOCKED_BY_FEE_MISSING`
- `B2_COST_BLOCKED_BY_ADVERSE_SELECTION_PROXY`
- `B2_COST_BLOCKED_BY_LIVE_PARITY_TELEMETRY`
- `B2_COST_GOVERNANCE_BLOCKED_PARTIAL_MEASUREMENT`
- `B2_COST_MEASURED_BUT_NOT_PROMOTION_GRADE`

Keep parent code `B2_COST_MEASUREMENT_BLOCKED` when appropriate, but attach `cost_blocker_components`.

## 9. Diagnostic - Engine A Executed Candidate Autopsy

Create:

- `reports/engine_a_executed_candidate_autopsy.json`
- `docs/audit/ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY.md`

Target:

`candidate_id=ae5c57f5197f33fcab27b346`

Required output:

```json
{
  "candidate_id": "ae5c57f5197f33fcab27b346",
  "engine_id": "engine_a",
  "distinct_signal_count": 1,
  "bucket_execution_count": 4,
  "capital_buckets": [400, 500, 1500, 4000],
  "engine_emit_status": "engine_a.emit.valid",
  "why_emit_valid": [],
  "why_selected": [],
  "why_executed": [],
  "fwd_h1_bps": -67.75,
  "mfe_bps": 0,
  "mae_bps": -99.36,
  "loss_cause": "PRICE_ADVERSE_MOVE|COST|SLIPPAGE|UNKNOWN",
  "contradictory_reason_codes": [],
  "verdict": "VALID_BUT_LOSSMAKING|BUCKET_EXPANDED_SINGLE_SIGNAL|INCONSISTENT_RECORD"
}
```

Questions to answer:

- Why did Engine A emit valid?
- Why was this candidate selected?
- Why was it executed?
- Why did it lose?
- Are the 4 records one signal expanded by bucket?
- Should the UI display it as 1 losing signal rather than 4 independent trades?

## 10. Backbone-Specific Verdicts

### data_backbone

Check:

- A2 uses canonical structures.
- Microstructure features come from `data_backbone`, not local substitutes.
- `spread_bps`, `slippage_bps`, `book_depth_levels`, `vpin`, `ofi`, `queue_pressure` are marked research-only or truth correctly.

Verdicts:

- `DATA_BACKBONE_PARITY_OK`
- `DATA_BACKBONE_PARTIAL`
- `DATA_BACKBONE_PROXY_CONTAMINATION`

### execution_backbone

Check:

- B2 spread/slippage/fill/fees/adverse selection source.
- Whether `shadow_execution_simulator.py` is still acting as truth adapter.
- Why `CANONICAL_OR_PROXY` remains present.

Verdicts:

- `EXECUTION_BACKBONE_PARITY_OK`
- `EXECUTION_BACKBONE_PARTIAL`
- `EXECUTION_BACKBONE_PROXY_FALLBACK`
- `EXECUTION_BACKBONE_MISSING_FOR_B2`

### scoring_backbone

Check:

- Break-even source.
- Expected cost source.
- Ranking source.
- Whether `break_even_not_cleared` uses measured cost or proxy.

Verdicts:

- `SCORING_BACKBONE_PARITY_OK`
- `SCORING_BACKBONE_PARTIAL`
- `SCORING_BACKBONE_MISSING`

### risk_backbone

Check:

- Drawdown.
- Loss budget.
- Risk limits.
- Capital exposure.
- Why true net equity drawdown is missing/not proven.

Verdicts:

- `RISK_BACKBONE_PARITY_OK`
- `RISK_BACKBONE_PARTIAL`
- `RISK_BACKBONE_MISSING`

### portfolio_minimal

Check:

- Capital bucket origin.
- Spot-only inventory.
- Sizing and capital fragmentation.
- Bucket expansion wording.

Verdicts:

- `PORTFOLIO_BACKBONE_PARITY_OK`
- `PORTFOLIO_COUNT_SEMANTICS_PATCH_REQUIRED`
- `PORTFOLIO_BACKBONE_PARTIAL`

### regime_classifier

Check:

- `regime_id` in replay records.
- Performance by regime.
- Engine A/B/C/D by regime.

Verdicts:

- `REGIME_CLASSIFIER_USED`
- `REGIME_CLASSIFIER_MISSING_IN_B2`
- `REGIME_REPORTING_MISSING`

### complete_enablers

Check:

- Build-14 use.
- Engine C/D context.
- Engine C filtered upstream vs not applied.

Verdicts:

- `COMPLETE_ENABLERS_OK`
- `ENGINE_C_MICROSTRUCTURE_WIRING_BUG`
- `ENGINE_C_REPORTING_LABEL_MISLEADING`

### meta_learning

Check:

- Used only IA Lab/research.
- No silent training in backtest.
- Expected-edge artifact absence blocks correctly.

Verdicts:

- `META_LEARNING_CORRECTLY_OUT_OF_B2`
- `META_LEARNING_SILENT_TRAINING_BUG`
- `EXPECTED_EDGE_ARTIFACT_REQUIRED`

### protocols

Check:

- Contracts/proofs/refusals use.
- No transport/live/VPS import into B2.
- Refusal records aligned with shadow/live contract.

Verdicts:

- `PROTOCOLS_CONTRACTS_USED`
- `PROTOCOLS_SHADOW_ONLY`
- `PROTOCOLS_TRANSPORT_NOT_REQUIRED_IN_B2`
- `PROTOCOLS_PARITY_GAP`

## 11. Final Diagnostic Report Format

Create `reports/backtest_backbone_parity_final_report.json`:

```json
{
  "schema_version": "v53.backtest_backbone_parity.v1",
  "run_id": "strategy_ladder_workflow-2df91d9d5c48dfbf",
  "audit_mode": "READ_ONLY_THEN_PATCH",
  "trading_logic_modified": false,
  "thresholds_modified": false,
  "modules": {},
  "decision_source_matrix": [],
  "count_semantics_verdict": "...",
  "reason_code_taxonomy_verdict": "...",
  "engine_native_runner_invocation_verdict": "...",
  "b2_cost_blocker_component_verdict": "...",
  "engine_a_autopsy_verdict": "...",
  "backbone_parity_overall": "PARITY_OK|PARITY_PARTIAL|PARITY_MISSING|PARITY_CONFLICT",
  "root_causes_ranked": [],
  "patch_plan": []
}
```

## 12. Phase 2 - Minimal Patch

Only after diagnostic artifacts exist.

### Patch A - Count Semantics

Add to reports and cockpit summaries:

- `selected_candidate_count`
- `selected_bucket_record_count`
- `executed_candidate_count`
- `executed_bucket_record_count`
- `independent_signal_count`
- `capital_bucket_expansion_factor`

No historical record rewrite.

### Patch B - Reason-Code Taxonomy

Add explicit reason-code classes:

- `blocking_reason_codes`
- `diagnostic_reason_codes`
- `advisory_reason_codes`
- `historical_reason_codes`
- `previous_stage_reason_codes`

### Patch C - `ENGINE_NATIVE_RUNNER_NOT_INVOKED` Reclassification

If B2 reuses B1:

- reclassify `ENGINE_NATIVE_RUNNER_NOT_INVOKED` as diagnostic/previous-stage;
- emit `B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1` or `B2_ENGINE_NATIVE_REEVALUATION_NOT_REQUESTED`.

If actual bug:

- emit `ENGINE_NATIVE_RUNNER_INVOCATION_MISSING_BUG`;
- flag `INCONSISTENT_EXECUTION_RECORD`.

### Patch D - Split B2 Cost Measurement Blocker

Keep parent:

- `B2_COST_MEASUREMENT_BLOCKED`

Add:

- `cost_blocker_components=[...]`

No promotion unblock.

### Patch E - Ranking Wording Safety

If only one pair:

- use `only_pair_tested`, not `best_pair`.

If only one timeframe:

- use `only_timeframe_tested`, not `best_timeframe`.

Recommendation must be:

- `ONLY_AVAILABLE_PARTIAL_RESEARCH_ONLY`

### Patch F - Executed Record Invariant Audit

Create:

- `reports/executed_record_invariant_report.json`

Executed records with final contradictory blockers become:

- `INCONSISTENT_EXECUTION_RECORD`

or codes are moved to diagnostic-only if justified.

## 13. Forbidden In This Tranche

Do not implement:

- full backbone refactor;
- expected-edge ML training;
- B_ML promotion-ready;
- Engine C/D rewrite;
- threshold calibration;
- risk policy change;
- live/shadow/VPS integration;
- performance optimization B1 refs_only.

Those remain later work.

## 14. Tests To Add

Create:

- `tests/test_local_replay_runtime/test_backtest_backbone_parity_audit.py`
- `tests/test_local_replay_runtime/test_count_semantics_deep_audit.py`
- `tests/test_local_replay_runtime/test_reason_code_taxonomy.py`
- `tests/test_local_replay_runtime/test_engine_native_runner_invocation_audit.py`
- `tests/test_local_replay_runtime/test_b2_cost_blocker_component_audit.py`
- `tests/test_local_replay_runtime/test_executed_record_invariants.py`
- `tests/test_local_replay_runtime/test_report_wording_safety.py`

Minimum assertions:

- Audit does not modify trades.
- Audit does not modify thresholds.
- Audit does not modify engine output.
- `1 candidate x 4 buckets` is reported as 1 independent signal and 4 bucket records.
- Executed record cannot have `ENGINE_NATIVE_RUNNER_NOT_INVOKED` as final blocker.
- `ENGINE_NATIVE_RUNNER_NOT_INVOKED` becomes diagnostic-only if B2 reuses B1.
- `B2_COST_MEASUREMENT_BLOCKED` is decomposed into components.
- Depth20 + fill measured + slippage/adverse proxy is `PARTIAL`, not `book missing`.
- Single pair does not produce `best_pair`.
- Single timeframe does not produce `best_timeframe`.
- `expected_edge_proxy_count > 0` still blocks profitability.
- No proxy is promoted to truth.

## 15. Verification Commands

Run:

```powershell
python -m compileall -q src tests
pytest tests/test_local_replay_runtime/test_backtest_backbone_parity_audit.py -q --tb=short
pytest tests/test_local_replay_runtime/test_count_semantics_deep_audit.py -q --tb=short
pytest tests/test_local_replay_runtime/test_reason_code_taxonomy.py -q --tb=short
pytest tests/test_local_replay_runtime/test_engine_native_runner_invocation_audit.py -q --tb=short
pytest tests/test_local_replay_runtime/test_b2_cost_blocker_component_audit.py -q --tb=short
pytest tests/test_local_replay_runtime/test_executed_record_invariants.py -q --tb=short
pytest tests/test_local_replay_runtime/test_report_wording_safety.py -q --tb=short
pytest tests/test_local_replay_runtime/test_no_shadow_threshold_challenge.py -q --tb=short
pytest tests/test_local_replay_runtime/test_b2_label_store_ml_training_audit.py -q --tb=short
```

If Windows `__pycache__` permission blocks compileall, rerun with:

```powershell
$env:PYTHONPYCACHEPREFIX='E:\claude  v5.3\v53_trading_system\tmp_pycache_backbone_parity'
python -m compileall -q src tests
```

## 16. Final Patch Verdict Artifacts

Create:

- `reports/backtest_backbone_parity_patch_final_verdict.json`
- `docs/audit/BACKTEST_BACKBONE_PARITY_PATCH_FINAL_VERDICT.md`

Possible verdicts:

- `BACKTEST_BACKBONE_PARITY_DIAGNOSED`
- `BACKTEST_BACKBONE_PARITY_PARTIAL`
- `BACKTEST_LOCAL_REPLAY_DOMINANT`
- `COUNT_SEMANTICS_PATCHED`
- `REASON_CODE_TAXONOMY_PATCHED`
- `ENGINE_NATIVE_RUNNER_NOT_INVOKED_RECLASSIFIED`
- `B2_COST_BLOCKER_COMPONENTS_ADDED`
- `REPORT_WORDING_SAFETY_PATCHED`
- `NO_TRADING_LOGIC_CHANGED`

The final verdict must state:

- which backbone layers are really used;
- which layers remain proxy/local replay;
- whether B2 tests the same logical system as future shadow/live;
- how many independent signals were executed;
- why 4 executions are actually 1 signal x 4 buckets;
- why `ENGINE_NATIVE_RUNNER_NOT_INVOKED` was false or misclassified;
- why `B2_COST_MEASUREMENT_BLOCKED` was too coarse;
- what remains for later:
  - B1 refs_only;
  - B2 execution_backbone measured-only;
  - scoring/risk/regime parity;
  - B_ML expected-edge dataset;
  - OOS ML frozen.

## 17. Work Order

1. Implement read-only builder for backbone parity and related audits.
2. Generate reports on run `2df91`.
3. Review diagnostic outputs before patch.
4. Implement minimal reporting/taxonomy patches.
5. Regenerate reports.
6. Run targeted tests.
7. Produce final verdict docs.

No trading behavior change is allowed at any step.
