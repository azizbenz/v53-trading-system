# V5.3 — MD détaillé pour Codex
## Slice ML prod-safe — LightGBM tabulaire local-only comme `ml_confidence_enabler`

**Date** : 2026-04-22  
**Auteur** : ChatGPT — cadrage quant / math / trading / software engineering  
**Statut** : SPEC D'IMPLEMENTATION POUR CODEX  
**Portée** : ajouter une couche ML utile, bornée, auditable, compatible V5.3, sans casser le canon A/B/C/D ni le rail gouverné Local IA Lab → artefact → VPS.

---

## 0. Résumé exécutable

Ce slice n'ajoute **pas** un nouveau moteur.
Il ajoute :

1. un **LightGBM tabulaire** entraîné **uniquement dans le Local IA Lab** ;
2. une sortie bornée `ml_confidence ∈ [0,1]` ;
3. une **fusion additive bornée** avec le score existant des moteurs A/B/C/D ;
4. un **artefact de modèle** versionné et transportable ;
5. un **promotion gate** fail-closed ;
6. un minimum de **model risk / drift tracking** ;
7. un jeu de **features microstructure + contexte** engineering-ready.

Ce slice **n'autorise jamais** :
- que le ML décide seul du `side` ;
- que le ML remplace les moteurs A/B/C/D ;
- que le VPS entraîne un modèle ;
- qu'un artefact opaque devienne la logique souveraine du runtime.

---

## 1. Doctrine non négociable

### 1.1 Identité du rail

Le IA Lab V5.3 est d'abord un **laboratoire local gouverné** de replay, review, calibration, packaging, promotion-readiness et preuve.

Le ML est **une sous-couche locale bornée**, pas le cœur souverain du système.

### 1.2 Répartition Local / VPS

- **Local Lab PC** : calibration, ML training, walk-forward, backtests, SHAP, drift registries, recherche microstructure.
- **VPS** : exécution, monitoring runtime, ordre, kill switch, observabilité.
- **Transport** : Local -> VPS via artefacts seulement.

### 1.3 Règles dures

Codex ne doit jamais :

1. créer un 5e moteur ;
2. laisser le ML fixer le `side` ;
3. laisser le ML bypasser A/B/C/D ;
4. entraîner sur VPS ;
5. modifier les ancres quant gelées :
   - `src/calibration_methods/psr.py`
   - `src/calibration_methods/dsr.py`
   - `src/calibration_methods/pot_gpd.py`
   - `src/calibration_methods/energy_distance.py`
6. introduire torch / deep learning / RL / policy model / LLM dans la boucle critique ;
7. transformer la couche ML en “second canon” ;
8. injecter du code opaque exécutable depuis l'artefact ;
9. dépasser `alpha > 0.5` dans la fusion ML ;
10. écrire un fichier `src/` > 700 lignes.

---

## 2. Objectif exact du slice

Ajouter une couche ML **utile mais modeste** qui améliore la hiérarchisation des signaux existants, sans changer la structure de décision de V5.3.

### 2.1 Ce que la couche ML doit faire

- apprendre, en local, à estimer une **confiance** sur les opportunités détectées par le système ;
- produire `ml_confidence` ;
- moduler le score existant via une formule simple, bornée, auditée ;
- rester compatible avec replay, shadow, micro-live, live.

### 2.2 Ce qu'elle ne doit pas faire

- créer un trade alors que le moteur a refusé ;
- forcer un buy/sell ;
- changer `bet_structure` ;
- changer `forecast_horizon_class` ;
- casser les caps `forecast_strength` par moteur ;
- devenir un moteur autonome.

---

## 3. Choix ML figé

### 3.1 Modèle retenu

**Un seul modèle ML maintenant** :

- `LightGBM` tabulaire
- entraîné **offline**
- utilisé comme **`ml_confidence_enabler`**

### 3.2 Pourquoi ce choix

