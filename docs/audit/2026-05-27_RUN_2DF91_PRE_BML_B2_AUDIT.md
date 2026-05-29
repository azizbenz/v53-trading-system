# Audit Pre-Launch B_ML / B2 - Run 2df91d9d5c48dfbf

Date: 2026-05-27

Run audite:

```text
L:\output backtest\runs\strategy_ladder_workflow-2df91d9d5c48dfbf
```

Scope:

```text
pair: BTCUSDT
timeframe: 15m
start: 2025-07-25
end: 2025-07-26
ml_mode: ML_MODE_OFF
candidate_discovery_mode: TEMPORAL_STRATIFIED
silver_storage: jsonl_gz
```

## Verdict Executif

Le workflow A1 -> A2 -> B1 est coherent et les fichiers requis existent.

Verdict:

```text
A1_READY = true
A2_READY_FOR_RESEARCH = true
B1_REFS_READY = true
B2_TARGETED_TRUTH_GO = true
B_ML_RESEARCH_GO = true
PROD_SAFE = false
PROFITABILITY_READY = false
```

Ordre recommande:

1. lancer B2 `ML_MODE_OFF` en truth replay cible;
2. lire les rapports B2 cost/fill/slippage;
3. lancer B_ML pour dataset research/training si B2 confirme que les post-windows/couts sont exploitables;
4. ne pas lancer IA Lab promotion tant que B_ML/B2 ne produisent pas de labels gouvernes.

## A1 - Preview

Fichiers:

```text
phase_a1_preview/source_date_preview_manifest.json
phase_a1_preview/source_scope_report.json
```

Statut:

```text
inspection_status = PHASE_A1_PREVIEW_READY
blockers = []
requested_pairs = BTCUSDT
detected_pairs = ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,SOLUSDT,XRPUSDT
active_pairs_after_pruning = BTCUSDT
common_date_range = 2025-07-25 -> 2025-07-26
matched_files_total = 83
timeframes = 15m
metadata_status = BYBIT_HISTORICAL_METADATA_READY
warning = IGNORED_SOURCE_PAIR_DETECTED
```

Interpretation:

- A1 est bon.
- Les autres pairs detectees viennent surtout du metadata/root global, mais le run est bien prune sur `BTCUSDT`.
- Pas de blocker A1 pour A2/B1/B2/B_ML.

## A2 - Data Factory

Fichiers critiques:

```text
phase_a2_data_factory/data_factory_manifest.json
phase_a2_data_factory/silver_index.json
phase_a2_data_factory/data_quality_report.json
phase_a2_data_factory/gold_feature_manifest.json
phase_a2_data_factory/gold_feature_quality_report.json
phase_a2_data_factory/data_factory_prod_safety_report.json
phase_a2_data_factory/a2_microstructure_performance_report.json
phase_a2_data_factory/a2_feature_equivalence_report.json
```

Statut:

```text
data_factory_status = DATA_FACTORY_READY
raw_source_status = RAW_SOURCE_READY
silver_index_status = SILVER_INDEX_READY
gold_feature_store_status = FEATURE_STORE_READY
silver_storage_format = jsonl_gz
rows_processed = 2,503,144
rows_rejected = 0
files_processed = 10
files_skipped = 6,330
gold_feature_row_count = 192
gold_timeframes_generated = 15m
feature_equivalence_status = A2_FEATURE_EQUIVALENCE_READY
microstructure_streaming_status = A2_MICROSTRUCTURE_STREAMING_READY
microstructure_overlay_rows = 190 / 192
microstructure_missing_rows = 2 / 192
```

Features Gold disponibles:

```text
book_depth_levels
break_even_bps
close_return
cumulative_ofi
false_breakout_context
fragility
fragility_score
high_low_range
latency_penalty_bps
realized_vol_current
session_tags
slippage_bps
spread_bps
sweep_score
trade_count_hint
volume
vpin
```

Blockers A2:

```text
RAW_SOURCE_TYPE_INFERRED
CURRENT_METADATA_PROXY
SINGLE_PAIR_RESEARCH_ONLY
```

Prod safety:

```text
prod_safety_status = RESEARCH_ONLY_NOT_PROD_SAFE
prod_safe = false
coverage.trades = TRADES_WINDOW_COVERED
coverage.klines = KLINES_WINDOW_COVERED
coverage.orderbook = ORDERBOOK_WINDOW_COVERED
coverage.orderbook_depth20 = ORDERBOOK_DEPTH20_WINDOW_COVERED
```

Interpretation:

- A2 est bon pour research, B1, B2 cible et B_ML.
- A2 n'est pas prod-safe car metadata temporelle reste proxy, source typing inferre, et single-pair.
- A2 calcule bien les features ex-ante; cela ne suffit pas a debloquer expected-edge.

## B1 - Candidate Discovery

Fichiers critiques:

```text
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/run_manifest.json
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/reports/strategy_ladder_summary.json
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/fast_candidates/candidate_events.jsonl
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/fast_candidates/candidate_events.parquet
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/fast_candidates/candidate_events.tabular_manifest.json
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/preselection_candidates.jsonl
phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-2df91d9d5c48dfbf/reports/preselection_summary.json
```

Statut:

```text
phase_status = PHASE_B1_CANDIDATE_DISCOVERY_READY
raw_window_materialization_mode = REFS_ONLY
raw_window_extraction_status = RAW_WINDOW_REFS_ONLY
candidate_count = 200
unique_candidate_count = 200
candidate_events_lines = 200
preselection_lines = 200
candidate_windows_count = 200 refs
detailed_replay_exists = false
raw_windows_exists = false
total_wall_time_s = 4.644181
rows_processed = 192
files_scanned = 0
```

