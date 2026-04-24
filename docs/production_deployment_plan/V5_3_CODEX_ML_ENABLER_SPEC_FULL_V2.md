# V5.3 — Spécification complète Codex — ML Enabler tabulaire gouverné (version détaillée)

## Statut
Spécification d’engineering détaillée pour Codex.

## But
Ajouter la première couche ML réellement compatible avec V5.3 :
- entraînement **local uniquement**,
- modèle **LightGBM tabulaire**,
- usage comme **enabler de confiance borné**,
- **aucun** nouveau moteur,
- **aucun** override de A/B/C/D,
- **aucune** dépendance live du VPS vers le training.

Ce document sert de cahier d’implémentation complet : doctrine, périmètre, architecture, features, formule de fusion, labels, fichiers, tests, garde-fous, et checklist d’audit.

---

## 1. Doctrine non négociable

### 1.1 Identité du composant
Ce slice n’implémente **pas** un "ML trading engine".
Il implémente un **ML confidence enabler** local, consommé ensuite comme modulation bornée du score des moteurs A/B/C/D.

### 1.2 Règles dures
1. Le ML ne remplace jamais A/B/C/D.
2. Le ML ne décide jamais seul du `side`.
3. Le ML n’émet jamais de `SignalCandidate` canonique à lui seul.
4. Le VPS n’entraîne jamais, ne fait jamais de fit LightGBM, ne lance jamais Optuna.
5. Les modèles sont entraînés localement, versionnés, hashés, promus, puis consommés via artefact.
6. Les ancres quant suivantes restent **hors modification** dans ce slice :
   - `src/calibration_methods/psr.py`
   - `src/calibration_methods/dsr.py`
   - `src/calibration_methods/pot_gpd.py`
   - `src/calibration_methods/energy_distance.py`
7. La fusion ML reste bornée par `alpha <= 0.5`.
8. Le ML ne doit jamais contourner les hard blocks, le refusal journal, les gates de promotion, ni le quadruple filter.
9. Les ranges de `forecast_strength` existants restent souverains :
   - Engine A : [0, 20]
   - Engine B : [0, 15]
   - Engine C : [0, 15]
   - Engine D : [0, 10]
10. Aucun nouveau package `src/local_ai_lab/`.
11. Aucun profil nouveau.
12. Aucune réécriture large de la doctrine.

### 1.3 Ce que ce slice doit produire
1. Un builder de dataset local.
2. Un entraîneur LightGBM local.
3. Un artefact modèle gelé et hashé.
4. Un gate de promotion ML fail-closed.
5. Une fusion bornée `base_score -> fused_score`.
6. Une consommation runtime additive via `ml_confidence_enabler`.
7. Un minimum de model-risk / drift tracking.

---

## 2. Périmètre exact

### Inclus
- LightGBM tabulaire.
- Features microstructure + contexte + prix.
- Builder de dataset local.
- Walk-forward local.
- SHAP local.
- Artefact modèle.
- Promotion gate.
- Fusion ML bornée.
- Drift/model risk minimal.

### Exclus
- Deep learning.
- RL.
- Policy network.
- Nouveau moteur autonome.
- Training sur VPS.
- Refonte des moteurs A/B/C/D.
- Modification des formules PSR/DSR/POT-GPD/Energy.
- Hyper-optimisation pair-par-pair agressive.

---

## 3. Architecture cible

### 3.1 Flux autorisé
`Données historiques locales -> feature matrix locale -> training LightGBM local -> artefact modèle hashé -> validation/promotion -> import vers VPS -> runtime consomme artefact`

### 3.2 Flux interdit
`VPS live -> entraîneur -> fit -> nouveau modèle -> activation immédiate`

### 3.3 Principe d’intégration
Le ML est un **soft layer** qui transforme un `base_score` existant en `fused_score`.
Le `side`, le `bet_structure`, les `hard blocks`, le `forecast_target_class`, et la logique moteur restent gouvernés par les moteurs canoniques.

---

## 4. Définition du problème ML

### 4.1 Type de modèle
- Modèle : **LightGBM classifier**.
- Sortie principale : `ml_confidence` dans [0, 1].
- Sortie secondaire facultative : `ml_direction` dans {`long`, `short`, `flat`} pour debug / analyse uniquement.

