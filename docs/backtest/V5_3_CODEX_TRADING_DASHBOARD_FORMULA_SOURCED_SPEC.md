# V5.3 — TRADING DASHBOARD SCIENTIFIC / FORMULA-SOURCED SPEC

**Scope:** Cockpit page `Trading`  
**Target page:** `src/cockpit/templates/pages/trading.html`  
**Mode:** read-only trading truth surface  
**Critical rule:** the Trading page must display formulas and quant metrics **only when they already exist in code or in generated reports**. If a formula is missing, the cockpit must show `FORMULA_SOURCE_MISSING` / `NOT_YET_PERSISTED` and must not implement the missing quant formula inside display adapters.

---

# 0. Executive Decision

The Trading page must become a **scientific trading runtime dashboard**, not a place where new quant formulas are invented.

The page must answer:

```text
Are the engines seeing opportunities?
Are the decisions explainable?
Is the edge still positive after cost?
Are costs/slippage/liquidity/toxicity under control?
Are features modern, traceable, and fresh?
Is the sample large enough to interpret the result?
Which formulas are actually backed by existing code/reports?
```

## Golden Rule

```text
Existing quant formula/report value exists  -> read it and display it.
Formula exists in domain code               -> call/read the existing canonical function only if safe.
Formula does not exist                      -> show FORMULA_SOURCE_MISSING.
Dashboard wants a derived trading metric    -> do NOT implement it in display code unless explicitly allowed as a non-quant display diagnostic.
```

The cockpit is a truth surface, not a quant library.

---

# 1. Current Trading Page Audit

The current `trading.html` already displays:

```text
Selected pair
Market stat cards
Engines active / dormant / suspended
Economics status + ce_net
PHASE 2.5 Operational Proof Metrics
Engine Why
Economic Sterilization
Decision Trace
Data Quality
Engines Grid
Replay Metrics
Capacity Guard
Feature Bridge
Calibration Thresholds
Sizing Chain
```

This is a good foundation, but it still lacks a **Formula Source Ledger** and a strict distinction between:

```text
metric read from report
metric read from existing domain formula
metric display-derived
metric missing
metric forbidden in dashboard
```

---

# 2. Page Ownership

## 2.1 Trading page owns

The Trading page owns:

```text
engine activity
pair activity
engine x pair behavior
decision trace
score anatomy
edge after cost
cost realism
economic sterilization
sizing chain
feature integrity
microstructure feature presence
sample-size guard
trading thresholds used by engines
trading-readiness verdict
```

## 2.2 Trading page does not own

The Trading page must not become:

```text
VPS infra page
Shadow warmup page
IA Lab artifact page
Backtest formula ledger page
Logs explorer
Prometheus/Grafana observability page
runtime action page
```

Only compact badges may be repeated:

```text
service_status
queue_consumption_status
warmup_passed
source_freshness
```

Full diagnostics stay on their owner pages.

---

# 3. Non-Negotiable Safety Rules

## R1 — Read-only

Forbidden in Trading state adapters/templates:

```text
write_text
write_bytes
atomic_write
os.kill
signal
queue writes
engine activation
runtime mode mutation
artifact activation
live/micro-live promotion
```

## R2 — No formula invention in display code

The Trading page must not create new implementations for:

```text
PSR
DSR
HLZ
POT-GPD
Energy distance
Sharpe
Sortino
CVaR
Kyle lambda
Amihud
Roll
Corwin-Schultz
realized kernel volatility
VPIN
PIN
Hawkes intensity
OFI
queue pressure
walls/spoofing/deceptive liquidity formulas
slippage model
fill probability
toxicity model
```

If these exist in domain code or reports, display them.  
If they do not exist, show:

```text
FORMULA_SOURCE_MISSING
```

## R3 — No formulas in Jinja

Templates may format values only.

Forbidden in Jinja:

```text
financial formulas
ratio formulas
if/else trading rules beyond display badges
threshold logic except simple status rendering from model fields
```

All computed values must come from typed Python state objects.

## R4 — Do not modify protected backend

Do not modify:

```text
src/engines/
src/protocols/
src/interface_contracts/
src/calibration_methods/
src/meta_learning/
src/meta_minimal/
src/execution_backbone/
```

unless the task explicitly changes from dashboard work to backend formula implementation.

## R5 — Missing formula is a valid output

