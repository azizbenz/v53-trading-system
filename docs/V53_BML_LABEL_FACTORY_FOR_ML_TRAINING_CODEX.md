# V5.3 — Phase B_ML : Data Factory Labelisée pour Training ML

## 0. Résumé exécutif

Objectif : ajouter une phase dédiée `B_ML` dans la data factory V5.3 pour produire un dataset ML labelisé, sans lancer un backtest complet B1/B2 de validation et sans attendre `selected_count > 0` ou `executed_count > 0`.

La logique cible devient :

```text
A1 — Dataset plan / preview
A2 — Data factory ex-ante features depuis raw/gold
B_ML — Counterfactual label factory pour training ML
ML Training — entraîne sur B_ML dataset
Frozen Artifact — modèle figé + hash + manifest
Backtest OOS — période différente, évaluation future
Shadow — seulement après backtest OOS gouverné
```

`B_ML` n’est pas une phase de trading. Elle ne sélectionne pas de trades, ne crée pas d’exécution, ne modifie pas les engines, ne change pas les seuils, ne produit aucun claim de rentabilité. Elle produit uniquement des couples ML :

```text
X = features ex-ante disponibles au timestamp décisionnel
y = labels counterfactual replay-grounded calculés après le timestamp
```

Cette phase est la sortie propre de la boucle actuelle :

```text
expected_edge_proxy bloque les trades
mais le ML a besoin de labels non-proxy
et les labels actuels attendent trop souvent des trades sélectionnés/exécutés
```

La nouvelle règle est :

```text
Les labels ML counterfactual n’exigent pas selected/executed.
Ils exigent seulement un candidat/timestamp, des features ex-ante, une post-window, un coût mesurable, et une provenance claire.
```

---

## 1. Rôle de Codex

Tu es développeur senior quant / data engineering / ML systems / test engineer sur V5.3.

Ta mission est d’ajouter une phase `B_ML` reporting/data-only dans la data factory/backtest workflow.

Tu dois travailler en deux temps :

1. **Audit read-only** : localiser les modules existants, les artifacts, les contrats de features, le label store actuel et les chemins de runner.
2. **Patch minimal** : ajouter la phase `B_ML` et ses rapports sans modifier la politique trading.

Tu ne dois pas optimiser la stratégie. Tu ne dois pas forcer des trades. Tu ne dois pas modifier les seuils.

---

## 2. Problème actuel à résoudre

Le système a détecté une boucle :

```text
Pour supprimer expected_edge proxy → besoin d’un ML frozen.
Pour entraîner un ML frozen → besoin de labels replay-grounded non-proxy.
Pour avoir des labels non-proxy → le système attend des selected/executed.
Mais selected/executed = 0 car expected_edge proxy bloque.
```

Cette boucle est conceptuellement mauvaise.

Le ML n’a pas besoin de trades live ou de selected/executed pour apprendre. Il a besoin de candidats historiques rejoués de manière counterfactual avec :

- features avant décision ;
- outcome après décision ;
- coûts mesurés ou statut bloqué ;
- absence de leakage ;
- séparation train/validation/backtest.

`B_ML` doit produire ces labels sans passer par une phase B2 de backtest complet orientée sélection/exécution.

---

## 3. Invariants à préserver

Ne pas modifier :

- Engine A/B/C/D ;
- `SignalCandidate` ;
- les seuils ;
- les gates sharia / spot-only / long-only ;
- le runtime shadow/micro-live/live ;
- les hard blockers ;
- la logique de selected/executed ;
- le ML authority contract ;
- les guards feature grounding / label leakage / train-eval overlap.

Interdictions absolues :

```text
NO_ENGINE_REWRITE
NO_SIGNALCANDIDATE_CHANGE
NO_THRESHOLD_CHANGE
NO_FAKE_SELECTED
NO_FAKE_EXECUTED
NO_PROXY_TO_TRUTH_PROMOTION
NO_BACKTEST_PROFITABILITY_CLAIM
NO_SHADOW_SIDE_EFFECT
NO_RUNTIME_TRADE_SIDE_EFFECT
NO_TRAIN_EVAL_OVERLAP
NO_LABEL_LEAKAGE
```