### 4.2 Ce que prédit le modèle
Le modèle ne doit pas prédire une vérité absolue de marché.
Il doit prédire une **probabilité de follow-through favorable** conditionnée par un contexte de marché et par un candidat moteur.

### 4.3 Définition du label recommandée
Pour chaque échantillon à l’instant `t`, construit à partir d’un candidat moteur historique ou replay :

- `side_sign = +1` si le candidat est `buy`, `-1` si `sell`
- `mid_t = (best_bid_t + best_ask_t) / 2`
- `mid_t_plus_H = mid-price observé à horizon H strictement après t`
- `signed_return_H = side_sign * ((mid_t_plus_H / mid_t) - 1)`
- `cost_buffer_H = estimated_expected_cost_t + delta_safe_t`

Label binaire principal :

`y_favorable_followthrough = 1 si signed_return_H > cost_buffer_H, sinon 0`

### 4.4 Horizon recommandé
- Engine A : horizon `MEDIUM` aligné avec son horizon runtime.
- Engine B : horizon `SHORT`.
- Engine C : horizon `MEDIUM`.
- Engine D : horizon `SHORT`.

Le builder doit permettre un horizon par engine, mais commencer par une première implémentation stable, simple et audit-safe.

---

## 5. Contrat temporel et anti-leakage

### 5.1 Règle absolue
Pour toute ligne de dataset au timestamp `t` :
- les features utilisent uniquement des données observées à des timestamps `<= t`
- le label utilise uniquement des données observées à des timestamps `> t`

### 5.2 Interdits
- Interdit d’utiliser `High_t` ou `Low_t` pour construire la target au temps `t`.
- Interdit d’utiliser une valeur publiée après `t` pour une feature au temps `t`.
- Interdit de forward-fill une donnée au-delà de sa disponibilité réelle.
- Interdit d’utiliser des splits random standards sans purge / embargo.

### 5.3 Alignement temporel
Pour chaque source :
- prendre la **dernière valeur disponible à ou avant `t`**
- si aucune valeur n’existe, la feature est `missing`
- ne jamais interpoler avec une observation future

### 5.4 Split recommandé
Utiliser le plan canonique déjà présent de type purged walk-forward :
- 180 jours train
- 30 jours validation / test
- 5 folds
- purge / embargo respectés

---

## 6. Feature registry complet — 29 features

### 6.0 Convention générale
Pour chaque feature :
- `eps = 1e-12` sauf indication contraire
- si dénominateur quasi nul -> feature = missing ou clip selon règle explicitée
- toute feature doit être calculée dans `float64`
- les versions canoniques déjà existantes dans `src/data_backbone/microstructure/` doivent être **réutilisées**, pas réinventées à la main

### 6.1 Priorités d’implémentation
- **V1 Core** : 16 features à implémenter dans ce slice
- **V2 Secondary** : 8 features si V1 est verte
- **V3 Research/Deferred** : 5 features seulement si la formule est fermée et le temps restant le permet

---

## 7. V1 Core Features (à implémenter obligatoirement)

### F1 — `ofi_ratio`
**Nom long** : order_flow_imbalance_ratio

**Formule**
`ofi_ratio_t = ofi_sum_t / (abs_bid_flow_t + abs_ask_flow_t + eps)`

avec :
- `ofi_sum_t = sum(delta_bid_size_k - delta_ask_size_k)` sur la fenêtre des N derniers événements de book `<= t`
- `abs_bid_flow_t = sum(abs(delta_bid_size_k))`
- `abs_ask_flow_t = sum(abs(delta_ask_size_k))`

**Source**
- `depth20`

**Fenêtre recommandée**
- 200 mises à jour carnet ou 60 secondes, selon ce qui est déjà cohérent avec le repo

**Règle d’implémentation**
- si un calcul OFI canonique existe déjà dans `src/data_backbone/microstructure/order_flow_imbalance.py`, l’utiliser
- ne pas recoder une variante ad hoc si le calculateur canonique existe

**Sortie**
- float dans [-1, 1] approximativement

