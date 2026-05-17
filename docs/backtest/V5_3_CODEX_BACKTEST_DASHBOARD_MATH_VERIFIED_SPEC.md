# V5.3 — BACKTEST DASHBOARD PHASE 4
## Math-Verified, Source-Mapped, Read-Only Cockpit Spec for Codex

**Date:** 2026-04-28  
**Scope:** Backtest / Replay dashboard extension  
**Target:** `src/cockpit/`  
**Mode:** Read-only display + audited local job runner visibility  
**Primary rule:** verify whether formulas already exist in code or reports; use existing implementation first. Only use fallback equations for explicitly allowed simple dashboard/display metrics.

---

# 0. Objective

This specification instructs Codex to turn the current `Backtest / Replay` page from a **runner monitor** into a **quant backtest review dashboard**.

The current page shows mainly:

- latest job status
- requested/running/completed/failed counts
- job_id
- duration
- stdout log
- produced file count
- error summary

That is useful, but not sufficient.

The Backtest dashboard must answer:

1. Did the job run?
2. Which data/config/artifacts were used?
3. Are the files fresh and reproducible?
4. Which engines/pairs were tested?
5. Is the result economically positive after costs?
6. Were refusals/blockers economically useful or did they sterilize the strategy?
7. Are feature lineage and anti-leakage checks clean?
8. Are formulas sourced from existing code/reports, not reinvented in templates?
9. Is there enough sample size to interpret anything?
10. Is the run better than baseline, worse, or inconclusive?

---

# 1. Non-Negotiable Invariants

## 1.1 Read-only dashboard

The dashboard must not mutate trading state.

Forbidden:

- no engine activation
- no micro-live/live promotion
- no runtime mode mutation
- no queue writes
- no artifact activation
- no kill switch logic
- no config rewrite from dashboard state adapters
- no quant-anchor edits
- no ML directional label

The dashboard may launch audited local jobs only through the already existing governed local runner seam if present. If the runner seam is absent, it must report `NOT_IMPLEMENTED`.

## 1.2 Do not duplicate existing math

For every metric with mathematical content, Codex must first search the repository for an existing implementation.

Required formula source priority:

1. **Report value already produced by backtest / Local IA Lab**
2. **Existing code function already implementing the formula**
3. **Dashboard fallback equation only if explicitly allowed in this spec**
4. **Otherwise show `NOT_YET_PERSISTED` or `FORMULA_NOT_AVAILABLE`**

## 1.3 Advanced quant formulas are not dashboard-owned

The dashboard must not implement or “quickly approximate” these unless an existing module already does it and Codex imports/uses that module:

- PSR
- DSR
- POT-GPD
- Energy distance
- HLZ / multiple-testing deflation
- Walk-forward governance
- Bootstrap confidence intervals
- Stationary bootstrap
- Any human-signed calibration logic

If absent, display:

```text
NOT_YET_PERSISTED
```

or:

```text
FORMULA_SOURCE_MISSING
```

Do not invent.

## 1.4 Jinja templates must not contain formulas

Templates may format values only.

Forbidden in templates:

- metric formulas
- cost equations
- Sharpe/Sortino logic
- aggregation loops that compute financial metrics
- hidden business rules

All computations must live in typed Python adapters.

## 1.5 Small-sample warning

If `n_trades`, `executed_count`, or `total_opportunities` is below the required threshold, display:

```text
SAMPLE_TOO_SMALL — DO NOT INTERPRET PERFORMANCE
```

Default warning thresholds:

```text
total_opportunities < 30
executed_count < 30
n_returns < 30
```

These thresholds are display warnings only, not promotion rules.

---

# 2. Source Discipline — Mandatory First Step

Before coding, Codex must perform:

## 2.1 CODE CHECK