---

## 4. Positionnement de B_ML dans le workflow

### 4.1 Avant

```text
A1 preview
A2 data factory
B1 candidate discovery
B2 detailed replay / by-bucket / selection / execution audit
ML training optionnel depuis B2 label store
```

### 4.2 Après

Ajouter un rail parallèle dédié :

```text
A1 preview
A2 data factory
B_ML label factory       ← nouveau rail training dataset
B1/B2 backtest           ← rail validation/backtest séparé
```

`B_ML` peut réutiliser des composants B1/B2, mais il doit avoir une identité séparée :

```text
phase_b_ml_training_label_factory/
```

Il ne doit pas écrire dans les outputs B2 de backtest comme si c’étaient des replay records de validation.

---

## 5. Nom de phase et statuts

Nom recommandé :

```text
phase_b_ml_training_label_factory
```

Statuts de phase :

```text
B_ML_NOT_REQUESTED
B_ML_PLANNED
B_ML_RUNNING
B_ML_READY_FOR_RESEARCH_TRAINING
B_ML_READY_FOR_GOVERNED_TRAINING
B_ML_BLOCKED_BY_MISSING_A2_FEATURES
B_ML_BLOCKED_BY_MISSING_RAW_WINDOWS
B_ML_BLOCKED_BY_MISSING_POST_WINDOW
B_ML_BLOCKED_BY_COST_MEASUREMENT
B_ML_BLOCKED_BY_LABEL_LEAKAGE
B_ML_BLOCKED_BY_TRAIN_EVAL_OVERLAP
B_ML_RESEARCH_ONLY
B_ML_FAILED
```

Important :

- `B_ML_READY_FOR_RESEARCH_TRAINING` ne veut pas dire promotion/live.
- `B_ML_READY_FOR_GOVERNED_TRAINING` exige labels non-proxy, post-windows complètes, coût mesuré selon contrat et absence de leakage.

---

## 6. Inputs de B_ML

### 6.1 Inputs obligatoires

```json
{
  "workflow_run_id": "strategy_ladder_workflow-...",
  "a2_run_root": ".../phase_a2_data_factory",
  "output_root": ".../phase_b_ml_training_label_factory",
  "pair_list": ["BNBUSDT", "BTCUSDT"],
  "timeframes": ["1m", "5m", "15m"],
  "start": "2025-02-02T00:00:00Z",
  "end": "2025-06-02T23:59:59Z",
  "label_horizons": ["5m", "15m", "1h"],
  "capital_buckets": [400, 500, 1500, 4000],
  "candidate_sampler_mode": "ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID",
  "feature_names": ["close_return", "high_low_range", "volume", "spread_bps", "queue_pressure"],
  "target_policy": "BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1",
  "runtime_mode": "RESEARCH_DATASET_ONLY"
}
```

### 6.2 Inputs optionnels

```json
{
  "raw_trade_root": "...",
  "raw_orderbook_root": "...",
  "raw_ohlcv_root": "...",
  "feature_grounding_registry_path": ".../reports/feature_grounding_registry.json",
  "training_source_manifest_path": ".../manifest.json",
  "existing_b1_candidate_events_path": ".../candidate_events.jsonl",
  "existing_b2_raw_windows_root": ".../raw_windows",
  "max_candidates_per_day": 500,
  "background_negative_ratio": 2.0,
  "allow_reuse_existing_raw_windows": true,
  "allow_generate_new_raw_windows": true
}
```

---

## 7. Candidate sampler B_ML

B_ML a besoin de timestamps candidats pour produire des labels. Il ne doit pas dépendre de `selected/executed`.

### 7.1 Modes autorisés

#### Mode 1 — `ENGINE_NATIVE_DRY_EVAL`

Exécuter les builders/engines en dry-eval pour produire des timestamps/contextes natifs, mais sans sélection finale.

Sortie :

