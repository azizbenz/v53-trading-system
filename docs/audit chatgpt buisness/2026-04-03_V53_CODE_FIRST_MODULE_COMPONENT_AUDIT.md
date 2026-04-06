# 2026-04-03 - V5.3 code-first audit des modules et composants

## Objet

Ce document est un audit **strictement a partir du code** de V5.3.

Objectif:
- lister les familles reelles presentes dans `src/`
- decomposer les composants visibles dans le code
- documenter pour chaque composant:
  - `role`
  - `in`
  - `out`
  - `id`
  - `log`

Ce document **ne reconstruit pas** l'architecture depuis les MD comme source primaire.
Les MD canoniques restent utiles pour comparer et enrichir, mais ici la source de verite est:
- `src/manifest_registry/module_inventory.py`
- les packages reels dans `src/`
- les `__init__.py`
- les contrats `contracts.py`
- les runtimes et builders exposes

## Methode

Regles appliquees:
- `code-first`: seules les surfaces confirmees dans `src/` sont declarees comme existantes.
- `honnetete de surface`: quand un composant est canonique dans les MD mais n'apparait pas comme package ou contrat distinct, il est note comme `implicite` ou `non isole`.
- `IDs`: on ne retient que les identifiants, correlation IDs, refs, alert IDs, request IDs, order IDs ou champs de lineage effectivement visibles dans le code.
- `Logs`: on ne retient que les surfaces de preuve reelles:
  - `structured_log_key`
  - `alert_id`
  - evenements structures
  - refs d'artefacts/evidence
  - projections monitoring/UI

## Inventaire reel confirme dans `src/`

Modules/familles presents:
- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`
- `data_backbone`
- `execution_backbone`
- `risk_backbone`
- `scoring_backbone`
- `engine_a`
- `engine_b`
- `engine_c`
- `engine_d`
- `engines.engine_a`
- `engines.engine_b`
- `engines.engine_c`
- `engines.engine_d`
- `portfolio_minimal`
- `portfolio`
- `meta_minimal`
- `meta`
- `meta_learning`
- `local_replay_runtime`
- `backtest_artifact_import`
- `monitoring`
- `ui`
- `protocols`
- `complete_enablers`

## Lecture rapide par build

| Build | Module reel | Presence code | Observation |
| --- | --- | --- | --- |
| 1 | `interface_contracts`, `manifest_registry`, `dag_validator`, `contract_test_suite`, `smoke_bootstrap_recovery` | oui | socle contractuel et architecture |
| 2 | `data_backbone` | oui | pipeline data + qualite + sante paire |
| 3 | `execution_backbone` | oui | execution mesurable et reconciliee |
| 4 | `risk_backbone` | oui | budgets/guards/kill path |
| 5 | `scoring_backbone` | oui | hard/soft/rank runtime |
| 6 | `engine_a` + `engines.engine_a` | oui | facade canonique + implementation |
| 7 | `engine_b` + `engines.engine_b` | oui | facade canonique + implementation |
| 8 | `portfolio_minimal` | oui | selection/allocation Light |
| 9 | `meta_minimal` | oui | DTR/CRA/break-even/edge |
| 9X | `meta_learning` | oui | gouvernance learning explicite |
| 10 | `local_replay_runtime`, `backtest_artifact_import`, `monitoring`, `ui` | oui | replay/import + supervision |
| 11-13 | `protocols` | oui | Shadow / Micro-live / Live-Light |
| 14 | `complete_enablers` | oui | readers/enablers gouvernes |
| 15 | `engine_c` + `engines.engine_c` | oui | moteur code-backed |
| 16 | `engine_d` + `engines.engine_d` | oui | moteur code-backed |
| 17 | pas de package runtime dedie `live_complete` | partiel | surface UI Complete presente, fermeture runtime non isolee en module distinct |

---

## Build-1 - Architecture, contrats et bootstrap

### 1. `interface_contracts`

Sources observees:
- `src/interface_contracts/domain_types.py`
- `src/interface_contracts/decision_contracts.py`
- `src/interface_contracts/market_event_contracts.py`
- `src/interface_contracts/meta_contracts.py`
- `src/interface_contracts/error_contracts.py`
- `src/interface_contracts/operator_contracts.py`
- `src/interface_contracts/atomic_io.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `domain_types` | langage metier canonique transverse | enums, types de profil, runtime mode, paires, tiers, timeframes | `EngineId`, `ProfileId`, `RuntimeMode`, `PairId`, `TradeId`, `OrderId`, `RunId` | `TradeId`, `OrderId`, `RunId`, `PairId.symbol` | pas de `structured_log_key`; sert de base a tous les autres logs |
| `decision_contracts` | surface commune des decisions typagees | candidats/signaux/decisions metier | modeles pydantic de decision | IDs non confirms dans l'inspection fine de ce tour | journalisation indirecte via les runtimes consommateurs |
| `market_event_contracts` | langage commun des events de marche | payloads marche / timestamps / classification | modeles de marche normalises | event/pair typing, pas d'ID specifique confirme ici | journalisation indirecte via data/protocols |
| `meta_contracts` | langage commun meta/monitoring | diagnostics / reviews / projections | types meta transverses | correlation selon composants aval | monitoring indirect |
| `error_contracts` | erreurs canoniques et violations de contrat | exceptions et erreurs de pipeline | classes d'erreur partagees | non applicable | erreurs auditables par type |
| `operator_contracts` | gouvernance operateur et safing | action manuelle, raison, mode source/cible | `OperatorSafingAction`, `OperatorSafingRequest` | `request_id`, `source_runtime_mode`, `target_runtime_mode`, `requested_by`, `ui_channel` | evenement operator side + monitoring projection |
| `atomic_io` | IO atomique des artefacts/JSON | ecriture/lecture structuree | fichiers atomiques et garde-fous IO | pas d'ID metier | preuve indirecte par artefacts persistants |

