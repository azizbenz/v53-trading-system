# P0-A — Détail des 6 Phases (Plan d'Exécution Approfondi)

**Date :** 2026-05-20
**Document parent :** [`2026-05-20_P0A_EXECUTION_PLAN.md`](2026-05-20_P0A_EXECUTION_PLAN.md)
**Statut :** PLAN — décisions utilisateur attendues phase par phase

---

## Comment utiliser ce document

Chaque phase est documentée avec la structure :
- **Rôle dans la chaîne** : pourquoi cette phase existe
- **Input** : ce qu'elle consomme
- **Action concrète** : étapes effectives + modules touchés
- **Output** : artifacts produits
- **Décisions à prendre** : choix utilisateur explicites (tableau)
- **Implications par option** : conséquences de chaque choix
- **Risques + mitigations**
- **Validation** : comment savoir que la phase est OK
- **Effort détaillé**

À la fin : tableaux récap + recommandation par défaut.

---

## Vue d'ensemble — pipeline P0-A

```
PHASE 1 — Préalables data
    ↓ produit silver + gold pour la fenêtre choisie
PHASE 2 — Build datasets training (4 timeframes)
    ↓ produit train.jsonl.gz + val.jsonl.gz × 4 tf
PHASE 3 — Train 4 LightGBM models
    ↓ produit expected_edge_<tf>.lgb + manifests × 4
PHASE 4 — Wire models dans expected_edge_model_provider
    ↓ active la résolution GOVERNED_BACKTEST_TRUTH
PHASE 5 — Re-run B2 avec governed model
    ↓ produit runs avec expected_edge_governed_count > 0
PHASE 6 — Verdict + Comparison + Shadow plan
    ↓ produit les 5 livrables finaux P0-A
```

**Dépendances :** chaque phase exige que la précédente soit complète. Phases 5 peut s'exécuter en parallèle pour les 4 tf.

---

# PHASE 1 — Préalables data

## Rôle dans la chaîne

**Première brique.** Sans données de qualité et de volume suffisant, toute la suite est garbage-in/garbage-out. C'est là que se joue la **validité statistique** du verdict final.

C'est la phase qui détermine si on aura assez d'observations pour passer les gates Bailey-LdP MinTRL et MinBTL.

## Input

- Raw dumps L: (orderbook, trades, klines) — déjà disponibles
- Fenêtre temporelle `start`/`end` à définir (la décision principale)
- Pair scope : BTCUSDT (multi-pair = Phase futur)

## Action concrète

Re-run de la phase A2 (data factory) avec une nouvelle fenêtre `start/end` dans la config cockpit ou via CLI.

**Module concerné :** [`strategy_ladder_data_factory.py`](../src/local_replay_runtime/strategy_ladder_data_factory.py) — pas de modification code requise, juste paramètre

**Commande type :**
```bash
python scripts/run_data_factory.py \
  --start <YYYY-MM-DD> \
  --end <YYYY-MM-DD> \
  --pair BTCUSDT \
  --timeframes 1m,5m,10m,15m
```

## Output

```
phase_a2_data_factory/
├── silver/bybit/spot/
│   ├── ohlcv/<tf>/BTCUSDT/<year>/<month>/<day>.jsonl.gz
│   ├── orderbook_delta/BTCUSDT/<year>/<month>/<day>.jsonl.gz
│   ├── orderbook_snapshot/BTCUSDT/<year>/<month>/<day>.jsonl.gz
│   └── trades/BTCUSDT/<year>/<month>/<day>.jsonl.gz
├── gold/features_<tf>/BTCUSDT/<year>/<month>/<day>.jsonl
├── data_factory_manifest.json
├── silver_index.json
└── 25+ rapports d'audit (raw_source_report, data_quality_report, etc.)
```

## Décisions à prendre

| Option | Fenêtre | Durée run A2 | Stockage disque | Validité statistique |
|---|---|---|---|---|
| **α — Full year** | `2024-08-01 → 2025-07-31` (12 mois) | ~3-5h | ~10 GB silver + ~500 MB gold | ✅ MinTRL Bailey-LdP satisfaite si SR ≥ 1.5 |
| **β — Dégradé 10j** | `2025-07-18 → 2025-07-28` (existant) | 0 (déjà fait) | déjà sur disque | ❌ INCONCLUSIVE garanti |
| **γ — 3 mois** | `2025-05-01 → 2025-07-31` (3 mois) | ~1-2h | ~3 GB silver | 🟡 partiel — couvre 1 régime, pas multi-régime |
| **δ — 6 mois** | `2025-02-01 → 2025-07-31` (6 mois) | ~2-3h | ~5 GB silver | 🟢 OK si SR ≥ 2.0 |