Inspect current files:

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/routes_*.py
src/cockpit/templates/pages/backtest.html
src/cockpit/templates/index.html
src/cockpit/templates/partials/*.html
scripts/run_cockpit.py
```

Inspect current backtest/runner related files by search:

```text
grep -R "backtest_summary\|backtest_jobs\|replay_metrics\|replay_dtr\|parity_diagnostics\|run_manifest\|statistical_report\|risk_report" -n src scripts tests
```

## 2.2 DATA FILE CHECK

Search for the latest existing files:

```text
build/**/replay_metrics.json
build/**/feature_bridge.json
build/**/replay_dtr.jsonl
build/**/replay_dtr.json
build/**/parity_diagnostics.json
build/**/replay_run_manifest.json
build/**/risk_report.json
build/**/statistical_report.json
build/**/cost_report.json
build/**/comparison_report.json
build/**/audit_manifest.json
build/**/backtest_report.json
build/**/trade_log.csv
build/**/trade_log.jsonl
```

## 2.3 FORMULA SOURCE CHECK

For each formula metric, Codex must search existing code first:

```text
grep -R "def .*sharpe\|sharpe" -n src tests
grep -R "def .*sortino\|sortino" -n src tests
grep -R "max_drawdown\|drawdown" -n src tests
grep -R "profit_factor" -n src tests
grep -R "cvar\|expected_shortfall\|tail_loss" -n src tests
grep -R "probabilistic_sharpe\|psr" -n src tests
grep -R "deflated_sharpe\|dsr" -n src tests
grep -R "multiple_testing\|HLZ\|Harvey" -n src tests
grep -R "ce_net\|expected_cost\|realized_cost" -n src tests
```

Codex must output a **Formula Source Ledger** before implementing.

---

# 3. Formula Source Ledger — Required Output

Codex must create and expose a typed snapshot named:

```text
BacktestFormulaSourceLedger
```

For every formula metric, record:

```text
metric_id
display_name
source_status
source_file
source_function
source_report_file
formula_used
fallback_allowed
dashboard_computed
sample_warning
reason_codes
```

Allowed `source_status` values:

```text
REPORT_VALUE_FOUND
CODE_FORMULA_FOUND
DASHBOARD_FALLBACK_USED
NOT_YET_PERSISTED
FORMULA_SOURCE_MISSING
FORBIDDEN_TO_IMPLEMENT_IN_DASHBOARD
```

If `DASHBOARD_FALLBACK_USED`, the formula must match Section 7 exactly.

---

# 4. Files to Create / Modify

## 4.1 Python state adapters

Create if missing:

```text
src/cockpit/state_backtest_truth.py
src/cockpit/state_backtest_config.py
src/cockpit/state_backtest_metrics.py
src/cockpit/state_backtest_engine_breakdown.py
src/cockpit/state_backtest_pair_breakdown.py
src/cockpit/state_backtest_decision_trace.py
src/cockpit/state_backtest_refusals.py
src/cockpit/state_backtest_cost_realism.py
src/cockpit/state_backtest_data_quality.py
src/cockpit/state_backtest_baseline.py
src/cockpit/state_backtest_statistical_proof.py
src/cockpit/state_backtest_artifacts.py
src/cockpit/state_backtest_reproducibility.py
src/cockpit/state_backtest_formula_ledger.py
```

If this creates too many files for current style, Codex may consolidate into fewer files, but:

- each source file must stay under 700 lines
- each function should stay under 60 lines
- public models must remain typed and testable

## 4.2 Templates

Create or update:

```text
src/cockpit/templates/pages/backtest.html