### 2. `manifest_registry`

Sources observees:
- `src/manifest_registry/module_inventory.py`
- `src/manifest_registry/dependency_registry.py`
- `src/manifest_registry/build_order_registry.py`
- `src/manifest_registry/profile_registry.py`
- `src/manifest_registry/version_registry.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `module_inventory` | table canonique code-backed des modules V5.3 | definitions statiques de modules | `ModuleEntry`, lookup par nom/build/layer/profile | `module_name`, `build_stage`, `module_layer`, `profile_scope` | pas de log structure interne; sert de preuve d'inventaire |
| `dependency_registry` | registre des dependances module -> module | noms de modules / dependances | DAG logique declare | noms de modules | validation indirecte par `dag_validator` |
| `build_order_registry` | ordre de construction / dependances par build | build stages / modules | ordre d'assemblage | build IDs | pas de log confirme dans ce tour |
| `profile_registry` | regles de profil `LIGHT/COMPLETE` | `ProfileId` | scope profil / modules autorises | profile ids | pas de log confirme |
| `version_registry` | versioning du systeme et des surfaces | versions / contracts | refs de version | version strings | pas de log confirme |

### 3. `dag_validator`

Sources observees:
- `src/dag_validator/cycle_detector.py`
- `src/dag_validator/dependency_matcher.py`
- `src/dag_validator/import_scanner.py`
- `src/dag_validator/layer_validator.py`
- `src/dag_validator/report_builder.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `cycle_detector` | detecter les cycles d'import/dependance | graphes/imports | cycle findings | modules/nodes | rapport de validation |
| `dependency_matcher` | comparer imports reels et dependances declarees | imports scannes + registry | mismatches | noms de modules | rapport de validation |
| `import_scanner` | scanner le code pour les imports effectifs | packages Python | graphe d'import | modules/fichiers | preuve via report builder |
| `layer_validator` | verifier le respect des couches | module layers + DAG | violations de layer | layer/module names | rapport build-1 |
| `report_builder` | produire un rapport consolide | findings build-1 | rapport final de validation | execution/report ids non inspectes | surface de preuve principale Build-1 |

### 4. `contract_test_suite`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `contract_test_suite` | verifier que les contrats exportes restent valides et coherents | modeles, enums, surfaces publiques | verdict de test | IDs de test/pytest, pas d'ID metier | sorties de test, preuve de regression |

### 5. `smoke_bootstrap_recovery`