- adapté au tabulaire microstructure ;
- cohérent avec machine locale sobre ;
- explicable via SHAP ;
- facile à versionner et à auditer ;
- compatible avec un runtime VPS léger ;
- conforme à la doctrine : enabler, pas moteur.

### 3.3 Modèles explicitement exclus

Pour ce slice, interdits :

- deep learning séquentiel lourd ;
- torch comme dépendance principale ;
- RL / policy gradient / agent autonome ;
- ensembles complexes multi-modèles ;
- XGBoost/CatBoost/RandomForest en parallèle du LightGBM ;
- tout modèle qui décide seul d'entrer/sortir.

---

## 4. Formulation du rôle mathématique du ML

### 4.1 Sortie du modèle

Le modèle produit au minimum :

- `ml_confidence ∈ [0, 1]`

Optionnellement pour la recherche/debug uniquement :

- `ml_direction ∈ {long, short, flat}`

**Interdiction** : `ml_direction` ne doit jamais devenir le `side` canonique d'exécution.

### 4.2 Fusion avec le score moteur

La formule imposée est :

```text
fused_score = base_score × (1 + alpha × (ml_confidence - 0.5))
```

### 4.3 Propriétés obligatoires

- si `ml_confidence = 0.5`, alors `fused_score = base_score`
- si `ml_confidence > 0.5`, le score augmente
- si `ml_confidence < 0.5`, le score diminue
- si `alpha = 0`, aucune influence ML
- `alpha` doit être configurable
- **hard cap absolu** : `alpha <= 0.5`
- **zone recommandée** : `alpha ∈ [0.0, 0.3]`
- le `side` ne change jamais
- aucun trade ne doit être fabriqué si le moteur a refusé

### 4.4 Conséquence d'architecture

Le ML agit comme :

- `SCORING_SOFT_PENALTY_LAYER`
- ou `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`

mais jamais comme :

- `ENGINE_*_PRIMARY_DECIDER`
- `EXECUTION_SIDE_DECIDER`

---

## 5. Cible d'entraînement

### 5.1 Nature de la target

Le modèle doit apprendre une cible **future**, strictement postérieure à `t`.

Exemples autorisés :

- `target_direction_t+5m`
- `target_hit_break_even_before_invalidation`
- `target_positive_ce_over_horizon`
- `target_net_positive_after_cost`

### 5.2 Règle anti-leakage absolue

Pour toute ligne du dataset à l'instant `t` :

- toutes les features utilisent uniquement des données `<= t`
- toute target utilise uniquement des données `> t`
- il est interdit d'utiliser `high_t`, `low_t`, `close_future`, ou tout proxy de futur dans les features
- les splits doivent respecter purge + embargo si le plan de walk-forward l'exige

### 5.3 Target recommandée pour V1

Commencer simple et utile :

```text
Target_V1 = 1 si la trajectoire future sur horizon H produit un résultat net positif après coût,
            0 sinon
```

Version plus stricte optionnelle :

```text
Target_V1_strict = 1 si gain net > 0 ET break-even dépassé avant invalidation,
                   0 sinon
```

---

## 6. Features — découpage en 3 classes

La liste collée par l'utilisateur contient de bonnes idées, mais toutes ne sont pas encore suffisamment définies pour être codées sans hallucination.

On impose donc 3 classes :

### 6.1 Core features V1 — à implémenter maintenant

Ces features sont suffisamment cohérentes avec la doctrine et peuvent former une V1 robuste.

#### Groupe flux / microstructure

1. `ofi_ratio`
2. `vpin_score`
3. `cvd_divergence`
4. `depth_imbalance`
5. `kyle_lambda`
6. `adr_ratio`

#### Groupe prix / régime

7. `log_return`
8. `vol_ratio`
9. `hurst_exp`
10. `vsd_deviation`

#### Groupe carnet / coût

11. `spread_rel`
12. `mpd_divergence`

#### Groupe contexte dérivés / cross-asset

13. `funding_norm`
14. `delta_oi`
15. `session_mult`
16. `btcd_delta`

**Total V1 recommandé** : 16 features.