## Implications par option

### Option α (1 an)
- ➕ Verdict statistiquement défendable (Bailey-LdP MinBTL ≥ 1 an avec 20 trials testés)
- ➕ Couvre multi-régime (bull/bear/range BTC)
- ➕ DSR multi-testing correction crédible
- ➖ Run A2 long (3-5h)
- ➖ 10 GB silver — vérifier place disque K:
- ➖ Bronze gaps potentiellement plus nombreux sur 1 an
- ⚠ Si tu manques de raw L: pour certains jours → A2 va skip et te le dire dans `pair_data_coverage`

### Option β (10j actuel)
- ➕ Zéro travail data
- ➕ Pipeline déjà validé sur cette fenêtre
- ➖ Verdict garanti `INCONCLUSIVE_STATISTICAL_POWER` (PSR mathématiquement infaisable)
- ➖ Pas de cross-régime
- ⚠ Tu obtiendras des modèles entraînés mais le verdict ne tranchera rien

### Option γ (3 mois)
- 🟡 Bon compromis durée/validité
- 🟡 Permet WF 60j train + 30j val + 30j test
- ⚠ Risque single-régime (mai-juillet 2025 = comportement spécifique)
- ⚠ MinBTL Bailey-Borwein-LdP-Zhu 2014 : avec N_trials=20, MinBTL=2*ln(20)/SR² ≈ 6 ans pour SR=1.0 → 3 mois insuffisants pour DSR

### Option δ (6 mois)
- ➕ Permet WF 120j train + 30j val + 30j test
- ➕ Multi-régime probable (couvrir au moins 2 phases marché)
- ➕ Compromis effort/validité optimal
- ➖ Run A2 ~2-3h

## Validation

Vérifier après le run A2 :
- `data_factory_manifest.blocker_codes` ne contient PAS d'erreur disque/parsing critique
- `pair_universe_report.pair_data_coverage.coverage_status: PAIR_DATA_COVERAGE_READY` sur toute la fenêtre
- Pas de jour manquant : `find silver/<tf>/BTCUSDT/<year>/<month>/ -name '*.jsonl.gz' | wc -l` == nombre_jours_fenêtre
- `silver_quality_report.silver_sync_status` == `SILVER_SYNC_COMPLETE` (ou `PARTIAL` si bronze gaps connus)
- `compression_report.silver_storage_status: SILVER_STORAGE_READY_COMPRESSED`

## Risques + mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Manque de raw L: sur certains jours | Moyenne (1 an) | Couverture trouée | A2 produit `pair_data_coverage` détaillé — vérifier avant Phase 2 |
| Disque K: insuffisant | Faible | A2 échoue mid-run | Pré-vérifier `df -h K:` ≥ 15 GB libre pour option α |
| Bronze gaps explose sur 1 an | Élevée | Features biaisées | Pré-requis F2 (bronze gap severity classifier) avant Phase 2 |
| Metadata fees anachroniques | Élevée | break_even biaisé | Pré-requis F4 (`bybit_historical_metadata` mode switch) |

## Effort

- α (1 an) : ~3-5h run + 30min vérification + résolution bronze gaps potentiels
- β (10j) : 0
- γ (3 mois) : ~1-2h
- δ (6 mois) : ~2-3h

---

# PHASE 2 — Build datasets training (4 timeframes)

## Rôle dans la chaîne

**Pont entre data brute et modèle ML.** Transforme les features gold + forward returns en (X, y) training rows utilisables par LightGBM. C'est là que se définit ce que le modèle va apprendre.

C'est la phase critique pour **anti-leakage** (purge/embargo) et **walk-forward correctness** (Bailey-LdP).

## Input

- Gold features : `gold/features_<tf>/BTCUSDT/<year>/<month>/<day>.jsonl` (de Phase 1)
- Target horizon en minutes (paramètre doctrinal)
- Walk-forward params (train_days, val_days, purge, embargo)

## Action concrète

Pour chaque `tf ∈ {1m, 5m, 10m, 15m}` :

1. Charger les barres gold du tf depuis la fenêtre Phase 1
2. Joindre forward return target : `forward_return = (close[t + horizon] - close[t]) / close[t]`
3. Filtrer rows invalides (NaN, gaps, post-window)
4. Appliquer purge + embargo aux limites train/val (anti-leakage)
5. Split walk-forward train/val
6. Sérialiser en `train.jsonl.gz` + `val.jsonl.gz`
7. Calculer hashes + manifest

**Module à toucher :** [`strategy_ladder_expected_edge_training.py`](../src/local_replay_runtime/strategy_ladder_expected_edge_training.py) — **existe déjà**, paramétrer 4 runs en batch

## Output

