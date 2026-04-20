# Cartographie src/ — Groupe E : meta + portfolio + ui + petits packages
> Date : 2026-04-19 | Auteur : Opus (lecture directe ligne par ligne)

---

## Package : `ui/`

### Fichier : `__init__.py` (80L)
**Rôle** : Re-exports publics du package UI locked Build-10.
**Exports** : `DashboardCard`, `DashboardSection`, `LockedOperatorDashboardView`, `LightDashboardView`, `LockedControlSurface`, `OperatorActionType`, `build_locked_operator_dashboard_view`, `build_light_dashboard_view`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `contracts.py` (175L)
**Rôle** : Contrats Pydantic pour la surface UI operator locked Build-10 — DashboardCard, sections, actions, notifications.
**Inputs** : N/A (dataclasses)
**Outputs** : Types exportés : `DashboardCard(key, title, value, status, detail)`, `DashboardSection(title, cards)`, `LockedOperatorDashboardView`, `LightDashboardView`, `OperatorActionRequest`, `OperatorActionOutcome`, `OperatorActionLogEntry`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `interface_contracts` (AlertSeverity, ProfileId, RuntimeMode, TimestampedModel)
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `light_ui_runtime.py` (404L)
**Rôle** : Runtime stateful pour l'UI operator locked Build-10 — gère le state des notifications, screens ouverts, et projections depuis `HealthDashboardPayload`.
**Inputs** : `HealthDashboardPayload` (depuis `monitoring.contracts`)
**Outputs** : `LockedOperatorDashboardView`, `NotificationDeliveryState`, `OperatorActionLogEntry`
**Équations mathématiques** : Aucune.
**Logging** : structlog — clés `operator_screen_opened`, `operator_action_rejected`, `notification_delivered`
**Dépendances internes** : `interface_contracts`, `monitoring.contracts`, `ui.contracts`, `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `operator_actions.py` (270L)
**Rôle** : Actions operator gouvernées — liste des actions autorisées par profil (LIGHT vs COMPLETE), validation des requêtes, journal des actions.
**Inputs** : `OperatorActionRequest`, `ProfileId`, `RuntimeMode`
**Outputs** : `OperatorActionOutcome` (GRANTED / DENIED + reason), `OperatorActionLogEntry`
**Équations mathématiques** : Aucune.
**Logging** : `operator_action_granted`, `operator_action_denied`
**Dépendances internes** : `interface_contracts`, `ui.contracts`
**État** : COMPLETE
**Anomalies** : ⚠️ `_LIGHT_ALLOWED_ACTIONS` hardcodé dans le code — devrait venir d'une config externe si les profils évoluent. **Note doctrinale** : le fichier distingue encore LIGHT / COMPLETE actions — à harmoniser avec doctrine "une seule solution".

---

### Fichier : `ui_light_locked.py` (462L)
**Rôle** : Couche de projection UI locked Build-10 — construit la vue dashboard depuis `HealthDashboardPayload`.
**Inputs** : `HealthDashboardPayload`
**Outputs** : `LockedOperatorDashboardView` avec sections Health / Profile / Portfolio / Pairs / Engines / Risk
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `interface_contracts`, `monitoring.contracts`, `ui.contracts`, `ui.operator_actions`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `technical_dashboard_view.py` (1940L)
**Rôle** : Vue technique avancée du dashboard — projette `TechnicalDashboardPayload` vers toutes les cards (system, extensions, portfolio, pairs, engines, protocols, calibration, risk, meta). Fichier god — 1940L.
**Inputs** : `TechnicalDashboardPayload` (depuis `monitoring.contracts`)
**Outputs** : Vue composée de `DashboardSection` + `DashboardCard`
**Équations mathématiques** : Aucune (rendu pur).
**Logging** : Aucun.
**Dépendances internes** : `monitoring.contracts`, `ui.contracts`
**État** : COMPLETE
**Anomalies** :
- ❌ **BUG CONFIRMÉ — duplication `governed_extensions`** :
  - Card 1 (section "Extensions") : L1050-1052 → `value=_governed_extensions_value(payload)`, `status=_governed_extensions_status(payload)`, `detail=payload.system.governed_extensions_detail`
  - Card 2 (section "System") : L1082-1086 → `key="governed_extensions"`, mêmes `value`/`status`/`detail`
  - **Correction** : supprimer la card L1082-1086 (section "System"), garder L1050-1052 (section "Extensions")
- ⚠️ Fichier 1940L — god file, bien au-dessus du cap 700 (baselined non-runtime)

---

### Fichier : `technical_dashboard_html.py` (1271L)
**Rôle** : Rendu HTML du dashboard technique — templates Jinja2 inline pour l'affichage web.
**Inputs** : `LockedOperatorDashboardView` ou dict de sections
**Outputs** : `str` HTML
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `ui.contracts`
**État** : COMPLETE
**Anomalies** : ⚠️ 1271L — god file, baselined non-runtime.

---

### Fichier : `complete_dashboard_view.py` (652L)
**Rôle** : Vue dashboard complète (COMPLETE profile) — étend `ui_light_locked` avec cards supplémentaires (calibration details, meta learning, shadow specifics).
**Inputs** : `TechnicalDashboardPayload`
**Outputs** : `LockedOperatorDashboardView` enrichie
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `monitoring.contracts`, `ui.contracts`, `ui.ui_light_locked`
**État** : COMPLETE
**Anomalies** : ⚠️ 652L — proche cap 700 (non-runtime, baselined).

---

## Package : `dag_validator/`

### Fichier : `import_scanner.py` (~250L)
**Rôle** : Scan AST de tous les fichiers `.py` src/ — extrait les imports first-party, détecte les imports dynamiques (`importlib.import_module`, `__import__`). Normalise les noms de packages (`portfolio_minimal` → `portfolio`, `meta_minimal` → `meta`).
**Inputs** : `src_root: Path`, `known_modules: frozenset[str]`
**Outputs** : `ScanResult(imports, files_scanned, errors, discovered_modules, unknown_modules, dynamic_imports)`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune (stdlib only).
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `cycle_detector.py` (~110L)
**Rôle** : Détection de cycles dans le DAG de dépendances — DFS WHITE/GRAY/BLACK sur le graphe manifest ou le graphe observé.
**Inputs** : `allowed_dependencies: dict[str, frozenset[str]]` OU `ScanResult`
**Outputs** : `CycleResult(cycles, has_cycles)`
**Équations mathématiques** : Algorithme DFS — coloration 3 états (WHITE=non-visité, GRAY=en cours, BLACK=terminé). Cycle détecté quand on atteint un nœud GRAY.
**Logging** : Aucun.
**Dépendances internes** : `dag_validator.import_scanner`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `layer_validator.py` (~100L)
**Rôle** : Validation des couches d'architecture — vérifie que les imports respectent la hiérarchie de couches (ex: engines ne peut pas importer protocols).
**Inputs** : `ScanResult`, `layer_rules: dict`
**Outputs** : Liste de violations de couche
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `dag_validator.import_scanner`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `dependency_matcher.py` (~80L)
**Rôle** : Comparaison imports observés vs imports déclarés dans le manifest — identifie imports non-déclarés et déclarés non-utilisés.
**Inputs** : `ScanResult`, manifest whitelist
**Outputs** : `MatchResult(undeclared, unused_declarations)`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `dag_validator.import_scanner`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `report_builder.py` (~80L)
**Rôle** : Construit le rapport final de validation DAG — agrège cycles + violations couche + undeclared imports.
**Inputs** : `CycleResult`, violations, `MatchResult`
**Outputs** : `DAGReport` (markdown ou dict)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `dag_validator.*`
**État** : COMPLETE
**Anomalies** : Aucune.

---

## Package : `secrets_manager/`

### Fichier : `_dpapi.py` (~50L)
**Rôle** : Wrapper Windows DPAPI (Data Protection API) — `protect_bytes` et `unprotect_bytes` via `ctypes.windll.crypt32`. Chiffrement lié à la session utilisateur Windows courante.
**Inputs** : `data: bytes`, `entropy: bytes | None`
**Outputs** : `bytes` (ciphertext ou plaintext)
**Équations mathématiques** : Aucune (délégué à DPAPI Windows).
**Logging** : Aucun.
**Dépendances internes** : Aucune (ctypes stdlib).
**État** : COMPLETE — Windows only.
**Anomalies** : ⚠️ Windows-only — non portable VPS Linux. Sur VPS Linux, il faudra un backend alternatif (env vars ou vault). **Critique pré-déploiement VPS**.

---

### Fichier : `loader.py` (~110L)
**Rôle** : Charge et déchiffre un envelope sealed (JSON/YAML chiffré DPAPI) depuis disque. Retourne `dict[str, object]` en mémoire seulement.
**Inputs** : `path: Path`, `key_path: Path` (fichier entropy)
**Outputs** : `dict[str, object]` (payload déchiffré)
**Équations mathématiques** : Aucune.
**Logging** : Aucun (fail-fast par exception).
**Dépendances internes** : `secrets_manager._dpapi`, `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** : ⚠️ Dépend de `_dpapi.py` Windows-only.