### 6.2 Secondary features V2 — à ajouter seulement après V1

17. `hhi_trades`
18. `aci_score`
19. `ppe_score`
20. `dei_entropy`
21. `obs_skew`
22. `mem_state`
23. `ltr_ratio`
24. `vsd_deviation` variantes multi-horizon
25. `residualized_cross_pair_momentum_feature`

### 6.3 Features research-only / bloquées tant que formule non figée

26. `adx_trend` → seulement comme feature contextuelle secondaire ; ne doit pas devenir pilier du modèle
27. toutes les features dont la formule est tronquée ou ambiguë dans le texte source
28. toute feature dont la définition dépend d'une convention non encore figée dans le repo

---

## 7. Feature registry engineering-ready

Avant tout entraînement, Codex doit créer un **registry de features**.

### 7.1 Fichier à créer

- `src/complete_enablers/ml_feature_registry.py`

### 7.2 Structure imposée par feature

Pour chaque feature :

- `feature_id`
- `feature_name`
- `group`
- `status` = `core_v1` / `secondary_v2` / `research_only`
- `input_sources`
- `window_definition`
- `formula_markdown`
- `epsilon_policy`
- `nan_policy`
- `dtype`
- `normalization_policy`
- `anti_leakage_max_timestamp = t`
- `tests_required`

### 7.3 Interdiction

Aucune feature ne doit être codée “à la volée” sans fiche de registry.

---

## 8. Formules V1 à figer

Les formules ci-dessous doivent être utilisées textuellement dans la spec et dans les tests.

### 8.1 `ofi_ratio`

```text
ofi_ratio = (ΔV_bid - ΔV_ask) / (ΔV_bid + ΔV_ask + eps)
```

### 8.2 `depth_imbalance`

```text
depth_imbalance = (V_bid_top5 - V_ask_top5) / (V_bid_top5 + V_ask_top5 + eps)
```

### 8.3 `spread_rel`

```text
spread_rel = (ask_best - bid_best) / mid_price
mid_price = (ask_best + bid_best) / 2
```

### 8.4 `log_return`

```text
log_return = ln(price_t / price_t-1)
```

### 8.5 `vol_ratio`

```text
vol_ratio = std(log_return, 20) / (std(log_return, 100) + eps)
```

### 8.6 `funding_norm`

```text
funding_norm = funding_t - mean(funding, 168h)
```

### 8.7 `delta_oi`

```text
delta_oi = (oi_t - oi_t-1h) / (oi_t-1h + eps)
```

### 8.8 `mpd_divergence`

```text
micro_price = (ask_price * bid_size + bid_price * ask_size) / (bid_size + ask_size + eps)
mpd_divergence = (micro_price - mid_price) / (mid_price + eps)
```

### 8.9 `adr_ratio`

```text
adr_ratio = trade_size / (best_level_depth + eps)
```

### 8.10 `vsd_deviation`

```text
vsd_deviation = sigma_current / (sigma_hour_of_week_baseline + eps)
```

### 8.11 `hurst_exp`

Utiliser l'implémentation rolling déjà canonique si elle existe ; sinon créer une implémentation bornée, documentée et testée, sans sur-optimisation.

### 8.12 `kyle_lambda`

Si un module canonique existe déjà dans `src/data_backbone/microstructure/`, réutiliser son output.
Ne pas réinventer une nouvelle définition concurrente.

---

## 9. Fichiers à créer ou étendre

### 9.1 Enabler runtime

Créer ou étendre :

- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/ml_fusion.py`
- `src/complete_enablers/ml_feature_registry.py`

### 9.2 Entraînement local

Créer ou étendre :

- `src/calibration_methods/ml_trainer.py`

### 9.3 Contrat d'artefact

Créer :

- `src/interface_contracts/ml_model_artifact.py`

### 9.4 Promotion gate

Créer :

- `src/complete_enablers/ml_model_promotion_gate.py`

### 9.5 Drift / model risk

Créer ou étendre :

- `src/meta_learning/model_risk_registry/`
- `src/meta_learning/strategy_drift_monitor/`

### 9.6 Intégration runtime bornée

Si nécessaire seulement, étendre de façon additive les seams existants :

- hook scoring soft penalty
- portfolio relative rank adjustment

**Interdiction** : toucher la logique souveraine des moteurs.

---

## 10. Hyperparamètres d'entraînement imposés pour V1

### 10.1 Entraînement

- modèle : `LightGBM`
- split principal : `180d train / 30d test`
- bagging : `5 folds`
- Optuna : `<= 100 trials`
- `early_stopping = 50`
- `max_depth = 6`
- seed déterministe obligatoire

### 10.2 Reproductibilité obligatoire

L'entraînement doit être stable par :

- `training_seed`
- `dataset_hash`
- `feature_hash`
- `model_family`
- `pair_universe`
- `train_window`

---

## 11. Contrat d'artefact ML

### 11.1 Fichier

- `src/interface_contracts/ml_model_artifact.py`

### 11.2 Champs obligatoires

- `schema_version`
- `artifact_id`
- `artifact_version`
- `model_family = "lightgbm"`
- `feature_hash`
- `pair_universe`
- `train_window`
- `validation_window`
- `training_seed`
- `backtest_sharpe`
- `oos_sharpe`
- `promotion_state`
- `artifact_hash`
- `created_at`
- `calibration_version`
- `training_metrics`
- `shap_summary_ref | shap_summary_digest`

### 11.3 Règle d'interprétation

Le runtime ne doit **jamais** exécuter un modèle brut opaque comme souverain.
Le runtime ne lit que :

- des sorties bornées
- des métadonnées de contrôle
- un modèle sérialisé compatible avec le runtime choisi

Si le format de sérialisation introduit une opacité excessive, préférer une lecture bornée via loader contrôlé et promotion signée.

---

## 12. Promotion gate ML

### 12.1 Fichier

- `src/complete_enablers/ml_model_promotion_gate.py`

### 12.2 Règles obligatoires

Le modèle n'est promotable que si :

```text
oos_sharpe >= 0.80 * backtest_sharpe
ks_test_features_pvalue > 0.05
shadow_diff_pct < 0.1%
```

### 12.3 Règles supplémentaires fail-closed

Refuser si :

- métriques absentes
- hash invalide
- feature_hash manquant
- pair_universe incohérent
- artifact incomplet
- métriques NaN / inf
- score drifté au-delà des bornes admises

---

## 13. Model risk / drift

### 13.1 `model_risk_registry`

Le registre doit stocker au minimum :

- `train_window`
- `feature_hash`
- `oos_sharpe`
- `promotion_state`
- `shadow_live_parity_metrics`
- `replay_shadow_live_drift`
- `artifact_version`

### 13.2 `strategy_drift_monitor`

Doit signaler au minimum :

- dérive de distribution forecast
- dérive de win rate
- dérive de CE
- dérive coût ex-ante vs coût réalisé
- pause recommandée ou promotion block

### 13.3 Règle de philosophie

La surveillance drift sert à :
- bloquer ou dégrader
- jamais “auto-réentraîner et pousser live”

---

## 14. Tests obligatoires

### 14.1 Tests `ml_feature_registry`

- every core feature has full metadata
- no duplicate `feature_id`
- research-only features cannot be used in V1 training config

### 14.2 Tests `ml_trainer`

- same seed + same data => same artifact hash
- invalid data => explicit error
- walk-forward respected
- Optuna cap respected

### 14.3 Tests `ml_model_artifact`

- frozen contract
- missing mandatory field rejected
- invalid hash rejected
- serialization round-trip stable

### 14.4 Tests `ml_confidence_enabler`

- `ml_confidence` clipped to `[0,1]`
- missing artifact => graceful degradation
- stale artifact => neutral path or promotion block
- `ml_direction` never overrides engine side

### 14.5 Tests `ml_fusion`

- `alpha = 0` => no change
- `ml_confidence = 0.5` => no change
- `ml_confidence > 0.5` => uplift
- `ml_confidence < 0.5` => penalty
- `alpha > 0.5` rejected
- side unchanged

### 14.6 Tests `ml_model_promotion_gate`

- green path
- fail on missing metrics
- fail on `oos_sharpe < 0.80 * backtest_sharpe`
- fail on `ks_test_features_pvalue <= 0.05`
- fail on `shadow_diff_pct >= 0.1%`

### 14.7 Tests drift / model risk

- synthetic drift => promotion block
- stable path => no overfire
- missing data => insufficient_data / fail-closed state

### 14.8 Tests anti-leakage

Créer des tests explicites qui prouvent que :

- chaque feature V1 utilise uniquement `<= t`
- la target utilise uniquement `> t`
- aucune feature ne lit `high_t` / `low_t` si la target est horizon future

---

## 15. Critères d'acceptation du slice

Le slice est **COMPLETE** seulement si :

1. LightGBM local-only opérationnel
2. artefact ML versionné créé
3. fusion bornée implémentée
4. `alpha <= 0.5` garanti
5. aucun override du side
6. promotion gate fail-closed vert
7. tests ML ciblés verts
8. DAG vert
9. `new_violations=0`
10. aucun fichier quant gelé modifié
11. audit pack créé

Le slice est **PARTIAL** si :

- le trainer existe mais pas la promotion gate
- ou la fusion existe mais pas le drift monitor
- ou les features V1 ne sont pas toutes engineering-ready

Le slice est **BLOCKED** si :

- Codex tente de transformer le ML en moteur
- ou tente de toucher les ancres quant gelées
- ou introduit torch / RL / modèle opaque central

---

## 16. Ce que Codex doit écrire dans le pack d'audit

Sous :

`docs/production_deployment_plan/update_audit/YYYY-MM-DD_ml_enabler_lightgbm_v1.md`

Minimum requis :

1. `Objective`
2. `Docs Governants`
3. `Current Code Seam`
4. `Placement`
5. `Files Changed`
6. `Claims Implemented`
7. `Tests and Proof`
8. `Deferred / Not Done`
9. `Risks / Open Questions`
10. `Completion Status`
11. `Next Safe Step`

---

## 17. Brief d'ouverture exact à coller dans Codex

```text
You are working on the V5.3 ML enabler slice only.