Pour chaque tf :
```
artifacts/expected_edge_training/<tf>/
├── train.jsonl.gz           # features + target rows pour training
├── val.jsonl.gz             # features + target rows pour validation
├── dataset_manifest.json    # hashes + walk-forward params + row counts
└── label_quality_report.json # MFE/MAE, NaN counts, gap detection
```

## Décisions à prendre

| Décision | Options | Recommandation | Justification |
|---|---|---|---|
| **Target horizon (par tf)** | 5min / 15min / 30min / 60min | **15min** | Cohérent doc 21 §5 V5.3 |
| **Walk-forward train days** | 60 / 120 / 180 | **180** (doctrine V5.3) | Exige Phase 1 ≥ option δ (6 mois) |
| **Walk-forward validation days** | 14 / 30 / 60 | **30** (doctrine V5.3) | Bailey-LdP standard |
| **Purge window** | 0 / horizon / 2×horizon | **= horizon** | Bailey-LdP anti-leakage |
| **Embargo window** | 0 / horizon / 2×horizon | **= horizon** | Bailey-LdP |
| **Feature set par tf** | 3 verrouillé / enrichi microstructure | **3 verrouillé** | Validator V5.3 P6 |
| **Sample stride** | toutes barres / chaque N | **horizon** | Évite over-sampling de séquences corrélées |

## Implications

### Target horizon plus court (5min vs 60min)
- ➕ Plus de samples (plus de paires (t, t+h) possibles dans la même fenêtre)
- ➖ Edge plus petit (mouvements 5min < 60min)
- ⚠ Pour 1m target horizon=5min ⇒ horizon=5 bars ; pour 15m horizon=15min ⇒ horizon=1 bar
- **Recommandation :** ratio horizon/barre ≥ 1 pour avoir signal exploitable

### Walk-forward 180+30
- ➕ Validation OOS robuste, Bailey-LdP compliant
- ➖ EXIGE fenêtre ≥ 210 jours (option α ou δ)
- Si fenêtre = 10j (option β), WF impossible → fallback dégradé 6j+3j (verdict INCONCLUSIVE garanti)

### Feature set 3 vs enrichi
- **3 (close_return, high_low_range, volume)** : ce que validator V5.3 autorise aujourd'hui
- **Enrichi (+VPIN, OFI, queue, spread)** : aligne train avec engines C/D mais nécessite F16 (modifier validator)
- Recommandation : commencer avec 3 (cohérent), élargir si verdict INCONCLUSIVE par sous-fit

## Risques + mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| NaN forward_return en fin de fenêtre | Élevée | Rows perdues | Skip rows + log count dans label_quality_report |
| Target leakage involontaire | Moyenne | Modèle "magique" sur val | feature_timestamp_policy enforced + purge + embargo |
| Feature distribution shift train→val | Moyenne | Modèle mal calibré | Documentation distribution + analyse drift |
| 1m volume trop faible pour LightGBM | Faible (si α) | Modèle 1m sous-performant | Skip 1m si train_row_count < 1000 |

## Validation

- `dataset_manifest.feature_hash` stable et reproductible (`sha256` du schéma features)
- `feature_timestamp_policy: FEATURE_TIMESTAMP_LEQ_DECISION_TIMESTAMP_ENFORCED` présent
- `train_row_count + val_row_count` = expected total samples (calc depuis fenêtre)
- `purge_window_minutes` + `embargo_window_minutes` cohérents entre train/val (mêmes valeurs)
- Pas de NaN dans target colonne (`forward_return finite`)
- Manifest cite `source_gold_feature_refs` exhaustif

## Effort

- 4 datasets en parallèle : ~30min-1h selon volume Phase 1
- Plomberie code (paramétrage 4 runs en batch) : ~0.5j
- Validation manuelle des manifests : ~30min

---

# PHASE 3 — Train 4 LightGBM models

## Rôle dans la chaîne

**Création du signal `GOVERNED_BACKTEST_TRUTH`.** C'est LA brique qui débloque `edge_is_truth=True` dans le runner. Sans ces modèles, le pipeline reste bloqué sur proxy.

## Input

- 4 datasets `train.jsonl.gz` + `val.jsonl.gz` de Phase 2
- Hyperparamètres LightGBM (Optuna trials, bagging folds, early stopping)

## Action concrète

Pour chaque tf :

1. Charger `train.jsonl.gz` + `val.jsonl.gz`
2. Appeler `compute_expected_edge_training_artifact` ([`src/calibration_methods/ml_trainer.py`](../src/calibration_methods/ml_trainer.py)) avec :
   - `max_optuna_trials = <choix>`
   - `bagging_folds = 5`
   - `early_stopping_rounds = 50`
   - `training_seed = 42` (reproductibilité)
