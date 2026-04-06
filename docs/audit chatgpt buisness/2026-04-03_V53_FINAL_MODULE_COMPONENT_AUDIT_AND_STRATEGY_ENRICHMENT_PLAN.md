# V5.3 - PLAN FINAL D'AUDIT MODULE PAR MODULE ET COMPOSANT PAR COMPOSANT
## Date : 2026-04-03
## Branche : `codex/full-shadow-abcd-migration-20260403`
## Statut : ACTIVE

---

# 0. Objet

Ce document fixe le **plan de deep work final** pour :

1. auditer la composition détaillée de chaque module et de chaque composant de V5.3
2. vérifier ce que chaque brique permet réellement pour la création de stratégies
3. identifier où enrichir la solution sans casser le canon
4. éviter de sauter une étape, un module, une dépendance, un garde-fou ou un composant

Ce plan n’est pas un re-audit “from scratch”.

C’est un **plan d’audit orienté stratégie + enrichissement**, guidé par trois besoins :

- exploiter toute la capacité réelle de V5.3
- enrichir proprement chaque composant utile
- ne jamais oublier une brique critique de sécurité, de coût, de gouvernance ou d’opérabilité

---

# 1. Règles de lecture et discipline anti-hallucination

## 1.1 Sources de vérité

Sources canoniques prioritaires :

1. `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
2. `docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
4. `docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`
5. `docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md`
6. `docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
7. `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`

Sources de structure détaillée :

- `docs/specs/V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md`
- `docs/specs/V5_3_TABLE_DETAILLEE_MOTEURS.md`
- `src/manifest_registry/module_inventory.py`

Sources de réalité branche actuelle :

- `docs/audit chatgpt buisness/2026-04-03_BUILD1_TO_BUILD17_CLOSURE_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_MEMORY.json`
- `docs/audit chatgpt buisness/2026-04-04_BUILD11_TARGET_ENV_CAMPAIGN_DAY2_BLOCKED_WEBSOCKET_CONNECT_AUDIT.md`

## 1.2 Règles non négociables

- ne jamais créer de profils hors `LIGHT` et `COMPLETE`
- ne jamais créer de moteurs hors A/B/C/D sans demande explicite
- ne jamais court-circuiter `SHADOW`, `MICRO_LIVE` ou `LIVE`
- ne jamais confondre “codé” avec “fermé”
- ne jamais enrichir un moteur ou un reader sans mesurer :
  - coût
  - CE
  - risque
  - effet portefeuille
  - opérabilité

## 1.3 Règle de travail

Chaque composant devra être relu selon la même grille :

1. rôle exact
2. inputs
3. outputs
4. équations et métriques
5. seuils et hard blockers
6. dépendances autorisées
7. logs obligatoires
8. tests obligatoires
9. usage stratégique possible
10. angle mort
11. enrichissement possible
12. risque d’enrichissement

---

# 2. But final de cet audit

L’objectif n’est pas seulement documentaire.

Le but est de construire un **cadre de création de stratégies et d’enrichissement système** qui permette ensuite de répondre proprement à des questions comme :

- quelles nouvelles variantes de A ou B sont légitimes ?
- quelles extensions doivent vivre dans Build-14 plutôt que dans un moteur ?
- quel enrichissement appartient à C ou à D ?
- quels composants sont suffisamment matures pour être utilisés dans une stratégie plus ambitieuse ?
- quels composants doivent rester `READ_ONLY`, `SHADOW_ENABLED` ou `DORMANT` ?

Ce plan est donc le chaînon entre :

- l’architecture V5.3 existante
- le futur enrichissement stratégique
- l’audit continu de cohérence

---

# 3. Matrice de couverture anti-oubli

## 3.1 Modules canoniques à auditer sans exception

### Build-1

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`

### Build-2

- `data_backbone`

### Build-3

- `execution_backbone`

### Build-4