If a metric is scientifically desired but not currently produced:

```text
Display: FORMULA_SOURCE_MISSING
Add to ledger: missing formula source
Add backlog suggestion: domain-layer implementation required
Do not fake it in cockpit
```

---

# 4. Formula Source Ledger

Create a Trading-specific formula ledger:

```text
src/cockpit/state_trading_formula_ledger.py
```

or integrate into an existing cockpit formula ledger if present.

## 4.1 Model

Create a typed model:

```text
TradingFormulaLedgerEntry
```

Fields:

```text
metric_id
display_name
metric_family
desired_on_trading_page
source_status
source_report_file
source_code_file
source_function
display_value_available
dashboard_computed
fallback_allowed
reason_codes
backlog_target_if_missing
```

Allowed `source_status`:

```text
REPORT_VALUE_FOUND
CODE_FORMULA_FOUND
DISPLAY_DIAGNOSTIC_DERIVED
FORMULA_SOURCE_MISSING
NOT_YET_PERSISTED
FORBIDDEN_IN_DASHBOARD
```

## 4.2 Mandatory ledger section on Trading page

Add a collapsible section:

```text
Trading Formula Source Ledger
```

Columns:

```text
Metric
Family
Source status
Report/code source
Displayed?
Dashboard computed?
Backlog if missing
```

This makes the page audit-safe.

---

# 5. Formula Discovery Procedure

Before modifying UI, Codex must search existing code and reports.

## 5.1 Search report fields

Inspect latest available files:

```text
build/**/replay_metrics.json
build/**/feature_bridge.json
build/**/replay_dtr.jsonl
build/**/cost_report.json
build/**/risk_report.json
build/**/statistical_report.json
build/**/trade_log.jsonl
build/**/live_websocket_snapshot_batch.json
build/**/shadow_vps_service.state.json
config/calibration/v1/thresholds.yml
```

## 5.2 Search code formulas

Codex must run searches equivalent to:

```text
grep -R "ce_net\|gross_return\|expected_cost\|realized_cost" -n src tests
grep -R "slippage\|spread_cost\|impact_cost\|fee" -n src tests
grep -R "ofi\|order_flow_imbalance" -n src tests
grep -R "vpin\|pin" -n src tests
grep -R "queue_pressure" -n src tests
grep -R "kyle\|lambda" -n src tests
grep -R "amihud" -n src tests
grep -R "roll\|corwin\|schultz" -n src tests
grep -R "realized_kernel\|kernel_vol" -n src tests
grep -R "hawkes" -n src tests
grep -R "walls\|spoof\|deceptive_liquidity\|microprice" -n src tests
grep -R "toxicity\|toxic" -n src tests
grep -R "fill_probability\|partial_fill\|queue_position" -n src tests
grep -R "sharpe\|sortino\|cvar\|expected_shortfall" -n src tests
grep -R "psr\|probabilistic_sharpe\|dsr\|deflated_sharpe" -n src tests
```

## 5.3 Output required before implementation

Codex must output:

```text
Formula Search Ledger
- formulas found in reports
- formulas found in code
- formulas absent
- formulas forbidden in cockpit
- formulas requiring backend-domain implementation
```

If this search is skipped, the task is invalid.

---

# 6. Metric Families for Trading Page

## 6.1 Engine / pair activity

Display only from existing reports:

```text
engine_id
pair
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
```

Preferred sources:

```text
replay_metrics.json::engine_aggregates[]
replay_metrics.json::pair_aggregates[]
replay_dtr.jsonl
```

If engine-pair matrix is absent:

```text
engine_pair_matrix = NOT_YET_PERSISTED
```

Do not synthesize engine-pair matrix from global aggregates.

---

## 6.2 Decision Trace

Desired fields:

```text
timestamp
pair
engine
raw_score
feature_score
penalized_score
final_score
selected
hard_blocked
refusal_reason
expected_cost
realized_cost
ce_net
candidate_size
final_size
reason_codes
```

Source priority:

```text
replay_dtr.jsonl
service decision log
```

If DTR does not exist:

```text
DECISION_TRACE_NOT_YET_PERSISTED
```

Do not reconstruct from aggregates.

---

## 6.3 Score Anatomy

Desired fields:

```text
raw_score
feature_score
penalty_score
cost_penalty
toxicity_penalty
final_score
entry_threshold
score_margin
```