3. Sauvegarder `Booster` LightGBM dans `expected_edge_<tf>.lgb`
4. Écrire `expected_edge_<tf>.manifest.json` companion

**Modules :**
- [`src/calibration_methods/ml_trainer.py`](../src/calibration_methods/ml_trainer.py) — **existe**
- Nouveau script `scripts/train_expected_edge_per_tf.py` (~80 lignes) qui orchestre les 4 trainings

## Output

```
artifacts/expected_edge_models/
├── expected_edge_1m.lgb              # binaire LightGBM
├── expected_edge_1m.manifest.json    # métadonnées complètes
├── expected_edge_5m.lgb
├── expected_edge_5m.manifest.json
├── expected_edge_10m.lgb
├── expected_edge_10m.manifest.json
├── expected_edge_15m.lgb
└── expected_edge_15m.manifest.json
```

Schéma manifest companion (cf. P0A_EXECUTION_PLAN §2 livrable 3) avec model_id, feature_hash, training_dataset_hash, best_params, best_validation_metric, trained_at_utc, git_commit, artifact_hash.

## Décisions à prendre

| Décision | Options | Implication |
|---|---|---|
| **`max_optuna_trials`** | 0 / 20 / 50 / 100 | 0 = base params (rapide, déterministe), 50 = bon compromis (~10-30min par tf), 100 = plafond max |
| **Métrique d'optimisation Optuna** | RMSE / MAE / R² / DSR-aware | RMSE par défaut, MAE plus robuste outliers |
| **Bagging folds** | 3 / 5 / 10 | 5 (doctrine V5.3) |
| **Early stopping rounds** | 20 / 50 / 100 | 50 (équilibre overfitting/underfitting) |
| **Re-train sur train+val final** | oui / non | Non par défaut (best val checkpoint) |
| **Seed** | random / 42 | **42 fixed** pour reproductibilité audit |

## Implications par choix Optuna

### `max_optuna_trials = 0`
- ➕ Run rapide, déterministe
- ➕ Pas de chance influence
- ➖ Modèle non optimisé — peut être sous-performant
- **Usage :** smoke test, premier passage end-to-end pour valider le pipeline

### `max_optuna_trials = 20`
- ➕ Modèle décent
- ➕ ~5-15min par tf
- 🟡 Couvre learning_rate ×_num_leaves_×_min_data_in_leaf grid partiellement
- **Usage :** premier vrai training

### `max_optuna_trials = 50`
- ➕ Bon optimum trouvé typiquement
- ➕ Couvre grid raisonnablement
- ➖ ~10-30min par tf, soit 40min-2h pour les 4 tf
- **Usage :** run sérieux pour verdict P0-A

### `max_optuna_trials = 100`
- ➕ Plafond max V5.3, search space complet
- ➖ ~1h par tf, 4h total
- ➖ Diminishing returns au-delà de 50 typiquement
- **Usage :** training final si verdict initial avec 50 trials est borderline

## Risques + mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Overfitting validation set | Moyenne | Modèle ne généralise pas | Bagging 5 folds + early stopping + DSR final post-train |
| Données insuffisantes 1m | Élevée si option β | Modèle 1m sous-performant | Skip 1m si train_row_count < 1000 |
| Hyperparamètres en dehors du grid Optuna | Faible | Optimum sous-jacent manqué | Augmenter trials ou tuner manuel |
| Target leakage involontaire | Moyenne | Modèle "magique" sur val, échec backtest | Purge + embargo Phase 2 |
| Non-reproductibilité | Faible | Audit re-run divergent | Seed fixed=42 + version freezing |

## Validation

- 4 fichiers `.lgb` chargeables par `lightgbm.Booster(model_file=path)`
- `best_validation_metric` raisonnable (typiquement RMSE 5-20 bps pour les forward returns)
- Manifest avec `git_commit` + `artifact_hash` + `trained_at_utc`
- Test reproducibilité : re-run avec seed=42 donne mêmes hashes
- Importance features cohérente avec attentes domain (close_return weight élevé)

## Effort

- Code paramétrage script : ~0.5j
- Run training (option β 10j) : ~5-15min total
- Run training (option α 1 an, Optuna 50) : ~40min-2h total
- Run training (option α 1 an, Optuna 100) : ~2-4h total
- Validation post-train : ~30min

---

# PHASE 4 — Wire models dans expected_edge_model_provider

## Rôle dans la chaîne

**Activation du governed mode.** Sans cette étape, les 4 modèles entraînés sont **inutiles** — le runner ne les consultera pas et restera sur proxy.

## Input

- 4 modèles `.lgb` + manifests de Phase 3
- Architecture provider existant dans `strategy_ladder_edge_model_provider.py`