src/cockpit/templates/partials/_backtest_truth_status.html
src/cockpit/templates/partials/_backtest_config.html
src/cockpit/templates/partials/_backtest_economic_kpis.html
src/cockpit/templates/partials/_backtest_engine_breakdown.html
src/cockpit/templates/partials/_backtest_pair_breakdown.html
src/cockpit/templates/partials/_backtest_decision_trace.html
src/cockpit/templates/partials/_backtest_refusals.html
src/cockpit/templates/partials/_backtest_cost_realism.html
src/cockpit/templates/partials/_backtest_data_quality.html
src/cockpit/templates/partials/_backtest_baseline.html
src/cockpit/templates/partials/_backtest_statistical_proof.html
src/cockpit/templates/partials/_backtest_artifacts.html
src/cockpit/templates/partials/_backtest_reproducibility.html
src/cockpit/templates/partials/_backtest_formula_ledger.html
```

## 4.3 Tests

Create or update:

```text
tests/cockpit/test_state_backtest_truth.py
tests/cockpit/test_state_backtest_config.py
tests/cockpit/test_state_backtest_metrics.py
tests/cockpit/test_state_backtest_engine_breakdown.py
tests/cockpit/test_state_backtest_pair_breakdown.py
tests/cockpit/test_state_backtest_decision_trace.py
tests/cockpit/test_state_backtest_refusals.py
tests/cockpit/test_state_backtest_cost_realism.py
tests/cockpit/test_state_backtest_data_quality.py
tests/cockpit/test_state_backtest_baseline.py
tests/cockpit/test_state_backtest_statistical_proof.py
tests/cockpit/test_state_backtest_artifacts.py
tests/cockpit/test_state_backtest_reproducibility.py
tests/cockpit/test_state_backtest_formula_ledger.py
tests/cockpit/test_routes_backtest_dashboard.py
```

---

# 5. Data Source Priority

For each backtest job, determine the `export_dir`.

Then resolve sources in this order:

## 5.1 Primary export files

```text
export_dir/replay_metrics.json
export_dir/feature_bridge.json
export_dir/replay_dtr.jsonl
export_dir/parity_diagnostics.json
export_dir/replay_run_manifest.json
export_dir/audit_manifest.json
```

## 5.2 Secondary report files

```text
export_dir/backtest_report.json
export_dir/risk_report.json
export_dir/statistical_report.json
export_dir/cost_report.json
export_dir/comparison_report.json
export_dir/trade_log.csv
export_dir/trade_log.jsonl
export_dir/equity_curve.csv
```

## 5.3 If a file is absent

Do not crash.

Return a typed placeholder:

```text
source_status = missing
reason_code = backtest.source.<name>.missing
```

## 5.4 If a file is corrupt

Return:

```text
source_status = parse_error
reason_code = backtest.source.<name>.parse_error
```

---

# 6. Dashboard Sections to Implement

The Backtest page must show these sections in this exact order:

```text
1. Backtest Truth Status
2. Launch Local Job
3. Runner Progress
4. Backtest Config
5. Economic KPIs
6. Engine Breakdown
7. Pair Breakdown
8. Refusal / Blocker Breakdown
9. Decision Trace
10. Cost Realism
11. Data Quality / Anti-Leakage
12. Baseline Comparison
13. Statistical Proof
14. Produced Artifacts
15. Reproducibility
16. Formula Source Ledger
17. Failure Diagnosis
```

---

# 7. Fallback Equations — Allowed Only When No Existing Formula Is Found

## 7.0 Rules for fallback formulas

Fallback formulas are allowed only for dashboard display and only if:

1. no existing code formula is found
2. no report value is found
3. the formula is listed below
4. the output is marked `DASHBOARD_FALLBACK_USED`
5. the metric is not used for promotion gates

Use:

```text
eps = 1e-12
```

## 7.1 Execution rate

```text
exec_rate = executed_count / max(selected_count, 1)
```

If `selected_count = 0`, display `0.0` and add reason:

```text
backtest.exec_rate.no_selected
```

## 7.2 Selection rate

```text
selection_rate = selected_count / max(total_opportunities, 1)
```

## 7.3 Rejection rate

```text
rejection_rate = rejected_count / max(total_opportunities, 1)
```

If `rejected_count` is absent:

```text
rejected_count = max(total_opportunities - selected_count, 0)
```

## 7.4 Hard block ratio

```text
hard_block_ratio = hard_blocked_count / max(total_opportunities, 1)
```

## 7.5 Economic sterilization ratio

```text
blocked_or_rejected_count = max(total_opportunities - selected_count, 0)

economic_sterilization_ratio =
    blocked_or_rejected_count / max(total_opportunities, 1)
```

Status:

```text
insufficient_sample if total_opportunities < 30
ok if ratio < 0.50
watch if 0.50 <= ratio < 0.80
critical if ratio >= 0.80
```

## 7.6 Cost drift

```text
cost_drift = realized_cost_mean - expected_cost_mean
```

## 7.7 Cost drift ratio

```text
cost_drift_ratio = realized_cost_mean / max(abs(expected_cost_mean), eps)
```

Status:

```text
ok if cost_drift_ratio <= 1.20
watch if 1.20 < cost_drift_ratio <= 1.50
critical if cost_drift_ratio > 1.50
unknown if expected_cost_mean is missing
```

## 7.8 Net return from trade returns

Only if trade returns are available and `net_return` is absent:

```text
net_return_total = product(1 + trade_net_return_i for i in trades) - 1
```

If only additive CE-style returns are used by current repo, do not compound. Instead display:

```text
FORMULA_SOURCE_MISSING
```

and ask for repo-specific return convention.

## 7.9 Mean return

```text
mean_return = sum(return_i) / n
```

Allowed only when `n >= 1`.

## 7.10 Sample standard deviation

```text
sample_variance = sum((return_i - mean_return)^2) / max(n - 1, 1)

