# V5.3 B_ML Operator White Book

Status: `B_ML_OPERATOR_GUIDE_READY`

## 1. Purpose

B_ML builds an ML training dataset from:

```text
A2 gold ex-ante features
-> B_ML candidate sampler
-> post-decision labels
-> labels/b_ml_label_store.jsonl
-> IA Lab / expected-edge training
```

B_ML is not a profitability backtest. It does not create trades, does not change
Engine A/B/C/D, does not change thresholds, and does not bypass hard blockers.

The target policy is:

```text
BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1
```

## 2. Best Config For First Launch

Use this configuration for the first clean launch from the Backtest dashboard:

```text
Phase: B_ML Training Label Factory
ML mode: ML_MODE_OFF
B_ML sampler mode: TEMPORAL_STRATIFIED_BACKGROUND_GRID
Pairs: start with one pair, BTCUSDT recommended for the smoke
Timeframes: start with 1m
Silver storage: jsonl_gz in A2
Label horizons: default 5m,15m,1h
Capital buckets: default 400,500,1500,4000
```

Recommended first feature set:

```text
close_return,
high_low_range,
volume,
spread_bps,
book_depth_levels,
cumulative_ofi,
vpin,
realized_vol_current
```

Add only after coverage is proven in A2:

```text
queue_pressure,
kyle_lambda,
realized_vol_at_break,
latency_penalty_bps
```

Reason: the first set balances row survival and microstructure value. The second
set can be useful, but missing or proxy provenance can block rows or downgrade
them to research-only.

## 3. Sampler Modes

### TEMPORAL_STRATIFIED_BACKGROUND_GRID

Best default for first launch.

What it does:

- reads A2 gold feature rows;
- samples decision timestamps by pair/timeframe/day;
- creates background candidates with `engine_id=background`;
- does not require B1;
- does not run engines;
- produces counterfactual labels when post-window and cost/fill inputs are available.

Use it when:

- A2 is ready but B1 is missing or not trusted yet;
- you want to verify that features and labels can be produced;
- you want maximum coverage before tying ML to engine-native candidates.

Expected result:

- `candidate_count > 0` if A2 gold rows exist;
- some rows may be `TRAINING_ROW_BLOCKED` near the end of the window if post-window is missing;
- `training_allowed=true` only if at least one row is `TRAINING_ROW_ELIGIBLE`.

### REUSE_B1_FAST_CANDIDATES

Best mode after B1 is clean.

What it does:

- reuses B1 `candidate_events.jsonl` / `preselection_candidates.jsonl`;
- preserves real `candidate_id`, `pair`, `timeframe`, `engine_id`;
- aligns each B1 candidate to the latest A2 feature row at or before decision time;
- does not run engines inside B_ML.

Use it when:

- B1 has produced native candidates for the same pair/timeframe/window;
- you want ML labels attached to actual engine candidate surfaces;
- you want the future IA Lab model to learn expected edge around native candidate events.

Do not use it when:

- B1 has not run;
- B1 candidate file is missing;
- B1 pair/timeframe differs from the B_ML request.

### ENGINE_NATIVE_DRY_EVAL

Current implementation: reused B1/native candidate artifacts only.

It does not create a new native engine evaluation inside B_ML. If B1/native
candidate artifacts are absent, this mode will not magically produce native
engine candidates.

Use it only when:

- upstream B1/native dry-eval artifacts already exist;
- the operator wants a strict native-only dataset.

Avoid it for first launch.

### ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID

Best later-stage mode when B1 is clean and A2 coverage is good.

What it does:

- reuses native/B1 candidates;
- also adds temporal background grid candidates;
- keeps both populations in one B_ML run.

Use it when:

- B1 is available;
- you want both native candidate labels and background market context;
- you are ready to audit class imbalance and row eligibility carefully.

Risk:

- larger dataset;
- more blocked/research-only rows if cost/fill/post-window coverage is incomplete;
- not ideal for first smoke.