- `risk_backbone`

### Build-5

- `scoring_backbone`

### Build-6

- `engine_a`

### Build-7

- `engine_b`

### Build-8

- `portfolio`

### Build-9

- `meta`

### Build-9X

- `meta_learning`

### Build-10

- `monitoring`
- `ui`

### Build-11 à Build-13

- `protocols`

### Build-14

- `complete_enablers`

### Build-15

- `engine_c`

### Build-16

- `engine_d`

### Build-17

- runtime/surfaces Complete de `ui`, `monitoring`, `protocols`

## 3.2 Sous-composants canoniques à ne pas oublier

### DATA_ENGINE

- `websocket_gateway`
- `rest_bootstrap`
- `event_normalizer`
- `internal_router`

### DATA_QUALITY_ENGINE

- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`

### MICROSTRUCTURE_ENGINE

- `ofi_calculator`
- `book_imbalance`
- `microprice_estimator`
- `persistence_filter`

### REGIME_ENGINE

- `regime_classifier_simple`
- `hmm_regime_layer`
- `regime_confidence`

### SIGNAL_ENGINE

- `moteur_A_premium_trend`
- `moteur_B_mean_reversion`
- `moteur_C_breakout`
- `moteur_D_reentry`

### SCORING_ENGINE

- `raw_score_builder`
- `penalty_aggregator`
- `hard_block_gate`
- `ranking_router`

### RISK_ENGINE

- `exposure_budgeter`
- `loss_budgeter`
- `btc_factor_guard`
- `correlation_cluster_guard`
- `kelly_guard_prudent`

### EXECUTION_ENGINE

- `order_decider`
- `fill_tracker`
- `execution_cost_meter`
- `reconciliation_layer`

### PORTFOLIO_ENGINE

- `opportunity_selector`
- `allocation_router`
- `risk_contribution_monitor`
- `effective_edge_diversity`

### MONITORING_ENGINE

- `metrics_collector`
- `alert_manager`
- `health_dashboard_backend`

### META_ENGINE

- `dtr_core`
- `cra_monitor`
- `amd_monitor`
- `edge_tracker_prudent`
- `break_even_dashboard`

### DEPENDENCY_ARCHITECTURE

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`

### UI_CONSOLE

- `profile_selector`
- `deployment_state_panel`
- `pair_activation_panel`
- `engine_status_panel`
- `risk_override_panel`

### BUILD-14 readers et influence

- `market_toxicity_snapshot`
- `execution_fragility_score`
- `lob_deep_filter_vwa`
- `order_book_imbalance`
- `false_breakout_model`
- `hurst_regime_classifier`
- `competition_monitor`
- `limited_influence`

### BUILD-9X gouvernance

- `diagnostics`
- `hypotheses`
- `candidates`
- `replay_bundle_builder`
- `learning_review_exporter`
- `review_orchestrator`
- `merge_gates`
- `capacity_guard`
- `persistence_store`

### BUILD-11/12/13 protocoles

- `shadow_runtime`
- `shadow_day_counter`
- `shadow_report_builder`
- `shadow_daily_orchestrator`
- `shadow_vps_service`
- `micro_live_runtime`
- `live_light_runtime`
- dashboards/projections associés

---

# 4. Ordre de travail recommandé

## 4.1 Phase A - Freeze de la cartographie

Objectif :

- figer la liste des modules et sous-composants canoniques
- figer la liste des builds fermés / ouverts
- figer la hiérarchie documentaire

Sortie attendue :

- registre maître modules/components
- registre maître builds ouverts/fermés

## 4.2 Phase B - Delta audit des builds déjà fermés

Builds à vérifier rapidement seulement :

- `1`
- `2`
- `3`
- `5`
- `6`
- `7`
- `8`
- `9`
- `9x`
- `10`
- `14`

Objectif :

- confirmer qu’aucune régression récente ne les a rouverts
- ne pas perdre du temps à réouvrir inutilement ce qui est déjà `ALIGNED`

