# V5.3 — STRATEGY BUILD INTEGRATION PLAYBOOK
## Guide opératoire build par build pour ajouter une stratégie dans la V5.3
### Document de travail dérivé du master canonique et du protocole d’onboarding
### Sans code — prod-safe

---

# 0. Objet

Ce document répond à une question pratique :

> Quand une nouvelle stratégie apparaît, **où** doit-on la classer, **dans quel build** doit-on l’intégrer, **dans quels fichiers** doit-on coder, **quels logs/tests** doit-on ajouter, et **qu’est-ce qui est interdit** ?

Ce document ne remplace pas le master canonique. Il sert de **playbook développeur**.

---

# 1. Règle d’or

Dans V5.3, une nouvelle stratégie ne suit **jamais** le chemin :

```text
idée -> code direct -> backtest local -> live
```

Le seul chemin acceptable est :

```text
idée stratégique
-> classification
-> versioning
-> intégration shared core
-> tests locaux
-> LOCAL_REPLAY
-> export artifact
-> import VPS
-> revue de valeur marginale
-> candidature contrôlée
-> Shadow / Micro-live / Live selon le plan officiel
```

---

# 2. Décision immédiate à prendre pour chaque nouvelle idée

## 2.1 Taxonomie obligatoire

Toute nouvelle stratégie doit être classée dans **une seule** catégorie :

- `A_variant`
- `B_variant`
- `Build14_enabler`
- `C_candidate`
- `D_candidate`
- `out_of_scope_for_V5_3`

## 2.2 Traduction immédiate en build cible

| Classification | Sens réel | Build cible principal | Statut attendu |
|---|---|---:|---|
| `A_variant` | variante du moteur A | Build-6 | NOW / Light-compatible |
| `B_variant` | variante du moteur B | Build-7 | NOW / Light-compatible |
| `Build14_enabler` | brique d’enrichissement non autonome | Build-14 | lecture seule puis influence limitée |
| `C_candidate` | logique breakout distincte de A | Build-15 | Complete candidate |
| `D_candidate` | logique re-entry distincte de A | Build-16 | Complete candidate |
| `out_of_scope_for_V5_3` | ne rentre pas proprement dans le canon | aucun | recherche locale seulement |

## 2.3 Ce qu’il ne faut jamais faire

- créer un moteur `E/F/G`
- créer un nouveau profil `LOCAL_PROFILE`, `RESEARCH_PROFILE`, `BACKTEST_PROFILE`
- laisser une feature ou formule vivre uniquement sur PC
- coder une stratégie seulement dans un notebook
- injecter un plugin stratégie arbitraire sur la VPS
- promouvoir live depuis un bon backtest seul

---

# 3. Artefacts de gouvernance obligatoires pour chaque stratégie

Avant de coder, produire au minimum une **fiche de classification**.

## 3.1 Fiche minimale

```text
proposal_id
proposal_name
classification
expected_engine_scope
why_not_A
why_not_B
why_not_Build14_enabler
why_not_duplicate
economic_hypothesis
portfolio_hypothesis
promotion_target
```

## 3.2 Contrat de versioning obligatoire

```text
strategy_id
strategy_version
feature_set_version
formula_set_version
scoring_version
regime_version
risk_policy_version
cost_model_version
```

## 3.3 Emplacement documentaire conseillé

Créer ou maintenir :

```text
docs/strategy_onboarding/
├── proposals/
│   ├── <proposal_id>.md
│   └── ...
├── classifications/
│   ├── <strategy_id>_classification.md
│   └── ...
├── reviews/
│   ├── <strategy_id>_marginal_value_review.md
│   └── ...
└── STRATEGY_REGISTRY.md
```

---

# 4. Arborescence de code recommandée

## 4.1 Principe

Le code métier reste dans le **shared core**. La logique locale/VPS ne doit pas dupliquer les moteurs.

## 4.2 Arborescence cible recommandée