---

### Fichier : `sealer.py` (~80L)
**Rôle** : Scelle (chiffre + sérialise) un secret en envelope JSON sur disque via DPAPI.
**Inputs** : `plaintext: str | bytes`, `path: Path`, `key_path: Path`, `source_name: str`
**Outputs** : `SealedSecretEnvelope` écrit sur disque
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `secrets_manager._dpapi`, `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** : ⚠️ Windows DPAPI only.

---

### Fichier : `cli.py` (~80L)
**Rôle** : CLI opérateur pour seal/unseal des secrets (`python -m secrets_manager seal/unseal`).
**Inputs** : Args CLI (path, key_path, source_name)
**Outputs** : stdout confirmation / stderr erreur
**Équations mathématiques** : Aucune.
**Logging** : `print()` — acceptable (CLI uniquement, pas src/ trading).
**Dépendances internes** : `secrets_manager.sealer`, `secrets_manager.loader`
**État** : COMPLETE
**Anomalies** : Aucune.

---

## Package : `smoke_bootstrap_recovery/`

### Fichier : `engineering_guardrails.py` (525L)
**Rôle** : Guardrails engineering exécutables — scan AST de tous les `.py` pour violations : FILE_TOO_LONG (>700L), FUNCTION_TOO_LONG (>120L), MISSING_FUTURE_ANNOTATIONS, BARE_EXCEPT, PRINT_IN_SRC, HOTSPOT (>12 violations). Gère les fingerprints acceptées (baseline).
**Inputs** : `src_root: Path`, `policy: EngineeringGuardrailsPolicy`, `baseline_fingerprints: set[str]`
**Outputs** : `GuardrailReport(violations, hotspots, new_violations, baseline_violations)`
**Équations mathématiques** : `fingerprint = sha256(rule_id + file_path + symbol)[:16]`
**Logging** : Aucun.
**Dépendances internes** : Aucune (stdlib only).
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_readiness.py` (~150L)
**Rôle** : Preflight shadow sans ouvrir le runtime Build-11 — vérifie les imports critiques (execution_backbone, calibration_loader, protocols shadow, replay) par importlib.
**Inputs** : `ProfileId`
**Outputs** : `ShadowReadinessReport(core_green, build10_supervision_ready, replay_import_ready, final_verdict)`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `interface_contracts`, `manifest_registry.profile_registry`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `config_validator.py` (~100L)
**Rôle** : Valide la configuration JSON du projet (thresholds, paths, secrets présents).
**Inputs** : `config_path: Path`
**Outputs** : `ConfigValidationReport(valid, errors)`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `interface_contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `bootstrap_runner.py` + `recovery_runner.py` + `smoke_reporter.py` + `smoke_models.py` + `state_sanity_checker.py`
**Rôle global** : Pipeline smoke test + recovery — bootstrap le système, vérifie la sanité des états critiques (calibration artefact frais, heartbeat actif, DB non corrompue), génère un rapport smoke, tente recovery si état invalide.
**État** : Tous COMPLETE.
**Anomalies** : Aucune.

---

## Package : `complete_enablers/`

### Fichier : `hurst_regime_classifier.py` (~80L)
**Rôle** : Classifie l'instabilité de régime à partir de l'exposant de Hurst.
**Inputs** : `Build14ObservationInput(hurst_exponent, edge_degraded_count, break_even_drift_alert)`
**Outputs** : `Build14EnablerSnapshot(regime_instability_score, status)`
**Équations mathématiques** :
```
hurst_distance = |hurst_exponent - 0.50| × 2.0
edge_component = min(edge_degraded_count / 2.0, 1.0)
drift_component = 1.0 if break_even_drift_alert else 0.0
regime_instability_score = 0.55 × hurst_distance + 0.25 × edge_component + 0.20 × drift_component
```
Seuils : CRITICAL ≥ 0.70, ELEVATED ≥ 0.35, NOMINAL < 0.35.
**Logging** : Aucun.
**Dépendances internes** : `complete_enablers.contracts`, `complete_enablers.enums`
**État** : COMPLETE
**Anomalies** : ⚠️ Poids (0.55, 0.25, 0.20) et seuils (0.70, 0.35) hardcodés — doivent passer par calibration seam.

---

### Fichiers : `false_breakout_model.py`, `lob_deep_filter_vwa.py`, `market_toxicity_snapshot.py`, `micro_edge_entry_timing_layer.py`, `micro_edge_exit_governor.py`, `order_book_imbalance.py`, `execution_fragility_score.py`, `limited_influence.py`, `competition_monitor.py`
**Rôle global** : Enablers Build-14 SHADOW_ENABLED — couche de features avancées conditionnellement activées en shadow (false breakout, LOB deep filter volume-weighted average, toxicité marché, timing entry, governor exit, OBI, fragility score, influence limitée, competition monitor).
**Équations** : Chaque module implémente une formule spécifique basée sur microstructure — à documenter individuellement si requis.
**État** : Tous COMPLETE (Build-14 enablers opérationnels).
**Anomalies** : ⚠️ Poids et seuils numériques dans plusieurs modules — à connecter calibration_loader dans S32.

---

## Package : `meta_minimal/`

### Fichier : `meta_runtime.py` (428L)
**Rôle** : Runtime Build-9 — orchestre DTR, CRA, break-even et prudent edge tracking pour chaque décision/trade. Point d'entrée unique du layer meta.
**Inputs** : `DecisionRecord` (trade ou refusal), `ExecutedTradeRecord`
**Outputs** : `MetaRuntimeReport(dtr_summary, cra_report, break_even_report, edge_status)`
**Équations mathématiques** : Délégué aux sous-modules (DTR, CRA, break-even calculator).
**Logging** : structlog — `meta_runtime_decision_recorded`, `meta_runtime_trade_recorded`
**Dépendances internes** : `meta_minimal.dtr_core`, `meta_minimal.cra_monitor`, `meta_minimal.break_even_dashboard`, `meta_minimal.edge_tracker_prudent_minimal`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Sub-packages : `dtr_core/`, `cra_monitor/`, `break_even_dashboard/`, `edge_tracker_prudent_minimal/`, `refusal_journal/`

| Sub-package | Rôle | État |
|---|---|---|
| `dtr_core/` | Decision Trace Record — encode chaque décision (trade/refusal) avec cause chain, persiste JSON. | COMPLETE |
| `cra_monitor/` | Capital Risk Attribution — estime phantom risk, sterilization, réduit le trace par engine/pair. | COMPLETE |
| `break_even_dashboard/` | Calcule break-even réel et théorique par engine/pair, agrège les coûts, génère vues. | COMPLETE |
| `edge_tracker_prudent_minimal/` | Track l'edge prudent — retours agrégés, taille d'échantillon, incertitude Wilson. | COMPLETE |
| `refusal_journal/refusal_journal.py` | Journal des refusals — stocke et relit les events de refus par engine/pair/raison. | COMPLETE |

**Anomalies globales meta_minimal** : Aucune détectée — package complet et cohérent.

---

## Package : `portfolio/` + `portfolio_minimal/`

### `portfolio/__init__.py`
**Rôle** : Package vide (re-export façade) — la logique est dans `portfolio_minimal/`.
**État** : Thin wrapper.

---

### `portfolio_minimal/portfolio_orchestrator.py` (~150L)
**Rôle** : Pipeline d'allocation end-to-end Build-8 en 9 étapes séquentielles (candidats → conflict → rank → select → size → modulate → cap → phantom → report).
**Inputs** : `list[EngineSignal]`, `PortfolioConfig`, `RiskState`
**Outputs** : `AllocationReport(viable_trades, phantom_trades, rejections)`
**Équations mathématiques** :
```
R_i = composite ranking score (délégué comparative_ranker)
size_i = base_size × score_modulation_factor (score_size_mapper)
après caps : gross_cap, cluster_cap, loss_cap, beta_cap (portfolio_cap_applier)
```
**Logging** : `portfolio_allocation_completed`, `portfolio_trade_rejected`
**Dépendances internes** : Tous les sous-modules `portfolio_minimal.*`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Sub-modules `opportunity_selector/` + `allocation_router/`

| Module | Rôle | État |
|---|---|---|
| `candidate_pool_builder.py` | Filtre signaux score > 0 et taille > 0 → pool de candidats | COMPLETE |
| `correlation_conflict_checker.py` | Élimine doublons par corrélation paire — garde le meilleur ranking | COMPLETE |
| `comparative_ranker.py` | Classe candidats par score composite R_i | COMPLETE |
| `eligibility_filter.py` | Vérifie conditions d'éligibilité (sharia, pair santé, etc.) | COMPLETE |
| `selection_resolver.py` | Sélectionne N meilleurs (fail-closed cluster mapping) | COMPLETE |
| `base_size_builder.py` | Taille de base depuis profil | COMPLETE |
| `score_size_mapper.py` | Modulation taille par score tier | COMPLETE |
| `portfolio_cap_applier.py` | Applique caps gross/cluster/loss/beta | COMPLETE |
| `phantom_trade_guard.py` | Stérilise trades non viables | COMPLETE |
| `allocation_reporter.py` | Rapport final viable + phantoms | COMPLETE |

**Anomalies** : Aucune détectée.

---

## Package : `manifest_registry/`

### Fichier : `module_inventory.py` (401L)
**Rôle** : Table canonique de tous les modules V5.3 — nom, couche, propriétaire, statut, priorité, profile_scope (COMMON/LIGHT/COMPLETE), build_stage.
**État** : COMPLETE — source de vérité unique.
**Anomalies** : ⚠️ Utilise encore `ProfileScope.LIGHT` et `ProfileScope.COMPLETE` — en conflit avec doctrine "une seule solution" (2026-04-19). À harmoniser.

---

### Fichier : `profile_registry.py` (~100L)
**Rôle** : Mapping modules → profils actifs (LIGHT/COMPLETE). Expose `is_module_active_in_profile(module, profile)`.
**État** : COMPLETE
**Anomalies** : ⚠️ Mentionne encore LIGHT/COMPLETE profiles — même conflit doctrinal que `module_inventory.py`. **Note** : le docstring dit explicitement "COMPLETE is the governed runtime target for Shadow → Micro-live → Live". LIGHT reste pour compatibilité ascendante. À clarifier avec user si LIGHT doit être supprimé du registre.

---

### Fichiers : `build_order_registry.py`, `dependency_registry.py`, `version_registry.py`
**Rôle** : Registres d'ordre de build, dépendances déclarées, versions des modules.
**État** : COMPLETE
**Anomalies** : Aucune.

---

## Package : `meta/` + `meta_learning/`

### `meta/__init__.py`
**Rôle** : Package vide — façade pour `meta_learning/` et `meta_minimal/`.
**État** : Thin wrapper.

---

### `meta_learning/` (25 fichiers, ~8000L total)
**Rôle global** : Layer d'apprentissage post-trade — review orchestrator, diagnostic engine, mistake classifier, near-miss analyzer, hypothesis registry, improvement candidates, learning memory store, merge gates, checklist generator, lifecycle registry, review queue, replay bundle, retention policy, trade loss attribution, monitoring projection.

| Fichier clé | Rôle | État |
|---|---|---|
| `review_orchestrator.py` (490L) | Orchestre le cycle complet de review post-trade | COMPLETE |
| `post_trade_diagnostic_engine.py` | Diagnostic moteur post-trade (win/loss attribution) | COMPLETE |
| `trade_loss_attribution.py` (421L) | Attribution des pertes par facteur (timing, sizing, signal) | COMPLETE |
| `mistake_classifier.py` | Classe les erreurs (faux signal, mauvais timing, surexposition) | COMPLETE |
| `near_miss_analyzer.py` | Analyse les near-misses (trade bon signal, mauvais momentum) | COMPLETE |
| `merge_gates.py` (515L) | Gates de merge des améliorations dans le système | COMPLETE |
| `persistence_store.py` (491L) | Persistence JSON des learning records | COMPLETE |
| `contracts.py` (684L) | Contrats Pydantic du layer meta learning | COMPLETE |

**Anomalies** : Aucune critique détectée.

---

## Package : `local_replay_runtime/`

### Vue d'ensemble (50+ fichiers, 10 828L)
**Rôle global** : Moteur de replay local — rejoue le système complet sur données historiques pour calibration et audit. Inclut : orchestration replay, simulation exécution shadow, calibration des edge gates, export artefacts, manifest replay, séquences walk-forward.

| Fichier clé | LOC | Rôle | État |
|---|---|---|---|
| `replay_orchestrator.py` | ~200 | Point d'entrée orchestration replay | COMPLETE |
| `replay_orchestrator_execution.py` | 554 | Logique d'exécution replay tick par tick | COMPLETE |
| `replay_orchestrator_chunking.py` | ~150 | Découpage en chunks pour gros datasets | COMPLETE |
| `shadow_execution_simulator.py` | 295 | Simule l'exécution shadow (fills, slippage synthétique) | COMPLETE |
| `edge_gate_calibration.py` | 399 | Calibration des edge gates depuis replay runs | COMPLETE |
| `historical_data_gateway.py` | 281 | Interface données historiques (OHLCV, trades) | COMPLETE |
| `artifact_proof_summary_builder.py` | 507 | Construit la preuve d'artefact (hash, métriques, gate verdicts) | COMPLETE |
| `local_lab_execution_telemetry_artifact.py` | 617 | Artefact telemetry exécution (fills, latence, slippage) | COMPLETE |
| `local_lab_research_priority.py` | 479 | Priorités de recherche (P0/P1/P2 items à investiguer) | COMPLETE |
| `local_lab_loss_surrogate.py` | 401 | Surrogate de loss pour calibration rapide | COMPLETE |

**Anomalies** : `local_lab_execution_telemetry_artifact.py` à 617L — proche cap mais non-bloquant.

---

## Package : `backtest_artifact_import/`

### Vue d'ensemble (14 fichiers, ~4000L)
**Rôle global** : Import sécurisé d'artefacts backtest — vérification signature Ed25519, validation schema, bridge upload vers le registry, gestion compatibilité versions.

| Fichier clé | LOC | Rôle | État |
|---|---|---|---|
| `export_dir_bridge.py` | 683 | Bridge export vers le registry d'artefacts | COMPLETE |
| `validators.py` | 464 | Validation complète des artefacts (schema, hash, plage dates) | COMPLETE |
| `ed25519_verifier.py` | ~100 | Vérification signature Ed25519 sur les artefacts | COMPLETE |
| `contracts.py` | 443 | Contrats Pydantic artefacts backtest | COMPLETE |
| `compatibility_policy.py` | ~80 | Politique de compatibilité versions artefacts | COMPLETE |
| `signature_policy.py` | ~60 | Politique signature (obligatoire en prod, optionnelle en dev) | COMPLETE |

**Anomalies** : Aucune.

---

## Package : `contract_test_suite/`

### Vue d'ensemble (6 fichiers)
**Rôle global** : Suite de tests de contrats — vérifie la compatibilité backward des contrats Pydantic entre versions, génère des rapports de compatibilité.

| Fichier | Rôle | État |
|---|---|---|
| `contract_test_runner.py` | Exécute les tests de contrat | COMPLETE |
| `compatibility_checker.py` | Vérifie compatibilité champs Pydantic entre versions | COMPLETE |
| `schema_assertions.py` | Assertions schema (champs requis, types) | COMPLETE |
| `negative_case_runner.py` | Tests cas négatifs (invalides rejetés) | COMPLETE |
| `contract_models.py` | Modèles pour les résultats de test | COMPLETE |
| `contract_reporter.py` | Génère rapport Markdown compatibilité | COMPLETE |

**Anomalies** : Aucune.

---

## Synthèse Groupe E

### Bug `governed_extensions` — lignes exactes

```python
# À SUPPRIMER (duplication) dans src/ui/technical_dashboard_view.py :
# L1082-1086 (section "System")
DashboardCard(
    key="governed_extensions",
    ...
    value=_governed_extensions_value(payload),
    status=_governed_extensions_status(payload),
    detail=payload.system.governed_extensions_detail,
)
# À CONSERVER : L1050-1052 (section "Extensions")
```

---

### dag_validator — vérifications exactes

Le `dag_validator` vérifie :
1. **Cycles** dans le DAG d'imports (DFS WHITE/GRAY/BLACK)
2. **Violations de couche** (engines ne peut pas importer protocols, etc.)
3. **Imports non-déclarés** dans le manifest
4. **Déclarations inutilisées** dans le manifest
5. **Imports dynamiques** (`importlib.import_module`, `__import__`) — GEM-03

---

### secrets_manager — mécanisme

- **Backend** : Windows DPAPI (`ctypes.windll.crypt32`) — chiffrement lié à la session user Windows
- **Fichier envelope** : JSON `{schema_version, backend, source_name, created_at, ciphertext_b64}`
- **Entropy** : fichier clé externe séparé (`key_path`)
- ⚠️ **Non portable Linux VPS** — sur VPS, backend alternatif requis (env vars ou vault externe)

---

### Alerte doctrinale — LIGHT/COMPLETE dans manifest_registry/

`module_inventory.py` et `profile_registry.py` utilisent encore `ProfileScope.LIGHT` et `ProfileScope.COMPLETE`.
→ Le `profile_registry.py` docstring dit que COMPLETE est le target governed mais conserve LIGHT pour compatibilité.
→ **Action S32** : harmoniser avec doctrine "une seule solution complète" — décision user requise.

---

### Fichiers SKELETON ou PARTIAL

**Aucun** dans Groupe E — tous les packages analysés sont COMPLETE.

---

### Anomalies critiques (priorité)

| Priorité | Package | Fichier | Nature |
|---|---|---|---|
| P0 | `ui/` | `technical_dashboard_view.py` L1082-1086 | **Bug duplication `governed_extensions`** — card double |
| P1 | `secrets_manager/` | `_dpapi.py` | DPAPI Windows-only — non portable VPS Linux |
| P1 | `manifest_registry/` | `module_inventory.py`, `profile_registry.py` | Conflit doctrinal LIGHT/COMPLETE (doctrine "une seule solution" 2026-04-19) |
| P2 | `complete_enablers/` | `hurst_regime_classifier.py` + autres | Poids et seuils hardcodés — seam calibration manquant |
| P2 | `ui/` | `technical_dashboard_view.py` (1940L), `technical_dashboard_html.py` (1271L), `complete_dashboard_view.py` (652L) | God files UI — baselined (non-runtime) |

---

### Recommandations sprints suivants (S32+)

1. **Fix P0 immédiat** : supprimer card `governed_extensions` dupliquée (L1082-1086) — 5 min Codex
2. **S32** : solution VPS pour secrets_manager (env vars wrapper ou vault) — requis avant déploiement VPS Linux
3. **S32** : harmoniser `manifest_registry/` avec doctrine "une seule solution" — décision user sur LIGHT
4. **S32** : connecter `complete_enablers/` poids/seuils au `calibration_loader` (seams manquants)
5. **S33** : `meta_learning/` review orchestrator — vérifier intégration avec `local_replay_runtime/` (replay bundle builder)