sample_std = sqrt(sample_variance)
```

If `n < 2`, display:

```text
insufficient_sample
```

## 7.11 Sharpe ratio — display fallback only

Use only if no existing Sharpe function/report exists and `periods_per_year` is explicitly known.

```text
sharpe = mean_return / max(sample_std, eps) * sqrt(periods_per_year)
```

Warnings:

```text
FORMULA_FALLBACK_DASHBOARD_ONLY
SAMPLE_TOO_SMALL if n < 30
```

Do not use for promotion.

## 7.12 Sortino ratio — display fallback only

Use only if no existing Sortino function/report exists and `periods_per_year` is explicitly known.

```text
downside_returns = [min(return_i, 0) for each return_i]

downside_deviation =
    sqrt(sum(downside_returns_i^2) / max(n - 1, 1))

sortino = mean_return / max(downside_deviation, eps) * sqrt(periods_per_year)
```

Warnings:

```text
FORMULA_FALLBACK_DASHBOARD_ONLY
SAMPLE_TOO_SMALL if n < 30
```

## 7.13 Max drawdown from equity curve

Allowed if equity curve is present and no existing drawdown function/report exists.

For each time t:

```text
peak_t = max(equity_0, equity_1, ..., equity_t)

drawdown_t = (equity_t - peak_t) / max(abs(peak_t), eps)

max_drawdown = min(drawdown_t)
```

Display absolute positive magnitude as:

```text
max_drawdown_abs = abs(max_drawdown)
```

## 7.14 Profit factor

Allowed if trade PnL or net trade returns are present.

```text
gross_profit = sum(pnl_i for pnl_i > 0)

gross_loss_abs = abs(sum(pnl_i for pnl_i < 0))

profit_factor = gross_profit / max(gross_loss_abs, eps)
```

If `gross_loss_abs = 0` and `gross_profit > 0`, display:

```text
profit_factor = INF
```

with reason:

```text
backtest.profit_factor.no_losses
```

## 7.15 Empirical VaR — display fallback only

Allowed only for display if returns exist and no risk report exists.

For confidence level `alpha`, default 0.95:

```text
loss_i = -return_i

var_alpha = quantile(losses, alpha)
```

Warnings:

```text
FORMULA_FALLBACK_DASHBOARD_ONLY
SAMPLE_TOO_SMALL if n < 100
```

## 7.16 Empirical CVaR / Expected Shortfall — display fallback only

Allowed only for display if returns exist and no risk report exists.

```text
loss_i = -return_i

var_alpha = quantile(losses, alpha)

tail_losses = [loss_i for loss_i >= var_alpha]

cvar_alpha = mean(tail_losses)
```

Warnings:

```text
FORMULA_FALLBACK_DASHBOARD_ONLY
SAMPLE_TOO_SMALL if n < 100
```

## 7.17 Baseline deltas

If current and baseline metrics exist:

```text
delta_ce_net = current_ce_net - baseline_ce_net

delta_drawdown = current_drawdown_proxy - baseline_drawdown_proxy

delta_cost = current_realized_cost_mean - baseline_realized_cost_mean

