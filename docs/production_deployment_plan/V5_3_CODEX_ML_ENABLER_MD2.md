
# V5.3 — MD2 — SPEC DÉTAILLÉE CODEX — ML ENABLER (Features V2, Tests, Garde-fous, Audit, Ordre d’implémentation)

## 0. Rôle de MD2

Ce fichier complète MD1.  
Il sert de :
- garde-fou anti-oubli
- registre des features secondaires / différées
- plan de tests
- checklist de clôture
- ordre d’implémentation

Codex ne doit pas interpréter MD2 comme optionnel.  
MD2 verrouille tout ce qui rend le slice **audit-ready**.

---

## 1. Features V2 — exactes et autorisées après V1

Les features V2 sont utiles mais non nécessaires au tout premier atterrissage.  
Elles peuvent être codées dans la même tranche **si et seulement si** V1 est propre et testée.

---

## 1.1 `cvd_divergence_20`

### Définition
Soit le CVD :
```text
CVD_t = sum(signed_trade_volume_i for i up to t)
```

Avec `signed_trade_volume_i = +volume_i` si trade agressif buy, `-volume_i` sinon.

Feature :
```text
cvd_divergence_20_t =
    corr( delta(CVD) over last 20 bars,
          delta(mid_price) over last 20 bars )
```

### Interprétation
- corr forte positive -> flux soutient le prix
- corr faible / négative -> divergence

### Règle
Ne coder que si la classification aggressor est bien disponible ou clairement définie.

---

## 1.2 `adr_ratio`

### Définition
Aggression-to-Depth Ratio :

pour l’événement ou la barre agrégée :
```text
adr_ratio_t =
    aggressed_volume_t / (best_level_depth_t + eps)
```

### Variables
- `aggressed_volume_t` = volume des trades agressifs dans la fenêtre de calcul
- `best_level_depth_t` = profondeur disponible au meilleur niveau avant exécution

---

## 1.3 `hhi_trades`

### Définition
Indice Herfindahl-Hirschman sur tailles de trades dans la fenêtre W :

```text
w_i = trade_size_i / (sum(trade_size_j over window W) + eps)
hhi_trades_t = sum(w_i^2 over trades in window W)
```

### Interprétation
- élevé -> quelques gros blocs
- faible -> beaucoup de petits trades

---

## 1.4 `aci_score`

### Définition
Aggressor Consistency Index :

```text
aci_score_t =
    (buy_aggressed_volume_t - sell_aggressed_volume_t)
    / (buy_aggressed_volume_t + sell_aggressed_volume_t + eps)
```

### Interprétation
- proche de +1 -> agressivité acheteuse persistante
- proche de -1 -> agressivité vendeuse persistante

---

## 1.5 `ppe_score`

### Définition
Price Path Efficiency sur fenêtre W :

```text
ppe_score_t =
    abs(price_end_t - price_start_t)
    / (sum(abs(price_k - price_k-1) over window W) + eps)
```

### Domaine
```text
0 <= ppe_score_t <= 1
```

### Interprétation
- proche de 1 -> trajectoire directionnelle propre
- proche de 0 -> trajectoire bruitée / erratique

---

## 1.6 `dei_entropy`

### Définition
Directional Entropy Index sur séquence binaire des directions de variation.

Soit une fenêtre W de signes de returns :
```text
s_k ∈ {up, down}
p_up = count(up) / W
p_down = count(down) / W
```

Alors :
```text
dei_entropy_t =
    -(p_up * log(p_up + eps) + p_down * log(p_down + eps)) / log(2)
```

### Domaine
```text
0 <= dei_entropy_t <= 1
```

---

## 1.7 `vsd_deviation`

### Définition
Volatility Seasonality Deviation :

```text
vsd_deviation_t =
    current_realized_vol_t
    / (mean_realized_vol_for_same_hour_of_week + eps)
```

### Interprétation
- > 1 = volatilité anormalement forte pour cette heure
- < 1 = volatilité anormalement faible

---

## 1.8 `funding_oi_interaction`

### Définition
Feature d’interaction :

```text
funding_oi_interaction_t = funding_norm_168h_t * delta_oi_1h_t
```

### Intérêt
Permet au modèle de distinguer :
- OI en hausse + funding extrême = crowding possible
- OI en baisse + funding extrême = unwind possible

---

## 1.9 `pair_liquidity_rank`

### Définition
Rang ordinal de liquidité parmi l’univers live/shadow au timestamp `t`.

### Règle
- calculé uniquement à partir de données observables à `t`
- si non disponible proprement, laisser en `DEFERRED`

---

## 2. Features `RESEARCH_ONLY` ou `DEFERRED`

Ces features ne doivent pas être improvisées.  
Codex doit les laisser hors runtime initial s’il ne peut pas prouver une définition fermée.

---