---

### F2 — `vpin_score`
**Nom long** : volume_synchronized_probability_of_informed_trading

**Formule**
Utiliser le calculateur canonique existant si présent.
Sinon :
`vpin_t = (1 / (n_buckets * bucket_volume)) * sum_tau(abs(v_buy_tau - v_sell_tau))`

**Source**
- `aggTrades`

**Fenêtre recommandée**
- 50 buckets de volume

**Règle d’implémentation**
- priorité absolue à la réutilisation de `src/data_backbone/microstructure/vpin.py`

**Sortie**
- float dans [0, 1]

---

### F3 — `spread_rel`
**Nom long** : relative_spread

**Formule**
`spread_rel_t = (best_ask_t - best_bid_t) / (mid_t + eps)`

avec :
- `mid_t = (best_bid_t + best_ask_t) / 2`

**Source**
- `depth20`

**Sortie**
- float >= 0

---

### F4 — `funding_norm`
**Nom long** : normalized_funding_rate

**Formule**
`funding_norm_t = funding_t - mean(funding_{t-168h ... t})`

**Source**
- funding rate venue derivatives feed

**Alignement**
- utiliser la dernière observation funding disponible à ou avant `t`

**Sortie**
- float centré

---

### F5 — `delta_oi`
**Nom long** : open_interest_delta_1h_ratio

**Formule**
`delta_oi_t = (open_interest_t - open_interest_t_minus_1h) / (open_interest_t_minus_1h + eps)`

avec :
- `open_interest_t = dernière valeur d’open interest disponible à ou avant t`
- `open_interest_t_minus_1h = dernière valeur d’open interest disponible à ou avant t-1h`

**Source**
- open interest derivatives feed

**Règle**
- si `open_interest_t` ou `open_interest_t_minus_1h` manque : feature = missing

**Sortie**
- float

---

### F6 — `queue_pressure`
**Nom long** : weighted_top5_queue_pressure

**Formule**
`queue_pressure_t = (sum_i(w_i * bid_size_i) - sum_i(w_i * ask_size_i)) / (sum_i(w_i * (bid_size_i + ask_size_i)) + eps)`

avec :
- `i in {1,2,3,4,5}` niveaux du carnet
- `w_i = 1 / i`

**Source**
- `depth20`

**Sortie**
- float dans [-1, 1]

---

### F7 — `realized_kernel_vol`
**Nom long** : realized_kernel_volatility

**Formule**
Réutiliser le calculateur canonique existant.
Ne pas recoder une pseudo-volatilité simplifiée si `src/data_backbone/microstructure/realized_kernel_vol.py` existe.

**Source**
- trades / prix haute fréquence agrégés

**Sortie**
- float >= 0

---

### F8 — `log_return`
**Nom long** : one_bar_log_return

**Formule**
`log_return_t = ln(close_t / close_t_minus_1)`

**Source**
- OHLCV 1min ou granularité canonique retenue

**Sortie**
- float

---

### F9 — `vol_ratio`
**Nom long** : short_to_long_volatility_ratio

**Formule**
`vol_ratio_t = std(log_return_{t-20 ... t}) / (std(log_return_{t-100 ... t}) + eps)`

**Source**
- OHLCV

**Sortie**
- float >= 0

---

### F10 — `btcd_delta`
**Nom long** : btc_dominance_delta_4h

**Formule**
`btcd_delta_t = dominance_btc_t - dominance_btc_t_minus_4h`

**Source**
- dominance BTC feed / market context dataset

**Règle**
- alignement last-known-at-or-before t

---

### F11 — `cvd_divergence`
**Nom long** : cumulative_volume_delta_price_divergence

**Étapes**
1. `trade_sign_k = +1` si trade agressif buy, `-1` si sell
2. `delta_volume_k = trade_sign_k * trade_size_k`
3. `cvd_t = sum(delta_volume_k)` sur la fenêtre glissante canonique
4. construire `corr_t = corr(cvd_series, price_series)` sur 20 barres

**Forme finale recommandée**
`cvd_divergence_t = -corr_t`

Interprétation :
- `corr_t` élevé -> flux et prix convergent
- `cvd_divergence_t` élevé -> divergence

