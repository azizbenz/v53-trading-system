
# V5.3 — MD1 — SPEC DÉTAILLÉE CODEX — ML ENABLER (Doctrine, Architecture, Données, Features V1)

## 0. Rôle

Tu agis comme **ingénieur Python senior systèmes critiques**, **quant senior**, **math PhD**, **trader systématique**, et **ingénieur logiciel orienté prod-safe**.

Tu n’écris pas un prototype.  
Tu dois implémenter une tranche **audit-ready**, **additive**, **bornée**, **surgicale**.

---

## 1. Objectif

Implémenter la **première couche ML prod-safe** de V5.3 :

> un **LightGBM tabulaire** entraîné en **Local IA Lab uniquement**, utilisé comme **ML confidence enabler** qui module le score de candidats déjà émis par les moteurs A/B/C/D, sans remplacer leur logique ni leur souveraineté.

Le modèle doit être :
- local-only pour l’entraînement,
- artifact-driven,
- hashable,
- versionné,
- testable,
- gouverné par promotion gate fail-closed,
- compatible avec le flux canonique `Local IA Lab -> artefact signé -> VPS`.

---

## 2. Doctrine non négociable

### 2.1 Invariants globaux

1. **Une seule solution complète**
2. **Aucun nouveau moteur** hors A/B/C/D
3. **Pas de nouveau profil**
4. **Pas de nouveau package top-level** de type `src/local_ai_lab/`
5. **VPS ne calibre rien**
6. **VPS n’entraîne jamais**
7. **Le modèle ne fixe jamais le side**
8. **Le modèle ne bypass jamais les moteurs**
9. **Le modèle ne remplace jamais la logique canonique A/B/C/D**
10. **Le ML reste un enabler additif borné**

### 2.2 Interdits absolus

- Interdit de modifier :
  - `src/calibration_methods/psr.py`
  - `src/calibration_methods/dsr.py`
  - `src/calibration_methods/pot_gpd.py`
  - `src/calibration_methods/energy_distance.py`
- Interdit d’ajouter :
  - torch
  - deep learning
  - RL
  - nouveau moteur ML
- Interdit d’introduire des features TA années 1990 comme pilier
- Interdit d’utiliser `ADX` comme feature structurante ; au mieux, éventuelle feature auxiliaire secondaire, mais **hors V1**
- Interdit d’implémenter une feature dont la formule n’est pas complètement définie dans ce MD
- Interdit de dépasser `alpha > 0.5` pour la fusion ML

---

## 3. Repo seams existants à réutiliser

**Ne pas réinventer ce qui existe déjà.**

### 3.1 Contrats / identité / forecast
- `src/interface_contracts/forecast_contracts.py`
- `src/interface_contracts/strategy_identity.py`

### 3.2 Scoring / coûts
- `src/scoring_backbone/break_even_filter.py`
- `src/scoring_backbone/forecast_normalizer.py`

### 3.3 Meta / drift
- `src/meta_minimal/cost_drift_monitor/`
- `src/meta_learning/model_risk_registry/`
- `src/meta_learning/strategy_drift_monitor/`