```text
src/
├── interface_contracts/
├── manifest_registry/
├── data_backbone/
├── execution_backbone/
├── risk_backbone/
├── scoring_backbone/
├── engines/
│   ├── engine_a/
│   ├── engine_b/
│   ├── engine_c/
│   └── engine_d/
├── portfolio_engine/
├── meta_engine/
├── monitoring_ui/
├── build14_enablers/
│   ├── microstructure_enriched/
│   ├── regime_enriched/
│   ├── robust_covariance/
│   ├── risk_contribution/
│   └── edge_diversity/
└── local_replay_runtime/
```

## 4.3 Convention de nommage recommandée

Pour éviter les collisions documentaires du type `A1/A2/A3` réutilisés dans plusieurs sources, nommer les variantes ainsi :

```text
A_variant_pullback_structure_v1
A_variant_vcp_expansion_v1
B_variant_vwap_microprice_reversion_v1
Build14_enabler_market_toxicity_v1
C_candidate_absorption_breakout_v1
D_candidate_trend_reacquisition_v1
```

---

# 5. Build-1 — Dependency Architecture
## Rôle stratégique

Build-1 ne code pas l’alpha. Il verrouille l’architecture.

## Ce qu’une nouvelle stratégie doit toucher ici

### À mettre à jour

```text
src/interface_contracts/
src/manifest_registry/
src/dag_validator/
tests/test_contracts/
tests/test_manifest_registry/
```

### À ajouter ou maintenir

- identifiants de stratégie
- identifiants moteur
- versions de stratégie
- contrats d’output auditables
- enregistrement manifest des nouveaux modules si la stratégie crée un sous-module officiel

## Exemples de fichiers à créer/modifier

```text
src/interface_contracts/strategy_contracts.py
src/interface_contracts/decision_contracts.py
src/manifest_registry/module_inventory.py
src/manifest_registry/profile_registry.py
src/manifest_registry/version_registry.py
```

## Logs attendus

Build-1 log peu. Mais il doit exposer au moins :

- `contract_version`
- `strategy_version`
- `manifest_registration_ok`
- `dependency_violation_detected`

## Tests obligatoires

- contrat sérialisable
- présence des champs obligatoires
- stratégie connue du manifest
- absence d’import interdit
- pas de dépendance cachée d’une stratégie vers runtime local ou VPS

## Interdictions

- stratégie connue du code mais absente du manifest
- seuil critique caché dans un notebook
- import dynamique libre

---

# 6. Build-2 — Data Backbone
## Rôle stratégique

Build-2 fournit les **inputs observables** nécessaires aux stratégies.

## Ce qu’une stratégie peut toucher ici

Seulement si elle a besoin de **données nouvelles et légitimes** :

- nouveau champ normalisé
- nouvelle mesure de fraîcheur/cohérence
- nouveau score de santé paire
- nouvelle métrique microstructure de base

## Fichiers cibles recommandés

```text
src/data_backbone/websocket_gateway.py
src/data_backbone/rest_bootstrap.py
src/data_backbone/event_normalizer.py
src/data_backbone/internal_router.py
src/data_backbone/freshness_checker.py
src/data_backbone/consistency_checker.py
src/data_backbone/pair_health_scorer.py
```

## Quand modifier Build-2

Modifier Build-2 seulement si la stratégie a besoin d’un input qui doit devenir **canonique**, par exemple :

- `recv_time` enrichi
- `depth_consistency_state`
- `pair_health_reason_codes`
- `microprice_raw`
- `basic_order_flow_imbalance`

## Logs à ajouter si Build-2 est touché

- `event_normalized`
- `field_missing_rejected`
- `pair_health_degraded`
- `freshness_hard_breach`
- `consistency_contradiction_detected`

## Tests obligatoires

- nouveau champ présent sur tous les chemins valides
- backward compatibility de schéma
- pas de contamination inter-paires
- pas de décision prise sur donnée non horodatée proprement

## Interdictions

- coder de la logique de stratégie directement ici
- faire dépendre la couche data d’un moteur A/B/C/D

---

# 7. Build-3 — Execution Backbone
## Rôle stratégique

Aucune stratégie n’a de sens si son coût réel n’est pas mesurable.

## Ce qu’une stratégie peut toucher ici

