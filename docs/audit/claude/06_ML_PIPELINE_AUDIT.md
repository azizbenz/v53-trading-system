# Audit ML pipeline V5.3

**Date** : 2026-05-07
**Modules audités** :
- `src/calibration_methods/ml_trainer.py` (449 lignes)
- `src/calibration_methods/regime_detector_*.py` (4 fichiers)
- `src/local_replay_runtime/local_lab_loss_surrogate.py`
- `src/local_replay_runtime/local_lab_ml_artifact_training.py`
- `src/local_replay_runtime/ml_final_audit_report.py`
- `src/calibration_methods/multiple_testing_guard.py`
- `src/meta_learning/build9x_ml_seam.py`

## Résumé exécutif

| Module | Status | Best practice quant |
|---|---|---|
| `ml_trainer.py` | ✅ VERIFIED | walk-forward + bootstrap + Sharpe + KS drift + Optuna HPO |
| `regime_detector_trainer.py` | 🟡 PARTIAL | structure ok, pas vérifié ligne-à-ligne |
| `multiple_testing_guard.py` | 🟡 PARTIAL | Sharpe-deflated Harvey-Liu-Zhu 2016 (à vérifier) |
| `local_lab_loss_surrogate.py` | 🟡 PARTIAL | surrogate de loss ex-post |
| `ml_final_audit_report.py` | 🟡 PARTIAL | audit report compiler |

## 1. `ml_trainer.py` — VERIFIED audit-ready

### Architecture LightGBM walk-forward + Bayesian bagging + Optuna HPO

**Best practices ML quant détectées** :

#### 1.1 Walk-forward split causal (lignes 154-179)
```python
def _split_walk_forward(rows, *, train_days, validation_days):
    sorted_rows = tuple(sorted(rows, key=lambda r: r.timestamp))
    validation_end = sorted_rows[-1].timestamp
    validation_start = validation_end - timedelta(days=validation_days - 1)
    train_start = validation_start - timedelta(days=train_days)
    train_rows = tuple(r for r in sorted_rows if train_start <= r.timestamp < validation_start)
    validation_rows = tuple(r for r in sorted_rows if validation_start <= r.timestamp <= validation_end)
```

✅ **Pas de leakage temporel** : validation strictement après train. Standard académique.

#### 1.2 Bootstrap bagging
```python
def _bootstrap_bags(row_count, *, folds, seed):
    bag_size = max(1, row_count - 1)  # Bayesian bagging
    for bag_index in range(folds):
        rng = random.Random(seed + bag_index)  # deterministic per bag
        bags.append(tuple(rng.randrange(0, row_count) for _ in range(bag_size)))
```

✅ **Bayesian bagging avec seeds dédiés** par fold → reproductible.

#### 1.3 Strategy Sharpe metric (anti-overfitting)
```python
def _strategy_sharpe(predictions, targets):
    realized = [pred * target for pred, target in zip(predictions, targets)]
    return statistics.mean(realized) / statistics.pstdev(realized)
```

✅ **Pas un MSE in-sample** mais le **Sharpe** d'une stratégie qui pondère par predictions. C'est la métrique économique pertinente.

#### 1.4 Feature drift KS test
```python
def _evaluate_feature_drift(train_rows, validation_rows, feature_names):
    pvalues = []
    for feature_name in feature_names:
        train_values = [...]
        validation_values = [...]
        result = compute_ks_2sample(train_values, validation_values)
        pvalues.append(result.p_value)
    return min(pvalues)
```

✅ **Kolmogorov-Smirnov 2-sample** par feature, retourne le min p-value (pire feature). Détection automatique de drift covariate.

#### 1.5 Optuna hyperparameter tuning
**Lignes 315-350** :
- `learning_rate` ∈ [0.01, 0.1]
- `num_leaves` ∈ [16, 63]
- `min_data_in_leaf` ∈ [8, 32]
- direction = "maximize" sur Sharpe validation
- `n_trials` ∈ [0, 100] borné

✅ Bayesian HPO standard. Bornes raisonnables LightGBM tabulaire.

#### 1.6 Determinism complet
```python
"seed": request.training_seed,
"feature_fraction_seed": request.training_seed,
"bagging_seed": request.training_seed,
"data_random_seed": request.training_seed,
```

✅ **4 seeds LightGBM propagés** depuis `training_seed`. Reproductibilité totale.

#### 1.7 Artifact production-ready
**Lignes 395-426** :
```python
artifact = MlModelArtifact.create(
    model_family="lightgbm",
    feature_names=...,
    feature_hash=...,
    pair_universe=...,
    train_window=..., validation_window=...,
    oos_sharpe=...,           # validation
    backtest_sharpe=...,      # train (overfit detection)
    ks_test_features_pvalue=..., # drift
    shadow_diff_pct=None,
    training_seed=...,
    calibration_version=...,
    dataset_hash=...,
    model_bytes_b64=base64.b64encode(booster.model_to_string()...),  # serialized
    drift_baseline=MlModelDriftBaseline(
        forecast_mean=mean(train_predictions),
        win_rate=sum(t > 0)/n,
        ce_mean=mean(train_targets),
        ...
    ),
    stale_after=validation_window.end_at + timedelta(days=walk_forward_test_days),
)
```

