# V5.3 Backtest + IA Lab ML Operator Guide

## Purpose

This document explains how to work with the current V5.3 backtest rail and the current IA Lab ML rail after the recent patches.

It answers one practical question first:

**What comes first?**

**Backtest comes first. IA Lab comes second.**

The backtest rail is the canonical truth rail.
The IA Lab rail is a governed research and handoff rail built on top of backtest evidence.

Do not start from ML.
Do not use IA Lab as a replacement for A1/A2/B1/B2.


## The Order

### 1. `/backtest` is first

Use the backtest page first for:

1. `PHASE_A1_PREVIEW`
2. `PHASE_A2_DATA_FACTORY`
3. `PHASE_B1_CANDIDATE_DISCOVERY`
4. `PHASE_B2_DETAILED_REPLAY`

This is the canonical path because it gives you:

- source/date validation
- raw to silver to gold data proof
- candidate discovery proof
- detailed replay proof
- refusal and trade ledgers
- backtest proof status
- execution fidelity blockers
- replay-grounded B2 artifacts

### 2. `/lab` is second

Use the lab page only after backtest has already produced useful evidence.

The lab page is for:

- ML handoff preview
- rolling ML window planning
- governed expected-edge training
- frozen artifact packaging
- backtest ML input sidecar generation

The preferred scientific input for IA Lab is a **B2 run root**.
The older kline-only path still exists as fallback, but it is not the preferred canon anymore.


## What Each Phase Does

### Phase A1 - Preview

Page: `/backtest`

Goal:

- validate roots
- validate pairs
- validate dates
- validate common intersection across orderbook / trades / klines / metadata

What you inspect:

- `source_date_preview_manifest.json`
- preview blockers on the dashboard

If A1 is blocked:

- do not continue
- fix roots, pairs, or dates first


### Phase A2 - Data Factory

Page: `/backtest`

Goal:

- build the canonical data rail
- materialize the research-ready data artifacts

Current data logic:

- raw -> bronze -> silver -> gold

Important output artifacts:

- `data_factory_manifest.json`
- `silver_index.json`
- `raw_data_processing_report.json`
- `gold_microstructure_feature_manifest.json`
- `expected_edge_feature_manifest.json`

What A2 proves:

- source coverage
- schema readiness
- compression/storage status
- feature group readiness

If A2 is blocked:

- do not go to B1 or IA Lab
- fix data quality, metadata, compression, or missing feature groups


### Phase B1 - Candidate Discovery

Page: `/backtest`

Goal:

- generate candidate events from the canonical feature store

Important output artifacts:

- `fast_candidates/candidate_events.jsonl`
- `fast_candidates/candidate_summary.json`

What B1 tells you:

- candidate count
- pair / engine coverage
- whether the discovery run was sample-capped

If B1 is weak:

- the problem is still upstream in data, feature quality, or strategy logic
- do not jump to ML yet


### Phase B2 - Detailed Replay

Page: `/backtest`

Goal:

- replay the selected candidates with execution-aware evidence
- produce the real diagnostic truth for the current slice

Important output artifacts:

- `run_manifest.json`
- `reports/strategy_ladder_summary.json`
- `trade_detail_ledger.jsonl`
- `refusal_ledger.jsonl`
- `loss_analysis_ledger.jsonl`
- `reports/engine_matrix.json`
- `reports/pair_matrix.json`
- `reports/timeframe_matrix.json`
- `reports/governed_audit_evidence_index.json`
- `replay_performance_profile.json`

This is the phase that tells you:

- did the candidates survive detailed replay?
- are there executed trades or not?
- what are the fidelity blockers?
- what is the real backtest proof state?

If B2 ends in `STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES`:

- do not try to fix this first with ML
- treat it as a backtest / execution / selection problem first


## Where ML Starts

ML starts **after** you have a meaningful B2 result.

That means:

1. You already ran A1
2. You already ran A2
3. You already ran B1
4. You already ran B2
5. You have a B2 run root worth studying

Only then go to `/lab`.


## The IA Lab Workflow

### Step 1 - Fill the IA Lab form

Page: `/lab`

Use:

- `kline_root`
- `orderbook_root`
- `trades_root`
- `metadata_root`
- `b2_run_root`
- train window
- requested backtest window
- train / validation / freshness / chunk days

If your goal is scientific ML, the critical field is:

- `b2_run_root`

because that is what unlocks the replay-grounded label path.


### Step 1A - Exact folder mapping for `/lab`

Do not put the whole backtest workflow root into every field.
Each IA Lab field has one exact role.

Use this mapping:

- `kline_root` -> raw klines root such as `L:\klines\BTCUSDT` or `L:\klines`
- `orderbook_root` -> raw orderbook root such as `L:\ordrebookpart1\BTCUSDT` or `L:\ordrebookpart1`
- `trades_root` -> raw trades root such as `L:\trades\BTCUSDT` or `L:\trades`
- `metadata_root` -> historical metadata cache root such as `K:\v5.3 backtest\metadata\bybit\spot`
- `b2_run_root` -> one exact `phase_b2_detailed_replay/backtest_strategy_ladder/<run_id>` directory
- `handoff_export_dir` -> one dedicated ML export directory, separate from the original B2 run if possible

