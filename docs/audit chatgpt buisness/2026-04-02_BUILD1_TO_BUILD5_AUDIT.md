# V5.3 — AUDIT BUILD-1 À BUILD-5
## Date : 2026-04-02
## Statut : ACTIF

---

# 0. Objet

Ce document enregistre l'audit critique du socle commun :

- Build-1
- Build-2
- Build-3
- Build-4
- Build-5

Méthode :

- lecture des specs canoniques Build-1 à Build-5
- cartographie des surfaces code
- exécution des suites de tests ciblées
- classement des écarts en `P0 / P1 / P2`

---

# 1. Résumé exécutif

Verdict provisoire du lot :

- Build-1 : `STILL PARTIAL`
- Build-2 : `ALIGNED`
- Build-3 : `ALIGNED`
- Build-4 : `STILL PARTIAL`
- Build-5 : `ALIGNED`

Lecture courte :

- le socle data / execution / scoring tient bien
- le risk backbone canonique tient globalement, mais une partie de la suite reste perturbée par un problème d'environnement de test sur `tmp_path`
- le vrai point rouge du lot est Build-1 : le DAG global du dépôt ne passe plus, avec des imports non autorisés entre modules récents

---

# 2. Évidence exécutée

## 2.1 Lecture canonique

Documents relus :

- `docs/specs/V5_3_BUILD1_SPECS_MODULES.md`
- `docs/specs/V5_3_BUILD2_SPECS_MODULES.md`
- `docs/specs/V5_3_BUILD3_SPECS_MODULES.md`
- `docs/specs/V5_3_BUILD4_SPECS_MODULES.md`
- `docs/specs/V5_3_BUILD5_SPECS_MODULES.md`

## 2.2 Cartographie code

Surfaces confirmées :

- `src/interface_contracts`
- `src/manifest_registry`
- `src/dag_validator`
- `src/contract_test_suite`
- `src/smoke_bootstrap_recovery`
- `src/data_backbone`
- `src/execution_backbone`
- `src/risk_backbone`
- `src/scoring_backbone`

## 2.3 Tests exécutés

- `rtk pytest tests/test_interface_contracts tests/test_manifest_registry tests/test_dag_validator tests/test_contract_test_suite tests/test_smoke_bootstrap_recovery -q`
  - résultat : `389 passed, 6 failed`
- `pytest tests/test_dag_validator/test_report_and_pipeline.py::TestFullPipeline::test_v53_codebase_passes_validation -q`
  - résultat : `1 failed`
- `pytest tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py::TestFullBuild1Smoke::test_build1_smoke_passes -q`
  - résultat : `1 failed`
- `rtk pytest tests/test_data_backbone -q`
  - résultat : `164 passed`
- `rtk pytest tests/test_execution_backbone -q`
  - résultat : `110 passed`
- `pytest tests/test_risk_backbone -q`
  - résultat : `127 passed, 14 errors`
  - cause observée : `PermissionError` sur création/scan du répertoire temporaire `pytest`
- `rtk pytest tests/test_scoring_backbone -q`
  - résultat : `117 passed`

---

# 3. Findings

## P0 — Build-1 DAG global cassé dans l'état courant du dépôt

Preuve :

- `tests/test_dag_validator/test_report_and_pipeline.py::TestFullPipeline::test_v53_codebase_passes_validation` échoue
- `tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py::TestFullBuild1Smoke::test_build1_smoke_passes` échoue

Erreur centrale observée :

- `local_replay_runtime` importe `meta` alors que cette dépendance n'est pas autorisée par `manifest_registry.dependency_registry`
- `protocols` importe `local_replay_runtime` alors que cette dépendance n'est pas autorisée non plus

Traces code relevées :