✅ **Artifact complet audit-ready** :
- model serialized (model_bytes_b64)
- comparison oos vs in-sample Sharpe → overfitting detector
- KS p-value → drift surveillance
- drift_baseline (forecast_mean, win_rate, ce_mean) → runtime drift detection
- stale_after → expiration timestamp pour eviter d'utiliser un modèle obsolète

### Verdict ml_trainer
✅ **VERIFIED** — implémentation sérieuse anti-leakage, anti-overfitting, audit-ready, deterministic.

**Recommandation usage** :
- Train mode "Local Lab only" (pas en live runtime)
- Output : MlModelArtifact qui peut être chargé par CalibrationLoader
- Pour le backtest engine_X : load le modèle, predict, alimenter `expected_edge_bps_override` du service economic provenance

## 2. `regime_detector_*.py`

Modules présents (non lus ligne-à-ligne) :
- `regime_detector_feature_calibration.py`
- `regime_detector_projection.py`
- `regime_detector_trainer.py`
- `regime_detector_runtime.py` (dans `complete_enablers/`)

### Architecture supposée (audit structurel uniquement)
- Trainer offline (regime_detector_trainer)
- Calibration des features sur historique
- Projection runtime pour classer le régime actuel (trend / range / breakout)

### Status
🟡 **PARTIAL** — structure ok, à auditer en détail si critique pour shadow.

## 3. `multiple_testing_guard.py` — Sharpe-deflated

### Référence canonique
Harvey, Liu, Zhu (2016), "...and the Cross-Section of Expected Returns" :

> SR_deflated = SR × √((N − k_HLZ) / (N − 1))
>
> où :
> - SR = observed Sharpe
> - N = nombre de trades
> - k_HLZ = nombre de tests indépendants (= number of pairs/strategies tested)

### Modes V5.3
Doc 21 §8 mentionne 2 modes :
- **observed-shadow mode** : `k_HLZ = pairs_tested` (default actuel = 12 pairs)
- **promotion-floor mode** : `k_HLZ = max(pairs_tested, 20)` (conservateur)

### Status
🟡 **PARTIAL** — formule canonique connue, à vérifier ligne-à-ligne dans le code.

## 4. `local_lab_loss_surrogate.py`

Module trouvé : `LocalLabLossSurrogateModel`, `LocalLabLossSurrogateRecordScore`, `LocalLabLossSurrogateScopeScore`, `LocalLabLossSurrogateReport`.

Fonction principale : `build_local_lab_loss_surrogate_report(...)` construit un rapport ex-post de surrogate models de loss (probablement régression linéaire ou simple bagging sur losses observées).

### Status
🟡 **PARTIAL** — usage : analyse ex-post de loss patterns, pas predictor runtime.

## 5. `ml_final_audit_report.py`

Compilateur d'audit report. Status : 🟡 PARTIAL.

## 6. ML pipeline integration

### Path actuel (backtest)
```
silver data (Bybit historical)
    ↓
backtest features extraction
    ↓
ml_trainer.train_lightgbm_ml_artifact(request)  ← OFFLINE training
    ↓
MlModelArtifact (sérialisé)
    ↓
CalibrationLoader (signed artifacts)
    ↓
Engine X cost/edge consumer (NOT WIRED YET)
```

### Path live (cible)
```
Binance live feeds
    ↓
live microstructure feature extractor (NOT WIRED YET)
    ↓
ml_artifact.predict(features)  ← RUNTIME PREDICT
    ↓
edge_bps prediction → compute_economic_provenance(...override...)
    ↓
Engine X runner
```

### Gap identifié
Le `ml_trainer.py` produit l'artifact, mais **aucun module ne le charge et ne l'utilise pour predict ex-ante** dans le pipeline actuel. C'est exactement ce que `strategy_ladder_edge_model_provider.py` (livré cette session) fait avec une simple median forward-return en attendant.

Pour Sprint 1 : remplacer le forward-return median par un vrai LightGBM predictor :
1. Charger le `MlModelArtifact` via `CalibrationLoader.load_artifact(...)`
2. Désérialiser via `lightgbm.Booster(model_str=...)`
3. Construire feature vector au timestamp t
4. `booster.predict(features)` → edge_bps_override
5. Provenance flag : `MEASURED_FROM_LIGHTGBM_MODEL`

## Conclusion globale ML

✅ `ml_trainer.py` est **production-ready** et bien designed (anti-leakage, anti-overfitting, audit-ready, reproducible).

🟡 Les autres modules ML existent mais n'ont pas été vérifiés ligne à ligne. Audit ciblé recommandé si l'un d'eux devient critique pour shadow.

**Le gap principal** n'est pas la qualité des modules ML, c'est leur **non-intégration au runtime predict** :
- Le trainer fait son travail (offline)
- Mais aucun runtime ex-ante (live ou backtest) ne charge l'artifact pour predict

→ **Sprint 1 priorité haute** : wirer `ml_artifact.predict()` dans `strategy_ladder_edge_model_provider` pour remplacer le forward-return median naïf.