```text
candidate_id
pair
timeframe
engine_id
decision_timestamp_ms
native_reason_codes
native_scores
side = buy only
```

Ce mode ne doit pas activer les hard blockers de expected-edge comme condition pour créer un label. Les blockers restent enregistrés, mais ne bloquent pas la création du label counterfactual si les données sont disponibles.

#### Mode 2 — `TEMPORAL_STRATIFIED_BACKGROUND_GRID`

Créer des timestamps de fond pour exemples négatifs/background.

But : éviter que le ML apprenne seulement sur des candidats déjà filtrés par engines.

Champs :

```text
candidate_source = TEMPORAL_STRATIFIED_BACKGROUND_GRID
engine_id = background
side = buy
```

#### Mode 3 — `REUSE_B1_FAST_CANDIDATES`

Réutiliser `candidate_events.jsonl` ou `preselection_candidates.jsonl` existant si fourni.

Important : si réutilisation B1, marquer :

```text
candidate_source = REUSED_B1_DISCOVERY
```

### 7.2 Mode recommandé

```text
ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID
```

Avec :

- 1 partie engine-native candidates ;
- 1 partie background/negative sampling ;
- stratification par jour, pair, timeframe, régime si disponible.

---

## 8. Features ex-ante

B_ML doit utiliser uniquement des features disponibles avant ou au timestamp décisionnel.

### 8.1 Sources de features

```text
A2 gold kline features
A2 trade features
A2 orderbook features
microstructure bridge features
engine-native dry-eval scores
execution cost estimates available at decision timestamp
```

### 8.2 Exemples autorisés

```text
close_return
high_low_range
volume
spread_bps measured at decision timestamp
queue_pressure
cumulative_ofi
vpin
realized_vol_current
kyle_lambda pre-decision
structure_score
z_score
breakout_score
history_score
book_depth_top1/top5/top20
```

### 8.3 Interdits comme features

```text
mfe_bps
mae_bps
future_return
forward_return
realized_pnl
net_edge_label
break_even_outcome
selected_count
executed_count
trade_success
post_window_adverse_selection
```

Ces éléments peuvent être labels, jamais inputs runtime.

---

## 9. Labels counterfactual B_ML

Pour chaque candidat/timestamp, calculer après décision :

```text
forward_return_5m_bps
forward_return_15m_bps
forward_return_1h_bps
mfe_bps_by_horizon
mae_bps_by_horizon
entry_reference_price
measured_spread_bps
measured_slippage_bps_by_bucket
fee_bps
latency_penalty_bps
net_return_after_cost_bps_by_bucket
break_even_cleared_by_bucket
fillable_from_depth20_by_bucket
depth_fill_ratio_by_bucket
label_status
label_truth_status
```

### 9.1 Target policy principale

Nom recommandé :

```text
BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1
```

Définition :

```text
net_return_after_cost_bps(bucket, horizon)
= forward_return_bps(horizon)
- fee_bps
- spread_cost_bps
- slippage_bps(bucket)
- latency_penalty_bps
- optional impact/adverse_selection if measured
```

Si adverse selection n’est pas mesurée, ne pas appeler le label `fully_execution_aware`. Utiliser :

```text
COUNTERFACTUAL_REPLAY_GROUNDED_COST_AWARE_PARTIAL_ADVERSE_SELECTION
```

### 9.2 Label classification

```text
LABEL_COUNTERFACTUAL_REPLAY_GROUNDED
LABEL_COUNTERFACTUAL_COST_AWARE
LABEL_COUNTERFACTUAL_EXECUTION_AWARE_PARTIAL
LABEL_BLOCKED_BY_MISSING_POST_WINDOW
LABEL_BLOCKED_BY_MISSING_BOOK
LABEL_BLOCKED_BY_STALE_BOOK
LABEL_BLOCKED_BY_SLIPPAGE_MEASUREMENT
LABEL_BLOCKED_BY_INSUFFICIENT_DEPTH
LABEL_RESEARCH_ONLY_PROXY_COST
```

### 9.3 Training eligibility

Chaque row reçoit :

