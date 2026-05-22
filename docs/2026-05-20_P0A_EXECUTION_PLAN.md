# P0-A Execution Plan — Expected-Edge GOVERNED_BACKTEST_TRUTH

**Date :** 2026-05-20
**Status :** PLAN — pas encore exécuté
**Référence run de départ :** `strategy_ladder_workflow-03a3ffe825e7e9fb`
**Verdict de la session d'audit :** Co-P0 nécessaire (P0-A + P0-B), pas single P0

---

## 1. Objet

Remplacer `expected_edge_provenance = DEFAULT_TO_CALIBRATE | PROXY_*` par un modèle entraîné qui produit `expected_edge_provenance = GOVERNED_BACKTEST_TRUTH`, débloquant ainsi `edge_is_truth = True` dans la sélection ([strategy_ladder_runner.py:1775](src/local_replay_runtime/strategy_ladder_runner.py:1775)).

**Sans cela :** `target_state = "hard_blocked"` pour tous les candidats, peu importe les autres fixes.
**Avec cela seul :** débloque condition `edge_is_truth`, mais `is_emit` reste indépendamment requis (correction Codex 2026-05-19 — Co-P0).

---

## 2. Definition of Done — 5 livrables

### Livrable 1 — `docs/2026-05-XX_P0A_FINAL_VERDICT.md`

**Schéma obligatoire :**
```
# V5.3 P0-A Final Verdict

## Verdict
- BACKTEST_PROFITABILITY_PROVEN_POSITIVE | NEGATIVE | INCONCLUSIVE_STATISTICAL_POWER

## Evidence
- run_id: <id>
- window: <start> → <end> = <N> jours
- executed_trade_count: <N>
- net_return_bps: <X>
- net_return_annualized_sharpe: <X>
- max_drawdown_bps: <X>
- psr_observed: <X> (acceptance_floor 0.95)
- dsr_observed: <X> (acceptance_floor 0.95, trial_count <N>)
- min_trl_required: <N_trades>
- min_trl_satisfied: <bool>
- min_btl_required: <N_years> (Bailey-Borwein-LdP-Zhu 2014)
- min_btl_satisfied: <bool>

## Doctrinal compliance
- venue_transfer_status: <BYBIT_NATIVE | BINANCE_SHADOW_REQUIRED | LIVE_READY>
- promotion_grade: <bool>
- evidence_class: <SCRATCH_ONLY | AUDIT_VALIDATED | PROMOTION_GRADE>

## Limitations
- (liste les caveats détectés : fenêtre, single-pair, etc.)
```

**Critère d'acceptation :**
- Verdict tranche binaire (PROVEN_POSITIVE / NEGATIVE / INCONCLUSIVE)
- Tous les anchors V5.3 (PSR/DSR/MinTRL/MinBTL) calculés et cités
- Tous les blockers explicitement listés
- `INCONCLUSIVE_STATISTICAL_POWER` autorisé si window < MinTRL

### Livrable 2 — `docs/2026-05-XX_P0A_TIMEFRAME_COMPARISON.md`

**Schéma obligatoire :**
```
# P0-A Timeframe Comparison

| Metric                     | 1m     | 5m     | 10m    | 15m    |
|----------------------------|--------|--------|--------|--------|
| training_row_count         |        |        |        |        |
| validation_row_count       |        |        |        |        |
| feature_count              |        |        |        |        |
| model_feature_hash         |        |        |        |        |
| training_window_days       |        |        |        |        |
| early_stopping_rounds      |        |        |        |        |
| best_validation_rmse_bps   |        |        |        |        |
| best_validation_mae_bps    |        |        |        |        |
| optuna_trial_count         |        |        |        |        |
| best_lightgbm_params       |        |        |        |        |
| backtest_trades_executed   |        |        |        |        |
| backtest_net_bps_per_trade |        |        |        |        |
| backtest_psr               |        |        |        |        |
| backtest_dsr               |        |        |        |        |
| selected_timeframe         | <bool> | <bool> | <bool> | <bool> |
```

**Critère d'acceptation :**
- 4 colonnes obligatoires (1m, 5m, 10m, 15m)
- Tous les hashes citables (model_feature_hash, dataset_hash, artifact_hash)
- 1 seul timeframe avec `selected_timeframe=true` (le meilleur DSR)

### Livrable 3 — Modèles sérialisés `expected_edge_<tf>.lgb`