delta_exec_rate = current_exec_rate - baseline_exec_rate
```

Verdict:

```text
BETTER_THAN_BASELINE if delta_ce_net > 0 and delta_drawdown <= 0 and delta_cost <= 0
WORSE_THAN_BASELINE if delta_ce_net < 0
INCONCLUSIVE_SAMPLE_TOO_SMALL if current sample or baseline sample < 30
MIXED if signs conflict
```

## 7.18 PSR — forbidden fallback

Do not implement a fallback.

Allowed sources only:

```text
existing calibration_methods/psr.py function
statistical_report.json field
calibration_report.json field
```

If not found:

```text
source_status = FORBIDDEN_TO_IMPLEMENT_IN_DASHBOARD
display = NOT_YET_PERSISTED
```

## 7.19 DSR — forbidden fallback

Do not implement a fallback.

Allowed sources only:

```text
existing calibration_methods/dsr.py function
statistical_report.json field
calibration_report.json field
```

If not found:

```text
source_status = FORBIDDEN_TO_IMPLEMENT_IN_DASHBOARD
display = NOT_YET_PERSISTED
```

## 7.20 HLZ / Multiple Testing Guard — forbidden fallback

Do not implement a fallback.

Allowed sources only:

```text
src/calibration_methods/multiple_testing_guard.py
src/local_replay_runtime/local_lab_multiple_testing_review.py
multiple_testing_review.json
statistical_report.json
```

If not found:

```text
display = NOT_YET_PERSISTED
```

## 7.21 POT-GPD / Energy distance — forbidden fallback

Do not implement fallback formulas in Backtest dashboard.

These remain quant-anchor/calibration concerns.

If absent:

```text
display = NOT_YET_PERSISTED
```

---

# 8. Backtest Truth Status

Create:

```text
BacktestTruthStatusSnapshot
```

Fields:

```text
data_status
feature_bridge_status
lineage_lock_status
anti_leakage_status
costs_included
slippage_included
fees_included
engines_tested
sample_status
result_usable
truth_verdict
reason_codes
```

Possible `truth_verdict`:

```text
USABLE_REVIEW
RUNNER_ONLY
MISSING_DATA
LINEAGE_MISSING
ANTI_LEAKAGE_UNKNOWN
SAMPLE_TOO_SMALL
FAILED_RUN
```

Rules:

```text
FAILED_RUN if latest job status failed
MISSING_DATA if replay_metrics missing
LINEAGE_MISSING if feature_bridge.lineage_lock_status != valid/present
SAMPLE_TOO_SMALL if total_opportunities < 30 or executed_count < 30
RUNNER_ONLY if only job records exist and no metrics files exist
USABLE_REVIEW only if metrics + feature bridge + manifest exist
```

---

# 9. Backtest Config Section

Create:

```text
BacktestConfigSnapshot
```

Display:

```text
pair list
start timestamp/date
end timestamp/date
timeframe/event source
capital
allocation mode
fees config
slippage model
spread model
engines enabled
runtime profile
artifact version
calibration version
config_hash
```

Source priority:

1. `replay_run_manifest.json`
2. `backtest_report.json`
3. job request record
4. config YAML referenced by job
5. placeholder `not_persisted`

---

# 10. Economic KPIs

Create:

```text
BacktestEconomicKpiSnapshot
```

Fields:

```text
ce_net
gross_return_mean
net_return_total
expected_cost_mean
realized_cost_mean
cost_drift
cost_drift_ratio
drawdown_proxy
max_drawdown
exec_rate
selection_rate
hard_block_ratio
total_opportunities
selected_count
executed_count
hard_blocked_count
sample_warning
```

Source priority:

1. `replay_metrics.json`
2. `backtest_report.json`
3. `risk_report.json`
4. fallback equations Section 7 where allowed

---

# 11. Engine Breakdown

Create:

```text
BacktestEngineBreakdownSnapshot
```

For each engine:

```text
engine_id
status
record_count
opportunities
selected_count
executed_count
hard_blocked_count
ce_net
gross_return_mean
expected_cost_mean
realized_cost_mean
drawdown_proxy
exec_rate
main_refusal_reason
sample_warning
```

Source:

```text
replay_metrics.json::engine_aggregates[]
feature_bridge.json::engines[]
decision_trace if available
```

---

# 12. Pair Breakdown

Create:

```text
BacktestPairBreakdownSnapshot
```

For each pair:

```text
pair
record_count
opportunities
selected_count
executed_count
ce_net
gross_return_mean
expected_cost_mean
realized_cost_mean
drawdown_proxy
exec_rate
sample_warning
```

Source:

```text
replay_metrics.json::pair_aggregates[]
```

---

# 13. Decision Trace

Create:

```text
BacktestDecisionTraceSnapshot
```

Parse last N records from:

```text
replay_dtr.jsonl
replay_dtr.json
service decision logs if explicitly documented
```

Fields:

```text
timestamp
pair
engine
raw_score
penalized_score
final_score
selected
hard_blocked
refusal_reason
expected_cost
ce_net
candidate_size
final_size
reason_codes
```

If no DTR file:

```text
source_status = not_yet_persisted
```

Do not invent a DTR from aggregates.

---

# 14. Refusal / Blocker Breakdown

Create:

```text
BacktestRefusalBreakdownSnapshot
```

Fields:

```text
top_refusal_reasons
hard_veto_count
soft_veto_count
economic_blocked_count
slippage_blocked_count
min_notional_blocked_count
data_stale_blocked_count
feature_missing_blocked_count
sterilization_ratio
status
```

Sources:

1. `replay_dtr.jsonl`
2. `refusal_journal dump`
3. `replay_metrics.json` aggregate fields
4. fallback `economic_sterilization_ratio` only

---

# 15. Cost Realism

Create:

```text
BacktestCostRealismSnapshot
```

Fields:

```text
expected_fee
realized_fee
expected_slippage
realized_slippage
spread_cost
impact_cost
expected_cost_mean
realized_cost_mean
cost_drift
cost_drift_ratio
status
```

Sources:

1. `cost_report.json`
2. `replay_metrics.json`
3. `replay_dtr.jsonl`
4. fallback cost drift formulas only

Status:

```text
ok if cost_drift_ratio <= 1.20
watch if <= 1.50
critical if > 1.50
unknown if missing
```

---

# 16. Data Quality / Anti-Leakage

Create:

```text
BacktestDataQualitySnapshot
```

Fields:

```text
rows
events
missing_rows
stale_rows
future_timestamp_violations
duplicate_timestamps
out_of_order_events
feature_missing_rows
lineage_lock_status
train_validation_test_split
purge_embargo_status
anti_leakage_status
parity_status
dtr_coverage
reason_codes
```

Sources:

```text
parity_diagnostics.json
replay_run_manifest.json
feature_bridge.json
replay_metrics.json
```

If no anti-leakage proof exists:

```text
anti_leakage_status = UNKNOWN
```

Do not infer PASS from absence of errors.

---

# 17. Baseline Comparison

Create:

```text
BacktestBaselineComparisonSnapshot
```

Inputs:

```text
current_export_dir
baseline_export_dir
```

Fields:

```text
current_ce_net
baseline_ce_net
delta_ce_net
current_drawdown
baseline_drawdown
delta_drawdown
current_cost
baseline_cost
delta_cost
current_exec_rate
baseline_exec_rate
delta_exec_rate
verdict
sample_warning
```

Source:

```text
current_export_dir/replay_metrics.json
baseline_export_dir/replay_metrics.json
```

If baseline is absent:

```text
source_status = missing
verdict = BASELINE_NOT_CONFIGURED
```

---

# 18. Statistical Proof

Create:

```text
BacktestStatisticalProofSnapshot
```

Fields:

```text
sharpe
sortino
profit_factor
max_drawdown
cvar
psr
dsr
hlz_status
trial_count
walk_forward_status
bootstrap_ci_status
sample_warning
formula_source_ledger_refs
```

Rules:

- Read from `statistical_report.json` first.
- If absent, use existing code functions if found.
- If absent and fallback allowed, compute display-only Sharpe/Sortino/Profit Factor/Max Drawdown/CVaR with warnings.
- Never fallback PSR/DSR/HLZ/POT/Energy.

---

# 19. Produced Artifacts

Create:

```text
BacktestProducedArtifactsSnapshot
```

For each produced file:

```text
name
path
size_bytes
mtime_iso
sha256
status
open_ref
artifact_kind
```

Expected files:

```text
backtest_report.json
replay_metrics.json
feature_bridge.json
replay_dtr.jsonl
parity_diagnostics.json
replay_run_manifest.json
risk_report.json
cost_report.json
statistical_report.json
comparison_report.json
audit_manifest.json
trade_log.csv
equity_curve.csv
review_export.md
```

If file absent:

```text
status = missing
```

Hash must be stable SHA256 over file bytes.

---

# 20. Reproducibility

Create:

```text
BacktestReproducibilitySnapshot
```

Fields:

```text
run_id
job_id
git_commit
code_version
config_hash
data_hash
artifact_hash
calibration_hash
created_at
signed_by
command_line
python_version
platform
```

Sources:

```text
audit_manifest.json
replay_run_manifest.json
job record
backtest_report.json
```

If missing:

```text
source_status = partial
```

---

# 21. Failure Diagnosis

Create:

```text
BacktestFailureDiagnosisSnapshot
```

Fields:

```text
failed
exit_code
failed_stage
last_successful_stage
error_summary
stdout_tail
stderr_tail
suggested_fix
reason_codes
```

Suggested fixes mapping:

```text
missing replay_metrics -> check export_dir and runner output
feature_bridge lineage missing -> regenerate feature bridge with lineage lock
parse_error -> inspect JSON file and runner stdout
no DTR -> enable DTR export in local replay
sample too small -> run longer window / more pairs
```

---

# 22. UI Requirements

## 22.1 Existing Launch Local Job form

Keep existing form.

Add warnings near it:

```text
Audited local runner only.
No live trading.
No runtime mutation.
```

## 22.2 Visual statuses

Use consistent badges:

```text
GREEN: ok / usable
YELLOW: partial / sample too small / stale
RED: failed / missing required source
GRAY: not_yet_persisted / not_configured
```

## 22.3 Formula Ledger visible

Add a collapsible section:

```text
Formula Source Ledger
```

For each metric:

```text
Metric | Source | Function/report | Fallback? | Status
```

This is mandatory.

---

# 23. Route Requirements

Update `/backtest`.

Update `/api/snapshot` to include:

```json
{
  "backtest": {
    "truth_status": {},
    "config": {},
    "economic_kpis": {},
    "engine_breakdown": {},
    "pair_breakdown": {},
    "decision_trace": {},
    "refusals": {},
    "cost_realism": {},
    "data_quality": {},
    "baseline": {},
    "statistical_proof": {},
    "artifacts": {},
    "reproducibility": {},
    "formula_ledger": {},
    "failure_diagnosis": {}
  }
}
```

No POST route changes unless current runner form already exists.

---

# 24. Tests

## 24.1 Formula ledger tests

Required:

```text
test_existing_formula_source_preferred_over_fallback
test_report_value_preferred_over_code_formula
test_fallback_marked_dashboard_only
test_psr_dsr_do_not_fallback
test_missing_formula_returns_not_yet_persisted
```

## 24.2 Metric tests

Required:

```text
test_exec_rate_formula
test_selection_rate_formula
test_economic_sterilization_ratio
test_cost_drift_ratio
test_baseline_delta_verdict
test_max_drawdown_from_equity_curve
test_profit_factor
test_sharpe_fallback_requires_periods_per_year
test_cvar_fallback_sample_warning
```

## 24.3 Source tests

Required:

```text
test_missing_replay_metrics_returns_runner_only
test_corrupt_replay_metrics_parse_error
test_feature_bridge_lineage_missing_sets_truth_verdict
test_dtr_missing_not_yet_persisted
test_artifact_hash_stable
test_reproducibility_partial_when_manifest_missing
```

## 24.4 Route/template tests

Required:

```text
test_backtest_page_renders_all_sections
test_api_snapshot_contains_backtest_section
test_jinja_templates_do_not_compute_formulas
test_dashboard_survives_all_sources_missing
```

## 24.5 Read-only invariant tests

Required grep or unit test:

```text
No write_text/write_bytes/atomic_write/os.kill/signal in state_backtest*.py
No engine/protocol/interface_contracts/calibration_methods diff
```

---

# 25. Commands to Run

Codex must run:

```bash
python -m py_compile src/cockpit/*.py
python -m pytest tests/cockpit/ -q
python scripts/run_engineering_guardrails.py
```

If route testing requires app launch:

```bash
python scripts/run_cockpit.py --port 8091
curl -s http://127.0.0.1:8091/backtest
curl -s http://127.0.0.1:8091/api/snapshot
```

---

# 26. Completion Criteria

Codex may return `COMPLETE` only if:

- formula ledger exists
- all formulas are source-mapped
- existing code/report formulas are preferred over fallback
- PSR/DSR/HLZ/POT/Energy have no dashboard fallback
- page renders with missing files
- economic KPIs visible
- engine/pair breakdown visible
- decision trace visible or explicitly `NOT_YET_PERSISTED`
- data quality / anti-leakage status visible
- baseline comparison visible or `BASELINE_NOT_CONFIGURED`
- produced artifact hashes visible
- reproducibility block visible
- tests pass
- read-only invariant is proven

Otherwise return `PARTIAL` or `BLOCKED`.

---

# 27. Codex Output Format

Return exactly:

```text
1. Source Ledger
2. Formula Source Ledger
3. Files inspected
4. Files created / modified
5. Sections implemented
6. Metrics implemented
7. Fallback formulas used
8. Forbidden formulas not implemented
9. Tests added
10. Test results
11. Read-only invariant proof
12. Remaining gaps
13. Completion status
```

---

# 28. Final Reminder

The Backtest dashboard is not allowed to become a quant library.

It is a truth surface.

It must show:

```text
what file produced the metric
which function/report owns the formula
whether the formula is fallback display-only
whether the sample is too small
whether the result is usable
whether the run is reproducible
```

If this cannot be proven, display `UNKNOWN`, `NOT_YET_PERSISTED`, or `FORMULA_SOURCE_MISSING`.

Do not invent.