```text
TRAINING_ROW_ELIGIBLE
TRAINING_ROW_RESEARCH_ONLY
TRAINING_ROW_BLOCKED
```

`TRAINING_ROW_ELIGIBLE` exige :

- features ex-ante valides ;
- aucun input post-décision ;
- post-window disponible ;
- spread/slippage mesurés ou statut de coût conforme ;
- target policy cohérente ;
- pas de train/eval overlap ;
- pas de proxy déguisé en truth.

`TRAINING_ROW_RESEARCH_ONLY` si :

- coût partiel mais transparent ;
- fill realism non live-proven ;
- adverse selection non mesurée ;
- labels utiles pour recherche mais pas promotion.

`TRAINING_ROW_BLOCKED` si :

- missing post-window ;
- missing book pour label coût ;
- leakage ;
- target mismatch ;
- feature critical manquante ;
- provenance inconnue.

---

## 10. Outputs de B_ML

Structure de dossier :

```text
phase_b_ml_training_label_factory/
  manifest.json
  b_ml_run_request.json
  b_ml_run_summary.json
  candidates/
    b_ml_candidate_events.jsonl
    b_ml_candidate_events.parquet
    b_ml_candidate_events.tabular_manifest.json
    b_ml_candidate_sampling_report.json
  features/
    b_ml_feature_matrix.jsonl
    b_ml_feature_matrix.parquet
    b_ml_feature_matrix.tabular_manifest.json
    b_ml_feature_contract_report.json
  labels/
    b_ml_label_store.jsonl
    b_ml_label_store.parquet
    b_ml_label_store.tabular_manifest.json
    b_ml_label_summary.json
    b_ml_target_policy_report.json
  windows/
    raw_window_index.jsonl
    raw_window_index.parquet
    raw_window_index.tabular_manifest.json
    post_window_index.jsonl
    post_window_index.parquet
    post_window_index.tabular_manifest.json
  reports/
    b_ml_training_dataset_audit.json
    b_ml_tabular_artifact_index.json
    b_ml_training_row_eligibility_report.json
    b_ml_feature_label_leakage_report.json
    b_ml_cost_label_fidelity_report.json
    b_ml_train_eval_overlap_report.json
    b_ml_final_verdict.json
  docs/
    B_ML_TRAINING_DATASET_AUDIT.md
```

Les fichiers `.parquet` sont des mirrors de performance. Les fichiers `.jsonl`
restent les artefacts audit source-of-truth. Si `pyarrow` n'est pas disponible,
le runtime doit produire un fallback `*.columns.json` et le déclarer dans
`*.tabular_manifest.json`.

Règle de lecture gouvernée :

```text
Le training / IA Lab peut lire le Parquet seulement si :
- le manifest frère existe ;
- status = TABULAR_MIRROR_PARQUET_READY ;
- storage_format = parquet ;
- source_path correspond au JSONL demandé ;
- audit_jsonl_preserved = true.

Sinon le lecteur doit revenir au JSONL.
```

---

## 11. manifest.json

Chaque B_ML run doit produire :

```json
{
  "schema_version": "v53.b_ml_training_dataset_manifest.v1",
  "dataset_role": "ML_TRAINING_SOURCE",
  "phase": "B_ML_COUNTERFACTUAL_LABEL_FACTORY",
  "workflow_run_id": "strategy_ladder_workflow-...",
  "dataset_name": "bml_dataset_train_2025-02-02_to_2025-06-02",
  "source_type": "A2_FEATURES_PLUS_COUNTERFACTUAL_REPLAY_LABELS",
  "a2_run_root": ".../phase_a2_data_factory",
  "b_ml_run_root": ".../phase_b_ml_training_label_factory",
  "train_start": "2025-02-02",
  "train_end": "2025-06-02",
  "allowed_backtest_start_after": "2025-06-03",
  "forbidden_eval_overlap": true,
  "target_policy": "BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1",
  "label_truth_status": "COUNTERFACTUAL_REPLAY_GROUNDED_COST_AWARE",
  "promotion_allowed": false,
  "training_allowed": true,
  "notes": "Training dataset only. Not a profitability backtest. No selected/executed claims."
}
```