Sortie attendue :

- confirmation `keep frozen`
- ou alerte de régression localisée

## 4.3 Phase C - Audit profond des builds ouverts

Builds à traiter en profondeur :

- `Build-4`
- `Build-11`
- `Build-12`
- `Build-13`
- `Build-15`
- `Build-16`
- `Build-17`

Objectif :

- identifier exactement ce qui bloque
- distinguer :
  - `code`
  - `tests`
  - `runtime`
  - `ops`
  - `governance`

Sortie attendue :

- plan minimal de fermeture par build

## 4.4 Phase D - Audit composant par composant pour usage stratégique

Objectif :

- relire chaque composant sous l’angle “que permet-il pour créer ou enrichir une stratégie ?”

Questions obligatoires pour chaque composant :

1. apporte-t-il du filtrage, du signal, du sizing, du risque, de l’observabilité ou de la gouvernance ?
2. son effet est-il déjà borné ou autonome ?
3. sa sortie est-elle directement actionnable ou seulement informative ?
4. quelles métriques permettent de savoir s’il aide ou s’il stérilise ?
5. peut-il servir A, B, C, D ou seulement Build-14 ?

## 4.5 Phase E - Audit enrichissement

Objectif :

- déterminer, pour chaque composant, si l’on doit :
  - `conserver`
  - `durcir`
  - `enrichir`
  - `shadow-only`
  - `dormant`
  - `refactorer`
  - `rejeter`

Sortie attendue :

- matrice d’enrichissement par composant

## 4.6 Phase F - Audit stratégie-capacité

Objectif :

- cartographier comment exploiter **toute la capacité réelle** de V5.3 pour créer des stratégies ou variantes

Les nouvelles stratégies devront être classées dans l’un des bacs suivants :

- `A_variant`
- `B_variant`
- `Build14_enabler`
- `C_candidate`
- `D_candidate`
- `out_of_scope_for_V5_3`

Sortie attendue :

- protocole d’onboarding stratégie propre et non ambigu

---

# 5. Plan détaillé par famille de modules

## 5.1 Fondations structurelles

Modules :

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`

Questions :

- le langage métier est-il encore cohérent ?
- une nouvelle stratégie peut-elle être onboardée sans créer de dette structurelle ?
- les manifests, imports et contracts empêchent-ils vraiment les dérives ?

Intérêt stratégique :

- sans socle structurel sain, tout enrichissement futur devient dangereux

## 5.2 Donnée, qualité, microstructure, régime

Modules / familles :

- `data_backbone`
- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`
- `ofi_calculator`
- `book_imbalance`
- `microprice_estimator`
- `persistence_filter`
- `regime_classifier_simple`
- `hmm_regime_layer`
- `regime_confidence`

Questions :

- quelles lectures de marché sont déjà réellement disponibles ?
- lesquelles servent au trading réel ?
- lesquelles sont encore des proxys ou des surfaces partielles ?
- quels composants sont utiles pour enrichir A/B/C/D ?

Intérêt stratégique :

- cette famille détermine si la stratégie lit vraiment le marché, ou seulement des prix et des heuristiques pauvres

## 5.3 Signal, scoring, risque, portefeuille

Modules / familles :

- `signal_engine`
- `scoring_backbone`
- `risk_backbone`
- `portfolio`

Questions :

- où naît réellement la sélection ?
- qu’est-ce qui bloque trop ?
- qu’est-ce qui ne bloque pas assez ?
- comment la stratégie passe du “possible” au “retenu” ?
- où enrichir sans casser l’économie ?

Intérêt stratégique :

- cette famille est le coeur de la monétisabilité de V5.3

## 5.4 Exécution et vérité économique

Modules / familles :

- `execution_backbone`
- `meta`
- `break_even_dashboard`
- `cra_monitor`
- `edge_tracker_prudent`