- calibration du coût ex ante
- règles de refus exécution si coût tue l’edge
- métriques d’exécution spécifiques utiles à l’audit stratégique

## Fichiers cibles recommandés

```text
src/execution_backbone/order_decider.py
src/execution_backbone/fill_tracker.py
src/execution_backbone/execution_cost_meter.py
src/execution_backbone/reconciliation_layer.py
```

## Si la stratégie dépend du timing ou du coût

Alors elle doit brancher au minimum :

- coût attendu
- coût réalisé
- fill latency
- no-trade d’exécution
- partial fill impact

## Logs obligatoires

- `expected_cost_computed`
- `expected_break_even_computed`
- `trade_refused_by_execution_cost`
- `partial_fill_detected`
- `execution_fragility_warning`
- `local_vs_exchange_reconciliation_gap`

## Tests obligatoires

- la stratégie ne force jamais l’exécution si `expected_cost` détruit l’edge
- logs coûts présents
- pas de divergence silencieuse état local/exchange

## Interdictions

- exécution parfaite simulée
- coût nul
- latence nulle

---

# 8. Build-4 — Risk Backbone
## Rôle stratégique

Le risk backbone décide si la stratégie a **le droit** d’exister dans le portefeuille.

## Ce qu’une nouvelle stratégie peut toucher ici

- caps spécifiques de concentration
- nouveau mapping de cluster
- budget BTC/facteur
- politique de re-entry marginale
- borne de position pour une variante plus agressive

## Fichiers cibles recommandés

```text
src/risk_backbone/exposure_budgeter.py
src/risk_backbone/loss_budgeter.py
src/risk_backbone/btc_factor_guard.py
src/risk_backbone/correlation_cluster_guard.py
```

## Quand toucher Build-4

Seulement si la stratégie modifie réellement :

- l’exposition projetée
- la perte planifiée
- le facteur BTC caché
- la corrélation cluster

## Logs obligatoires

- `trade_refused_by_exposure_budget`
- `trade_refused_by_loss_budget`
- `btc_factor_overuse_detected`
- `cluster_concentration_refused`
- `reentry_marginal_risk_excessive`

## Tests obligatoires

- la stratégie ne contourne pas les caps via plusieurs petites positions
- concentration cachée détectée
- refus explicite journalisé

---

# 9. Build-5 — Scoring Backbone
## Rôle stratégique

C’est ici que la stratégie devient une **décision lisible**.

## Ce qu’une nouvelle stratégie touche presque toujours ici

- `raw_score_builder`
- `penalty_aggregator`
- `hard_block_gate`
- `ranking_router`

## Fichiers cibles recommandés

```text
src/scoring_backbone/raw_score_builder.py
src/scoring_backbone/penalty_aggregator.py
src/scoring_backbone/hard_block_gate.py
src/scoring_backbone/ranking_router.py
```

## Règle de design

- le score brut décrit la qualité du signal
- les pénalités décrivent la prudence graduelle
- les hard blockers restent fatals et rares
- le ranking compare les opportunités survivantes

## Logs obligatoires

- `raw_score_computed`
- `score_components_breakdown`
- `penalty_applied`
- `hard_block_triggered`
- `ranking_position_assigned`
- `phantom_trade_detected`

## Tests obligatoires

- score reproductible
- pénalités non binaires sauf cas fatal
- hard blockers réservés aux risques fatals
- ranking cohérent avec coût/CE/portefeuille

## Interdictions

- transformer les soft penalties en veto cachés
- faire du ranking “plus gros score brut gagne toujours”

---

# 10. Build-6 — Moteur A
## Portée

Toutes les stratégies classées `A_variant` vivent ici.

## Ce qu’on peut intégrer ici

- pullback structurel premium
- continuation de trend propre
- sortie de compression type A2 si elle reste dans l’esprit A
- reprise de structure après consolidation
- amélioration conviction / invalidation / CE attendue / coût

## Ce qu’on ne doit pas intégrer ici

- breakout autonome qui mérite C
- re-entry autonome qui mérite D
- brique analytique Build-14 déguisée en A

## Fichiers cibles recommandés

