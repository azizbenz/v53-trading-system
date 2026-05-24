# Livre Blanc V5.3 IA Lab / Backtest

## 1. Objet

Ce document est le livre blanc opérateur pour :

- lancer un run de training ML Strategy Ladder depuis **IA Lab**
- lancer un **backtest** avec ou sans ML
- comprendre quand un ensemble de features est scientifiquement autorisé
- diagnostiquer pourquoi un run a été rapide, bloqué, ou a semblé "perdre" ses features sélectionnées

Ce document est fondé sur le code courant et sur le run audité :

- `strategy_ladder_ml_lab_handoff-1779581789540`
- racine du run : `K:\v5.3 backtest\output2\ml_handoffstrategy\runs\strategy_ladder_ml_lab_handoff-1779581789540`

## 2. Doctrine centrale

V5.3 conserve les invariants suivants :

- spot-only, long-only, compatible sharia
- les engines A/B/C/D restent natifs et canoniques
- la sélection de features dans le cockpit **ne modifie pas directement** la logique A/B/C/D
- la sélection de features agit uniquement sur le **rail ML de training / frozen artifact**
- la discovery proxy n’est pas une vérité de backtest
- les features ML non-legacy exigent une preuve `B2` replay-grounded

Règle pratique :

- les **3 features legacy** peuvent être entraînées depuis `kline_root` seul
- les **features non-legacy / microstructure / F16** exigent `b2_run_root` ou un label store replay-grounded

## 3. Étude de cas : ce qui s’est passé sur le run `1779581789540`

### Faits observés

- durée du run : environ `8.93s`, donc ce n’était pas un crash
- statut final : `READY`
- le run a utilisé seulement :
  - `close_return`
  - `high_low_range`
  - `volume`
- le run n’a **pas** utilisé l’univers complet des features supposées sélectionnées

### Artifacts de preuve

- requête cockpit :
  - `build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job_request.json`
- statut cockpit :
  - `build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job_status.json`
- état persistant IA Lab :
  - `build/cockpit/backtest_jobs/_last_lab_ml_handoff_form_state.json`
- rapport handoff :
  - `strategy_ladder_ml_lab_handoff_report.json`
- résumé du bundle modèle :
  - `strategy_ladder_expected_edge_ml_model_bundle.summary.json`

### Pourquoi il a été rapide

Le run était :

- `gold_store_kline_features`
- `EXPECTED_EDGE_PROXY_DISCOVERY_ONLY`
- sans `b2_run_root`
- sans label store replay-grounded
- en pratique un slice LightGBM léger multi-timeframe sur les 3 features legacy

### Ce qui était anormal

L’intention opérateur était "toutes les features sélectionnées", mais le jeu de features effectivement soumis était déjà retombé sur les 3 features legacy avant l’exécution du trainer.

### Patch désormais en place

- le picker recopie maintenant l’état réel des checkboxes dans des champs CSV cachés robustes au submit
- le cockpit persiste plus explicitement le jeu de features effectif dans la requête de job
- IA Lab bloque désormais tout launch non-legacy sans `b2_run_root`
- la chaîne ML du backtest bloque aussi les features non-legacy sans racine replay Phase B2

## 4. Familles de features

### Features legacy

- `close_return`
- `high_low_range`
- `volume`

Ce sont les seules features autorisées pour un training purement kline-only.

### Famille replay / microstructure / F16

Exemples :

- `spread_bps`
- `slippage_bps`
- `book_depth_levels`
- `break_even_bps`
- `vpin`
- `cumulative_ofi`
- `queue_pressure`
- `kyle_lambda`
- `realized_vol_current`
- `realized_vol_at_break`
- `latency_penalty_bps`
- `micro_edge_exit_governor_observed`
- `micro_edge_entry_timing_observed`
- `history_score`
- `marginal_value_score`
- `reentry_lateness`
- `concentration_headroom`
- `anti_revenge_state__active`
- `anti_revenge_state__cooling`
- `anti_revenge_state__idle`

Ces features exigent un grounding replay.

## 5. Engines vs ML : qui consomme quoi

### Engines natifs

Les engines A/B/C/D ne lisent **pas** directement le feature picker cockpit.

Ils gardent leurs propres gates et équations natives :

- Engine A : structure / direction
- Engine B : excess / cost feasibility
- Engine C : breakout structure
- Engine D : history / re-entry governance

### Overlay ML

L’overlay ML consomme :

- le jeu de features sélectionné au training
- la liste de features du frozen artifact
- l’hydratation runtime des features fournie par le rail replay

Donc :

- les engines produisent une partie du contexte natif qui peut ensuite être remonté en features ML
- la sélection cockpit pilote **le scope du training ML**, pas la politique de décision native des engines

## 6. IA Lab : flux opérateur correct

### A. Training legacy kline-only

À utiliser si tu veux un run rapide legacy.

Requis :