---

## 12. b_ml_label_store.jsonl schema

Une ligne par candidat × horizon × capital_bucket, ou une ligne par candidat avec maps par horizon/bucket. Choisir la forme la plus compatible avec le trainer actuel.

Schéma recommandé flat :

```json
{
  "schema_version": "v53.b_ml_label_store_row.v1",
  "candidate_id": "...",
  "candidate_source": "ENGINE_NATIVE_DRY_EVAL",
  "pair": "BNBUSDT",
  "timeframe": "15m",
  "engine_id": "engine_a",
  "side": "buy",
  "decision_timestamp_ms": 1750000000000,
  "horizon": "15m",
  "capital_bucket": 500,
  "feature_values": {
    "close_return": 0.001,
    "volume": 12345.0,
    "spread_bps": 0.8,
    "queue_pressure": 0.12
  },
  "feature_provenance": {
    "spread_bps": "ORDERBOOK_GROUNDED_MEASURED_AT_DECISION"
  },
  "entry_reference_price": 689.5,
  "post_window_status": "POST_WINDOW_READY",
  "spread_bps_measured": 0.8,
  "slippage_bps_measured": 0.4,
  "fee_bps": 10.0,
  "latency_penalty_bps": 1.5,
  "depth_fill_ratio": 1.0,
  "forward_return_bps": 18.2,
  "mfe_bps": 24.5,
  "mae_bps": -6.1,
  "net_return_after_cost_bps": 5.5,
  "break_even_cleared": true,
  "label_value": 5.5,
  "label_name": "net_return_after_cost_bps",
  "target_policy": "BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1",
  "label_truth_status": "COUNTERFACTUAL_REPLAY_GROUNDED_COST_AWARE",
  "training_row_status": "TRAINING_ROW_ELIGIBLE",
  "promotion_allowed": false,
  "raw_window_refs": {
    "orderbook": "...",
    "trades": "...",
    "ohlcv": "...",
    "post_window": "..."
  },
  "warnings": []
}
```

---

## 13. Runner / CLI

Ajouter un CLI ou une option workflow :

```bash
python -m src.local_replay_runtime.strategy_ladder_runner \
  --phase B_ML \
  --a2-run-root ".../phase_a2_data_factory" \
  --output-root ".../phase_b_ml_training_label_factory" \
  --pairs BNBUSDT,BTCUSDT \
  --timeframes 5m,15m \
  --start 2025-02-02 \
  --end 2025-06-02 \
  --label-horizons 5m,15m,1h \
  --capital-buckets 400,500,1500,4000 \
  --candidate-sampler-mode ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID \
  --target-policy BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1
```

Si le runner actuel ne supporte pas proprement `--phase`, ajouter un script dédié :

```text
src/local_replay_runtime/strategy_ladder_b_ml_label_factory.py
```

Puis le brancher optionnellement dans le workflow support.

---

## 14. Intégration avec le trainer ML

Le trainer doit accepter :

```text
label_store_dataset_path = phase_b_ml_training_label_factory/labels/b_ml_label_store.jsonl
```

Mais seulement si :

```text
b_ml_final_verdict.training_allowed = true
train_eval_overlap_status = OK
feature_label_leakage_count = 0
target_policy_actual == target_policy_declared
training_row_eligible_count > minimum
```

Sinon :

```text
ML_TRAINING_BLOCKED_BY_BML_LABEL_STORE_NOT_READY
```

Ne jamais traiter B_ML comme promotion proof.

---

## 15. UI cockpit

Ajouter un mode opérateur dans IA Lab / Backtest si possible :

```text
Run type:
[ ] Backtest native
[ ] ML handoff training
[x] B_ML training dataset factory
```

Champs UI :

- A2 run root ;
- output root ;
- train start/end ;
- pairs ;
- timeframes ;
- label horizons ;
- capital buckets ;
- candidate sampler mode ;
- selected features ;
- target policy ;
- manifest preview ;
- overlap status ;
- expected output path.