Global invariants:
- One shared V5.3 core only.
- No new engine outside A/B/C/D.
- ML is additive score modulation only.
- VPS never trains and never runs LightGBM fit or Optuna.
- Do not edit:
  - src/calibration_methods/psr.py
  - src/calibration_methods/dsr.py
  - src/calibration_methods/pot_gpd.py
  - src/calibration_methods/energy_distance.py
- Preserve engine sovereignty on side.
- Preserve additive migration discipline.

Modules that must connect to this slice:
- src/complete_enablers/
- src/calibration_methods/
- src/interface_contracts/
- src/meta_learning/
- src/meta_minimal/
- existing scoring hook seams only

Forbidden defaults:
- no torch
- no RL
- no deep learning
- no second canon
- no alpha > 0.5
- no VPS training
- no quant-anchor edits
- no file > 700 lines

Objective:
Implement a LightGBM local-only ml_confidence enabler with:
- feature registry
- trainer
- artifact contract
- promotion gate
- bounded fusion
- model risk / drift tracking
- tests

After generation verify explicitly:
1. ML does not override side.
2. VPS does not train.
3. alpha <= 0.5.
4. anti-leakage tests exist.
5. new ML tests are green.
6. DAG is green.
7. new_violations=0.
8. quant-anchor files unchanged.
```

---

## 18. Verdict de cadrage

Ce slice est **autorisé** et **souhaitable**.

Mais il doit rester :

- petit,
- borné,
- tabulaire,
- offline,
- explicable,
- artifact-driven,
- subordonné à A/B/C/D.

Si Codex dérive vers une architecture ML-first, le slice doit être considéré comme **non conforme**.