- `kline_root`
- fenêtre de training
- sélection limitée aux 3 features legacy

Non requis :

- `b2_run_root`

Comportement attendu :

- run rapide
- labels proxy-discovery-only
- pas de features microstructure replay-grounded

### B. Training complet / étendu / non-legacy

À utiliser si tu veux un ML replay-grounded.

Requis :

- `kline_root`
- `b2_run_root`
- fenêtre de training
- features non-legacy sélectionnées

Comportement attendu :

- run plus lent que le legacy-only
- features et labels appuyés sur le replay
- audit scientifique possible pour un expected-edge plus riche

### C. Ce qui est désormais bloqué

Si la sélection IA Lab contient au moins une feature non-legacy et que `b2_run_root` est vide :

- le launch est bloqué avant le training
- la sélection reste persistée dans la page
- l’opérateur voit un blocker clair au lieu d’un run trompeusement court

## 7. Backtest : flux opérateur correct

### A. Backtest natif sans ML

Utiliser :

- `ML_MODE_OFF`
- aucune feature sélectionnée

Comportement :

- chemin natif uniquement
- pas de handoff ML, pas de frozen artifact training

### B. Backtest avec features sélectionnées depuis `/backtest`

Utiliser :

- `ML_MODE_OFF`
- une ou plusieurs features sélectionnées
- `training_timeframe` explicite

Comportement :

- le cockpit lance d’abord le handoff ML
- puis relance le replay avec le frozen artifact produit

Si les features sont legacy-only :

- aucune racine replay B2 n’est requise

Si les features sont non-legacy :

- une racine replay Phase B2 doit exister
- sinon la chaîne est bloquée avant le handoff

### C. Backtest avec frozen ML artifact

Utiliser :

- `ML_MODE_OVERLAY_FROZEN`
- un handoff run root / artifact path / hash gouverné

Comportement :

- la liste de features de l’artifact fait autorité
- le picker devient informatif / read-only
- le replay score contre le contrat du frozen artifact

## 8. Checklist d’audit opérateur

Avant launch :

- confirmer si la sélection est legacy-only ou non-legacy
- si non-legacy, confirmer que `b2_run_root` existe
- confirmer les dates de training
- confirmer `training_timeframe`
- confirmer le nombre de features affiché dans la page

Après launch :

- inspecter `job_request.json`
- inspecter `job_status.json`
- inspecter `_last_lab_ml_handoff_form_state.json` ou `_last_form_state.json`
- inspecter `strategy_ladder_ml_lab_handoff_report.json`
- inspecter `strategy_ladder_backtest_ml_input.json`
- inspecter `strategy_ladder_expected_edge_ml_model_bundle.summary.json`

Ce qui doit matcher :

- nombre de features sélectionnées
- noms des features
- portée timeframe
- fenêtre de training
- mode artifact
- présence ou absence de replay grounding

## 9. Modes d’erreur / de confusion fréquents

### "Le run a fini trop vite"

Cela signifie souvent l’un de ces cas :

- training legacy-only
- pas de replay grounding
- pas de slice Optuna lourde
- faible volume de lignes / early stopping

Cela ne veut **pas** dire automatiquement échec.

### "Toutes les features étaient cochées mais seulement 3 ont été utilisées"

C’est désormais audité via :

- miroir caché des features au submit
- état persistant du formulaire
- payload de features dans la requête du job

Si cela se reproduit, comparer :

- le compteur de sélection dans la page
- le form-state persisté
- `feature_names_csv` dans la job request

### "Pourquoi le non-legacy est bloqué ?"

Parce que le code du trainer interdit les features microstructure / replay sans source replay-grounded.

C’est un comportement fail-closed intentionnel.

## 10. Cartographie fichiers

Modules UI / contrôle concernés :

- `src/cockpit/templates/pages/lab.html`
- `src/cockpit/templates/pages/backtest.html`
- `src/cockpit/server.py`
- `src/cockpit/state.py`
- `src/cockpit/action_support.py`

Modules training / runtime concernés :

- `src/local_replay_runtime/strategy_ladder_expected_edge_training.py`
- `src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py`
- `src/local_replay_runtime/strategy_ladder_runner.py`

Tests pertinents :

- `tests/cockpit/test_lab_feature_picker.py`
- `tests/cockpit/test_backtest_feature_picker_chain.py`

## 11. Règle opérationnelle actuelle

Si tu veux :

- **un training exploratoire rapide** : utiliser les 3 features legacy avec `kline_root`
- **un vrai training étendu** : fournir `b2_run_root`
- **un backtest natif uniquement** : garder le ML off et laisser la sélection de features vide
- **un backtest assisté par ML depuis `/backtest`** : choisir les features, fixer le timeframe, laisser le cockpit faire d’abord le handoff puis le replay

Le modèle mental sûr est :

- **Legacy 3 = autorisé en kline-only**
- **Tout ce qui dépasse Legacy 3 = replay grounding requis**