- `src/manifest_registry/dependency_registry.py`
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/shadow_runtime_evidence.py`
- `src/protocols/shadow_websocket_ingest.py`

Lecture critique :

- ce n'est pas un faux positif de test unitaire isolé
- c'est une régression de la validation architecturale globale
- Build-1 ne peut donc pas être déclaré aligné dans l'état courant de la branche

Owner probable :

- soit `dependency_registry` est devenu trop strict / incomplet pour l'architecture actuelle
- soit des modules récents ont traversé une frontière d'architecture non autorisée

Décision :

- ne pas corriger à l'aveugle
- traiter ce point comme un arbitrage d'architecture inter-builds avant tout verdict vert sur Build-1

## P2 — Build-4 package-level test gap sur la suite `test_circuit_breaker`

Preuve :

- `pytest tests/test_risk_backbone -q` retourne `127 passed, 14 errors`
- les erreurs ne pointent pas vers une assertion métier du risk backbone canonique
- elles viennent d'un `PermissionError` lié à `tmp_path` / `pytest-of-azizbez`

Lecture critique :

- les modules canoniques Build-4 semblent passer :
  - `btc_factor_guard`
  - `correlation_cluster_guard`
  - `exposure_budgeter`
  - `loss_budgeter`
- mais la suite package-level n'est pas propre
- le sous-ensemble `emergency_kill_switch / circuit_breaker` n'est pas revalidé proprement dans cet environnement

Décision :

- ne pas classer Build-4 comme totalement vert
- garder `STILL PARTIAL` avec caveat environnemental/test sur le kill switch

---

# 4. Verdict par build

## 4.1 Build-1 — Dependency Architecture

Verdict :

- `STILL PARTIAL`

Pourquoi :

- les briques canoniques existent bien :
  - `interface_contracts`
  - `manifest_registry`
  - `dag_validator`
  - `contract_test_suite`
  - `smoke_bootstrap_recovery`
- mais le DAG global du dépôt échoue sur des dépendances non autorisées
- le smoke Build-1 hérite de cet échec

Conclusion :

- Build-1 est régressé au niveau architectural global

## 4.2 Build-2 — Data Backbone

Verdict :

- `ALIGNED`

Pourquoi :

- les 7 briques canoniques existent bien dans `src/data_backbone`
- la suite ciblée passe : `164 passed`
- la structure racine du package correspond à la spec :
  - `websocket_gateway`
  - `rest_bootstrap`
  - `event_normalizer`
  - `internal_router`
  - `freshness_checker`
  - `consistency_checker`
  - `pair_health_scorer`

Conclusion :

- aucun écart majeur observé sur le périmètre Build-2

## 4.3 Build-3 — Execution Backbone

Verdict :

- `ALIGNED`

Pourquoi :

- les 4 briques canoniques existent bien dans `src/execution_backbone`
- la suite ciblée passe : `110 passed`
- la structure racine du package correspond à la spec :
  - `order_decider`
  - `fill_tracker`
  - `execution_cost_meter`
  - `reconciliation_layer`

Conclusion :

- Build-3 ressort propre dans ce lot d'audit

## 4.4 Build-4 — Risk Backbone

Verdict :

- `STILL PARTIAL`

Pourquoi :

- les briques canoniques Build-4 sont présentes :
  - `exposure_budgeter`
  - `loss_budgeter`
  - `btc_factor_guard`
  - `correlation_cluster_guard`
- les tests métier canoniques passent visiblement
- mais la suite package-level n'est pas entièrement propre à cause des erreurs sur `test_circuit_breaker`

Conclusion :

- Build-4 n'est pas classé rouge métier
- mais il n'est pas assez net pour un verdict `ALIGNED` complet dans cet environnement

## 4.5 Build-5 — Scoring Backbone

Verdict :

- `ALIGNED`

Pourquoi :

- les 4 briques canoniques existent bien dans `src/scoring_backbone`
- la suite ciblée passe : `117 passed`
- la structure racine du package correspond à la spec :
  - `raw_score_builder`
  - `penalty_aggregator`
  - `hard_block_gate`
  - `ranking_router`

Conclusion :

- Build-5 ressort propre dans ce lot d'audit

---

# 5. Lecture transversale

Le lot Build-1 -> Build-5 raconte quelque chose de clair :

- les backbones métier du socle commun sont globalement en bon état
- la plus forte dette visible n'est pas dans la logique data/execution/scoring
- elle est dans la cohérence de l'architecture déclarative elle-même :
  - le dépôt a évolué
  - mais le DAG déclaré n'est plus cohérent avec toutes les dépendances réelles

Autrement dit :

- le socle technique utile tient
- le garde-fou Build-1 qui doit empêcher la dérive d'architecture n'est plus propre

---

# 6. Actions recommandées

## Action 1

Ouvrir un audit ciblé Build-1 sur :

- `src/manifest_registry/dependency_registry.py`
- `src/local_replay_runtime/*`
- `src/protocols/*`

Question à trancher :

- faut-il autoriser explicitement certaines dépendances devenues canoniques
- ou faut-il découpler le code pour revenir au DAG déclaré

## Action 2

Traiter Build-4 `circuit_breaker` comme point séparé :

- vérifier si le problème est seulement environnemental
- ou si le kill switch a besoin d'une révision de ses tests / fixtures

## Action 3

Passer ensuite au lot `Build-6 -> Build-10`, sans oublier que le verdict global Build-1 reste bloquant au niveau architectural

---

# 7. Décision de lot

Décision retenue après audit :

- Build-1 : ne pas déclarer aligné
- Build-2 : aligné
- Build-3 : aligné
- Build-4 : partiel avec caveat test/environnement
- Build-5 : aligné