For the real run discussed in this chantier, the correct `b2_run_root` example is:

- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-d99ebf0186a0a273\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-d99ebf0186a0a273`

What not to do:

- do not put `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-d99ebf0186a0a273` into `b2_run_root`
- do not put `phase_a2_data_factory` into `kline_root`
- do not put a `phase_b1_candidate_discovery` directory into any IA Lab source field
- do not reuse the same directory for raw sources and handoff exports

Current repo truth:

- `b2_run_root` is the preferred scientific path because it provides replay-grounded labels
- `kline_root` is still required by the current trainer rail
- `orderbook_root`, `trades_root`, and `metadata_root` are important for provenance and future data rails, but the current expected-edge trainer is not yet fully consuming all of them as direct training tensors


### Step 2 - Preview first

Use the IA Lab preview before launch.

The preview should tell you:

- source scope readiness
- rolling ML plan status
- required artifact count for the requested backtest window

Important output artifacts:

- `rolling_ml_window_plan.json`
- `rolling_ml_window_plan.md`

Rule:

- if the requested backtest is longer than freshness, one artifact is not enough
- the plan must split the run into rolling chunks


### Step 2A - What the rolling plan means

The rolling plan is not optional decoration.
It is the proof that one frozen artifact cannot illegally cover too much future backtest time.

Read it like this:

- each chunk has its own `train_start` -> `train_end`
- then its own `validation_start` -> `validation_end`
- then its own backtest chunk start/end
- `validation_end` must be exactly one day before `backtest_chunk_start`
- `artifact_stale_after` defines the maximum backtest coverage allowed for the artifact trained on that chunk

If the requested backtest is `130` days and freshness is `30` days:

- one artifact is not enough
- the plan should require multiple chunks
- this is correct fail-closed behavior, not an inconvenience to bypass


### Step 3 - Train / Handoff

When preview is acceptable, launch the IA Lab handoff.

Important output artifacts:

- `strategy_ladder_ml_lab_handoff_report.json`
- `strategy_ladder_backtest_ml_input.json`
- `strategy_ladder_expected_edge_ml_model_artifact.json`
- `strategy_ladder_expected_edge_ml_model_artifact.summary.json`
- `ml_anti_leakage_proof_artifact.json`
- `ml_live_drift_snapshot.json`

Current doctrine:

- training is governed
- transport is governed
- the output is frozen for backtest consumption
- this does **not** auto-promote anything


### Step 3A - What "launch" really does

The IA Lab launch is not "turn ML on in production".
It does a governed research handoff.

Operationally, it should do this:

1. read the selected raw roots and the selected `b2_run_root`
2. build or read the replay-grounded B2 label store
3. attach anti-leakage and walk-forward metadata
4. train the expected-edge artifact in research mode
5. freeze the artifact for backtest-side overlay usage
6. emit the sidecars and reports needed for audit

That means the training launch is valid only if:

- the B2 run exists
- the label store is readable
- the rolling plan is coherent for the requested backtest horizon
- the anti-leakage proof is emitted

It does not mean:

- automatic promotion
- live deployment
- freshness bypass
- blocker removal


### Step 3B - Minimum operator checklist before training

Before pressing launch in `/lab`, verify all of this:

1. `run_manifest.json` exists in the chosen `b2_run_root`
2. `reports/strategy_ladder_summary.json` exists in the chosen `b2_run_root`
3. the `b2_run_root` points to one exact Strategy Ladder replay run, not a parent workflow directory
4. `kline_root` is a raw source directory, not a workflow artifact directory
5. the rolling plan preview is present
6. the rolling plan status is not blocked by missing train history
7. if the requested backtest exceeds freshness, the required artifact count is greater than `1`
8. you have a dedicated `handoff_export_dir` if you want stable artifact collection


### Step 3C - What to read after training

After the IA Lab job finishes, inspect these files first:

1. `strategy_ladder_ml_lab_handoff_report.json`
2. `strategy_ladder_b2_label_store.jsonl`
3. `label_store_summary.json`
4. `label_store_quality_report.json`
5. `rolling_ml_window_plan.json`
6. `ml_anti_leakage_proof_artifact.json`
7. `strategy_ladder_expected_edge_ml_model_artifact.summary.json`
8. `strategy_ladder_backtest_ml_input.json`

Read them in this order:

1. Did the handoff complete?
2. Was the label source replay-grounded or still proxy?
3. How many labels were replay-grounded vs proxy?
4. Is anti-leakage attached?
5. How many frozen artifacts are required by the rolling plan?
6. What exact backtest-side ML input was emitted?


## The New Label Store Order

The expected-edge trainer should now be thought about in this order:

1. `B2 detailed replay`
2. `strategy_ladder_b2_label_store.jsonl`
3. `label_store_summary.json`
4. `label_store_quality_report.json`
5. expected-edge training artifact
6. frozen artifact handoff back to backtest

Important output artifacts:

- `strategy_ladder_b2_label_store.jsonl`
- `label_store_summary.json`
- `label_store_quality_report.json`

This is important because the trainer is no longer supposed to be understood as "close-return ML first".
The correct mental model is now:

**Replay truth first, model second.**


### Step 4A - How to interpret the label store

The label store is now the scientific bridge between replay and ML.

The operator questions are:

1. `label_source_type`: is this really replay-grounded, or still proxy execution?
2. `replay_grounded_label_count`: how many rows are backed by replay truth?
3. `proxy_execution_label_count`: how many rows are still based on partial execution realism?
4. `net_positive_rate`: is the dataset trivially all negative or all positive?
5. `break_even_clearance_rate`: are labels clearing realistic costs?
6. `MFE/MAE availability`: do we truly have excursion evidence, or are those fields null?
7. `execution_fidelity_status`: are we still blocked by spread/slippage/adverse-selection proxies?

If the label store says proxy execution or research-only:

- treat the artifact as research-only
- do not reinterpret it as promotion-grade
- keep `EXPECTED_EDGE_PROXY_BLOCKED` as healthy fail-closed behavior


## When To Re-run Backtest With ML

Only after IA Lab has produced a frozen artifact and the rolling plan is coherent.

The backtest-side ML mode to think about is:

- `ML_MODE_OVERLAY_FROZEN`

But keep these rules:

- `ML_MODE_OFF` stays the default
- do not enable ML just because the lab can train
- do not use one artifact for a long backtest beyond freshness
- do not bypass `rolling_ml_window_plan`


## What Stays Blocked On Purpose

Even after the new patches, some blockers are supposed to remain active unless the evidence truly exists.

The most important one is:

- `EXPECTED_EDGE_PROXY_BLOCKED`

Treat it as healthy fail-closed behavior unless all of this becomes true:

1. the label store is replay-grounded
2. anti-leakage is proven
3. walk-forward metadata is attached
4. execution fidelity is good enough
5. shadow/live parity is proven enough for the intended usage

So:

- do not clear `EXPECTED_EDGE_PROXY_BLOCKED` manually
- do not reinterpret proxy labels as promotion-grade truth


## The Practical Working Loop

For a new research slice, the normal order is:

1. Go to `/backtest`
2. Run `PHASE_A1_PREVIEW`
3. Run `PHASE_A2_DATA_FACTORY`
4. Run `PHASE_B1_CANDIDATE_DISCOVERY`
5. Run `PHASE_B2_DETAILED_REPLAY`
6. Read `run_manifest.json` and `reports/strategy_ladder_summary.json`
7. If B2 is poor, debug backtest/execution/data first
8. If B2 is worth learning from, go to `/lab`
9. Preview the ML handoff and rolling plan
10. Train the governed artifact
11. Return to backtest only if you want a frozen-ML rerun

Short version:

**Backtest explains what happened.**
**IA Lab tries to learn from what happened.**
**Backtest is the first truth rail.**


## How To Think About Problems

### If A1 fails

It is a source/date/pair problem.

### If A2 fails

It is a data engineering / schema / feature readiness problem.

### If B1 is weak

It is a candidate discovery or feature usefulness problem.

### If B2 is weak

It is a replay / execution / selection / cost realism problem.

### If the label store is proxy-only

The ML result stays research-only.

### If the rolling plan requires many artifacts

That is normal.
It means the freshness rule is being enforced correctly.


## Dashboard Use

### Use `/backtest` for:

- source and date selection
- canonical phase progression
- replay diagnostics
- proof and blocker reading
- performance profile reading

### Use `/lab` for:

- ML handoff preview
- B2-root-driven training
- rolling window planning
- frozen artifact preparation


## One Concrete Example

If you want to train from the known run `strategy_ladder_workflow-d99ebf0186a0a273`, the operator flow is:

1. open `/lab`
2. set `kline_root` to `L:\klines` or `L:\klines\BTCUSDT`
3. set `orderbook_root` to `L:\ordrebookpart1` or `L:\ordrebookpart1\BTCUSDT`
4. set `trades_root` to `L:\trades` or `L:\trades\BTCUSDT`
5. set `metadata_root` to `K:\v5.3 backtest\metadata\bybit\spot`
6. set `b2_run_root` to `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-d99ebf0186a0a273\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-d99ebf0186a0a273`
7. choose the requested backtest start/date horizon
8. preview the rolling plan first
9. launch only if the rolling plan and label-store path are coherent
10. inspect the generated handoff and label-store reports before any frozen-ML rerun in `/backtest`


## Final Doctrine

If you remember only one thing, remember this:

**For V5.3, you work backtest first, IA Lab second, ML third.**

More precisely:

1. data truth first
2. replay truth second
3. label truth third
4. model training fourth
5. frozen overlay backtest fifth

That is the correct current order for the repo.