### 3.4 Microstructure calculators déjà présents
- `src/data_backbone/microstructure/order_flow_imbalance.py`
- `src/data_backbone/microstructure/vpin.py`
- `src/data_backbone/microstructure/queue_pressure.py`
- `src/data_backbone/microstructure/realized_kernel_vol.py`
- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/pin.py`
- `src/data_backbone/microstructure/hawkes_intensity.py`
- `src/data_backbone/microstructure/feature_registry.py`

### 3.5 Transport / artefacts
- `src/backtest_artifact_import/`

**Règle** : utiliser ces seams avant toute création nouvelle.

---

## 4. Fichiers à créer ou étendre

## 4.1 Runtime-facing enabler

Créer ou étendre :
- `src/complete_enablers/ml_confidence_enabler.py`

Responsabilité :
- charger un artefact ML validé
- produire `ml_confidence ∈ [0,1]`
- fournir une méthode de modulation du score
- dégrader proprement si artefact absent / invalide / périmé

### 4.2 Trainer LAB_ONLY

Créer :
- `src/calibration_methods/ml_trainer.py`

Responsabilité :
- entraîner un LightGBM local-only
- produire un `MlModelArtifact`
- rester déterministe

### 4.3 Dataset builder LAB_ONLY

Créer :
- `src/calibration_methods/ml_dataset_builder.py`

Responsabilité :
- construire le dataset tabulaire
- aligner features / label sans leakage
- sérialiser un snapshot d’apprentissage
- calculer un `feature_hash`

### 4.4 Artifact contract

Créer :
- `src/interface_contracts/ml_model_artifact.py`

### 4.5 Promotion gate

Créer :
- `src/complete_enablers/ml_model_promotion_gate.py`

### 4.6 Fusion helper

Créer :
- `src/complete_enablers/ml_fusion.py`

### 4.7 Model risk / drift (si pas déjà suffisants)

Étendre ou compléter :
- `src/meta_learning/model_risk_registry/`
- `src/meta_learning/strategy_drift_monitor/`

---

## 5. Nature exacte du modèle

## 5.1 Famille

Le seul modèle autorisé dans cette tranche est :

- **LightGBM classifier tabulaire**

Aucun autre modèle n’est autorisé dans cette slice.

## 5.2 Rôle exact

Le modèle ne prédit **pas** directement un trade à exécuter.  
Il prédit une **confiance additive** pour un candidat déjà construit par A/B/C/D.

Sortie principale :
- `ml_confidence: float ∈ [0, 1]`

Sortie de recherche optionnelle :
- `ml_direction_hint ∈ {"long", "short", "flat"}`

Mais :
- `ml_direction_hint` ne doit jamais devenir la source canonique du side
- le side reste celui du moteur

---

## 6. Définition du label

## 6.1 Principe

Le label doit refléter une **issue nette de coût** cohérente avec le rôle d’enabler.

Le modèle doit apprendre :

> “ce candidat de moteur, dans ce contexte de marché et avec ce coût attendu, a-t-il une probabilité suffisamment élevée d’aboutir à une issue nette positive sur l’horizon cible ?”

## 6.2 Définition mathématique

Pour un exemple au timestamp `t`, avec :
- `s_t ∈ {-1, +1}` = side du candidat (`+1` long, `-1` short)
- `P_t` = mid-price observable à `t`
- `P_{t+h}` = mid-price observable à horizon `h`
- `c_t` = coût attendu total relatif au trade (fees + slippage + uplift si disponible), exprimé en ratio
- `m_t` = marge de sécurité nette (`delta_safe` / floor net) exprimée en ratio

Définir le retour futur signé net :
```text
r_signed_net(t, h) = s_t * (P_{t+h} - P_t) / P_t - c_t
```

Label binaire :
```text
y_t = 1  si  r_signed_net(t, h) > m_t
y_t = 0  sinon
```

## 6.3 Horizon

Le modèle doit utiliser l’horizon du candidat :
- `SHORT` → horizon de 5 minutes
- `MEDIUM` → horizon de 30 minutes
- `LONG` → horizon de 4 heures

Pour cette première tranche, limiter l’implémentation à :
- `SHORT`
- `MEDIUM`

`LONG` peut rester défini mais non activé si le repo réel n’a pas encore le support propre.

## 6.4 Anti-leakage du label

Il est interdit d’utiliser pour `y_t` :
- le `high` ou `low` de la bougie `t`
- une information timestampée après `t` côté features
- une donnée de coût réalisée future

Le label utilise uniquement :
- les features observables à `≤ t`
- le prix futur `> t` pour la cible
- un coût **ex-ante** construit à `t`

---

## 7. Dataset builder — règles exactes

## 7.1 Ligne de dataset

Une ligne = un **candidat moteur déjà émis** ou un point d’évaluation lab-compatible sur lequel on peut reconstruire :
- features microstructure / contexte à `t`
- caractéristiques du candidat à `t`
- label net à horizon `h`

## 7.2 Colonnes interdites côté apprentissage

Le modèle ne doit jamais voir directement :
- `timestamp_ns`
- `price_raw`
- `high`
- `low`
- `volume_raw`
- tout identifiant brut non encodé
- tout champ dérivé de la cible future

## 7.3 Colonnes obligatoires de contexte candidat

Le modèle doit inclure, en plus des features marché, des colonnes de **contexte candidat** :

- `engine_id` (encodage catégoriel)
- `pair`
- `forecast_horizon_class`
- `bet_structure`
- `base_score`
- `forecast_strength`
- `expected_cost`
- `expected_break_even`
- `expected_ce`
- `expected_gain`
- `candidate_side`

Raison : le ML enabler évalue un **candidat moteur**, pas un état de marché abstrait.

---

## 8. Features V1 — exactes et autorisées

Les features V1 sont les seules autorisées pour la première implémentation.

Pour chacune :
- formule complète
- variables définies
- source
- fenêtre
- règle d’alignement
- statut = **IMPLEMENT_NOW**

---

## 8.1 `ofi_window_200`

### Définition
Order Flow Imbalance cumulé sur les 200 derniers événements L1/L2.

Soit `e_n` la contribution Cont-Kukanov-Stoikov :
```text
e_n =
    I{P_bid_n >= P_bid_n-1} * q_bid_n
  - I{P_bid_n <= P_bid_n-1} * q_bid_n-1
  - I{P_ask_n <= P_ask_n-1} * q_ask_n
  + I{P_ask_n >= P_ask_n-1} * q_ask_n-1