**Source**
- `aggTrades` + prix

---

### F12 — `depth_imbalance`
**Nom long** : top5_depth_imbalance

**Formule**
`depth_imbalance_t = (bid_depth_top5_t - ask_depth_top5_t) / (bid_depth_top5_t + ask_depth_top5_t + eps)`

avec :
- `bid_depth_top5_t = sum_{i=1..5}(bid_size_i)`
- `ask_depth_top5_t = sum_{i=1..5}(ask_size_i)`

**Source**
- `depth20`

---

### F13 — `session_mult`
**Nom long** : session_multiplier_context

**Définition**
Feature de contexte de session.
Deux options autorisées :
1. `one-hot` des buckets de session
2. variable continue bornée, déterministe, basée sur l’heure UTC

**Première implémentation recommandée**
- one-hot ou ordinal simple
- ne pas sur-ingénieriser

**Source**
- timestamp UTC

---

### F14 — `adx_trend_ctx`
**Nom long** : adx_context_only

**Statut**
Feature **secondaire de contexte**, non pilier.

**Formule**
Utiliser la définition ADX standard si déjà disponible dans le repo.
Sinon, ne pas l’implémenter dans V1 si cela crée une dépendance TA lourde.

**Règle doctrinale**
- ADX ne doit pas devenir une colonne structurante du modèle
- surveiller SHAP : si ADX domine, le feature set doit être revu

---

### F15 — `roll_spread`
**Nom long** : roll_effective_spread_estimate

**Formule**
Réutiliser le calculateur canonique `roll_spread.py` si présent.

**Source**
- prix de transaction

**Sortie**
- float >= 0

---

### F16 — `mem_state`
**Nom long** : microstructure_memory_state

**Formule V1 fermée**
`mem_state_t = sum_{j=0..2}(ofi_ratio_{t-j}) / (abs(norm_price_move_t) + eps)`

avec :
- `norm_price_move_t = (mid_t - mid_t_minus_3bars) / (realized_kernel_vol_t + eps)`

**Source**
- `depth20` + prix + RK vol

**Sortie**
- float

---

### F17 — `amihud_illiquidity`
**Nom long** : amihud_illiquidity_proxy

**Formule**
Réutiliser le calculateur canonique existant si présent.
Sinon :
`amihud_t = mean(|return_k| / (dollar_volume_k + eps))` sur la fenêtre

**Source**
- OHLCV / trades

---

### F18 — `ltr_ratio`
**Nom long** : local_turnover_ratio

**Formule V1 fermée**
`ltr_ratio_t = executed_volume_window_t / (depth_change_abs_window_t + eps)`

avec :
- `executed_volume_window_t = somme des tailles de trades exécutés sur la fenêtre`
- `depth_change_abs_window_t = somme des variations absolues de profondeur top5 sur la même fenêtre`

**Source**
- `aggTrades` + `depth20`

**Fenêtre recommandée**
- 60 secondes

---

### F19 — `kyle_lambda`
**Nom long** : kyle_lambda_estimate

**Formule**
Réutiliser le calculateur canonique existant dans `kyle_lambda.py`.
Ne pas recoder une régression simplifiée si le module canonique existe.

**Source**
- `aggTrades` / returns signés

---

### F20 — `hhi_trades`
**Nom long** : trade_size_hhi

**Formule**
`hhi_trades_t = sum_j(s_j^2)`

avec :
- `s_j = trade_size_j / total_trade_volume_window`
- somme sur tous les trades de la fenêtre

**Source**
- `aggTrades`

**Sortie**
- float dans (0, 1]

---

### F21 — `aci_score`
**Nom long** : aggressor_consistency_index

**Formule V1 fermée**
`aci_score_t = abs(buy_aggr_volume_t - sell_aggr_volume_t) / (buy_aggr_volume_t + sell_aggr_volume_t + eps)`

avec :
- `buy_aggr_volume_t = volume agressif buy sur la fenêtre`
- `sell_aggr_volume_t = volume agressif sell sur la fenêtre`

**Source**
- `aggTrades`

---

### F22 — `vsd_deviation`
**Nom long** : volatility_seasonality_deviation

