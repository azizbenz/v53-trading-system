# B_ML Label Factory Implementation Audit

Status: `B_ML_CORE_PLUS_COCKPIT_WIRING_READY_FOR_TEST`

Scope:
- Reads A2 gold feature rows only.
- Builds counterfactual ML training rows with ex-ante `feature_values` and post-decision labels.
- Does not modify Engine A/B/C/D, thresholds, `SignalCandidate`, selected trades, executed trades, live policy, shadow policy, or hard blockers.

A2 feature availability:
- Always available from A2 gold when OHLCV rows exist: `close_return`, `high_low_range`, `volume`.
- Available when selected and source-backed: `spread_bps`, `book_depth_levels`, `vpin`, `cumulative_ofi`, `queue_pressure`, `realized_vol_current`, `kyle_lambda`, `realized_vol_at_break`, `latency_penalty_bps`.
- Training eligibility still depends on provenance. Proxy/default/stale economic fields stay research-only or blocked.

B_ML outputs:
- `manifest.json`
- `b_ml_run_request.json`
- `b_ml_run_summary.json`
- `candidates/b_ml_candidate_events.jsonl`
- `candidates/b_ml_candidate_events.parquet` when pyarrow is available
- `candidates/b_ml_candidate_events.tabular_manifest.json`
- `features/b_ml_feature_matrix.jsonl`
- `features/b_ml_feature_matrix.parquet` when pyarrow is available
- `features/b_ml_feature_matrix.tabular_manifest.json`
- `labels/b_ml_label_store.jsonl`
- `labels/b_ml_label_store.parquet` when pyarrow is available
- `labels/b_ml_label_store.tabular_manifest.json`
- `labels/b_ml_label_summary.json`
- `labels/b_ml_target_policy_report.json`
- `reports/b_ml_training_dataset_audit.json`
- `reports/b_ml_tabular_artifact_index.json`
- `reports/b_ml_training_row_eligibility_report.json`
- `reports/b_ml_feature_label_leakage_report.json`
- `reports/b_ml_cost_label_fidelity_report.json`
- `reports/b_ml_train_eval_overlap_report.json`
- `reports/b_ml_final_verdict.json`
- `docs/B_ML_TRAINING_DATASET_AUDIT.md`

Training integration:
- `strategy_ladder_expected_edge_training` now accepts `labels/b_ml_label_store.jsonl` through `label_store_dataset_path`.
- Only `TRAINING_ROW_ELIGIBLE` rows are projected into `MlTrainingRow`.
- Training blocks when `training_allowed=false`, target policy mismatches, leakage exists, overlap is blocked, or no eligible rows exist.
- B_ML target policy is `BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1`.

Cockpit / workflow integration:
- Backtest phase selector now exposes `PHASE_B_ML_LABEL_FACTORY`.
- Backtest form persists `bml_candidate_sampler_mode`.
- Preflight command preview emits `scripts/run_strategy_ladder_b_ml_label_factory.py`.
- Launch wiring uses A2 gold as the feature source and optional B1 candidate events as sampler input.
- Workflow phase status uses `PHASE_B_ML_LABEL_FACTORY_READY` / `PHASE_B_ML_LABEL_FACTORY_BLOCKED`.
- Artifact links point to `labels/b_ml_label_store.jsonl` and `reports/b_ml_training_dataset_audit.json`.
- Operator launch white book: `docs/audit/B_ML_OPERATOR_WHITEBOOK.md`.

Implemented MD deltas:
- Strict feature availability guard: `available_at_timestamp_ms` after decision becomes `FEATURE_POST_DECISION_LEAKAGE`.
- `REUSE_B1_FAST_CANDIDATES` reads existing `candidate_events.jsonl` / `preselection_candidates.jsonl` and preserves engine id.
- `ENGINE_NATIVE_DRY_EVAL` is represented only through reused B1/native candidate artifacts; no engine is run or simulated inside B_ML.
- `ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID` can combine reused candidate artifacts with background grid samples.
- `raw_window_index.jsonl` and `post_window_index.jsonl` are now populated from A2 feature/post-window refs instead of empty placeholders.
- Compact tabular mirrors are now emitted for label store, candidate events, feature matrix, and window indexes. JSONL remains audit source-of-truth; Parquet/ZSTD is a performance mirror.
- B_ML projection and expected-edge training now prefer a Parquet mirror only when its sibling `*.tabular_manifest.json` is `TABULAR_MIRROR_PARQUET_READY`, matches the JSONL source, and confirms `audit_jsonl_preserved=true`. Otherwise they fall back to JSONL.
- `b_ml_event_log.jsonl` records the required audit events.
- Default `allowed_backtest_start_after` in the manifest is the day after `train_end`.

Still remaining:
- IA Lab direct handoff mode for consuming B_ML folders without manual path entry.
- Native dry-eval candidate generation as a real upstream workflow step.
- Depth20 fill simulation by capital bucket from raw orderbook walk.
- High/low based MFE/MAE when A2 exposes high/low post-window fields.
- Full raw window extraction from raw roots; current refs are A2 feature/post-window indexes.

Non-goals:
- No profitability claim.
- No fake execution labels.
- No promotion-ready claim.
- No threshold calibration.