```text
src/engines/engine_a/structure_detector_a.py
src/engines/engine_a/context_validator_a.py
src/engines/engine_a/signal_builder_a.py
src/engines/engine_a/invalidation_logic_a.py
src/engines/engine_a/cost_guard_a.py
src/engines/engine_a/tier_router_a.py
src/engines/engine_a/version_registry_a.py
```

## Logs obligatoires

- `engine_a_candidate_created`
- `engine_a_structure_favorable`
- `engine_a_context_degraded`
- `engine_a_cost_refusal`
- `engine_a_ce_estimate`
- `engine_a_tier_proposed`
- `engine_a_no_trade_reason`

## Tests obligatoires

- signal lisible
- invalidation compréhensible
- non-régression sur A existant
- non-duplication évidente avec C
- refus si coût trop élevé

## Dossier tests conseillé

```text
tests/test_engine_a/
├── test_structure_detector_a.py
├── test_context_validator_a.py
├── test_signal_builder_a.py
├── test_invalidation_logic_a.py
└── test_engine_a_non_regression.py
```

---

# 11. Build-7 — Moteur B
## Portée

Toutes les stratégies classées `B_variant` vivent ici.

## Ce qu’on peut intégrer ici

- nouveau z-score plus robuste
- moyenne locale améliorée
- filtre anti-breakout plus fort
- reversion VWAP/microprice
- exhaustion fade gouvernée

## Pièce critique

Le **filtre anti-breakout** est central. Toute stratégie B doit être capable de dire :

```text
probabilité de continuation hostile > probabilité de reversion exploitable
=> no-trade
```

## Fichiers cibles recommandés

```text
src/engines/engine_b/local_mean_estimator_b.py
src/engines/engine_b/deviation_meter_b.py
src/engines/engine_b/anti_breakout_filter_b.py
src/engines/engine_b/context_guard_b.py
src/engines/engine_b/holding_horizon_guard_b.py
src/engines/engine_b/cost_guard_b.py
src/engines/engine_b/version_registry_b.py
```

## Logs obligatoires

- `engine_b_excess_detected`
- `engine_b_local_mean_estimated`
- `engine_b_anti_breakout_warning`
- `engine_b_reversion_toxic_refusal`
- `engine_b_expected_holding_horizon`
- `engine_b_ce_estimate`
- `engine_b_no_trade_reason`

## Tests obligatoires

- B ne reverte pas aveuglément contre une vraie cassure
- coût petit-edge pris en compte
- durée attendue courte ou raisonnable
- fréquence utile améliorée sans bruit excessif

## Dossier tests conseillé

```text
tests/test_engine_b/
├── test_local_mean_estimator_b.py
├── test_deviation_meter_b.py
├── test_anti_breakout_filter_b.py
├── test_cost_guard_b.py
└── test_engine_b_non_regression.py
```

---

# 12. Build-8 — Portfolio Minimal
## Rôle stratégique

Le portefeuille décide **quelles opportunités gagnent le capital**.

## Ce que les stratégies nouvelles peuvent toucher ici

- arbitrage A vs B
- coût d’opportunité du capital
- CE comparative
- pénalité crowding légère
- refus relatif entre plusieurs opportunités valides

## Fichiers cibles recommandés

```text
src/portfolio_engine/opportunity_selector.py
src/portfolio_engine/allocation_router.py
```

## Exemple de logique acceptable ici

- `CE_weighted_allocator`
- `capital_competition_monitor`
- bonus/malus de diversité effective

## Logs obligatoires

- `opportunity_pool_built`
- `comparative_rank_resolved`
- `relative_rejection_reason`
- `allocation_routed`
- `portfolio_capital_competition_warning`
- `portfolio_crowding_penalty_applied`

## Tests obligatoires

- plusieurs opportunités comparées correctement
- score seul ne suffit pas
- coût/CE/corrélation influencent bien la sélection

---

# 13. Build-9 — Meta Minimal
## Rôle stratégique

Build-9 permet de savoir si une stratégie est **vraiment utile** ou juste “jolie sur le papier”.

## Ce que toute nouvelle stratégie doit brancher ici