**Localisation :**
```
artifacts/expected_edge_models/
├── expected_edge_1m.lgb
├── expected_edge_1m.manifest.json
├── expected_edge_5m.lgb
├── expected_edge_5m.manifest.json
├── expected_edge_10m.lgb
├── expected_edge_10m.manifest.json
├── expected_edge_15m.lgb
└── expected_edge_15m.manifest.json
```

**Schéma `.manifest.json` :**
```json
{
  "schema_version": "v1",
  "model_id": "expected_edge_<tf>_v1",
  "timeframe": "<tf>",
  "pair_scope": ["BTCUSDT"],
  "method_version": "lightgbm.v1",
  "feature_names": [...],
  "feature_hash": "<sha256>",
  "training_dataset_path": "...",
  "training_dataset_hash": "<sha256>",
  "training_row_count": <N>,
  "validation_row_count": <N>,
  "walk_forward_train_days": 180,
  "walk_forward_validation_days": 30,
  "purge_window_minutes": <H>,
  "embargo_window_minutes": <H>,
  "best_params": {...},
  "best_validation_metric": <X>,
  "trained_at_utc": "<ts>",
  "git_commit": "<sha>",
  "artifact_hash": "<sha256 of the .lgb bytes>",
  "expected_edge_provenance_when_used": "GOVERNED_BACKTEST_TRUTH"
}
```

**Critère d'acceptation :**
- 4 fichiers `.lgb` chargeables par `lightgbm.Booster`
- 4 manifests avec hashes vérifiables
- Compatible avec consommateur existant [`strategy_ladder_edge_model_provider.py`](src/local_replay_runtime/strategy_ladder_edge_model_provider.py)

### Livrable 4 — Run audit-ready

**Localisation :** `K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-<P0A_RUN_ID>/`

**Critère d'acceptation :**
- `backtest_proof_matrix.md` overall = `BACKTEST_PROOF_PROMOTION_GRADE` OU `BACKTEST_PROOF_AUDIT_VALIDATED_NEGATIVE`
- Pas de blocker `EXPECTED_EDGE_PROXY_BLOCKED`
- Pas de blocker `BREAK_EVEN_PROXY_BLOCKED`
- `expected_edge_governed_count > 0` ET `expected_edge_proxy_count == 0`
- `statistical_validation_status` parmi {`PSR_PASS`, `PSR_FAIL_WITH_EVIDENCE`, `INCONCLUSIVE_INSUFFICIENT_TRADES`}
- `evidence_class: SCRATCH_ONLY` → 0 (tous artefacts en `AUDIT_VALIDATED` ou `PROMOTION_GRADE`)
- Empty ledgers (`trade_detail_ledger`, `loss_analysis_ledger`) ne sont PAS empty si `executed_trade_count > 0`

### Livrable 5 — `docs/2026-05-XX_P0A_SHADOW_30J_PROMOTION_PLAN.md`

**Schéma obligatoire :**
```
# Shadow 30j Promotion Plan

## Pré-requis (gates Bailey-LdP)
- PSR ≥ 0.60 (G2.1) : <status>
- PSR ≥ 0.85 (G2.2) : <status>
- PSR ≥ 0.95 (G2.3) : <status>
- DSR ≥ 0.95 (trial_count <N>) : <status>
- Shadow consecutive days : 30 required (promotion_gates.py:28)

## Doctrine venue
- historical = BYBIT (validé backtest)
- target = BINANCE
- transfer = BINANCE_SHADOW_REQUIRED
- live = BLOCKED → debloqué après shadow 30j Binance

## Shadow window
- start : <today + N>
- duration : 30 days consecutive
- venue : BINANCE (vs backtest BYBIT)
- pair : BTCUSDT (multi-pair après si P3 livré)

## Promotion gates au jour 30
1. shadow_30j_consecutive_days_passed
2. PSR_observed_live >= PSR_threshold
3. DSR_observed_live >= DSR_threshold
4. cost_parity_replay_vs_live : <ratio>
5. no_critical_incident_count_30j == 0

## Si gates passent → micro_live
- capital_bucket initial : 400 USDT
- promotion vers buckets supérieurs après 30j additionnels micro_live
```

**Critère d'acceptation :**
- Plan exécutable sans ambiguïté
- Tous les gates V5.3 cités avec leur source canonique (promotion_gates.py)
- Cap initial micro_live défini

---

## 3. Plan d'exécution — 6 phases

### Phase 1 — Préalables data (J1, 4h)

**Bloquant :** la fenêtre actuelle (10 jours) est insuffisante pour walk-forward 180j train / 30j val.

**Option α (recommandé) :** étendre A2 à 1 an de données
- Re-run A2 avec `start=2024-08-01, end=2025-07-31` (1 an)
- Effort : ~2-4h (selon volume L: dumps)
- Permet WF 180+30 réel