Questions :

- comment la solution mesure-t-elle le coût réel ?
- comment détecte-t-elle les faux gains ?
- comment mesure-t-elle la stérilisation ?
- comment mesurer l’utilité réelle d’un enrichissement futur ?

Intérêt stratégique :

- toute nouvelle stratégie devra survivre à cette vérité économique

## 5.5 Learning gouverné

Modules / familles :

- `meta_learning`
- `merge_gates`
- `capacity_guard`
- `review_orchestrator`
- `replay_bundle_builder`
- `learning_review_exporter`

Questions :

- le système sait-il produire des hypothèses utiles sans auto-mutant live ?
- sait-il bloquer les mauvaises propositions ?
- les gates sont-elles réellement exploitables pour enrichir V5.3 proprement ?

Intérêt stratégique :

- c’est la couche qui transformera l’audit en pipeline d’enrichissement contrôlé

## 5.6 Monitoring, UI, supervision, opérabilité

Modules / familles :

- `monitoring`
- `ui`
- dashboards locaux
- user-data / market lab
- projections techniques
- operator safing

Questions :

- qu’est-ce qui est vraiment live ?
- qu’est-ce qui est artifact-backed ?
- quelles métriques manquent pour piloter une stratégie enrichie ?
- quels panneaux devront exister en futur Grafana ?

Intérêt stratégique :

- sans supervision honnête, les enrichissements futurs deviennent inpilotables

## 5.7 Protocoles Build-11/12/13

Modules / familles :

- `shadow_runtime`
- `shadow_day_counter`
- `shadow_report_builder`
- `shadow_daily_orchestrator`
- `shadow_vps_service`
- `micro_live_runtime`
- `live_light_runtime`

Questions :

- quelle preuve faut-il vraiment produire pour passer de l’idée au rollout réel ?
- quels composants sont déjà pleinement observés ?
- quels enrichissements doivent rester `SHADOW_ENABLED` seulement ?

Intérêt stratégique :

- cette famille fixe le pipeline réel d’activation d’une future stratégie enrichie

## 5.8 Enablers Build-14

Composants :

- `market_toxicity_snapshot`
- `execution_fragility_score`
- `lob_deep_filter_vwa`
- `order_book_imbalance`
- `false_breakout_model`
- `hurst_regime_classifier`
- `competition_monitor`
- `limited_influence`

Questions :

- quel reader aide vraiment ?
- lequel stérilise ?
- lequel doit rester purement `SHADOW_ENABLED` ?
- lequel peut un jour devenir `READ_ONLY` ou `LIMITED_INFLUENCE` après preuve ?

Intérêt stratégique :

- cette famille est la principale réserve d’enrichissement prudent de V5.3

## 5.9 Moteurs C et D

Modules :

- `engine_c`
- `engine_d`

Questions :

- sont-ils réellement distincts de A/B ?
- apportent-ils un edge différent ou seulement une duplication ?
- que leur manque-t-il pour passer de `STILL_PARTIAL` à `ALIGNED` ?

Intérêt stratégique :

- ils représentent la capacité d’extension réelle de la solution, au-delà du socle initial

## 5.10 Surface Complete

Build :

- `Build-17`

Questions :

- que manque-t-il pour une vraie supervision Complete ?
- que faut-il pour afficher l’état complet sans illusion de fermeture ?
- quels composants supplémentaires devront exister avant une vraie phase `Live-Complete` ?

---

# 6. Modèle d’audit à appliquer à chaque composant

Pour chaque composant, produire obligatoirement les rubriques suivantes :

1. **Nom canonique**
2. **Build**
3. **Rôle exact**
4. **Type**
   - structure
   - data
   - signal
   - scoring
   - risk
   - execution
   - portfolio
   - meta
   - governance
   - UI/monitoring