Afficher clairement :

```text
This run creates a training dataset only.
It does not run a profitability backtest.
It does not create selected/executed trades.
```

UI statuses :

```text
B_ML_DATASET_READY_FOR_RESEARCH_TRAINING
B_ML_DATASET_READY_FOR_GOVERNED_TRAINING
B_ML_DATASET_BLOCKED
B_ML_RESEARCH_ONLY
```

---

## 16. Logs obligatoires

Logger :

```text
b_ml.run.started
b_ml.a2_root.validated
b_ml.feature_grounding.loaded
b_ml.candidate_sampler.started
b_ml.candidate_sampler.completed
b_ml.raw_window.extracted
b_ml.post_window.extracted
b_ml.label.computed
b_ml.row.eligible
b_ml.row.research_only
b_ml.row.blocked
b_ml.leakage.blocked
b_ml.target_policy.mismatch
b_ml.final_verdict
```

Chaque warning doit être explicite :

```text
MISSING_POST_WINDOW
MISSING_ORDERBOOK_WINDOW
STALE_BOOK
SLIPPAGE_NOT_MEASURED
FEATURE_POST_DECISION_LEAKAGE
TARGET_POLICY_MISMATCH
TRAIN_EVAL_OVERLAP
PROXY_COST_RESEARCH_ONLY
```

---

## 17. Rapports d’audit

### 17.1 b_ml_training_dataset_audit.json

```json
{
  "schema_version": "v53.b_ml_training_dataset_audit.v1",
  "run_id": "...",
  "row_count": 0,
  "candidate_count": 0,
  "training_row_eligible_count": 0,
  "training_row_research_only_count": 0,
  "training_row_blocked_count": 0,
  "feature_leakage_count": 0,
  "target_policy_mismatch_count": 0,
  "missing_post_window_count": 0,
  "missing_book_count": 0,
  "cost_aware_label_count": 0,
  "execution_aware_partial_label_count": 0,
  "proxy_label_count": 0,
  "scientifically_valid_for_training": false,
  "scientifically_valid_for_promotion": false,
  "final_verdict": "..."
}
```

### 17.2 Verdicts possibles

```text
B_ML_DATASET_READY_FOR_GOVERNED_TRAINING
B_ML_DATASET_READY_FOR_RESEARCH_TRAINING
B_ML_DATASET_RESEARCH_ONLY_COST_PARTIAL
B_ML_DATASET_BLOCKED_BY_MISSING_POST_WINDOW
B_ML_DATASET_BLOCKED_BY_MISSING_BOOK
B_ML_DATASET_BLOCKED_BY_LABEL_LEAKAGE
B_ML_DATASET_BLOCKED_BY_TARGET_POLICY_MISMATCH
B_ML_DATASET_BLOCKED_BY_TRAIN_EVAL_OVERLAP
B_ML_DATASET_INSUFFICIENT_ROWS
```

---

## 18. Tests obligatoires

Créer :

```text
tests/test_local_replay_runtime/test_b_ml_label_factory.py
tests/test_local_replay_runtime/test_b_ml_candidate_sampler.py
tests/test_local_replay_runtime/test_b_ml_label_store_schema.py
tests/test_local_replay_runtime/test_b_ml_training_integration.py
tests/cockpit/test_b_ml_dataset_factory_ui.py
```

### 18.1 Tests de non-régression

1. B_ML ne modifie aucun engine.
2. B_ML ne modifie aucun threshold.
3. B_ML ne crée pas `selected_count`.
4. B_ML ne crée pas `executed_count`.
5. B_ML ne change pas les replay decisions B2.
6. B_ML ne supprime aucun hard blocker.

### 18.2 Tests de leakage

1. `mfe_bps` comme feature input est bloqué.
2. `future_return` comme feature input est bloqué.
3. `selected_count` comme feature input est bloqué.
4. Feature timestamp après décision est bloquée.
5. Label timestamp avant décision est bloqué.

### 18.3 Tests de labels