**Option β (rapide, dégradé) :** WF dégradé sur 10 jours
- `walk_forward_train_days=6, walk_forward_validation_days=3, purge=1d, embargo=1d`
- Effort : 0
- Permet validation pipeline mais verdict statistique INCONCLUSIVE par construction

**Décision attendue :** α ou β (impacte tous les livrables : β garantit `INCONCLUSIVE_STATISTICAL_POWER`)

### Phase 2 — Build datasets training par timeframe (J1-J2)

Pour chaque timeframe `tf ∈ {1m, 5m, 10m, 15m}` :

1. Charger gold `features_<tf>/BTCUSDT/<year>/<month>/<day>.jsonl` (existe déjà)
2. Joindre les forward returns target sur horizon doctrinal :
   - target horizon par défaut `expected_edge_target_horizon_minutes = 15` (à valider)
3. Walk-forward split (purge + embargo doctrinaux)
4. Output : `artifacts/expected_edge_training/<tf>/train.jsonl.gz`, `val.jsonl.gz`

**Module à toucher :** [`strategy_ladder_expected_edge_training.py`](src/local_replay_runtime/strategy_ladder_expected_edge_training.py) — existe déjà, juste paramétrer 4 runs

**Critère :** 4 datasets produits, hashes stables, `feature_timestamp_policy: FEATURE_TIMESTAMP_LEQ_DECISION_TIMESTAMP_ENFORCED`

### Phase 3 — Train 4 LightGBM (J2-J3)

Pour chaque timeframe :

1. `ml_trainer.MlTrainerRequest(max_optuna_trials=50, bagging_folds=5, early_stopping_rounds=50)`
2. Sérialiser le booster trouvé dans `artifacts/expected_edge_models/expected_edge_<tf>.lgb`
3. Écrire le manifest companion `expected_edge_<tf>.manifest.json`

**Module à toucher :**
- [`src/calibration_methods/ml_trainer.py`](src/calibration_methods/ml_trainer.py) — existe
- Nouveau script `scripts/train_expected_edge_per_tf.py` qui orchestre 4 trainings

**Critère :** 4 modèles sérialisés + 4 manifests + hashes stables

### Phase 4 — Wire models dans expected_edge_model_provider (J3, 2h)

Modifier [`strategy_ladder_edge_model_provider.py`](src/local_replay_runtime/strategy_ladder_edge_model_provider.py) :

```python
def resolve_expected_edge_governed(
    *,
    timeframe: str,
    feature_payload: dict,
    pair: str,
) -> tuple[float, str]:
    model_path = Path(f"artifacts/expected_edge_models/expected_edge_{timeframe}.lgb")
    if not model_path.is_file():
        return _fallback_to_proxy(feature_payload)  # delegate to existing chain
    booster = _load_or_cache_booster(model_path)
    expected_edge = booster.predict([_extract_features(feature_payload)])[0]
    return expected_edge, "GOVERNED_BACKTEST_TRUTH"
```

Et modifier [`strategy_ladder_economic_provenance.py`](src/local_replay_runtime/strategy_ladder_economic_provenance.py) pour utiliser cette chaîne dans son resolver.

**Critère :** test unitaire qui charge un modèle factice et vérifie provenance retourne `GOVERNED_BACKTEST_TRUTH`

### Phase 5 — Re-run B2 avec governed model (J3-J4)

1. Re-run le workflow complet avec `expected_edge_model_artifact_ref="artifacts/expected_edge_models/expected_edge_15m.lgb"` (commencer par 15m, le timeframe par défaut V5.3)
2. Vérifier dans `strategy_ladder_summary.json` :
   - `expected_edge_governed_count > 0`
   - `expected_edge_proxy_count == 0`
   - `executed_trade_count > 0` (si P0-B est OK)
3. Répéter pour 1m, 5m, 10m

**Critère :** au moins 1 timeframe produit `executed_trade_count > 0` OU diagnostic clair pourquoi 0

### Phase 6 — Verdict + Comparison + Shadow plan (J4-J5)

1. Calculer PSR/DSR/MinTRL pour chaque timeframe (modules existants `psr.py`/`dsr.py`)
2. Écrire `docs/2026-05-XX_P0A_FINAL_VERDICT.md`
3. Écrire `docs/2026-05-XX_P0A_TIMEFRAME_COMPARISON.md`
4. Écrire `docs/2026-05-XX_P0A_SHADOW_30J_PROMOTION_PLAN.md`
5. Tagger le run audit-ready : passer tous les `evidence_class: SCRATCH_ONLY` → `AUDIT_VALIDATED`