Distribution candidats:

```text
pair = BTCUSDT: 200
timeframe = 15m: 200
engine_a = 50
engine_b = 50
engine_c = 50
engine_d = 50
candidate_source = ENGINE_NATIVE_UNAVAILABLE: 200
candidate_data_source_label = ENGINE_NATIVE_A_B_C_D_RUNNER: 200
```

Preselection:

```text
preselection_status = ENGINE_NATIVE_PRESELECTION_READY
engine_native_preselected_count = 200
preselection_hard_rejected_count = 0
preselection_soft_flagged_count = 200
b2_replay_candidate_count = 200
```

Top soft advisory reasons:

```text
B2_COST_MEASUREMENT_BLOCKED = 200
ENGINE_NATIVE_INPUT_BUILDER_FAILED_NO_RAW_WINDOW = 200
ENGINE_NATIVE_RUNNER_NOT_INVOKED = 200
```

Tabular mirror:

```text
candidate_events.parquet status = TABULAR_MIRROR_PARQUET_READY
storage_format = parquet
compression = zstd
audit_jsonl_preserved = true
row_count = 200
source_to_mirror_size_ratio = 47.82x
```

Feature coverage dans candidate events:

```text
close_return = 200
high_low_range = 200
volume = 200
spread_bps = 200
slippage_bps = 200
book_depth_levels = 192
realized_vol_current = 192
vpin = 192
cumulative_ofi = 96
```

Interpretation:

- B1 est valide comme refs-only candidate store.
- B1 n'est pas une preuve engine-native/execution truth.
- Les blockers `ENGINE_NATIVE_RUNNER_NOT_INVOKED`, `RAW_WINDOW_NOT_AVAILABLE` et `B2_COST_MEASUREMENT_BLOCKED` sont attendus dans B1 refs-only.
- B2 doit maintenant materialiser les raw windows et refaire le truth replay cible.

## Blockers Actuels

B1 summary:

```text
ENGINE_NATIVE_CANDIDATE_TRUTH_NOT_PROVEN
EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH
CANDIDATE_ENGINE_NATIVE_NOT_PROVEN
EXPECTED_EDGE_PROXY_BLOCKED
PARTIALLY_MEASURED
STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS
```

Ces blockers ne doivent pas etre supprimes. Ils disent simplement que:

- B1 refs-only n'a pas encore lance les engines avec raw windows;
- expected-edge n'a pas d'artifact ML gouverne;
- cost/fill/slippage ne sont pas encore mesures par B2;
- aucune execution backtest truth n'existe encore.

## Decision De Lancement B2

Verdict:

```text
B2_TARGETED_TRUTH_GO = true
```

Raison:

- A2 silver/gold existent.
- B1 `candidate_events.jsonl` existe.
- B1 `preselection_candidates.jsonl` existe.
- B2 pourra consommer la preselection ready.
- B2 doit rester materialise, pas `REFS_ONLY`.

Config recommandee:

```text
Phase: B2 Detailed Replay
ML mode: ML_MODE_OFF
workflow_run_id: strategy_ladder_workflow-2df91d9d5c48dfbf
pairs: BTCUSDT
timeframes: 15m
dates: 2025-07-25 -> 2025-07-26
```

Controle preview avant launch:

```text
blockers = []
command contient --detailed-only --resume
command contient --candidate-events-path
command ne contient pas --raw-window-mode REFS_ONLY
```

Apres B2, verifier:

```text
raw_window_extraction_status
measured_spread_report.json
measured_slippage_report.json
fill_realism_report.json
profitability_truth_verdict.json
backtest_decision_report_final_verdict.json
f16_feature_coverage_report.json
```

## Decision De Lancement B_ML

Verdict:

```text
B_ML_RESEARCH_GO = true
B_ML_PROMOTION_READY = false
```

Raison:

- A2 gold est ready.
- B1 candidate refs existent.
- Les features ex-ante sont disponibles.
- Mais expected-edge/cost/fill truth ne sont pas encore prouves.

Sampler recommande:

```text
Premier smoke B_ML: TEMPORAL_STRATIFIED_BACKGROUND_GRID
Dataset attache aux candidats B1: REUSE_B1_FAST_CANDIDATES
A eviter maintenant: ENGINE_NATIVE_DRY_EVAL seul
```

Pourquoi eviter `ENGINE_NATIVE_DRY_EVAL` seul:

```text
candidate_source = ENGINE_NATIVE_UNAVAILABLE
engine_native_status = ENGINE_NATIVE_CANDIDATES_PRESENT_NOT_INVOKED
engine_native_records_built = 0
```

Apres B_ML, verifier:

```text
labels/b_ml_label_store.jsonl
reports/b_ml_training_dataset_audit.json
reports/b_ml_training_row_eligibility_report.json
reports/b_ml_feature_label_leakage_report.json
reports/b_ml_final_verdict.json
```

## Recommendation Finale

Lancer maintenant:

1. B2 `ML_MODE_OFF` truth replay cible.
2. Si B2 produit cout/fill mesurables, lancer B_ML avec `REUSE_B1_FAST_CANDIDATES`.
3. Si l'objectif est seulement un smoke label dataset, lancer B_ML avec `TEMPORAL_STRATIFIED_BACKGROUND_GRID`.

Ne pas lancer:

- IA Lab promotion-ready;
- backtest `ML_MODE_OVERLAY_FROZEN`;
- jugement "rentable ou non".

Ces etapes exigent d'abord un B2/B_ML avec labels et cout/fill non proxy.