## 2.1 `ltr_ratio` — DEFERRED

Raison :
- définition initiale fournie par l’utilisateur incomplète/tronquée
- pas assez de fermeture mathématique pour une implémentation prod-safe

Action :
- ne pas coder en V1
- documenter comme `DEFERRED`

---

## 2.2 `mem_state` — DEFERRED

Raison :
- formule fournie trop ambiguë
- risque fort d’hallucination de normalisation et d’échelle

Action :
- ne pas coder sans validation humaine supplémentaire

---

## 2.3 `obs_skew` — RESEARCH_ONLY

Peut être défini comme asymétrie géométrique du carnet, mais il faut figer :
- la pondération,
- le nombre de niveaux,
- la définition exacte du `depth_price`.

Sans fermeture complète, garder hors runtime initial.

---

## 2.4 `hawkes_intensity_feature` — RESEARCH_ONLY

Le repo a un évaluateur d’intensité Hawkes à partir de paramètres déjà estimés.  
Cette feature n’est autorisée en runtime ML initial que si les paramètres sont fournis proprement par un seam gouverné. Sinon, rester `RESEARCH_ONLY`.

---

## 2.5 `pin_score_feature` — RESEARCH_ONLY

Même logique :
- le repo a un calcul PIN à partir de paramètres pré-estimés
- ne pas halluciner l’estimation de ces paramètres dans ce slice

---

## 2.6 `adx_trend` — EXCLUDED_FROM_V1

Raison :
- contradiction potentielle avec la prohibition formelle des indicateurs TA 1990s comme base structurante
- éventuellement tolérable plus tard comme feature secondaire de contrôle, mais **pas dans ce slice**

---

## 3. Tests obligatoires

## 3.1 `tests/test_calibration_methods/test_ml_dataset_builder.py`

Doit prouver :
- aucune feature n’utilise de données `> t`
- le label utilise des données `> t`
- colonnes interdites absentes
- trous et NaN gérés explicitement
- feature hash stable à données identiques

## 3.2 `tests/test_calibration_methods/test_ml_trainer.py`

Doit prouver :
- reproductibilité à seed fixe
- respect du split walk-forward
- plafond Optuna respecté
- hash artefact stable
- erreur explicite si dataset vide ou colonne obligatoire manquante

## 3.3 `tests/test_interface_contracts/test_ml_model_artifact.py`

Doit prouver :
- contrat gelé
- champs obligatoires présents
- serialization / deserialization stable
- hash invalide rejeté

## 3.4 `tests/test_complete_enablers/test_ml_confidence_enabler.py`

Doit prouver :
- `ml_confidence` bornée à `[0,1]`
- artefact manquant -> dégradation gracieuse
- artefact stale -> blocage ou dégradation gracieuse explicitement documentée
- jamais d’override du side

## 3.5 `tests/test_complete_enablers/test_ml_fusion.py`

Doit prouver :
- `alpha = 0` -> neutralité
- `ml_confidence = 0.5` -> neutralité
- uplift si confiance haute
- penalty si confiance basse
- `alpha > 0.5` rejeté
- side inchangé

## 3.6 `tests/test_complete_enablers/test_ml_model_promotion_gate.py`

Doit prouver :
- succès si toutes conditions vertes
- fail-close si métrique absente
- rejet si `oos_sharpe < 0.80 * backtest_sharpe`
- rejet si `ks_test_features_pvalue <= 0.05`
- rejet si `shadow_diff_pct >= 0.1%`

## 3.7 `tests/test_meta_learning/test_model_risk_registry.py`

Doit prouver :
- stockage de `feature_hash`, `train_window`, `oos_sharpe`
- détection de drift simulée
- état explicite `insufficient_data` si besoin

## 3.8 `tests/test_meta_learning/test_strategy_drift_monitor.py`

Doit prouver :
- drift distribution forecast détecté
- drift WR/CE détecté
- pas de sur-déclenchement sur série saine

## 3.9 Tests anti-leakage synthétiques indispensables

Créer au moins un test où :
- une feature volontairement calculée avec `t+1` ferait changer fortement le modèle
- le builder doit empêcher ce cas

---

## 4. Garde-fous d’engineering

### 4.1 Qualité code
- `from __future__ import annotations`
- fonctions courtes
- typage strict
- pas de `Any` gratuit
- pas de `print`
- pas de `except Exception:` nu
- fichiers `src/` < 700 lignes
- pas de god module

### 4.2 Sécurité runtime
- aucun import d’entraînement dans les chemins live chauds si artefact-only suffit
- aucun fallback silencieux “ML decides”
- aucune mutation du candidate side
- aucune mutation du canon `SignalCandidate`

### 4.3 Gouvernance
- aucune promotion par PnL seul
- aucune promotion sans hash / metrics / gate
- aucune auto-promotion live
- aucune calibration VPS