## Action concrète

Modifier [`strategy_ladder_edge_model_provider.py`](../src/local_replay_runtime/strategy_ladder_edge_model_provider.py) :

```python
# Nouveau resolver
def resolve_expected_edge_governed(
    *,
    timeframe: str,
    feature_payload: dict[str, object],
    pair: str,
) -> tuple[float, str]:
    """Returns (expected_edge_bps, 'GOVERNED_BACKTEST_TRUTH') OR fallback chain."""
    model_path = Path(f"artifacts/expected_edge_models/expected_edge_{timeframe}.lgb")
    if not model_path.is_file():
        return _fallback_to_proxy_chain(...)
    booster = _cached_booster_load(model_path)
    features = _extract_features_aligned_with_training(feature_payload)
    expected_edge_bps = float(booster.predict([features])[0])
    return expected_edge_bps, "GOVERNED_BACKTEST_TRUTH"
```

Et brancher ce resolver dans [`strategy_ladder_economic_provenance.py`](../src/local_replay_runtime/strategy_ladder_economic_provenance.py) au top de la chaîne provenance.

## Output

- Modules modifiés (diff ~80 lignes total)
- Test unitaire `tests/test_local_replay_runtime/test_governed_edge_provider.py` (~60 lignes)

## Décisions à prendre

| Décision | Options | Recommandation | Justification |
|---|---|---|---|
| **Cache booster en mémoire ?** | LRU 10 / persistent / no-cache | **LRU 10** | Équilibre RAM/IO ; 10 boosters × 50 MB = 500 MB max |
| **Si model manquant ?** | fallback proxy / fail-closed | **fallback proxy** | Continuité service (le runner ne plante pas) |
| **Feature mismatch ?** | fail-closed / log + fallback | **fail-closed** | Évite predictions hallucinées avec features dans mauvais ordre |
| **Provenance chain order** | GOVERNED > MEDIAN > NAIVE > DEFAULT | OK (cf. Patch 3 plan correction chirurgicale) | Doctrine V5.3 |

## Implications

### Cache LRU 10
- Permet de charger 10 boosters max simultanément (4 tf actuels + buffer pour multi-pair future)
- ~50 MB RAM par booster typique
- ~500 MB max RAM — acceptable pour cockpit/B2 runtime

### Fallback proxy si model absent
- Le runner ne plante pas si on n'a pas trained sur un tf donné
- Continuité : proxy continue de servir, juste statut reste `PROXY_*`
- Coté audit : `expected_edge_provenance` montre clairement quel mode est actif

### Fail-closed sur feature mismatch
- Si le runner envoie des features dans un ordre/nom différent du training → refus
- Évite predictions hallucinées
- Exige test régression strict
- Reason code `EXPECTED_EDGE_FEATURE_MISMATCH` propagé dans les refusal_ledger

## Risques + mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Feature mismatch runtime/training | Moyenne | Modèle inutile en runtime | Hash check feature_names avant predict |
| Cache memory leak | Faible | OOM long-run | LRU bornée + monitoring RAM |
| Booster load slow | Moyenne | Latence cockpit | Pré-warm cache au startup |
| Pickle deserialization version mismatch | Faible | Échec load | Versionner LightGBM dans manifest |

## Validation

- Test unit 1 : charger un modèle factice → resolver retourne `provenance == 'GOVERNED_BACKTEST_TRUTH'`
- Test unit 2 : modèle absent → resolver retourne proxy fallback avec `provenance == 'PROXY_*'`
- Test unit 3 : feature mismatch → resolver retourne `EXPECTED_EDGE_FEATURE_MISMATCH`
- Test integration : `economic_provenance.py` priorité respectée (GOVERNED > MEDIAN > NAIVE > DEFAULT)
- Test perf : 1000 predictions en < 100ms

## Effort

- Code resolver : ~0.5j
- Code wiring economic_provenance : ~0.3j
- Tests : ~0.5j
- Total : **~1.3j**

---

# PHASE 5 — Re-run B2 avec governed model

## Rôle dans la chaîne

**Le moment de vérité.** C'est là qu'on observe si débloquer `edge_is_truth=True` fait quelque chose ou si P0-B est aussi requis (Co-P0 doctrine).

C'est la phase qui consomme **tout** le travail précédent et produit les artifacts pour le verdict.

## Input

- Modèles wired (Phase 4)
- Data factory ready (Phase 1)
- Datasets training (Phase 2) — pas directement utilisés ici, mais leur existence valide le pipeline

## Action concrète

Pour chaque tf, lancer un B2 fresh :