- DTR (Decision Trace Record)
- CRA / stérilisation
- break-even réel
- edge tracker prudent

## Fichiers cibles recommandés

```text
src/meta_engine/dtr_core.py
src/meta_engine/cra_monitor.py
src/meta_engine/break_even_dashboard.py
src/meta_engine/edge_tracker_prudent_minimal.py
```

## Logs obligatoires

- `dtr_record_persisted`
- `decision_state_encoded`
- `phantom_trade_flagged`
- `cra_alarm_triggered`
- `break_even_updated`
- `edge_status_updated`

## Tests obligatoires

- chaque décision significative produit un DTR
- refus relatifs et refus fatals distingués
- stratégie audit-ready ex post

---

# 14. Build-10 — Monitoring + UI Light
## Rôle stratégique

Une stratégie n’est pas opérable si on ne voit pas : coût, CE, fréquence utile, dérive, stale, crowding.

## Fichiers cibles recommandés

```text
src/monitoring_ui/metrics_collector.py
src/monitoring_ui/alert_manager.py
src/monitoring_ui/health_dashboard_backend.py
src/monitoring_ui/ui_light_locked.py
```

## Ce qu’une stratégie doit exposer

- fréquence utile par stratégie/variante
- coût moyen / p90
- CE attendue / réalisée
- taux de no-trade
- hit rate des gates
- pair health dépendante
- drawdown local
- causes majeures de refus

## Logs/metrics obligatoires

- `strategy_activation_count`
- `strategy_no_trade_count`
- `strategy_cost_p90`
- `strategy_ce_live_estimate`
- `strategy_dtr_loss_warning`
- `strategy_edge_drift_warning`

---

# 15. Build-11 / 12 / 13 — Shadow / Micro-live / Live-Light
## Rôle stratégique

Ces builds ne redéfinissent pas la stratégie. Ils valident son comportement réel.

## Règle

Une stratégie intégrée dans A/B ne saute **jamais** ces étapes.

## Ce qui doit être vérifié

### Build-11 Shadow
- décisions cohérentes
- exécution shadow prudente
- coûts plausibles
- arbitrage portefeuille propre
- DTR/CRA complets

### Build-12 Micro-live
- coût réel
- fill réel
- réconciliation réelle
- discipline opératoire

### Build-13 Live-Light
- stabilité continue
- crédibilité économique
- gouvernance/rollback

## Fichiers typiques à toucher

```text
src/runtime/shadow_runner.py
src/runtime/micro_live_runner.py
src/runtime/live_light_runner.py
src/runtime/deployment_state_machine.py
```

## Logs obligatoires

- `shadow_decision_recorded`
- `micro_live_cost_observed`
- `live_light_rollback_triggered`
- `strategy_component_promoted_or_dormant`

---

# 16. Build-14 — Complete Enablers
## Portée

Toutes les stratégies classées `Build14_enabler` vivent ici.

## Ce qu’on met ici

- microstructure enrichie
- régime enrichi
- covariance robuste
- contribution marginale au risque
- diversité d’edge enrichie
- timing d’entrée/sortie gouverné

## Fichiers cibles recommandés

```text
src/build14_enablers/microstructure_enriched/spoofing_suspicion_filter.py
src/build14_enablers/microstructure_enriched/liquidity_evaporation_detector.py
src/build14_enablers/microstructure_enriched/market_toxicity_layer.py
src/build14_enablers/regime_enriched/machine_dominated_regime_detector.py
src/build14_enablers/risk_contribution/risk_contribution_monitor.py
src/build14_enablers/edge_diversity/crowding_signature_monitor.py
src/build14_enablers/edge_diversity/conditional_ce_surface.py
src/build14_enablers/timing/micro_edge_entry_timing_layer.py
src/build14_enablers/timing/micro_edge_exit_governor.py
```

## Politique d’introduction obligatoire

### Étape 1
- lecture seule
- monitoring
- aucun impact live direct

### Étape 2
- influence limitée
- pénalité légère
- alerte enrichie
- aide timing/ranking

### Étape 3
- seulement si utilité démontrée

## Logs obligatoires