5. **Inputs**
6. **Outputs**
7. **Équations / métriques**
8. **Seuils / blockers**
9. **Dépendances**
10. **Logs obligatoires**
11. **Tests obligatoires**
12. **Usage stratégique actuel**
13. **Capacité d’enrichissement**
14. **Risque d’enrichissement**
15. **Angles morts**
16. **État réel sur la branche**
17. **Action recommandée**

---

# 7. Plan d’exécution concret

## Lot 0 - Freeze du registre

Produire :

- inventaire final modules / composants
- matrice builds fermés / ouverts
- liste des sources canoniques à respecter

## Lot 1 - Audit structurel fondations

Périmètre :

- Build-1
- Build-2
- Build-3
- Build-4
- Build-5

But :

- prouver que le socle est prêt à supporter un enrichissement stratégie

## Lot 2 - Audit stratégie coeur

Périmètre :

- A
- B
- portfolio
- meta

But :

- comprendre ce que le coeur de V5.3 sait réellement monétiser aujourd’hui

## Lot 3 - Audit learning et gouvernance

Périmètre :

- Build-9X
- replay/import
- merge gates

But :

- préparer le pipeline d’enrichissement sans dérive

## Lot 4 - Audit supervision et opérabilité

Périmètre :

- monitoring
- UI
- account/user-data
- market lab
- opérateur safing

But :

- préparer un pilotage sûr des futurs enrichissements

## Lot 5 - Audit protocoles rollout

Périmètre :

- Build-11
- Build-12
- Build-13

But :

- comprendre la vérité réelle de passage Shadow -> Micro-live -> Live

## Lot 6 - Audit enrichissements Build-14

Périmètre :

- tous les readers Build-14

But :

- distinguer ce qui aide, ce qui stérilise, ce qui doit rester borné

## Lot 7 - Audit extensions C et D

Périmètre :

- Build-15
- Build-16

But :

- savoir si ces moteurs méritent vraiment une fermeture et une future activation

## Lot 8 - Audit surface Complete

Périmètre :

- Build-17

But :

- préparer proprement l’avenir Complete sans halluciner un état déjà fermé

---

# 8. Ordre recommandé pour ne rien oublier

Ordre strict recommandé :

1. freeze inventaire
2. delta audit builds fermés
3. audit profond des builds ouverts
4. audit composant par composant
5. audit usage stratégique
6. audit enrichissement possible
7. matrice de priorisation
8. seulement après, démarrage des vrais enrichissements

Ordre des familles :

1. structure
2. donnée
3. risque
4. scoring
5. moteurs A/B
6. portefeuille
7. meta
8. learning gouverné
9. monitoring/UI
10. protocoles rollout
11. Build-14
12. C
13. D
14. Complete

---

# 9. Critères de sortie de ce plan

Le plan sera considéré réussi si nous obtenons :

1. un registre complet des modules et sous-composants
2. un audit détaillé sans trou de couverture
3. une matrice claire :
   - `à conserver`
   - `à durcir`
   - `à enrichir`
   - `à laisser shadow-only`
   - `à laisser dormant`
   - `à refactorer`
   - `à rejeter`
4. une cartographie claire de ce qui peut servir à créer de nouvelles stratégies
5. une feuille de route d’enrichissement sans double travail ni oubli de composant

---

# 10. Conclusion

La bonne manière de créer de nouvelles stratégies avec toute la capacité de V5.3 n’est pas :

- d’empiler des idées
- de coder vite
- d’ajouter des readers ou moteurs “par intuition”

La bonne manière est :

- auditer d’abord toute la capacité réelle du système
- comprendre le rôle exact de chaque composant
- distinguer les briques de signal, de filtre, de risque, de portefeuille, de supervision et de gouvernance
- puis enrichir seulement composant par composant, avec preuve et discipline

Ce plan existe précisément pour éviter :

- l’oubli d’une brique
- le double travail
- la dérive doctrinale
- la création de stratégies incompatibles avec l’architecture V5.3