```

Feature :
```text
ofi_window_200_t = sum(e_n for n in last 200 valid book events up to t)
```

### Variables
- `P_bid_n`, `P_ask_n` = meilleur bid / ask
- `q_bid_n`, `q_ask_n` = tailles au meilleur bid / ask

### Source
- carnet d’ordres best bid/ask
- réutiliser le calculateur existant si disponible

### Alignement
- utiliser uniquement les événements `≤ t`

---

## 8.2 `vpin_50_bucket`

### Définition
VPIN sur 50 buckets de volume.

Pour bucket de volume `V` :
```text
V_buy_tau = V * Phi(delta_p_tau / sigma_delta_p)
V_sell_tau = V - V_buy_tau
VPIN_t = sum(|V_buy_tau - V_sell_tau| for tau in last 50 buckets) / (50 * V)
```

### Source
- flux trades agrégés ou trades classifiés aggressor
- ne pas utiliser une estimation future

### Alignement
- buckets clôturés à `≤ t`

---

## 8.3 `depth_imbalance_top5`

### Définition
```text
depth_imbalance_top5_t =
    (V_bid_top5_t - V_ask_top5_t)
    / (V_bid_top5_t + V_ask_top5_t + eps)
```

### Variables
- `V_bid_top5_t` = somme des quantités affichées sur les 5 meilleurs niveaux bid
- `V_ask_top5_t` = somme des quantités affichées sur les 5 meilleurs niveaux ask
- `eps = 1e-12`

### Source
- `depth20`

---

## 8.4 `spread_rel`

### Définition
```text
mid_t = (best_ask_t + best_bid_t) / 2
spread_rel_t = (best_ask_t - best_bid_t) / (mid_t + eps)
```

### Source
- best bid / ask à `t`

---

## 8.5 `mpd_divergence`

### Définition
Micro-price divergence :
```text
micro_price_t =
    (best_ask_t * q_bid_best_t + best_bid_t * q_ask_best_t)
    / (q_bid_best_t + q_ask_best_t + eps)