```bash
scripts/run_strategy_ladder_workflow.py \
  --start <date> --end <date> \
  --pair BTCUSDT \
  --timeframe <tf> \
  --expected-edge-model-artifact-ref artifacts/expected_edge_models/expected_edge_<tf>.lgb \
  --ml-mode-status ML_MODE_OFF \
  --engine-native-mode \
  --candidate-discovery-mode TEMPORAL_STRATIFIED \
  --sample-cap-per-engine <choix>
```

## Output

Pour chaque tf, un run complet :
```
K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-<P0A_<tf>_RUN_ID>/
├── phase_a1_preview/
├── phase_a2_data_factory/   (réutilise Phase 1 — pas re-run)
├── phase_b1_candidate_discovery/
└── phase_b2_detailed_replay/
    └── reports/
        ├── strategy_ladder_summary.json   ← vérifier expected_edge_governed_count
        ├── engine_no_trade_diagnosis.json
        └── ...
```

## Décisions à prendre

| Décision | Options | Implication |
|---|---|---|
| **Lancer 4 timeframes ?** | seul 15m / 2 tf / 4 tf | 4 tf pour livrable 2 (comparison), sinon comparison vide |
| **Capital buckets** | [400, 500, 1500, 4000] / réduit | Défaut V5.3 (4 buckets) |
| **`candidate_discovery_mode`** | `TEMPORAL_STRATIFIED` / `FULL_DISCOVERY` | **TEMPORAL_STRATIFIED** (sample uniforme dans le temps) |
| **`sample_cap_per_engine`** | 250 / 1000 / 5000 / unlimited | Augmenter pour Co-P0 — sinon insuffisant pour MinTRL |
| **P0-B en parallèle ?** | oui / non | **OUI recommandé** (sinon executed_count=0) |
| **Tagger evidence_class à la fin ?** | SCRATCH_ONLY / AUDIT_VALIDATED | AUDIT_VALIDATED si tout OK |

## Implications

### 4 timeframes vs 1
- **1 seul tf (15m par défaut)** : 1 run B2 ≈ 30-60min, livrable comparaison partiel
- **4 tf** : 4 runs séquentiels ou parallèles, 2-4h total, livrable comparaison complet

### Co-P0 : si P0-B pas fait
- `executed_trade_count` restera 0 même avec modèle gouverné
- Raisons : `ENGINE_NATIVE_NO_TRADE` (engines disent no_trade pour leurs raisons internes)
- Verdict sera `INCONCLUSIVE_INSUFFICIENT_TRADES`
- ⚠ **Décision critique** : faire P0-B en parallèle de cette phase ?

### `sample_cap_per_engine`
- **250 actuel × 4 engines × 12 jours** = 12 000 candidats max théoriques sur option α 1 an mais cap effectif 1000
- Si on veut **MinTRL = 200 trades**, et conversion candidat→trade ≈ 30%, il faut **667+ candidats sélectionnés/exécutés**
- Augmenter cap à 1000-5000 selon Phase 1 volume

## Risques + mitigations

| Risque | Symptôme attendu | Que faire |
|---|---|---|
| Co-P0 non clos → 0 trades | `executed_trade_count == 0` | Faire P0-B en parallèle |
| Modèle prédit edge < break-even | `selected_count > 0`, `executed_count > 0` mais net négatif | OK c'est le verdict |
| Feature mismatch runtime/training | `EXPECTED_EDGE_FEATURE_MISMATCH` partout | Re-aligner features Phase 2/4 |
| Volume gold insuffisant | `feature_row_count < N_min` | Étendre window Phase 1 |
| Bronze gaps biaisent edge | Spread/slippage proxy → edge artificially clean | Pré-requis F2 (Patch 2) |
| Run zombie comme dans 20260519-113403 | Multiple `run_manifest.json` contradictoires | Cleanup proactif (F8) |

## Validation

- `strategy_ladder_summary.expected_edge_governed_count > 0`
- `strategy_ladder_summary.expected_edge_proxy_count == 0`
- `final_status` parmi {`READY_FOR_PROMOTION`, `BLOCKED_BY_X` avec X ≠ NO_EXECUTED_TRADES}
- `governed_evidence_status: EVIDENCE_AUDIT_CONFIRMED`
- Au moins 1 trade exécuté par tf (sinon verdict INCONCLUSIVE par défaut)

## Effort

- 1 tf : ~30-60min run
- 4 tf séquentiels : ~2-4h total
- 4 tf parallèles (4 worktrees + 4 process) : ~30-60min
- Vérification + diagnostic post-run : ~1h par tf
- Total : **~3-6h selon parallélisme**

---

# PHASE 6 — Verdict + Comparison + Shadow plan

## Rôle dans la chaîne