**Formule**
`vsd_deviation_t = current_realized_vol_t / (seasonal_mean_vol_same_hour_slot_t + eps)`

avec :
- `current_realized_vol_t = volatilité courante sur la fenêtre locale`
- `seasonal_mean_vol_same_hour_slot_t = moyenne historique pour le même bucket horaire hebdomadaire`

**Source**
- OHLCV / realized vol context store

---

### F23 — `adr_ratio`
**Nom long** : aggression_to_depth_ratio

**Formule**
`adr_ratio_t = aggressive_trade_size_t / (best_level_depth_t + eps)`

avec :
- `aggressive_trade_size_t = taille du trade agressif courant ou agrégé sur micro-fenêtre`
- `best_level_depth_t = profondeur disponible au meilleur niveau correspondant`

**Source**
- `aggTrades` + `depth20`

---

### F24 — `ppe_score`
**Nom long** : price_path_efficiency

**Formule**
`ppe_score_t = abs(price_end_t - price_start_t) / (sum_{k}(abs(price_k - price_k_minus_1)) + eps)`

Interprétation :
- proche de 1 -> chemin efficace / directionnel
- proche de 0 -> trajectoire bruitée

**Source**
- prix sur fenêtre 60 barres ou fenêtre configurée

---

### F25 — `dei_entropy`
**Nom long** : directional_entropy_index

**Formule**
1. construire une séquence binaire/ternaire de directions de prix ou trades sur la fenêtre
2. calculer les fréquences `p_u`, `p_d`, éventuellement `p_0`
3. `dei_entropy_t = -sum_i(p_i * ln(p_i + eps))`

**Source**
- prix ou direction de trades selon convention retenue

**Première implémentation recommandée**
- directions up / down sans état neutre

---

### F26 — `mpd_divergence`
**Nom long** : microprice_divergence

**Formule**
`micro_price_t = (best_ask_t * bid_size_1_t + best_bid_t * ask_size_1_t) / (bid_size_1_t + ask_size_1_t + eps)`

`mpd_divergence_t = (micro_price_t - mid_t) / (mid_t + eps)`

**Source**
- `depth20`

---

### F27 — `obs_skew`
**Nom long** : order_book_skewness

**Formule V1 fermée**
Construire les niveaux de prix relatifs au mid sur les 10 premiers niveaux de bid et ask.
Calculer la skewness pondérée par la profondeur :

`obs_skew_t = weighted_skew(price_distance_i, weight_i = depth_i)`

Si aucune implémentation de skewness pondérée n’existe déjà, utiliser :
- moyenne pondérée des distances
- variance pondérée
- troisième moment centré pondéré / sigma^3

**Source**
- `depth20`

---

### F28 — `hurst_exp`
**Nom long** : rolling_hurst_exponent

**Formule**
Utiliser une estimation standard Hurst sur 100 barres, déterministe et documentée.

**Règle**
- pas de variante exotique
- méthode choisie doit être documentée dans docstring et tests
- si aucune implémentation stable n’existe, rester sur une estimation R/S simple, clairement bornée et testée

**Sortie**
- float typiquement dans [0,1]

---

### F29 — `pin_score`
**Nom long** : probability_of_informed_trading

**Formule**
Réutiliser le calculateur canonique `pin.py` si présent.
Ne pas simuler une version maison si le module canonique existe.

**Source**
- paramètres pré-estimés / pipeline microstructure existant

---

## 8. V2 Secondary Features (uniquement si V1 est verte)

Le slice peut inclure en V2 :
- versions multi-horizon de `ofi_ratio`
- version top10 de `depth_imbalance`
- version z-score de `funding_norm`
- bucketisation catégorielle de `session_mult`
- interaction `funding_norm * delta_oi`
- interaction `depth_imbalance * mpd_divergence`
- interaction `vpin_score * ofi_ratio`
- interaction `hurst_exp * ppe_score`

Règle :
- les interactions sont **secondaires**
- aucune interaction ne doit être introduite si la feature de base n’est pas d’abord testée seule

---

## 9. Features explicitement différées ou research-only