---

## 5. Ordre d’implémentation conseillé

## Étape 1
Créer les contrats et le dataset builder :
- `ml_model_artifact.py`
- `ml_dataset_builder.py`

## Étape 2
Créer le trainer :
- `ml_trainer.py`

## Étape 3
Créer la fusion et l’enabler runtime :
- `ml_fusion.py`
- `ml_confidence_enabler.py`

## Étape 4
Créer le promotion gate :
- `ml_model_promotion_gate.py`

## Étape 5
Brancher model risk / drift minimum :
- `model_risk_registry`
- `strategy_drift_monitor`

## Étape 6
Ajouter les features V2 si et seulement si V1 est propre et tous tests V1 verts

---

## 6. Critères d’acceptation

Le slice ne peut être déclaré `COMPLETE` que si :

1. V1 features implémentées proprement
2. aucune feature `DEFERRED` n’a été improvisée
3. trainer déterministe
4. artefact contract complet
5. promotion gate fail-closed
6. fusion exacte et bornée
7. VPS n’entraîne rien
8. side inchangé
9. tests verts
10. `engineering_guardrails new_violations=0`
11. DAG vert
12. aucun fichier quant gelé modifié

Sinon :
- `PARTIAL` si la logique est saine mais tout n’est pas fermé
- `BLOCKED` si une dépendance doctrinale ou technique bloque le slice

---

## 7. Preuves / commandes à rendre

Codex doit rendre les sorties de preuve suivantes :

```bash
python -m py_compile <all new/modified src files> <all new/modified test files>
pytest -q tests/test_calibration_methods/test_ml_dataset_builder.py
pytest -q tests/test_calibration_methods/test_ml_trainer.py
pytest -q tests/test_interface_contracts/test_ml_model_artifact.py
pytest -q tests/test_complete_enablers/test_ml_confidence_enabler.py
pytest -q tests/test_complete_enablers/test_ml_fusion.py
pytest -q tests/test_complete_enablers/test_ml_model_promotion_gate.py
pytest -q tests/test_meta_learning/test_model_risk_registry.py
pytest -q tests/test_meta_learning/test_strategy_drift_monitor.py
python scripts/run_engineering_guardrails.py
python scripts/run_dag_check.py
```

Il doit aussi reporter :
- nombre exact de tests passés
- `new_violations`
- éventuels fichiers > 700L
- deferred explicites

---

## 8. Checklist d’audit commune (toi + moi après retour Codex)

### Doctrine
- [ ] pas de moteur ML
- [ ] pas de training VPS
- [ ] pas d’override side
- [ ] pas d’édition quant-anchor

### Architecture
- [ ] seams existants réutilisés
- [ ] pas de package top-level inventé
- [ ] artefact versionné

### Data
- [ ] label net de coût
- [ ] anti-leakage propre
- [ ] features interdites absentes

### Features
- [ ] toutes V1 codées proprement
- [ ] V2 non forcées si ambiguës
- [ ] ADX absent de V1
- [ ] aucune formule inventée

### Runtime
- [ ] fusion exacte
- [ ] alpha cap <= 0.5
- [ ] dégradation gracieuse

### Gouvernance
- [ ] promotion gate fail-closed
- [ ] drift monitor présent
- [ ] model risk présent

### Tests
- [ ] preuves rendues
- [ ] DAG vert
- [ ] guardrails verts

---

## 9. Brief exact d’ouverture pour Codex

Utiliser exactement ce pattern au début de la session :

```text
You are working on the V5.3 ML enabler slice only.

Global invariants:
- one shared core only
- Local IA Lab -> signed artifact -> VPS is canonical
- VPS never trains
- no new engine outside A/B/C/D
- ML is additive score modulation only
- no side override
- no edits to protected quant-anchor files
- no 1990s-TA primary feature set
- alpha hard cap <= 0.5

Modules that must connect through real seams:
- src/interface_contracts/forecast_contracts.py
- src/interface_contracts/strategy_identity.py
- src/scoring_backbone/break_even_filter.py
- src/meta_minimal/cost_drift_monitor/
- src/meta_learning/model_risk_registry/
- src/meta_learning/strategy_drift_monitor/
- src/data_backbone/microstructure/*
- src/backtest_artifact_import/

Forbidden defaults:
- no torch
- no RL
- no new ML engine
- no VPS training
- no direct side control
- no edits to psr/dsr/pot_gpd/energy_distance
- no god files
- no formula hallucination

After generation, verify explicitly:
- V1 features only or explicitly documented V2
- deterministic trainer
- artifact contract complete
- promotion gate fail-closed
- fusion formula exact
- alpha <= 0.5
- side unchanged
- DAG green
- engineering_guardrails new_violations=0
- all targeted ML tests green
```

Fin de MD2.