**Synthèse finale.** Transforme les 4 runs Phase 5 en 3 documents lisibles qui répondent à la question d'origine : **V5.3 est-elle rentable ?**

## Input

- 4 runs B2 complets de Phase 5
- `strategy_ladder_summary.json` × 4
- Engine matrices, refusal ledgers, trade detail ledgers

## Action concrète

1. **Calculer métriques statistiques** pour chaque tf :
   - PSR via [`src/calibration_methods/psr.py`](../src/calibration_methods/psr.py) — formule Bailey-LdP 2012
   - DSR via [`src/calibration_methods/dsr.py`](../src/calibration_methods/dsr.py) — formule Bailey-LdP 2014 avec deflation
   - MinTRL : `1 + (z_{0.95}/SR̂)²` (~ formule Bailey-LdP)
   - MinBTL : `2·ln(N_trials)/SR_target²` années (Bailey-Borwein-LdP-Zhu 2014)

2. **Identifier `selected_timeframe`** = celui avec DSR max

3. **Écrire les 3 documents** (selon schémas définis dans P0A_EXECUTION_PLAN §2)

4. **Tagger les artifacts** `evidence_class: AUDIT_VALIDATED` (passer de `SCRATCH_ONLY`)

**Nouveau script :** `scripts/run_p0a_verdict.py` (~120 lignes)

## Output

```
docs/
├── 2026-05-XX_P0A_FINAL_VERDICT.md           # Verdict V5.3 rentable y/n
├── 2026-05-XX_P0A_TIMEFRAME_COMPARISON.md    # Table comparative 4 tf
└── 2026-05-XX_P0A_SHADOW_30J_PROMOTION_PLAN.md  # Plan promotion
```

## Décisions à prendre

| Décision | Options | Recommandation | Justification |
|---|---|---|---|
| **target_sharpe doctrinal pour MinTRL** | 1.0 / 1.5 / 2.0 / 3.0 | **1.5** | Modeste défendable crypto |
| **trial_count pour DSR** | engines × strategies = 12 / mesuré | **mesuré** depuis le run | Bailey-LdP 2014 exige effective N |
| **Verdict criteria** | PSR / DSR / les deux / triple-gate | **les deux ≥ 0.95** (G2.3) | Doctrine V5.3 fail-closed |
| **Si INCONCLUSIVE** | Reporter / Lancer Phase 1 plus longue | À ta décision | Affect Phase 1 future |
| **Format du verdict final** | binaire / nuancé | **3-niveaux** (POSITIVE/NEGATIVE/INCONCLUSIVE) | Permet honnêteté |

## Implications par verdict final

### Verdict POSITIVE (PSR & DSR ≥ 0.95)
- ➕ Trigger Shadow 30j Binance plan
- ➕ Capital initial micro_live 400 USDT
- ➕ Promotion gates [`promotion_gates.py`](../src/protocols/promotion_gates.py) active
- ➕ V5.3 prouvée rentable sur cette fenêtre (transférabilité Binance encore à valider)

### Verdict NEGATIVE (PSR observé < 0.50 sur tous tf)
- ➖ V5.3 a un edge réellement négatif sur cette fenêtre
- ➕ Reporter sans bypass — la doctrine fail-closed est respectée
- ➖ Investigation Co-P0 backwards : pourquoi engines émettent des candidats perdants ?

### Verdict INCONCLUSIVE (window trop courte)
- 🟡 Pipeline OK, juste pas assez de N
- 🟡 Re-lancer Phase 1 avec window plus longue (α)
- ➕ Pas de gaspillage : modèles entraînés réutilisables
- ⚠ Décision : repartir Phase 1 OU accepter limites

## Risques + mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Calcul PSR/DSR wrong sur edge cases | Faible | Verdict faussé | Tests anchor existants (test_psr.py, test_dsr.py) |
| MinTRL formula mismatch with paper | Faible | Verdict trop strict ou laxiste | Comparer avec exemples Bailey-LdP 2012 |
| Verdict positif sur fenêtre trop courte | Moyenne | Promotion prématurée | Vérifier MinBTL satisfaction obligatoire |
| Reproducibility broken | Faible | Audit non-vérifiable | Tous hashes citables + git commits |

## Validation

- Verdict tranche (POSITIVE / NEGATIVE / INCONCLUSIVE) sans ambiguïté
- Tous les hashes citables (run_id, dataset_hash, model_artifact_hash, git_commit)
- Reproductibilité : re-run du script produit même verdict
- 3 docs respectent les schémas définis dans `P0A_EXECUTION_PLAN.md §2`
- Shadow plan exécutable sans questions ouvertes

## Effort

- Script verdict + comparison + shadow : ~1j code + 0.5j test
- Rédaction docs : auto-générés depuis script
- Review humain : 1-2h
- Total : **~1.5j**