Si une feature n’a pas de formule fermée, elle reste différée.
Aucune formule implicite laissée à Codex.

Différées par défaut si le temps manque :
- variantes avancées de HHI par bucket
- variantes entropy multi-symbole
- versions complexes de book geometry non testées
- toute feature qui exigerait un nouveau calculateur microstructure non encore canonisé

---

## 10. Prétraitement et normalisation

### 10.1 Règle générale
LightGBM n’exige pas une normalisation lourde comme un réseau de neurones.
Donc :
- pas de standardisation obligatoire pour toutes les features
- privilégier des features déjà stables en échelle ou des ratios
- utiliser clipping/winsorisation seulement si justifié

### 10.2 Règles recommandées
- ratios bornés : conserver tels quels
- features très heavy-tail (`kyle_lambda`, `amihud`, `pin_score` selon cas) : autoriser `log1p` ou clipping quantile si documenté
- missingness : ajouter indicateur `is_missing` seulement si utile et maîtrisé

### 10.3 Ce qu’il ne faut pas faire
- ne pas standardiser avec statistiques calculées sur tout l’échantillon avant split
- ne pas faire de leakage de moyenne / variance cross-fold

---

## 11. Builder de dataset

### 11.1 Fichier recommandé
- `src/calibration_methods/ml_dataset_builder.py`

### 11.2 Responsabilités
Le builder doit :
1. aligner toutes les sources à un timestamp `t`
2. construire les 29 features à `t`
3. calculer le label à `t+H`
4. attacher `engine_id`, `pair`, `side`, `regime_bucket` si le dataset est engine-conditioned
5. exclure toute colonne brute interdite du training final
6. produire :
   - matrice X
   - vecteur y
   - metadata de dataset
   - feature hash déterministe

### 11.3 Colonnes interdites au training final
- timestamp brut si utilisé comme identifiant direct
- prix bruts non-engineered si non justifiés
- colonnes futures
- colonnes label-leaking

### 11.4 Colonnes autorisées de contexte
- `pair_id`
- `engine_id`
- `regime_bucket`
- `session_mult`

---

## 12. Training spec

### 12.1 Fichier recommandé
- `src/calibration_methods/ml_trainer.py`

### 12.2 Paramètres imposés
- modèle : LightGBM classifier
- walk-forward : 180 jours train / 30 jours validation
- 5 folds
- Optuna <= 100 trials
- early stopping = 50
- max_depth = 6
- seed fixe et reproductible

### 12.3 Determinisme
Le training doit être déterministe par :
- seed
- dataset hash
- feature hash
- model config hash

### 12.4 Sorties minimales
- modèle entraîné
- métriques fold par fold
- OOS Sharpe proxy / métriques OOS retenues
- feature importance
- SHAP summary
- artifact hash

---

## 13. Artefact modèle

### 13.1 Fichier recommandé
- `src/interface_contracts/ml_model_artifact.py`

### 13.2 Champs obligatoires
- `schema_version`
- `model_family = "lightgbm"`
- `artifact_hash`
- `feature_hash`
- `pair_universe`
- `engine_scope`
- `train_window`
- `validation_window`
- `training_seed`
- `backtest_sharpe`
- `oos_sharpe`
- `promotion_state`
- `created_at`
- `calibration_version`
- `model_payload_ref` ou `model_bytes`
- `metrics_summary`
- `shap_summary_ref` optionnel
- `drift_baseline` optionnel

### 13.3 Contrat de consommation
Le runtime ne consomme jamais le trainer.
Il consomme seulement l’artefact validé.

---

## 14. Promotion gate ML

### 14.1 Fichier recommandé
- `src/complete_enablers/ml_model_promotion_gate.py`

### 14.2 Règles obligatoires
Le modèle est promotable seulement si :
1. `oos_sharpe >= 0.80 * backtest_sharpe`
2. `ks_test_features_pvalue > 0.05`
3. `shadow_diff_pct < 0.1%`
4. métriques présentes
5. hash valide
6. artefact non stale

### 14.3 Politique de panne
- toute métrique manquante -> `fail_closed`
- tout hash invalide -> `fail_closed`
- tout drift rouge -> blocage de promotion

---

## 15. Fusion ML