## 4. Prerequisites Before Launch

### A2 prerequisites

A2 must have completed for the same workflow:

```text
phase_a2_data_factory/data_factory_manifest.json
phase_a2_data_factory/silver_index.json
phase_a2_data_factory/gold/features_<timeframe>/<pair>/*.jsonl*
```

Dashboard preview must show:

```text
PHASE_B_ML_LABEL_FACTORY_READY
```

If it shows blocked, do not launch. Fix the exact blocker first.

Common B_ML blockers:

```text
PHASE_B_ML_REQUIRES_A2_DATA_FACTORY_ARTIFACTS
PHASE_B_ML_REQUIRES_A2_GOLD_FEATURES
PHASE_B_ML_REQUIRES_A2_SILVER_INDEX
PHASE_B_ML_REQUIRES_B1_CANDIDATE_EVENTS
```

### B1 prerequisites

B1 is required only for these sampler modes:

```text
REUSE_B1_FAST_CANDIDATES
ENGINE_NATIVE_DRY_EVAL
ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID
```

Expected B1 path:

```text
phase_b1_candidate_discovery/backtest_strategy_ladder/<workflow_run_id>/fast_candidates/candidate_events.jsonl
```

For the first launch, avoid B1 dependency and use:

```text
TEMPORAL_STRATIFIED_BACKGROUND_GRID
```

## 5. Date Window Rule

B_ML labels need future rows after the decision timestamp.

Default horizons:

```text
5m,15m,1h
```

Therefore A2 must contain enough data after the final training decision. If the
B_ML window ends at the last available A2 row, the rows near the end will be
blocked by:

```text
LABEL_BLOCKED_BY_MISSING_POST_WINDOW
```

Best practice:

- A2 materialization window should include a tail after the intended training window.
- For dashboard launch, use a window where losing the last horizon tail is acceptable.
- For CLI precision, pass `--train-end` as the real training cutoff and keep `--end`
  large enough to read the post-window tail.

Example CLI concept:

```text
--start 2025-04-01
--end 2025-05-02
--train-end 2025-05-01
--label-horizons 5m,15m,1h
```

## 6. What To Inspect After Launch

Primary artifacts:

```text
manifest.json
labels/b_ml_label_store.jsonl
labels/b_ml_label_summary.json
labels/b_ml_target_policy_report.json
reports/b_ml_training_dataset_audit.json
reports/b_ml_training_row_eligibility_report.json
reports/b_ml_feature_label_leakage_report.json
reports/b_ml_cost_label_fidelity_report.json
reports/b_ml_train_eval_overlap_report.json
reports/b_ml_final_verdict.json
reports/b_ml_tabular_artifact_index.json
```

Minimum checks:

```text
row_count > 0
feature_leakage_count = 0
target_policy_mismatch_count = 0
train_eval_overlap_blocked = false
training_row_eligible_count > 0
training_allowed = true
scientifically_valid_for_training = true
scientifically_valid_for_promotion = false
```

Promotion remains false by doctrine. B_ML can feed training, but it is not a
live/shadow promotion proof.

Tabular mirrors:

```text
labels/b_ml_label_store.parquet
candidates/b_ml_candidate_events.parquet
features/b_ml_feature_matrix.parquet
windows/raw_window_index.parquet
windows/post_window_index.parquet
```

These Parquet/ZSTD files are performance mirrors only. The JSONL files remain
the audit source-of-truth. Consumers should use a Parquet mirror only if its
`*.tabular_manifest.json` status is `TABULAR_MIRROR_PARQUET_READY`.

Current reader behavior:

```text
1. check sibling *.tabular_manifest.json
2. use Parquet only when status = TABULAR_MIRROR_PARQUET_READY
3. require source_path match and audit_jsonl_preserved = true
4. fall back to JSONL if manifest is missing, invalid, or not ready
```

## 7. How To Interpret Row Status

```text
TRAINING_ROW_ELIGIBLE
```