- `build14_feature_computed`
- `build14_read_only_projection`
- `build14_penalty_light_applied`
- `build14_alert_emitted`
- `build14_cpu_budget_warning`

## Tests obligatoires

- formule explicite
- output contract stable
- aucune création de trade autonome
- non-régression Light
- coût CPU raisonnable

## Interdictions

- moteur autonome caché
- veto hard central immédiat
- bypass moteur/risk/portfolio

---

# 17. Build-15 — Moteur C
## Portée

Toutes les stratégies classées `C_candidate` vivent ici.

## Condition conceptuelle

La stratégie doit prouver qu’elle n’est **pas juste A plus nerveux**.

## Fichiers cibles recommandés

```text
src/engines/engine_c/range_detector_c.py
src/engines/engine_c/breakout_confirmation_c.py
src/engines/engine_c/anti_false_breakout_c.py
src/engines/engine_c/continuation_cost_guard_c.py
src/engines/engine_c/signal_builder_c.py
src/engines/engine_c/version_registry_c.py
```

## Logs obligatoires

- `engine_c_range_identified`
- `engine_c_breakout_confirmed`
- `engine_c_false_breakout_warning`
- `engine_c_cost_refusal`
- `engine_c_non_duplication_review_required`

## Tests obligatoires

- non-duplication avec A
- faux breakout détectable
- coût de breakout supportable
- contribution portefeuille distincte

---

# 18. Build-16 — Moteur D
## Portée

Toutes les stratégies classées `D_candidate` vivent ici.

## Condition conceptuelle

La stratégie doit prouver qu’elle n’est **pas du revenge trading automatisé**.

## Fichiers cibles recommandés

```text
src/engines/engine_d/previous_context_linker_d.py
src/engines/engine_d/reformation_detector_d.py
src/engines/engine_d/marginal_value_guard_d.py
src/engines/engine_d/reentry_concentration_guard_d.py
src/engines/engine_d/signal_builder_d.py
src/engines/engine_d/version_registry_d.py
```

## Logs obligatoires

- `engine_d_prior_context_linked`
- `engine_d_reentry_candidate_created`
- `engine_d_marginal_value_refusal`
- `engine_d_revenge_pattern_rejected`
- `engine_d_concentration_guard_refusal`

## Tests obligatoires

- valeur marginale positive exigée
- non-confusion avec A
- concentration supportable
- pas de cascade de re-entries non gouvernées

---

# 19. Build-17 — UI Complete + Live-Complete
## Rôle stratégique

Build-17 n’est pas l’endroit où on “invente” la stratégie. C’est l’endroit où la stratégie Complete devient supervisable et gouvernable à 12 paires / 4 moteurs.

## Fichiers cibles recommandés

```text
src/monitoring_ui/ui_complete.py
src/monitoring_ui/complete_dashboard_backend.py
src/monitoring_ui/risk_contribution_dashboard.py
src/monitoring_ui/edge_diversity_dashboard.py
src/runtime/live_complete_runner.py
```

## Ce que C/D/Build-14 doivent exposer ici

- contribution marginale
- impact corrélation
- impact CE
- état `SHADOW_ENABLED` / `DORMANT` / `PROMOTED`
- métriques de non-régression Light

---

# 20. LOCAL_REPLAY, artifacts et intégration VPS
## Principe

Le replay local n’est pas une seconde V5.3. Il doit réutiliser le shared core.

## Package local recommandé

```text
src/local_replay_runtime/
├── replay_clock.py
├── historical_data_gateway.py
├── replay_event_router.py
├── shadow_execution_simulator.py
├── replay_metrics_collector.py
├── replay_dtr_exporter.py
├── artifact_exporter.py
└── replay_orchestrator.py
```

## Module VPS d’import recommandé

```text
src/backtest_artifact_import/
├── artifact_validator.py
├── artifact_parser.py
├── artifact_registry.py
├── ui_projection_builder.py
└── meta_projection_builder.py
```

## Règle absolue

Le module d’import :
- valide
- enregistre
- projette

Il ne doit jamais :
- recalculer la stratégie
- exécuter la stratégie
- promouvoir automatiquement vers Shadow/Micro-live/Live