Rules:

```text
score_margin may be displayed only if final_score and entry_threshold are already present.
If entry_threshold source missing -> FORMULA_SOURCE_MISSING.
Do not invent entry threshold.
Do not infer entry threshold from selected=true.
```

---

## 6.4 Edge after cost

Source priority:

```text
ce_net from replay_metrics/report
domain function if present
```

Desired fields:

```text
gross_edge
expected_cost
realized_cost
ce_net
edge_cost_ratio
```

Rules:

```text
If ce_net exists: display report value.
If ce_net missing: do not invent net edge in cockpit unless domain code has a canonical function.
If edge_cost_ratio not already present: show FORMULA_SOURCE_MISSING unless explicitly classified as display diagnostic.
```

---

## 6.5 Cost realism

Desired fields:

```text
expected_cost_mean
realized_cost_mean
cost_drift
cost_drift_ratio
expected_fee
realized_fee
expected_slippage
realized_slippage
spread_cost
impact_cost
```

Rules:

```text
expected_cost_mean / realized_cost_mean: display from report.
cost_drift / cost_drift_ratio: may be DISPLAY_DIAGNOSTIC_DERIVED only if both report values exist.
expected_fee / realized_fee / slippage / spread / impact: display only if report/code source exists.
If missing: NOT_YET_PERSISTED.
```

Allowed display diagnostic:

```text
cost_drift = realized_cost_mean - expected_cost_mean

cost_drift_ratio = realized_cost_mean / max(abs(expected_cost_mean), eps)
```

It must be marked:

```text
DISPLAY_DIAGNOSTIC_DERIVED
```

not canonical quant formula.

---

## 6.6 Economic sterilization

Desired fields:

```text
total_opportunities
selected_count
executed_count
hard_blocked_count
rejected_count
cost_blocked_count
slippage_blocked_count
min_notional_blocked_count
data_stale_blocked_count
feature_missing_blocked_count
sterilization_ratio
```

Rules:

```text
Counts must come from report/DTR/refusal source.
sterilization_ratio may be DISPLAY_DIAGNOSTIC_DERIVED only from existing counts.
If counts missing: NOT_YET_PERSISTED.
```

Allowed display diagnostic:

```text
blocked_or_rejected_count = max(total_opportunities - selected_count, 0)

sterilization_ratio =
    blocked_or_rejected_count / max(total_opportunities, 1)
```

Must be marked display-only.

---

## 6.7 Market data quality

Desired fields:

```text
pair
last_price
best_bid
best_ask
mid_price
spread_bps
last_event_ns
age_ms
depth_available
ws_gap_seconds
time_sync_offset_ms
stale_flag
top_of_book_valid
```

Rules:

```text
best_bid / best_ask must come from snapshot report/source.
mid_price and spread_bps may be DISPLAY_DIAGNOSTIC_DERIVED only if bid/ask exist.
age_ms may be DISPLAY_DIAGNOSTIC_DERIVED only if now/event timestamp exists.
If no bid/ask: MISSING_DEPTH.
If best_bid >= best_ask: BROKEN_BOOK.
```

Allowed display diagnostics:

```text
mid_price = (best_bid + best_ask) / 2

spread_bps = ((best_ask - best_bid) / max(mid_price, eps)) * 10000

age_ms = (now_ns - last_event_ns) / 1_000_000
```

---

## 6.8 Feature integrity / microstructure formulas

Desired modern features to show if present:

```text
OFI
VPIN
PIN
queue_pressure
Kyle lambda
Amihud
Roll spread
Corwin-Schultz spread
realized kernel volatility
Hawkes intensity
walls/spoofing
deceptive_liquidity_score
microprice_pressure
book_shape_skew
wall_persistence
near_touch_cancel_ratio
executed_vs_displayed
```

Rules:

```text
Display only if feature_bridge/reports/code expose them.
Do not implement missing feature formulas in cockpit.
If feature family absent: show NOT_YET_PERSISTED or FORMULA_SOURCE_MISSING.
```

Forbidden classic indicators:

```text
RSI
MACD
Bollinger
Stochastic
ADX
Ichimoku
Elliott
candlestick pattern
```

If found in Trading UI, fail the task.

---

## 6.9 Sizing chain

Desired fields:

```text
forecast_score
vol_target
penalized_score
tier
candidate_size
final_size
min_notional_check
capital_cap_check
fee_safe_check
fee_safe_margin
size_reduction_ratio
```

Rules:

```text
Display only from DTR/report/domain sizing output.
size_reduction_ratio may be display-derived if candidate_size and final_size exist.
fee_safe_margin may be display-derived only if expected_edge_bps and expected_cost_bps exist.
If input missing: FORMULA_SOURCE_MISSING.
```

Allowed display diagnostics:

```text
size_reduction_ratio = final_size / max(candidate_size, eps)

fee_safe_margin = expected_edge_bps - expected_cost_bps
```

Mark both as display-only.

---

## 6.10 Sample-size guard

This is mandatory.

Fields:

```text
total_opportunities
selected_count
executed_count
engine_record_min
pair_record_min
sample_status
sample_message
```

Rules:

```text
TOO_SMALL if total_opportunities < 30 or executed_count < 30
WATCH if total_opportunities < 100
OK otherwise
```

This is a display guard, not a promotion gate.

Message:

```text
SAMPLE TOO SMALL — DO NOT INTERPRET TRADING PERFORMANCE
```

---

# 7. Trading Readiness Verdict

Create:

```text
src/cockpit/state_trading_readiness.py
```

Model:

```text
TradingReadinessSnapshot
```

Fields:

```text
market_data_status
engine_status
feature_lineage_status
cost_status
decision_trace_status
sample_status
economics_status
trading_verdict
reason_codes
```

Allowed verdicts:

```text
NOT_INTERPRETABLE
SHADOW_THIN
SHADOW_READY
```

No micro-live candidate here.

Rules:

```text
NOT_INTERPRETABLE if market_data_status != ok
NOT_INTERPRETABLE if active_engine_count == 0
SHADOW_THIN if sample_status in [TOO_SMALL, WATCH]
SHADOW_THIN if feature_lineage_status missing/invalid
SHADOW_THIN if decision_trace not persisted
SHADOW_READY only if:
    market_data ok
    at least one active engine
    feature lineage valid/present
    ce_net report value > 0
    costs included or cost_status ok/watch
    sample_status ok
```

If any required source missing:

```text
trading_verdict = NOT_INTERPRETABLE
```

---

# 8. UI Layout for Trading Page

Update `trading.html` order:

```text
1. Trading Readiness Verdict
2. Selected Pair Market Data Quality
3. Engines Active / Dormant / Suspended cards
4. Engine Why State
5. Engine × Pair Matrix
6. Pair Breakdown
7. Economic KPIs
8. Cost Realism
9. Edge After Cost
10. Economic Sterilization
11. Decision Trace
12. Score Anatomy
13. Feature Integrity / Microstructure Features
14. Data Quality Live
15. Capacity Guard
16. Trading Calibration Thresholds
17. Sizing Chain
18. Sample Size Guard
19. Trading Formula Source Ledger
```

Keep current sections that already exist. Add the missing sections as partials.

---

# 9. Files to Create / Modify

## 9.1 New state adapters

Create if missing:

```text
src/cockpit/state_trading_formula_ledger.py
src/cockpit/state_trading_readiness.py
src/cockpit/state_pair_breakdown.py
src/cockpit/state_engine_pair_matrix.py
src/cockpit/state_score_anatomy.py
src/cockpit/state_cost_realism.py
src/cockpit/state_edge_after_cost.py
src/cockpit/state_trading_feature_integrity.py
src/cockpit/state_trading_sample_guard.py
src/cockpit/state_market_data_quality.py
```

If equivalent adapters exist, extend them instead of duplicating.

## 9.2 New templates

Create if missing:

```text
src/cockpit/templates/partials/_trading_readiness.html
src/cockpit/templates/partials/_market_data_quality.html
src/cockpit/templates/partials/_pair_breakdown.html
src/cockpit/templates/partials/_engine_pair_matrix.html
src/cockpit/templates/partials/_score_anatomy.html
src/cockpit/templates/partials/_cost_realism.html
src/cockpit/templates/partials/_edge_after_cost.html
src/cockpit/templates/partials/_trading_feature_integrity.html
src/cockpit/templates/partials/_trading_sample_guard.html
src/cockpit/templates/partials/_trading_formula_ledger.html
```