1. Post-window manquante → `LABEL_BLOCKED_BY_MISSING_POST_WINDOW`.
2. Orderbook manquant → `LABEL_BLOCKED_BY_MISSING_BOOK`.
3. Spread/slippage mesurés → `LABEL_COUNTERFACTUAL_COST_AWARE`.
4. Coût proxy → `TRAINING_ROW_RESEARCH_ONLY`, pas eligible governed.
5. Target mismatch → blocked.

### 18.4 Tests anti-overlap

1. Train 2025-02-02→2025-06-02, backtest 2025-06-03→2025-07-03 → OK.
2. Train 2025-07-18→2025-08-01, backtest 2025-07-18→2025-08-01 → blocked.

### 18.5 Tests intégration trainer

1. Trainer accepte B_ML label store si `training_allowed=true`.
2. Trainer bloque si `target_policy_mismatch_count > 0`.
3. Trainer bloque si `feature_leakage_count > 0`.
4. Trainer marque artifact `promotion_allowed=false` si labels counterfactual research-only.

---

## 19. Commandes de vérification

```bash
python -m compileall -q src tests
pytest tests/test_local_replay_runtime/test_b_ml_label_factory.py -q --tb=short
pytest tests/test_local_replay_runtime/test_b_ml_candidate_sampler.py -q --tb=short
pytest tests/test_local_replay_runtime/test_b_ml_label_store_schema.py -q --tb=short
pytest tests/test_local_replay_runtime/test_b_ml_training_integration.py -q --tb=short
pytest tests/cockpit/test_b_ml_dataset_factory_ui.py -q --tb=short
```

Relancer aussi :

```bash
pytest tests/test_local_replay_runtime/test_feature_grounding_registry.py \
       tests/test_local_replay_runtime/test_training_source_contract.py \
       tests/test_local_replay_runtime/test_ml_label_leakage_guards.py \
       tests/test_local_replay_runtime/test_b2_label_store_ml_training_audit.py -q --tb=short
```

---

## 20. Mode anti-hallucination pour Codex

Avant tout patch :

1. Utiliser `rg` pour localiser les vrais modules existants.
2. Ne pas inventer de module si une surface existe déjà.
3. Ne pas dupliquer un label store existant si on peut l’étendre proprement.
4. Ne pas inventer de champs de replay absents.
5. Si un champ manque, écrire `MISSING_IN_ARTIFACT`.
6. Si une source manque, écrire `NOT_FOUND`.
7. Si une métrique ne peut pas être calculée, écrire `INSUFFICIENT_DATA`.
8. Ne pas conclure `READY_FOR_GOVERNED_TRAINING` sans row eligibility.
9. Ne pas conclure `EXECUTION_AWARE` si fill/slippage/adverse selection sont proxy.
10. Ne pas modifier le runtime trading.

---

## 21. Critères d’acceptation

Le patch est accepté si :

1. `B_ML` peut générer un dataset training sans B2 backtest complet.
2. Le dataset relie A2 features + candidats + post-windows + labels.
3. Aucune feature post-décision n’entre dans `feature_values`.
4. Les labels sont clairement séparés des features.
5. Le target policy déclaré match le target réel.
6. Les rows ont un statut eligibility.
7. Le trainer peut consommer le label store seulement si le contract est OK.
8. Le manifest empêche train/eval overlap.
9. Aucun engine/seuil/trade decision n’est modifié.
10. Les tests passent.
11. Le système ne prétend pas que B_ML est un backtest rentable.
12. Les outputs sont compréhensibles par l’opérateur et visibles dans le cockpit si possible.

---

## 22. Résumé doctrinal final

`B_ML` est une usine de labels ML, pas un backtest.

```text
A2 = features ex-ante
B_ML = labels counterfactual replay-grounded
ML Training = apprend X → y
Backtest OOS = évalue le frozen artifact sur période future
Shadow = seulement après validation
```

La sortie de boucle est :

```text
Ne pas attendre selected/executed.
Créer des labels counterfactual propres.
Entraîner le ML sur période passée.
Tester le frozen artifact sur période future.
```