mpd_divergence_t = (micro_price_t - mid_t) / (mid_t + eps)
```

### Interprétation
- positive -> pression implicite haussière
- négative -> pression implicite baissière

---

## 8.6 `queue_pressure_best`

### Définition
Réutiliser le calculateur repo s’il existe ; sinon :
```text
queue_pressure_best_t =
    (q_bid_best_t - q_ask_best_t)
    / (q_bid_best_t + q_ask_best_t + eps)
```

### Note
Si le module canonique de queue pressure existe déjà avec une formule plus riche, il doit gagner sur cette approximation.

---

## 8.7 `realized_kernel_vol_5m`

### Définition
Utiliser le calculateur canonique de realized kernel du repo sur une fenêtre de 5 minutes de returns haute fréquence.

### Sortie
```text
realized_kernel_vol_5m_t = value returned by canonical realized kernel estimator at t
```

### Règle
Ne pas réimplémenter une formule concurrente si le repo a déjà le calculateur.

---

## 8.8 `kyle_lambda_1h`

### Définition
Utiliser le calculateur canonique repo de Kyle lambda sur une fenêtre de 1h.

### Sortie
```text
kyle_lambda_1h_t = canonical rolling-OLS Kyle lambda estimate at t
```

### Règle
Pas de nouvelle estimation divergente.

---

## 8.9 `log_return_1m`

### Définition
```text
log_return_1m_t = ln(mid_t / mid_t_minus_1m)
```

### Source
- série mid-price 1 minute alignée à `t`

---

## 8.10 `vol_ratio_20_100`

### Définition
```text
vol_ratio_20_100_t =
    std(log_return_1m over last 20 bars)
    / (std(log_return_1m over last 100 bars) + eps)
```

### Interprétation
- > 1 = régime court terme plus volatil que le fond 100 barres

---

## 8.11 `hurst_exp_100`

### Définition
Exposant de Hurst estimé sur les 100 dernières barres 1m.

### Règle
- utiliser un estimateur explicite et déterministe
- documenter la méthode choisie dans le module
- refuser silencieusement toute implémentation vague

### Sortie
```text
hurst_exp_100_t ∈ [0,1]
```

---

## 8.12 `funding_norm_168h`

### Définition
```text
funding_norm_168h_t =
    funding_t - mean(funding over last 168 hours up to t)
```

### Variables
- `funding_t` = dernier funding observé à ou avant `t` sur le perp associé
- si funding indisponible, feature manquante, jamais inférée par le futur

---

## 8.13 `delta_oi_1h`

### Définition
```text
delta_oi_1h_t =
    (open_interest_t - open_interest_t_minus_1h)
    / (open_interest_t_minus_1h + eps)
```

### Variables
- `open_interest_t` = dernier open interest observé à ou avant `t`
- `open_interest_t_minus_1h` = dernier open interest observé à ou avant `t - 1h`
- même venue, même instrument, même famille de contrat
- `eps = 1e-12`

### Règle d’alignement
- jamais de valeur observée après `t`
- si l’un des deux points est absent -> feature manquante

---

## 8.14 `btcd_delta_4h`

### Définition
```text
btcd_delta_4h_t =
    btc_dominance_t - btc_dominance_t_minus_4h