Sources observees:
- `src/smoke_bootstrap_recovery/bootstrap_runner.py`
- `src/smoke_bootstrap_recovery/config_validator.py`
- `src/smoke_bootstrap_recovery/recovery_runner.py`
- `src/smoke_bootstrap_recovery/shadow_readiness.py`
- `src/smoke_bootstrap_recovery/smoke_models.py`
- `src/smoke_bootstrap_recovery/smoke_reporter.py`
- `src/smoke_bootstrap_recovery/state_sanity_checker.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `bootstrap_runner` | verifier le boot minimal du systeme | config, dependances, surfaces runtime | resultat de bootstrap | run/report ids non verifies ici | smoke reports |
| `config_validator` | valider la config minimale | fichiers/config runtime | verdict config | non confirme | logs de validation |
| `recovery_runner` | tester les chemins de reprise/recovery | etat degrade / artefacts | resultat de recovery | non confirme | smoke reports |
| `shadow_readiness` | verifier la readiness Shadow | artefacts/config/gates | readiness verdict | non confirme | preuve readiness |
| `state_sanity_checker` | verifier les invariants d'etat | etats/snapshots | findings de coherence | non confirme | smoke findings |
| `smoke_reporter` | ecrire les rapports de smoke | findings precedents | artefacts de preuve smoke | report refs | surface de preuve principale |

---

## Build-2 - `data_backbone`

Source observee:
- `src/data_backbone/__init__.py`

Sous-composants exposes par le package:
- `websocket_gateway`
- `rest_bootstrap`
- `event_normalizer`
- `internal_router`
- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `websocket_gateway` | connexion WS, subscription, heartbeat, reconnect, collecte brute | config flux, endpoints, pairs, stream types, frames exchange | raw messages, events de heartbeat/reconnect | IDs explicites non confirmes dans l'entree package | reconnect/stale/backlog ensuite projetes en monitoring |
| `rest_bootstrap` | snapshots REST, gap-fill, bootstrap initial | pair list, endpoints REST, besoin de snapshots | snapshots, gap-fill material, bootstrap data | pas d'ID confirme dans ce tour | preuves via bootstrap/shadow artefacts |
| `event_normalizer` | convertir le brut exchange en schema V5.3 | raw exchange payloads + timestamps | events normalises et valides | pair/timeframe/event classification; pas de correlation id confirme ici | anomalies ensuite observees via consistency/freshness |
| `internal_router` | dispatcher les events vers consommateurs internes | events normalises | queues internes, dispatch priorise, backpressure | pas d'ID confirme | backlog/drop metrics visibles en monitoring |
| `freshness_checker` | mesurer l'age des events et signaler le stale | events timestampes | freshness age, stale penalties, hard blocks | pair-scoped implicit IDs | stale warnings et pair freshness en monitoring |
| `consistency_checker` | detecter gaps, duplicates, contradictions | sequences/events normalises | findings de coherence | pair/event sequence implicites | coherence findings ensuite projetes par pair health |
| `pair_health_scorer` | agreger la qualite data par paire | freshness + consistency findings | health state, suspension, recovery | pair symbol | `PairMetrics.health`, `stale_pairs`, `suspension_reason` |

Observation critique:
- le role data est code-backed et net.
- les `IDs` data sont moins exposes comme objets typés centraux que dans `meta_learning` ou `protocols`.
- la preuve data passe surtout par les projections monitoring et les artefacts Shadow/live capture.

---

## Build-3 - `execution_backbone`

Source observee:
- `src/execution_backbone/__init__.py`

Exports confirms:
- `ExecutionOpportunity`
- `ExecutionRuntime`
- `ExecutionSubmission`
- `ExecutionSubmissionStatus`
- `ExecutionVenueAdapter`
- `RemoteExecutionState`
- `ReplaceReceipt`
- `RuntimeProcessingSummary`
- `RuntimeReconciliationResult`
- `SubmitReceipt`
- `TimeoutSweepResult`
- `VenueOrderEvent`
- `VenueOrderEventType`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `order_decider` | transformer une opportunite en intention/order plan executable | opportunite, contraintes venue, execution guards | submission intent, order type selection, timeout policy | `order_id` au niveau runtime, pas expose au package docstring | evenements runtime d'execution |
| `fill_tracker` | suivre le cycle de vie ordre -> fills -> terminal states | order events, venue fills | etat d'execution agrege, latence, fill summary | `order_id`, `fill_id` | latence/fill counters ensuite visibles en monitoring |
| `execution_cost_meter` | mesurer fees, ELW, adverse selection, partial fill costs | fills, execution state, reference prices | cost metrics et agregats | `order_id` | couts projetes en monitoring (`expected_cost_bps`, `realized_cost_bps`, `elw_bps`) |
| `reconciliation_layer` | reconcilier orders/fills/positions et detecter divergences | etat local + etat venue | resultats de reconciliation, alertes de divergence | `order_id`, etat distant | `reconciliation_alert_count`, preuves reconciliation |

Observation critique:
- famille forte sur les IDs transactionnels (`order_id`, `replacement_order_id`, `fill_id`).
- moins forte sur des `structured_log_key` textuels; la preuve est plutot orientee evenements et etats.

---

## Build-4 - `risk_backbone`

Source observee:
- `src/risk_backbone/__init__.py`

Exports confirms:
- `PortfolioRiskSnapshot`
- `RiskCandidate`
- `RiskEvaluation`
- `RiskLimits`
- `RiskRuntime`
- `RiskRuntimeAction`

Sous-familles visibles dans le package:
- `exposure_budgeter`
- `loss_budgeter`
- `btc_factor_guard`
- `correlation_cluster_guard`
- `emergency_kill_switch`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `exposure_budgeter` | encadrer l'exposition totale et par scope | opportunites, portfolio state, limits | budget decision / allowed notional | pas d'ID specifique confirme | breaches ensuite projetes dans monitoring |
| `loss_budgeter` | proteger la perte budgetee | PnL/risk state + limits | allow/block/reduce decisions | pas d'ID specifique confirme | `loss_warning`, breaches, alertes |
| `btc_factor_guard` | limiter la dependance au facteur BTC | correlations/factor exposure | guard decision | scope ids implicites | risk breaches / alerting |
| `correlation_cluster_guard` | limiter la concentration par cluster | pair clusters + allocations | allow/block/reduce decisions | cluster scope implicite | `dominant_cluster`, breaches |
| `emergency_kill_switch` | coupe-circuit critique | violations severes / decision operateur | HALT / emergency state | kill event ids non verifies ici | `kill_switch_active`, timestamp, operator safing |

Observation critique:
- la logique risk est bien code-backed mais les surfaces `id/log` sont moins riches textuellement que Build-9X/11/14.
- le vrai signal d'audit passe surtout par `RiskEvaluation`, `RiskRuntimeAction` et les projections monitoring.

---

## Build-5 - `scoring_backbone`

Source observee:
- `src/scoring_backbone/__init__.py`

Exports confirms:
- `ScoringCandidateInput`
- `ScoringCandidateAudit`
- `ScoringRoundResult`
- `ScoringRuntime`

Sous-familles visibles:
- `raw_score_builder`
- `penalty_aggregator`
- `hard_block_gate`
- `ranking_router`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `raw_score_builder` | construire le score brut d'une opportunite | inputs candidats + edge/context | score brut | IDs non exposes explicitement dans la surface inspectee | audit via `ScoringCandidateAudit` |
| `penalty_aggregator` | appliquer les penalites soft | score brut + frictions/risk penalties | score penalise | non confirme | details de penalites dans l'audit candidat |
| `hard_block_gate` | bloquer les candidats non conformes | candidat + hard constraints | pass/block verdict | non confirme | rationale visible dans les audits de round |
| `ranking_router` | produire le classement final | candidats survivants | ranking ordonne | non confirme | `ScoringRoundResult`, audit de classement |

Observation critique:
- la famille est bien isolee et typée.
- l'audit de cette couche semble passer davantage par `ScoringCandidateAudit` que par des logs structures nommes.

---

## Builds-6/7/15/16 - Moteurs A/B/C/D

Sources observees:
- `src/engine_a/__init__.py`
- `src/engine_b/__init__.py`
- `src/engine_c/__init__.py`
- `src/engine_d/__init__.py`
- `src/engines/engine_a/*`
- `src/engines/engine_b/*`
- `src/engines/engine_c/*`
- `src/engines/engine_d/*`

### Engine A

Sous-composants visibles:
- `structure_detector_a`
- `conviction_builder_a`
- `cost_feasibility_a`
- `invalidation_mapper_a`
- `signal_reporter_a`
- `engine_a_runner`
- `engine_a_runtime`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `engine_a_runner` | generer la decision moteur A | `EngineAInput` | `EngineAOutput`, `EngineADecision` | IDs non confirms dans l'audit de ce tour | `EngineALogEntry` |
| `engine_a_runtime` | executer/agreger le runtime A | `EngineARuntimeInput` | `EngineARuntimeResult`, `EngineARuntimeStatus` | runtime-scoped IDs implicites | runtime result + logs moteur |
| `structure_detector_a` | detecter la structure premium trend/expansion | donnees marche/scoring context | structure flags | non confirme | indirect via `EngineALogEntry` |
| `conviction_builder_a` | convertir le contexte en conviction | structure + contexte | conviction score | non confirme | indirect |
| `cost_feasibility_a` | verifier la faisabilite economique | signal + couts | allow/reduce/block | non confirme | indirect |
| `invalidation_mapper_a` | fixer l'invalidation du setup | signal structurel | invalidation map | non confirme | indirect |
| `signal_reporter_a` | produire la trace moteur | decision et contexte | report/log entry | non confirme | `EngineALogEntry` |

### Engine B

Sous-composants visibles:
- `local_mean_estimator_b`
- `excess_detector_b`
- `anti_breakout_filter_b`
- `conviction_builder_b`
- `cost_feasibility_b`
- `invalidation_mapper_b`
- `signal_reporter_b`
- `engine_b_runner`
- `engine_b_runtime`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `engine_b_runner` | generer la decision moteur B | `EngineBInput` | `EngineBOutput`, `EngineBDecision` | IDs non confirms dans ce tour | `EngineBLogEntry` |
| `engine_b_runtime` | executer/agreger le runtime B | `EngineBRuntimeInput` | `EngineBRuntimeResult`, `EngineBRuntimeStatus` | runtime-scoped IDs implicites | runtime result + logs moteur |
| `local_mean_estimator_b` | estimer la moyenne locale | donnees prix | mean reference | non confirme | indirect |
| `excess_detector_b` | detecter l'exces mean reversion | prix + mean local | excess flags | non confirme | indirect |
| `anti_breakout_filter_b` | eviter les faux cas de breakout | contexte/prix | filtre allow/reject | non confirme | indirect |
| `conviction_builder_b` | convertir le contexte B en conviction | excess + filtres | conviction | non confirme | indirect |
| `cost_feasibility_b` | verifier l'economie du setup B | signal + couts | allow/reduce/block | non confirme | indirect |
| `invalidation_mapper_b` | fixer l'invalidation du setup B | signal mean reversion | invalidation | non confirme | indirect |
| `signal_reporter_b` | produire la trace moteur B | decision et contexte | report/log entry | non confirme | `EngineBLogEntry` |

### Engine C

Sous-composants visibles:
- `engine_c_runner`
- `engine_c_runtime`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `engine_c_runner` | generer la decision breakout continuation | `EngineCInput` | `EngineCOutput`, `EngineCDecision`, `EngineCInvalidation` | IDs non confirms au niveau facade | `EngineCLogEntry` |
| `engine_c_runtime` | executer/agreger le runtime C | `EngineCRuntimeInput` | `EngineCRuntimeResult`, `EngineCRuntimeStatus` | runtime-scoped IDs implicites | runtime result + logs moteur |

### Engine D

Sous-composants visibles:
- `engine_d_runner`
- `engine_d_runtime`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `engine_d_runner` | generer la decision re-entry / second chance | `EngineDInput` | `EngineDOutput`, `EngineDDecision`, `EngineDInvalidation` | `origin_context_id`, `origin_trade_id`, `link_type` ont ete ajoutes et sont code-backed | `EngineDLogEntry` |
| `engine_d_runtime` | executer/agreger le runtime D | `EngineDRuntimeInput` | `EngineDRuntimeResult`, `EngineDRuntimeStatus` | runtime-scoped IDs implicites + lien contexte source | runtime result + logs moteur |

Observation critique:
- A/B ont une decomposition interne plus riche et plus modulaire.
- C/D sont code-backed mais avec une decomposition plus compacte.
- la surface `log` moteurs est forte via les `EngineXLogEntry`.

---

## Build-8 - `portfolio_minimal`

Sources observees:
- `src/portfolio_minimal/__init__.py`
- `src/portfolio_minimal/opportunity_selector`
- `src/portfolio_minimal/allocation_router`
- `src/portfolio_minimal/portfolio_orchestrator.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `opportunity_selector` | choisir les opportunites survivantes A/B | ranked/scored opportunities | shortlist portfolio | IDs d'opportunite non verifies dans ce tour | trace indirecte via orchestrator/monitoring |
| `allocation_router` | transformer la shortlist en allocation coherente | shortlist + budgets/limits | plan d'allocation | pair/engine scopes implicites | metrics portefeuille en monitoring |
| `portfolio_orchestrator` | orchestration portefeuille Light | opportunites + contraintes | decisions portefeuille consolidees | run scope implicite | projections portfolio monitoring |

Observation critique:
- package reel confirme mais la decomposition canonique plus large du portfolio n'apparait pas comme autant de packages distincts.
- des sous-capacites comme `risk_contribution_monitor` ou `effective_edge_diversity` n'apparaissent pas comme modules top-level separes; une partie de cette logique est aujourd'hui absorbee par Build-14 et monitoring.

---

## Build-9 - `meta_minimal`

Sources observees:
- `src/meta_minimal/__init__.py`
- `src/meta_minimal/dtr_core`
- `src/meta_minimal/cra_monitor`
- `src/meta_minimal/break_even_dashboard`
- `src/meta_minimal/edge_tracker_prudent_minimal`
- `src/meta_minimal/meta_runtime.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `dtr_core` | tracer les decisions/executions/rationales | decisions, events, runtime facts | DTR records / coverage | IDs non inspectes finement ici | DTR export et coverage monitoring |
| `cra_monitor` | mesurer la sterilisation / alerts CRA | candidate flow, sterilisation facts | CRA metrics / alert count | non confirme | `cra_alert_count`, sterilization rate |
| `break_even_dashboard` | suivre la derive break-even | couts, edge, performance | drift state / scopes | non confirme | drift scopes exposes au dashboard |
| `edge_tracker_prudent_minimal` | suivre edge credible/degraded/surveillance | trades/opportunites/performance | edge counts et state | non confirme | projections meta monitoring |
| `meta_runtime` | orchestration meta minimale | outputs precedents | resume meta coherent | run scope implicite | projection Build-9 monitoring |

Observation critique:
- Build-9 est bien code-backed mais ses `IDs/logs` sont surtout visibles via monitoring et DTR exports, moins via une grammaire de `structured_log_key`.

---

## Build-9X - `meta_learning`

Sources observees:
- `src/meta_learning/contracts.py`
- `src/meta_learning/merge_gate_contracts.py`
- `src/meta_learning/merge_gates.py`
- `src/meta_learning/post_trade_diagnostic_engine.py`
- `src/meta_learning/mistake_classifier.py`
- `src/meta_learning/near_miss_analyzer.py`
- `src/meta_learning/improvement_candidate_builder.py`
- `src/meta_learning/replay_bundle_builder.py`
- `src/meta_learning/review_queue.py`
- `src/meta_learning/review_orchestrator.py`
- `src/meta_learning/review_resolution.py`
- `src/meta_learning/learning_review_exporter.py`
- `src/meta_learning/persistence_store.py`
- `src/meta_learning/learning_memory_store.py`
- `src/meta_learning/monitoring_projection.py`
- `src/meta_learning/capacity_guard.py`

Exports/contrats visibles:
- `TradeLearningInput`
- `DiagnosticEvidence`
- `DiagnosticResult`
- `LearningCapacitySnapshot`
- `LearningHypothesis`
- `ImprovementCandidate`
- `LearningChecklist`
- `BreakdownReport`
- `LearningMemoryRecord`
- `LearningReviewExport`
- `ReviewQueueEntry`
- `MetaLearningReviewBundle`
- `ReplayComparisonProtocol`
- `ReplayExportBundle`
- `LifecycleTransitionRecord`
- `DiagnosticRecord`
- `HypothesisRecord`
- `CandidateRecord`
- `ReviewRecord`
- `ExportBundleRecord`
- `LearningEventRecord`
- `Build9XMergeGateName`
- `Build9XMergeGateResult`
- `Build9XMergeGateReport`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `post_trade_diagnostic_engine` | fabriquer le diagnostic post-trade | `TradeLearningInput` + evidence | `DiagnosticResult` | `correlation_id`, `diagnostic_id` | `DiagnosticResult.structured_log_key` |
| `mistake_classifier` | classifier les erreurs | diagnostic/evidence | categories d'erreur | `diagnostic_id` | rapport breakdown |
| `near_miss_analyzer` | detecter les quasi-occasions ratees | diagnostic/evidence | near-miss findings | `diagnostic_id` | diagnostic outputs |
| `improvement_candidate_builder` | transformer hypotheses en candidats d'amelioration | diagnostics + hypotheses | `ImprovementCandidate` | `candidate_id`, `correlation_id` | learning records/export refs |
| `replay_bundle_builder` | creer les bundles de replay gouvernes | candidats eligibles | `ReplayExportBundle` | `bundle_id`, `candidate_id`, `correlation_id` | bundle refs |
| `review_queue` | organiser la file de revue | candidats/bundles | `ReviewQueueEntry` | `candidate_id`, `bundle_id` | queue depth / backlog metrics |
| `review_orchestrator` + `review_resolution` | faire la revue gouvernee et ses decisions | queue, merge gates, evidences | review decision / lifecycle records | `candidate_id`, `bundle_id`, `correlation_id` | review logs + export |
| `learning_review_exporter` | ecrire le paquet de revue auditable | diagnostics/candidates/review state | `LearningReviewExport` | `bundle_id`, export refs | review export markdown/json |
| `persistence_store` + `learning_memory_store` | persister la memoire append-only | records lifecycle/diagnostics/reviews | stores et memory records | `diagnostic_id`, `candidate_id`, `bundle_id`, `correlation_id` | persistence refs |
| `capacity_guard` | proteger le worker learning contre surcharge | queue depth, worker metrics | `LearningCapacitySnapshot` | non centre sur un ID metier | backlog state, capture mode, thresholds |
| `merge_gates` | gates explicites Build-9X | review bundle, records, observability facts | `Build9XMergeGateReport` | gate names + correlation evidence | `structured_log_key` par gate result |
| `monitoring_projection` | projeter Build-9X vers Build-10 | diagnostics/review/capacity | `Build9XProjection` | correlation via source bundle/review refs | dashboard payload |

Gates code-backed explicites confirmes:
- `NO_LIVE_MUTATION_PATH`
- `END_TO_END_ID_CORRELATION`
- `STRUCTURED_LEARNING_LOGS_PRESENT`
- `LEARNING_BACKPRESSURE_HANDLED`
- `RESOURCE_BUDGETS_RESPECTED`
- `STATISTICAL_GOVERNANCE_PRESENT`

Observation critique:
- Build-9X est la famille la plus riche en `IDs` et en gouvernance explicite.
- c'est aussi la famille la plus proche d'un audit `phd-level` a partir du code, parce que la chaine `input -> diagnostic -> hypothese -> candidat -> bundle -> review -> persistence -> monitoring` existe reellement.

---

## Build-10 - Replay, import, monitoring, UI

### 1. `local_replay_runtime`

Sources observees:
- `src/local_replay_runtime/contracts.py`
- `src/local_replay_runtime/artifact_manifest.py`
- `src/local_replay_runtime/replay_orchestrator.py`
- `src/local_replay_runtime/performance_mode_guard.py`
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/replay_dtr_exporter.py`
- `src/local_replay_runtime/runtime_evidence.py`
- `src/local_replay_runtime/shadow_execution_simulator.py`
- etc.

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `contracts` | langage replay local unifie | dataset refs, clock refs, request replay | `LocalReplayRequest`, `ReplayBundle`, `ReplayExecutionPlan`, `LocalReplayRuntimeEvidence` | `correlation_id`, `dataset_id`, `clock_id`, `artifact_id`, `lineage_version` | evidence refs |
| `artifact_manifest` | lister ce qu'un export replay contient | diagnostics/candidates/artifacts | manifest d'artefacts | `artifact_id`, `correlation_id`, `diagnostic_ids`, `candidate_ids` | manifest json |
| `replay_orchestrator` | orchestrer l'export replay complet | replay inputs + modules replay | run complet | `run_id` + artifact hashes | run manifest / evidence |
| `performance_mode_guard` | proteger le replay contre surcout | worker/runtime metrics | guard report | `run_id` | performance guard json |
| `run_consistency_guard` | garantir la coherence entre runs | outputs replay | consistency report | `run_id` / run refs | consistency guard json |
| `replay_metrics_collector` | produire les metriques replay | replay facts | replay metrics | run scope implicite | `replay_metrics.json` |
| `replay_dtr_exporter` | exporter le DTR replay | replay facts | DTR replay | run scope implicite | `replay_dtr.jsonl` |
| `runtime_evidence` | construire la preuve runtime replay | export/replay facts | `LocalReplayRuntimeEvidence` | run/artifact correlation | evidence refs |

### 2. `backtest_artifact_import`

Sources observees:
- `src/backtest_artifact_import/contracts.py`
- `src/backtest_artifact_import/validators.py`
- `src/backtest_artifact_import/errors.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `contracts` | langage d'import gouverne local -> VPS | import proposal, lineage, source version | `ArtifactImportRequest`, `ArtifactImportDecision`, `ArtifactImportSummary`, `StrategyOnboardingDecision` | `artifact_id`, `correlation_id`, `proposal_id`, `lineage_version`, `strategy_version`, `source_version` | import summary refs |
| `validators` | valider qu'un artefact est recevable | replay bundles/import requests | verdicts de validation | IDs heritage de l'import | validation findings |
| `errors` | interdire les promotions implicites et violations | import misuse | erreurs typées | non applicable | surfaces d'erreur auditable |

### 3. `monitoring`

Sources observees:
- `src/monitoring/contracts.py`
- `src/monitoring/metrics_collector.py`
- `src/monitoring/alert_manager.py`
- `src/monitoring/health_dashboard_backend.py`
- `src/monitoring/technical_dashboard_backend.py`
- `src/monitoring/observability.py`
- `src/monitoring/build14_observation.py`
- `src/monitoring/monitoring_runtime.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `contracts` | modele unique des payloads monitoring/UI | metrics systeme, projections builds, alerts | `MonitoringSnapshot`, `HealthDashboardPayload`, `TechnicalDashboardPayload` | `correlation_id`, `alert_id`, `OperatorRuntimeEvent.correlation_id` | projections + alert history |
| `metrics_collector` | collecter les metriques d'etat | portfolio/engines/pairs/infra/meta | snapshots monitoring | correlation via `MonitoringSnapshot` | metrics export |
| `alert_manager` | construire les alertes et leur severite | snapshot monitoring | `AlertRecord`, alert history | `alert_id` | alert payloads |
| `health_dashboard_backend` | produire le payload verrouille Build-10 | snapshot + alerts | `HealthDashboardPayload` | `correlation_id` | payload UI |
| `technical_dashboard_backend` | produire le payload technique complet | runtime artifacts + projections builds | `TechnicalDashboardPayload` | `correlation_id`, alert IDs, refs artefacts | dashboard technique |
| `build14_observation` | deriver une observation Build-14 commune | snapshots Build-14 | projections/observations reader-level | reader names + evidence refs | reader projections |
| `observability` | exporter les metrics structurees | samples monitoring | `ObservabilityExport` | `correlation_id` | export texte + metrics samples |
| `monitoring_runtime` | relier runtime local et projections monitoring | artefacts locaux, events operateur, account data | runtime-backed monitoring payloads | runtime/event correlations | proofs runtime -> UI |

### 4. `ui`

Sources observees:
- `src/ui/contracts.py`
- `src/ui/light_ui_runtime.py`
- `src/ui/operator_actions.py`
- `src/ui/technical_dashboard_view.py`
- `src/ui/technical_dashboard_html.py`
- `src/ui/ui_light_locked.py`
- `src/ui/complete_dashboard_view.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `contracts` | types UI et actions operateur | operator actions, notifications, dashboard contracts | `OperatorActionRequest`, `OperatorActionOutcome`, `OperatorNotificationRecord` | request-like identifiers et alert refs | notifications / operator audit |
| `light_ui_runtime` | runtime local UI Light verrouille | operator events + dashboard state | UI projection et event log | correlation/event ids dans les events | event log local |
| `operator_actions` | gouverner kill/downgrade/ack operator | demandes UI | outcome structure | action target + operator reason | operator log entries |
| `technical_dashboard_view` | renderer texte/HTML du dashboard technique | `TechnicalDashboardPayload` | sections rendues | pas d'ID propre | rendu de toutes les preuves collecte |
| `technical_dashboard_html` | dashboard HTML local et widgets live | payload technique + market lab | page HTML locale | pas d'ID propre | rendu live local |
| `ui_light_locked` | surface verrouillee Build-10 | payloads monitoring + controls | vue Light | pas d'ID propre | UI locked state |
| `complete_dashboard_view` | supplement Complete cote UI | metadata Complete/demo | vue Complete supplementaire | pas d'ID propre | rendu Complete |

Observation critique:
- Build-10 est fortement code-backed.
- `monitoring` concentre beaucoup des `id/log` transverses du systeme.
- `ui` est surtout consommateur et presentateur de preuves, pas source primaire de calcul.

---

## Builds-11/12/13 - `protocols`

Sources observees:
- `src/protocols/contracts.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/shadow_report_builder.py`
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_daily_orchestrator.py`
- `src/protocols/shadow_vps_service.py`
- `src/protocols/shadow_live_websocket.py`
- `src/protocols/micro_live_runtime.py`
- `src/protocols/live_light_runtime.py`
- `src/protocols/*_dashboard.py`
- `src/protocols/promotion_gates.py`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `contracts` | langage des gates Build-11/12/13 | truth set, validation set, shadow/micro/live inputs | `Shadow*`, `MicroLive*`, `LiveLight*` contracts | `truth_ref`, `validation_ref`, `comparison_id`, `run_id`, `correlation_id` | report sections, evidence refs |
| `shadow_runtime` | executer la comparaison Shadow | `ShadowInput`, truth/validation sets | `ShadowDecision`, `ShadowRunSummary` | `run_id`, `comparison_id`, `correlation_id` | shadow report/evidence |
| `shadow_report_builder` | consolider le rapport Shadow | comparisons + assessments | `ShadowReportArtifact` | report refs | report JSON |
| `shadow_day_counter` | compter les jours Shadow et la readiness 30 jours | `ShadowRunSummary` + registries | day counts / gate state | session date / run refs | shadow session summary |
| `shadow_daily_orchestrator` | orchestrer un jour Shadow | export dir, replay bundle, config | day run orchestration result | session date + run refs | orchestrator state / last run |
| `shadow_vps_service` | service VPS de campagne Shadow | websocket/live capture + orchestrator + shadow session | campaign summary et runtime evidence bundle | session date, evidence refs | service state/events/campaign summary |
| `shadow_live_websocket` | capture live market + user-data Binance | public streams, optional user-data auth, pair scope | capture summaries + events jsonl | session date, `subscription_id`, capture refs | capture summaries / event logs |
| `micro_live_runtime` | gate Build-12 | `MicroLiveInput` | `MicroLiveDecision`, `MicroLiveRunSummary` | `run_id`, source shadow run refs | gating reasons |
| `live_light_runtime` | gate Build-13 | `LiveLightInput` | `LiveLightDecision`, `LiveLightRunSummary` | `run_id`, source micro-live run refs | gating reasons |
| `micro_live_dashboard` / `live_light_dashboard` | projection monitoring des gates | summaries runtime | `MicroLiveProjection`, `LiveLightProjection` | run refs | dashboard payloads |
| `promotion_gates` | blocs de promotion codifies | summaries/gates | allow/block | run/build refs | blocking reasons |
| `OperatorSafingRequest` | descente manuelle gouvernee | action operateur + raison | safing request | `request_id`, source/target runtime mode | operator + monitoring projections |

IDs/component IDs confirms dans `protocols/contracts.py`:
- moteurs requis Build-11:
  - `engine_a`
  - `engine_b`
  - `engine_c`
  - `engine_d`
- contributions Build-14:
  - `build14_microstructure`
  - `build14_regime`
  - `build14_covariance`
  - `build14_risk_contribution`
  - `build14_edge_diversity`
- reader IDs connus:
  - `market_toxicity_snapshot`
  - `execution_fragility_score`
  - `lob_deep_filter_vwa`
  - `order_book_imbalance`
  - `false_breakout_model`
  - `hurst_regime_classifier`
  - `competition_monitor`

Observation critique:
- `protocols` est la couche la plus forte en `refs`, `run_id`, `comparison_id`, evidence bundles et chaines de preuve runtime.
- c'est ici que V5.3 devient vraiment audit-ready du point de vue deployment lifecycle.

---

## Build-14 - `complete_enablers`

Sources observees:
- `src/complete_enablers/contracts.py`
- `src/complete_enablers/enums.py`
- `src/complete_enablers/market_toxicity.py`
- `src/complete_enablers/execution_fragility.py`
- `src/complete_enablers/false_breakout_model.py`
- `src/complete_enablers/hurst_regime_classifier.py`
- `src/complete_enablers/lob_deep_filter_vwa.py`
- `src/complete_enablers/order_book_imbalance.py`
- `src/complete_enablers/competition_monitor.py`
- `src/complete_enablers/limited_influence.py`

Contracts visibles:
- `Build14EnablerContract`
- `Build14ObservationInput`
- `Build14EnablerSnapshot`
- `Build14InfluenceSignal`
- `Build14InfluenceReport`

| Composant | Role | In | Out | ID | Log |
| --- | --- | --- | --- | --- | --- |
| `market_toxicity` | mesurer la toxicite de marche | `Build14ObservationInput` | `Build14EnablerSnapshot` | `correlation_id`, `reader_name` | `build14.shadow_enabled.market_toxicity` |
| `execution_fragility` | mesurer la fragilite d'execution | observation input | snapshot | `correlation_id`, `reader_name` | `build14.shadow_enabled.execution_fragility` |
| `false_breakout_model` | detecter contexte de faux breakout | observation input | snapshot | `correlation_id`, `reader_name` | `build14.shadow_enabled.false_breakout_model` |
| `hurst_regime_classifier` | mesurer le regime par Hurst | observation input | snapshot | `correlation_id`, `reader_name` | `build14.shadow_enabled.hurst_regime_classifier` |
| `lob_deep_filter_vwa` | lire la profondeur carnet / VWA | observation input | snapshot | `correlation_id`, `reader_name` | `build14.shadow_enabled.lob_deep_filter_vwa` |
| `order_book_imbalance` | mesurer OBI | observation input | snapshot | `correlation_id`, `reader_name` | `build14.shadow_enabled.order_book_imbalance` |
| `competition_monitor` | mesurer crowding/competition | observation input | snapshot | `correlation_id`, `reader_name` | `build14.shadow_enabled.competition_monitor` |
| `limited_influence` | transformer les snapshots en signal gouverne | snapshots + mode gouvernance | `Build14InfluenceSignal`, `Build14InfluenceReport` | `correlation_id`, evidence refs | `reason_codes`, evidence refs, projections monitoring |

Observation critique:
- Build-14 est fortement code-backed cote readers et preuves.
- les `structured_log_key` reader-level sont explicites et propres.
- Build-14 agit comme couche gouvernee, pas comme moteur autonome.

---

## Gaps et zones implicites detectes par l'audit code-first

### 1. Composants canoniques non isoles comme packages distincts

Depuis le code reel, certaines briques canoniques ne ressortent pas comme modules top-level independants:
- `microstructure_engine` n'existe pas comme package top-level unique; une partie est absorbee par:
  - `data_backbone`
  - `complete_enablers`
  - les moteurs
- `regime_engine` n'existe pas comme package top-level unique; une partie est absorbee par:
  - `complete_enablers.hurst_regime_classifier`
  - les moteurs
  - `meta`/monitoring
- `risk_contribution_monitor` et `effective_edge_diversity` n'apparaissent pas comme packages portfolio top-level distincts; ils existent surtout comme concepts/projections/gates.
- `Build-17` n'apparait pas comme package runtime `live_complete` isole; la surface Complete est surtout:
  - `complete_enablers`
  - `engine_c`
  - `engine_d`
  - `ui.complete_dashboard_view`

### 2. Familles les plus riches en preuve audit-ready

Les familles les plus robustes si l'objectif est de creer des strategies en utilisant toute la capacite de V5.3 sont:
- `meta_learning`
- `protocols`
- `complete_enablers`
- `monitoring`
- `local_replay_runtime`

Pourquoi:
- elles possedent les meilleures surfaces `ID/ref/log/evidence`.
- elles permettent une boucle propre:
  - idee
  - diagnostic
  - replay
  - review
  - shadow
  - monitoring
  - gouvernance

### 3. Familles plus faibles en audit textuel explicite

Les familles suivantes existent clairement, mais avec une surface `id/log` moins textuelle:
- `risk_backbone`
- `scoring_backbone`
- `portfolio_minimal`
- une partie de `meta_minimal`

Elles sont code-backed, mais souvent:
- leur preuve passe par leurs resultats agregees
- puis par les projections monitoring
- plutot que par des `structured_log_key` ou des contracts de lineage aussi riches que Build-9X/11/14

---

## Synthese finale code-first

### Ce qui est fortement confirme par le code

- la colonne vertebrale V5.3 existe reellement:
  - contrats
  - data
  - execution
  - risk
  - scoring
  - moteurs A/B/C/D
  - portfolio minimal
  - meta minimal
  - meta-learning
  - local replay
  - import gouverne
  - monitoring
  - UI
  - protocols Shadow/Micro-live/Live-Light
  - Build-14 enablers

- les meilleures surfaces pour un audit ou un enrichissement strategique profond sont:
  - `meta_learning`
  - `local_replay_runtime`
  - `protocols`
  - `complete_enablers`
  - `monitoring`

### Ce qui reste a garder en tete pour la suite

- tout le canon n'apparait pas toujours comme packages top-level 1:1.
- plusieurs briques canoniques sont aujourd'hui distribuees entre:
  - moteurs
  - Build-14
  - monitoring
  - protocols
- si l'objectif est d'enrichir V5.3 sans oublier de composants, il faut maintenant travailler avec deux vues en parallele:
  1. **vue code-first**: ce document
  2. **vue canonique**: les MD de specification

### Conclusion operable

Pour creer de nouvelles strategies en exploitant toute la capacite de V5.3, la meilleure base de travail code-first n'est pas simplement `engine_a/b/c/d`.
La vraie chaine exploitable est:

1. `data_backbone`
2. `risk_backbone`
3. `scoring_backbone`
4. `engine_*`
5. `portfolio_minimal`
6. `meta_minimal`
7. `meta_learning`
8. `local_replay_runtime`
9. `protocols`
10. `complete_enablers`
11. `monitoring/ui`

Autrement dit:
- les moteurs generent l'idee
- le risk/scoring/portfolio determinent si elle survit
- le meta/meta_learning expliquent ce qui a marche ou casse
- le replay/protocols prouvent
- Build-14 enrichit
- monitoring/UI rendent la gouvernance visible

Ce document peut maintenant servir de base a un **audit composant par composant d'enrichissement strategique**, sans sauter d'etapes et sans oublier un bloc du systeme.