The row has ex-ante features, post-decision label, no feature leakage, coherent
target policy, and non-blocked label fidelity.

```text
TRAINING_ROW_RESEARCH_ONLY
```

The row is useful for diagnosis, but cost/fill/proxy status is not strong enough
for governed expected-edge truth.

```text
TRAINING_ROW_BLOCKED
```

The row must not train expected-edge. Common causes:

```text
FEATURE_POST_DECISION_LEAKAGE
FEATURE_MISSING_ORDERBOOK_SOURCE
FEATURE_MISSING_TRADE_SOURCE
LABEL_BLOCKED_BY_MISSING_POST_WINDOW
LABEL_BLOCKED_BY_MISSING_BOOK
LABEL_BLOCKED_BY_STALE_BOOK
LABEL_BLOCKED_BY_SLIPPAGE_MEASUREMENT
```

## 8. Feature Rules

Allowed as X features only if available at or before decision time:

```text
close_return
high_low_range
volume
spread_bps
book_depth_levels
cumulative_ofi
vpin
queue_pressure
realized_vol_current
kyle_lambda
realized_vol_at_break
latency_penalty_bps
```

Never allowed as X features:

```text
mfe_bps
mae_bps
future_return
forward_return
realized_pnl
net_edge_label
break_even_outcome
trade_success
post_window_adverse_selection
```

Those can be labels/outcomes only.

## 9. Recommended Launch Sequence

### Smoke sequence

```text
1. A1 preview
2. A2 data factory
3. B_ML with TEMPORAL_STRATIFIED_BACKGROUND_GRID
4. Inspect b_ml_training_dataset_audit.json
5. If training_allowed=true, point IA Lab expected-edge training to labels/b_ml_label_store.jsonl
```

### Native candidate sequence

```text
1. A1 preview
2. A2 data factory
3. B1 candidate discovery
4. B_ML with REUSE_B1_FAST_CANDIDATES
5. Inspect B1/B_ML candidate alignment
6. Train IA Lab only on eligible B_ML rows
```

### Later-stage broad sequence

```text
1. A1 preview
2. A2 data factory with book/trades/klines coverage
3. B1 candidate discovery
4. B_ML with ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID
5. Audit class balance, label fidelity, and row eligibility
6. Train expected-edge artifact out-of-sample
7. Backtest with ML_MODE_OVERLAY_FROZEN
```

## 10. Best Config Summary

First truth dataset:

```text
B_ML sampler mode: TEMPORAL_STRATIFIED_BACKGROUND_GRID
Pairs: BTCUSDT
Timeframes: 1m
Features: close_return,high_low_range,volume,spread_bps,book_depth_levels,cumulative_ofi,vpin,realized_vol_current
Use B1: no
Use ML overlay: no
Expected verdict: BML_READY_RESEARCH or BML_READY_GOVERNED if cost/fill rows are eligible
```

Best native-candidate dataset after B1:

```text
B_ML sampler mode: REUSE_B1_FAST_CANDIDATES
Pairs: same as B1
Timeframes: same as B1
Features: same as first truth dataset, plus queue_pressure only if A2 coverage is proven
Use B1: yes
Use ML overlay: no
Expected verdict: BML_READY_RESEARCH until cost/fill is fully proven
```

Do not use as first launch:

```text
ENGINE_NATIVE_DRY_EVAL
ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID
```

They are useful only after B1/native candidate artifacts exist and have been
audited.

## 11. If B_ML Succeeds But Frozen ML Still Gives Zero Trades

That is not automatically a B_ML failure.

B_ML can replace expected-edge proxy only after IA Lab trains a governed artifact
from eligible rows. The frozen ML artifact still cannot bypass:

```text
native engine no_trade
cost/fill realism blockers
break-even blockers
sharia / spot-only / long-only blockers
stale or missing book
slippage not measured
```

If selected/executed remains zero after ML frozen, audit B2 blockers. Do not lower
thresholds or force trades from B_ML output.