```

### Source
- série de dominance BTC alignée à `t`

---

## 8.15 `session_mult`

### Définition
Feature catégorielle ou scalaire décrivant la session horaire.

Version V1 autorisée :
- encoder en catégories :
  - `asia`
  - `europe`
  - `us`
  - `overlap`
  - `off_hours`

Alternative continue autorisée seulement si explicitement documentée et déterministe.

---

## 8.16 `engine_base_score`

### Définition
```text
engine_base_score_t = canonical candidate score emitted by engine A/B/C/D before ML fusion
```

### Règle
- ne pas recalculer
- consommer le score canonique existant

---

## 8.17 `candidate_expected_cost`

### Définition
```text
candidate_expected_cost_t = expected_cost from candidate at t
```

---

## 8.18 `candidate_expected_ce`

### Définition
```text
candidate_expected_ce_t = expected_ce from candidate at t
```

---

## 8.19 `candidate_forecast_strength`

### Définition
```text
candidate_forecast_strength_t = forecast_strength from candidate at t
```

### Règle
respecter les caps existants :
- A: [0,20]
- B: [0,15]
- C: [0,15]
- D: [0,10]

---

## 8.20 `candidate_side_sign`

### Définition
```text
candidate_side_sign_t = +1 if side == buy else -1
```

---

## 9. Features V1 — règles globales de calcul

### 9.1 Anti-leakage
Toute feature `X_t` utilise uniquement des données `≤ t`.

### 9.2 Gestion des trous
- si une source est absente -> feature manquante
- aucune imputation par valeur future
- forward-fill autorisé uniquement si explicitement borné et documenté par source, jamais implicite

### 9.3 Epsilon
Utiliser partout :
```text
eps = 1e-12
```
sauf si un module canonique du repo impose une autre convention.

### 9.4 Normalisation
Le trainer peut appliquer une normalisation locale, mais :
- le runtime doit consommer les transformations figées dans l’artefact
- aucune normalisation implicite non versionnée

---

## 10. Trainer — paramètres obligatoires

### 10.1 Paramètres
- modèle : LightGBM classifier
- train window : 180 jours
- validation / OOS window : 30 jours
- bagging : 5 folds
- Optuna : max 100 trials
- `early_stopping_rounds = 50`
- `max_depth = 6`
- seed fixe
- hash déterministe des features et de la config

### 10.2 Reproductibilité
À données, seed, features, et config identiques :
- hash modèle identique attendu
- artefact identique attendu ou suffisamment stable pour hash de contenu contrôlé

---

## 11. Artefact ML

Créer un contrat gelé avec au minimum :

- `schema_version`
- `model_family = "lightgbm"`
- `artifact_hash`
- `feature_hash`
- `training_seed`
- `pair_universe`
- `train_window_start`
- `train_window_end`
- `validation_window_start`
- `validation_window_end`
- `oos_sharpe`
- `backtest_sharpe`
- `promotion_state`
- `created_at_ns`
- `calibration_version`
- `model_blob_ref`
- `training_metrics`
- `shap_summary_ref` (optionnel)
- `drift_baseline` (optionnel)

---

## 12. Promotion gate — règles exactes

Le modèle est promotable seulement si toutes les conditions suivantes sont vraies :

```text
oos_sharpe >= 0.80 * backtest_sharpe
ks_test_features_pvalue > 0.05
shadow_diff_pct < 0.1%
artifact_hash valid
feature_hash present
required metrics present
```

### Politique
- **fail-closed**
- toute métrique absente = rejet
- aucun override opérateur silencieux

---

## 13. Fusion score — formule exacte

Implémenter exactement :

```text
fused_score = base_score * (1 + alpha * (ml_confidence - 0.5))
```

### Contraintes
- `alpha` configurable
- `alpha <= 0.5` hard cap absolu
- plage de défaut conseillée : `[0.0, 0.3]`
- si `ml_confidence = 0.5` -> neutralité
- si artefact absent / invalide / stale -> `fused_score = base_score`
- le side reste inchangé
- aucun trade artificiel ne doit être créé

---

## 14. Model risk / drift minimum

Le slice doit stocker ou exposer au minimum :
- `feature_hash`
- `train_window`
- `oos_sharpe`
- `shadow/live drift metrics`
- `promotion_state`
- un flag de blocage/pause si drift sévère

---

## 15. Ce que Codex doit explicitement vérifier après génération

1. Le ML est additif uniquement
2. A/B/C/D restent souverains
3. VPS-side ne fait aucun entraînement
4. Le trainer est déterministe
5. La formule de fusion est exacte
6. `alpha > 0.5` est impossible
7. Le promotion gate est fail-closed
8. Les fichiers quant gelés n’ont pas été modifiés
9. DAG vert
10. `engineering_guardrails new_violations=0`
11. Tous les nouveaux tests V1 passent

Fin de MD1.