---

# TABLEAUX RÉCAP

## Tableau 1 — Choix par phase

| Phase | Décision principale | Effort | Bloquant pour suite |
|---|---|---|---|
| 1 | Window α/β/γ/δ | 0-5h | **OUI** — sans data pas de training |
| 2 | Target horizon par tf + WF params | ~1h | **OUI** — sans dataset pas de modèle |
| 3 | Optuna trials 0/20/50/100 | 5min-4h | **OUI** — sans modèle pas de governed |
| 4 | Cache + fallback policy | ~1j code | **OUI** — sans wiring pas d'effet |
| 5 | Combien de tf, P0-B en parallèle ? | ~30min-4h run | **OUI** — sans run pas de verdict |
| 6 | target_sharpe, verdict criteria | ~1j code | **NON** — produit docs finaux |

## Tableau 2 — Implications par option Phase 1

| Phase 1 Choix | Phase 5 résultat probable | Verdict Phase 6 |
|---|---|---|
| α (1 an) + P0-B parallèle + cap 5000 | `executed_trade_count` ≥ 200-1000 | ✅ Verdict tranchable (POSITIVE ou NEGATIVE) |
| α (1 an) + P0-B en attente | `executed_trade_count` = 0 | ❌ INCONCLUSIVE — Co-P0 confirmé |
| β (10j) + tout | `executed_trade_count` < 50 | ❌ INCONCLUSIVE statistical_power |
| γ (3 mois) + P0-B parallèle | `executed_trade_count` ≈ 50-200 | 🟡 verdict possible mais fragile |
| δ (6 mois) + P0-B parallèle | `executed_trade_count` ≈ 100-400 | 🟢 verdict défendable |

## Tableau 3 — Effort par phase et option

| Phase | β (10j) | γ (3 mois) | δ (6 mois) | α (1 an) |
|---|---|---|---|---|
| 1 | 0 | 1-2h | 2-3h | 3-5h |
| 2 | 1h | 1h | 1h | 1h |
| 3 (Optuna 50) | 15min | 30min | 1h | 2h |
| 4 | 1.3j | 1.3j | 1.3j | 1.3j |
| 5 (4 tf parallèle) | 1h | 2h | 3h | 4h |
| 6 | 1.5j | 1.5j | 1.5j | 1.5j |
| **TOTAL** | **~4j** | **~5j** | **~6j** | **~7j** |

---

# RECOMMANDATION DÉFAUT POUR CHOIX RAPIDE

Si l'objectif est un verdict P0-A **vraiment tranchable** en minimum de temps :

| Phase | Choix recommandé | Pourquoi |
|---|---|---|
| 1 | **δ (6 mois)** | Compromis durée vs validité — α est mieux mais 3-5h run |
| 2 | Target horizon 15min, WF 120+30, purge=embargo=horizon | Bailey-LdP compliant |
| 3 | Optuna 50 trials | Bon compromis qualité/temps |
| 4 | Fallback proxy + cache LRU 10 + fail-closed feature mismatch | Sécurité |
| 5 | 4 tf en parallèle + P0-B en parallèle + cap 2000 | Co-P0 nécessaire |
| 6 | target_sharpe=1.5, criteria PSR & DSR ≥ 0.95, 3-niveaux verdict | Doctrine V5.3 |

**Effort total estimé avec ces choix : 6-7 jours**
- 3j data/runs (Phase 1 + Phase 5)
- 2.5j code (Phases 2, 4, 6 + scripts)
- 1j synthèse + review

---

# CHECKLIST AVANT LANCEMENT

Avant de démarrer Phase 1, valider :

- [ ] Option Phase 1 tranchée (α/β/γ/δ)
- [ ] P0-B parallèle ou séquentiel décidé
- [ ] F2 bronze gaps : fix avant ou accepter contamination ?
- [ ] Venue doctrine Q1/Q2/Q3 : Bybit native / Binance shadow / mono-venue ?
- [ ] F4 metadata historique : mode switch avant Phase 1 ?
- [ ] Quick wins (~2j) à faire avant ou en parallèle ?
- [ ] Espace disque K: vérifié (≥ 15 GB libre pour option α)
- [ ] Permissions worktrees pour parallélisme Phase 5

---

## Statut document

- **Créé :** 2026-05-20
- **Auteur :** Audit V5.3 multidisciplinaire + corrections Codex
- **Référence parent :** [`2026-05-20_P0A_EXECUTION_PLAN.md`](2026-05-20_P0A_EXECUTION_PLAN.md)
- **Prochain document attendu :** Décisions utilisateur sur les 8 items du checklist ci-dessus, après quoi Phase 1 démarre