### 15.1 Fichier recommandé
- `src/complete_enablers/ml_fusion.py`

### 15.2 Formule obligatoire
`fused_score = base_score * (1 + alpha * (ml_confidence - 0.5))`

### 15.3 Propriétés à vérifier
- `alpha = 0 -> fused_score = base_score`
- `ml_confidence = 0.5 -> fused_score = base_score`
- `ml_confidence > 0.5 -> uplift`
- `ml_confidence < 0.5 -> penalty`
- `alpha > 0.5` interdit
- `side` inchangé
- artefact manquant -> `base_score` inchangé

### 15.4 Consommation runtime
Le ML doit être consommé comme une couche additive dans un hook ou support file déjà cohérent avec le repo.
Il ne doit pas injecter un chemin d’exécution parallèle.

---

## 16. Runtime enabler

### 16.1 Fichier recommandé
- `src/complete_enablers/ml_confidence_enabler.py`

### 16.2 Responsabilités
1. charger l’artefact modèle
2. reconstruire le vecteur de features runtime-safe
3. obtenir `ml_confidence`
4. appeler `ml_fusion`
5. journaliser état / dégradation / staleness si nécessaire

### 16.3 Dégradation gracieuse
Si :
- artefact absent,
- artifact hash invalide,
- feature set incomplet,
- drift trop fort,

alors :
- le moteur continue avec `base_score`
- aucun side n’est altéré
- aucun faux block n’est inventé
- la dégradation est observable / journalisée

---

## 17. Model risk et drift

### 17.1 Fichiers recommandés
- `src/meta_learning/model_risk_registry/`
- `src/meta_learning/strategy_drift_monitor/`

### 17.2 Minimum requis dans ce slice
- enregistrer `train_window`, `feature_hash`, `oos_sharpe`, `promotion_state`
- suivre drift replay/shadow/live
- produire un signal explicite de pause / promotion_block si drift fort

### 17.3 Règle
Pas de sous-système géant.
Le but de ce slice est un noyau auditable, pas une plateforme research totale.

---

## 18. Fichiers à créer / modifier

### Créations recommandées
- `src/calibration_methods/ml_dataset_builder.py`
- `src/calibration_methods/ml_trainer.py`
- `src/interface_contracts/ml_model_artifact.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/ml_fusion.py`
- `src/complete_enablers/ml_model_promotion_gate.py`
- `src/meta_learning/model_risk_registry/` (minimal)
- `src/meta_learning/strategy_drift_monitor/` (minimal)

### Modifications autorisées
- init exports correspondants
- points d’intégration additives seulement
- tests existants touchés uniquement si nécessaire pour brancher le nouveau seam

### Modifications interdites
- moteurs A/B/C/D comme nouvelle logique souveraine
- fichiers quant ancres protégés
- rewrite massif du runtime

---

## 19. Tests obligatoires

### 19.1 Dataset builder
Créer : `tests/test_calibration_methods/test_ml_dataset_builder.py`

Doit prouver :
1. aucune observation future dans les features
2. target strictement future
3. trous de données -> missing explicite
4. feature hash stable
5. colonnes interdites absentes du dataset final

### 19.2 Trainer
Créer : `tests/test_calibration_methods/test_ml_trainer.py`

Doit prouver :
1. training déterministe même seed + même dataset
2. split walk-forward respecté
3. Optuna cap respectée
4. dataset vide -> erreur explicite
5. artifact produit avec champs obligatoires

### 19.3 Artefact modèle
Créer : `tests/test_interface_contracts/test_ml_model_artifact.py`

Doit prouver :
1. validation Pydantic
2. hash invalide rejeté
3. champs manquants rejetés
4. round-trip sérialisation stable

### 19.4 Promotion gate
Créer : `tests/test_complete_enablers/test_ml_model_promotion_gate.py`

Doit prouver :
1. pass si règles vertes
2. fail closed si métrique manque
3. fail si `oos_sharpe < 0.80 * backtest_sharpe`
4. fail si `ks_test_features_pvalue <= 0.05`
5. fail si `shadow_diff_pct >= 0.1%`