## 9.3 Existing files to update

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/templates/pages/trading.html
tests/cockpit/
```

Do not modify backend protected modules.

---

# 10. Tests

Create tests:

```text
tests/cockpit/test_state_trading_formula_ledger.py
tests/cockpit/test_state_trading_readiness.py
tests/cockpit/test_state_market_data_quality.py
tests/cockpit/test_state_pair_breakdown.py
tests/cockpit/test_state_engine_pair_matrix.py
tests/cockpit/test_state_score_anatomy.py
tests/cockpit/test_state_cost_realism.py
tests/cockpit/test_state_edge_after_cost.py
tests/cockpit/test_state_trading_feature_integrity.py
tests/cockpit/test_state_trading_sample_guard.py
tests/cockpit/test_routes_trading_page.py
```

## 10.1 Mandatory test cases

```text
test_formula_ledger_marks_existing_report_values
test_formula_ledger_marks_missing_quant_formula_as_missing
test_no_quant_formula_implemented_in_display_adapter
test_ce_net_report_value_preferred
test_cost_drift_display_diagnostic_marked
test_market_data_spread_from_bid_ask_only
test_broken_book_detected
test_pair_breakdown_from_replay_metrics
test_engine_pair_matrix_not_synthesized_from_global_aggregates
test_score_margin_not_computed_without_threshold
test_feature_integrity_shows_missing_formula_for_absent_modern_features
test_classic_indicators_forbidden
test_sample_too_small_warning
test_trading_verdict_not_interpretable_when_sources_missing
test_trading_page_renders_all_sections
test_dashboard_survives_all_sources_missing
```

---

# 11. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run grep checks:

```bash
grep -iE "rsi|macd|bollinger|stochastic|adx|ichimoku|elliott|candlestick" src/cockpit/templates/pages/trading.html src/cockpit/templates/partials/
```

Expected: 0 matches except explicit `NO_CLASSIC_INDICATORS` text.

```bash
grep -E "def .*sharpe|def .*sortino|def .*cvar|def .*psr|def .*dsr|vpin|kyle|amihud|hawkes|realized_kernel" src/cockpit/state_trading*.py src/cockpit/state_*trading*.py
```

Expected: no new formula implementations. Ledger references are OK if they do not implement the math.

```bash
grep -E "write_text|write_bytes|atomic_write|os.kill|signal\." src/cockpit/state_trading*.py src/cockpit/state_*trading*.py
```

Expected: 0 matches.

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal
```

Expected: empty.

---

# 12. Acceptance Criteria

Return `COMPLETE` only if:

```text
Trading Formula Source Ledger exists
Every desired quant metric is source-mapped
Missing formulas are displayed as FORMULA_SOURCE_MISSING / NOT_YET_PERSISTED
No missing quant formula is implemented in display code
ce_net report value is preferred over fallback
Cost/sterilization/spread formulas are marked DISPLAY_DIAGNOSTIC_DERIVED if used
Classic indicators are absent
Trading readiness verdict is visible
Pair breakdown is visible
Engine-pair matrix is visible or explicitly NOT_YET_PERSISTED
Score anatomy is visible or FORMULA_SOURCE_MISSING
Feature integrity modern formulas are source-mapped
Sample-size guard is visible
All tests pass
Read-only invariant is proven
```

If not, return:

```text
PARTIAL
```

or:

```text
BLOCKED
```

with exact missing source/formula.

---

# 13. Codex Output Format

Codex must return exactly:

```text
1. Source Ledger
2. Formula Search Ledger
3. Current Trading Page Audit
4. Files Created / Modified
5. Sections Added
6. Formula Source Ledger Summary
7. Metrics Displayed From Existing Reports
8. Metrics Displayed From Existing Code
9. Display Diagnostics Derived
10. Missing Formulas Not Implemented
11. Tests Added
12. Test Results
13. Read-only Guardrail Proof
14. Remaining Gaps
15. Completion Status
```

---

# 14. Final Reminder

The page must not pretend that a metric exists.

The correct behavior is:

```text
Formula exists in report/code -> display it.
Formula does not exist        -> display FORMULA_SOURCE_MISSING.
Source file absent            -> display NOT_YET_PERSISTED.
Sample too small              -> display warning.
Dashboard formula invented    -> forbidden.
```

The Trading page must become a scientific truth surface, not a hidden quant engine.