---

# 21. Dossier tests recommandé

```text
tests/
├── test_contracts/
├── test_manifest_registry/
├── test_data_backbone/
├── test_execution_backbone/
├── test_risk_backbone/
├── test_scoring_backbone/
├── test_engine_a/
├── test_engine_b/
├── test_engine_c/
├── test_engine_d/
├── test_portfolio_engine/
├── test_meta_engine/
├── test_monitoring_ui/
├── test_local_replay_runtime/
└── test_backtest_artifact_import/
```

## Batteries à ne jamais oublier

- tests unitaires
- tests de contrats
- tests d’identité logique
- tests anti-fork
- tests de non-régression
- tests de logs structurés
- tests replay vs shadow parity

---

# 22. Format minimal de logs structurés recommandé

## 22.1 Champs communs

```text
ts
run_id
profile_scope
runtime_mode
pair_id
engine_id
strategy_id
strategy_version
module_name
event_type
severity
reason_codes
score_payload_ref
cost_payload_ref
dtr_id
```

## 22.2 Familles de logs par couche

### moteur
- candidat créé
- candidat refusé
- structure favorable/défavorable
- contexte dégradé

### scoring
- score brut
- pénalité
- hard block
- ranking

### risk
- cap atteint
- budget cluster dépassé
- facteur BTC excessif

### execution
- intent créé
- coût attendu
- fill/partial fill
- refus exécution

### portfolio
- sélection relative
- rejet relatif
- allocation finale

### meta
- DTR persisté
- CRA déclenché
- phantom trade
- edge drift

### monitoring
- alerte actionnable
- stale/backlog
- stratégie dormante
- non-régression violée

---

# 23. Checklist ultra simple avant de coder une stratégie

## Étape A — gouvernance
- [ ] classification faite
- [ ] fiche proposal écrite
- [ ] versions définies
- [ ] pas de collision de nommage

## Étape B — build cible
- [ ] build principal identifié
- [ ] modules secondaires impactés identifiés
- [ ] fichiers cibles listés

## Étape C — code
- [ ] shared core uniquement
- [ ] pas de fork PC/VPS
- [ ] output contract audit-ready
- [ ] logs structurés définis

## Étape D — tests
- [ ] unit tests
- [ ] contract tests
- [ ] anti-fork
- [ ] non-régression
- [ ] replay parity

## Étape E — promotion
- [ ] LOCAL_REPLAY
- [ ] artifact export
- [ ] import VPS
- [ ] revue de valeur marginale
- [ ] candidature contrôlée seulement ensuite

---

# 24. Résumé exécutif

La bonne règle n’est pas :

> nouvelle stratégie = nouveau build

La bonne règle est :

> nouvelle stratégie = **classification d’abord**, puis **intégration dans le build canonique correspondant**.

Donc :

- idée trend premium -> **Build-6**
- idée mean reversion -> **Build-7**
- brique analytique enrichie -> **Build-14**
- breakout autonome distinct -> **Build-15**
- re-entry autonome distinct -> **Build-16**
- le reste -> **hors scope V5.3**

Et à chaque fois :

> documentation -> classification -> versioning -> shared core -> tests -> LOCAL_REPLAY -> gouvernance -> promotion éventuelle

---

# 25. Modèle de prompt court pour travailler build par build

```text
On traite la stratégie suivante selon le canon V5.3.

1. Classifie-la entre A_variant / B_variant / Build14_enabler / C_candidate / D_candidate / out_of_scope_for_V5_3.
2. Donne le build principal cible.
3. Donne les modules secondaires impactés.
4. Donne les fichiers exacts à créer/modifier dans l’arborescence canonique.
5. Donne les logs structurés obligatoires.
6. Donne les tests obligatoires.
7. Donne les interdictions et risques de duplication.
8. Donne l’ordre d’intégration : shared core -> tests -> LOCAL_REPLAY -> artifact -> import VPS.

Pas de nouveau moteur hors A/B/C/D.
Pas de nouveau profil.
Pas de fork PC/VPS.
Pas de promotion live implicite.
```