### 19.5 Fusion
Créer : `tests/test_complete_enablers/test_ml_fusion.py`

Doit prouver :
1. `alpha = 0` neutre
2. `ml_confidence = 0.5` neutre
3. uplift si confidence haute
4. penalty si confidence basse
5. `alpha > 0.5` rejeté
6. side inchangé

### 19.6 Enabler runtime
Créer : `tests/test_complete_enablers/test_ml_confidence_enabler.py`

Doit prouver :
1. artefact absent -> base_score inchangé
2. artefact stale -> dégradation
3. confidence bornée [0,1]
4. direction debug non souveraine
5. side moteur inchangé

### 19.7 Drift / model risk
Créer :
- `tests/test_meta_learning/test_model_risk_registry.py`
- `tests/test_meta_learning/test_strategy_drift_monitor.py`

Doit prouver :
1. stockage identité modèle
2. drift synthétique détecté
3. pause / promotion_block émis
4. chemin vert sans sur-réaction

### 19.8 Tests feature-level
Créer : `tests/test_calibration_methods/test_ml_features_registry.py`

Doit prouver pour chaque feature V1 :
1. formule correcte sur fixture simple
2. pas de NaN silencieux non géré
3. alignement temporel correct
4. pas de leakage

---

## 20. Garde-fous d’implémentation

1. Aucun fichier `src/` nouveau > 700 lignes.
2. Aucune fonction > 60 lignes sans décomposition.
3. Typage complet.
4. Pas de `Any` non justifié.
5. Pas de `except Exception:` nu.
6. Pas de `print()` dans `src/`.
7. Pas de mutation silencieuse du score ou du side.
8. Pas de nouvelles dépendances lourdes inutiles.
9. Réutiliser les calculateurs microstructure canoniques existants si présents.
10. Pas de formule laissée implicite à Codex.

---

## 21. Ce que Codex ne doit surtout pas faire

1. Transformer ce slice en nouveau moteur ML.
2. Laisser le modèle produire directement le `side` live.
3. Réentraîner sur VPS.
4. Réécrire les moteurs A/B/C/D.
5. Toucher PSR / DSR / POT-GPD / Energy.
6. Introduire torch / deep learning / RL.
7. Ajouter 50 interactions opaques sans justifications.
8. Prendre ADX comme pilier principal.
9. Ajouter un second canon d’artefact.
10. Ignorer le refusal / drift / promotion gate.

---

## 22. Brief d’ouverture à copier dans Codex

You are working on the V5.3 ML enabler slice only.

Global invariants:
- ML is additive only.
- A/B/C/D remain sovereign.
- VPS never trains.
- LightGBM only.
- No edits to protected quant-anchor modules.
- No new engine.
- No side override.
- No alpha > 0.5.

Modules that must connect through real seams:
- calibration_methods
- interface_contracts
- complete_enablers
- meta_learning
- meta_minimal
- existing artifact transport

Forbidden defaults:
- no torch
- no RL
- no XGBoost/CatBoost zoo
- no VPS fit
- no second canon
- no broad rewrites

After generation, verify explicitly:
1. training local only
2. fusion formula exact
3. side unchanged
4. alpha <= 0.5 enforced
5. quant-anchor files untouched
6. targeted tests green
7. DAG green
8. new_violations=0

---

## 23. Critères d’acceptation

### COMPLETE
- dataset builder vert
- trainer vert
- artifact contract vert
- promotion gate vert
- fusion vert
- enabler runtime vert
- drift/model risk minimal vert
- tests V1 core features verts
- DAG PASS
- `new_violations=0`

### PARTIAL
- noyau ML enabler livré
- artifact + fusion + gate verts
- certaines features secondaires différées honnêtement
- aucun invariant violé

### BLOCKED
- tentative de side override
- tentative de VPS training
- quant anchors touchés
- alpha > 0.5
- nouvelle architecture ML-first

---

## 24. Verdict d’ingénierie attendu

À la fin, Codex doit rendre :
1. Résumé
2. Fichiers créés / modifiés
3. Formules implémentées
4. Tests ajoutés
5. Résultats de preuve
6. Deferred / not done
7. Risks / open questions
8. Completion status

Fin du document.