---

## 4. Modules à toucher (récap)

| Module | Modification | Effort |
|---|---|---|
| [`src/local_replay_runtime/strategy_ladder_expected_edge_training.py`](src/local_replay_runtime/strategy_ladder_expected_edge_training.py) | Paramétrer pour 4 tf en batch | 0.5j |
| [`src/calibration_methods/ml_trainer.py`](src/calibration_methods/ml_trainer.py) | Aucune (utilisé tel quel) | 0 |
| [`src/local_replay_runtime/strategy_ladder_edge_model_provider.py`](src/local_replay_runtime/strategy_ladder_edge_model_provider.py) | Ajouter `resolve_expected_edge_governed` | 0.5j |
| [`src/local_replay_runtime/strategy_ladder_economic_provenance.py`](src/local_replay_runtime/strategy_ladder_economic_provenance.py) | Wire chain : GOVERNED > MEDIAN > NAIVE > DEFAULT | 0.5j |
| Nouveau `scripts/train_expected_edge_per_tf.py` | Orchestration 4 trainings | 0.5j |
| Nouveau `scripts/run_p0a_verdict.py` | Orchestration verdict + comparaison | 0.5j |

**Total code : ~2.5j**

**Effort total avec runs (option α 1 an data) :** 4-5j
**Effort total avec runs (option β 10j data, dégradé) :** 2.5-3j

---

## 5. Risques + mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Window 10j → MinTRL impossible | Verdict INCONCLUSIVE garanti option β | Choisir α (étendre 1 an) |
| Co-P0 : P0-B pas fait → 0 trades quand même | Verdict INCONCLUSIVE même avec governed model | Faire P0-B en parallèle (closed_episode_journal engine_d, no_excess engine_b) |
| Engine_d sans closed_episode_journal | 1000/1972 records bloqués | Cold-start synthétique OU exclure engine_d du verdict initial |
| Engine_c sharia-rejection sur fenêtre bear | Pas de trades engine_c | Documenter exclusion + chercher fenêtre bull pour validation engine_c |
| Bronze gaps (F2 toujours ouvert) | Features potentiellement biaisées | Faire F2 (Patch 2 du plan de correction chirurgicale) AVANT P0-A |
| Venue mismatch (Bybit vs Binance target) | Verdict non-transférable live | Documenter explicitement dans `2026-05-XX_P0A_FINAL_VERDICT.md` |

---

## 6. Critères de succès finaux

✅ **Succès complet :**
- Verdict = `BACKTEST_PROFITABILITY_PROVEN_POSITIVE`
- PSR ≥ 0.95 sur au moins 1 timeframe
- DSR ≥ 0.95 avec multi-testing correction
- `executed_trade_count` ≥ MinTRL calculée
- Shadow 30j plan exécutable

🟡 **Succès partiel :**
- Verdict = `INCONCLUSIVE_STATISTICAL_POWER` (window trop courte)
- Pipeline débloqué, trades exécutés, mais N < MinTRL
- Suite : recommencer avec window étendu

🔴 **Échec audit :**
- Verdict = `BACKTEST_PROFITABILITY_PROVEN_NEGATIVE`
- PSR observé < 0.50 sur tous les timeframes après débloquage
- Le pipeline fonctionne, V5.3 perd réellement de l'argent sur cette fenêtre

❌ **Échec exécution :**
- `executed_trade_count == 0` même avec governed model
- Diagnostic P0-B (Co-P0) requis avant de pouvoir conclure

---

## 7. Pré-requis avant lancement Phase 1

- [ ] Décision option α (étendre 1 an) vs option β (10j dégradé)
- [ ] Décision P0-B en parallèle ou séquentiel avec P0-A
- [ ] Bronze gaps (F2) — fixer avant ou accepter contamination features ?
- [ ] Venue doctrine Q1/Q2/Q3 — toujours non tranchée
- [ ] Bootstrap fingerprints F1 — peut être différé après P0-A

---

## 8. Statut actuel

**Date du plan :** 2026-05-20
**Code écrit :** 0 lignes
**Décisions utilisateur prises :** 0 / 5 pré-requis ci-dessus
**Run de référence (input) :** `strategy_ladder_workflow-03a3ffe825e7e9fb` (10j, 2025-07-18→28)
**Run de validation (output) :** `strategy_ladder_workflow-<P0A_RUN_ID>` (à produire)

**NEXT — décision utilisateur attendue** sur les 5 pré-requis section 7 avant que Phase 1 puisse démarrer.
