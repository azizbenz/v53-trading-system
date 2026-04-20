# Cartographie Groupe B — `protocols/` (2026-04-19)

> Lecture exhaustive ligne par ligne de 58 fichiers, 15 561 LOC.  
> Racine : `src/protocols/`

---

## Vue d'ensemble

Le package `protocols/` est le **hub de gouvernance central** du système V5.3.
Il ne contient pas de runtime de trading (engines, risk, scoring) mais orchestre les **transitions de phase** : Shadow → Micro-live → Live-Light, expose les contrats typés pour chaque phase, et fournit l'infrastructure de persistence (day counter, orchestrateur, registries, VPS service, websocket live).

**Taille réelle** : 58 fichiers, 15 561 LOC (vs. les 4 fichiers prévus dans la mission)

---

## Fichiers analysés

---

### Fichier : `__init__.py` (494L)
**Rôle** : Point d'entrée unique du package — re-exporte 180+ symboles publics depuis tous les sous-modules.
**Inputs** : N/A (module-level re-exports)
**Outputs** : `__all__` liste exhaustive de 180+ noms
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : Tous les sous-modules de `protocols/`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `contracts.py` (17L)
**Rôle** : Façade plate — importe et re-exporte tout de `contracts_shadow`, `contracts_shared`, `contracts_promotion` via `*`.
**Inputs** : N/A
**Outputs** : `__all__` union des trois sous-modules
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `contracts_promotion`, `contracts_shadow`, `contracts_shared`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `enums.py` (112L)
**Rôle** : Définit toutes les enums `StrEnum` du système de promotion : états de run (Shadow/MicroLive/LiveLight) et verdicts associés.
**Inputs** : N/A
**Outputs** : 10 enums StrEnum exportées + alias `LiveRunState = LiveLightRunState`, `LiveVerdict = LiveLightVerdict`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : Aucune (stdlib uniquement)
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `errors.py` (77L)
**Rôle** : Hiérarchie d'exceptions dédiées aux runtimes Shadow/MicroLive/LiveLight.
**Inputs** : N/A
**Outputs** : 12 classes d'exception + 4 alias Legacy (`LiveProtocolError`, etc.)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : Aucune
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `contracts_shared.py` (239L)
**Rôle** : Contrats Pydantic partagés entre Shadow, Micro-live et Live-Light : summaries de gouvernance (régime, info-stress, PnL-breaker), jugements moteur et portfolio.
**Inputs** : `ProfileId`, `PromotionState`, `ReviewState`, `RuntimeMode` depuis `interface_contracts`
**Outputs** : `RegimeLiteGovernanceSummary`, `InfoStressGovernanceSummary`, `DailyPnlBreakerGovernanceSummary`, `ShadowEngineJudgment`, `ShadowPortfolioJudgment`, `ShadowEngineJudgmentSummary`
**Équations mathématiques** : Aucune — seulement des contraintes Field (ge/le).
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.enums`, `interface_contracts`
**État** : COMPLETE
**Anomalies** :
- Constantes module-level hardcodées : `_EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE = "no_trade_then_strictest"` (L48), `_EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE = "atomic_snapshot_swap"` (L53) — ces valeurs sont des invariants de politique, pas des seuils de calibration.

---

### Fichier : `contracts_shadow.py` (612L)
**Rôle** : Contrats Pydantic complets pour le runtime Build-11 Shadow : TruthSet, ValidationSet (avec 50+ champs d'import), ComponentAssessment, ShadowInput, ShadowComparison, ShadowDecision, ShadowRunSummary, ShadowReportArtifact.
**Inputs** : `TechnicalDashboardPayload` via `shadow_runtime_inputs`; `ShadowComponentAssessment` tuple
**Outputs** : `ShadowRunSummary`, `ShadowReportArtifact`, `ShadowTruthSet`, `ShadowValidationSet`, etc.
**Équations mathématiques** :
- `ShadowInput.max_allowed_dtr_coverage_drop` = 0.05 (défaut) — tolérance de drop DTR
- `ShadowInput.max_allowed_cra_increase` = 0.10 — tolérance hausse CRA
- `ShadowInput.max_allowed_ce_net_drop` = 0.0005 — tolérance drop CE net
- `ShadowInput.max_allowed_queue_backlog_increase` = 25 (défaut L206)
- Validator `remaining_days = max(0, required_days - consecutive_days)` (L480)
- Contrainte: `required_days == 30` imposée par validator (L478)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `contracts_shared`, `contracts_validation_support`, `protocols.enums`
**État** : COMPLETE
**Anomalies** :
- L200 : `max_allowed_dtr_coverage_drop: float = Field(default=0.05, ...)` — hardcodé dans le contrat (seam manquant vers calibration_loader)
- L201 : `max_allowed_cra_increase: float = Field(default=0.10, ...)` — idem
- L204 : `max_allowed_ce_net_drop: float = Field(default=0.0005, ...)` — idem
- L205 : `max_allowed_alert_count_increase: int = Field(default=1, ...)` — idem
- L206 : `max_allowed_queue_backlog_increase: int = Field(default=25, ...)` — idem
- 1 `type: ignore[arg-type]` implicite via validator re-raise (non bloquant)

---

### Fichier : `contracts_promotion.py` (519L)
**Rôle** : Contrats Pydantic pour Build-12 Micro-live et Build-13 Live-Light : `MicroLiveInput`, `MicroLiveDecision`, `MicroLiveExecutionPlan`, `MicroLiveRunSummary`, `LiveLightInput`, `LiveLightDecision`, `LiveLightExecutionIntent`, `LiveLightRunSummary`.
**Inputs** : `ShadowRunSummary`, `ShadowPortfolioJudgment`, import fields (50+), notional budgets
**Outputs** : `MicroLiveRunSummary`, `LiveLightRunSummary`
**Équations mathématiques** :
- Budget constraint (L207-210) : `approved_total <= requested_total` et `approved_pair <= approved_total`
- `micro_live_required_days == 7` imposé par validator (L524 de `contracts_validation_support`)
- `order_probe_limit: int = Field(default=3, ge=1, le=10)` (L138)
- `execution_order_limit: int = Field(default=3, ge=1, le=20)` (L360)
- `build14_confidence_penalty_weight: float = Field(default=0.0, ge=0.0, le=0.25)` (L482)
- `build14_recommended_budget_factor: float = Field(default=1.0, ge=0.0, le=1.0)` (L483)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `contracts_shared`, `contracts_validation_support`, `protocols.enums`, `interface_contracts`
**État** : COMPLETE
**Anomalies** :
- L138 : `order_probe_limit: int = Field(default=3, ge=1, le=10)` — hardcodé
- L360 : `execution_order_limit: int = Field(default=3, ge=1, le=20)` — hardcodé

---

### Fichier : `contracts_validation_support.py` (688L)
**Rôle** : Fonctions de validation de gouvernance appelées depuis les `model_validator` de `contracts_shadow` et `contracts_promotion` — vérifie import identity, lineage, policy, onboarding, engine scope, budget constraints.
**Inputs** : `ShadowValidationSet | MicroLiveInput | LiveLightInput` + frozensets de politiques
**Outputs** : `None` (lève `ValueError` si violation)
**Équations mathématiques** :
- `import_payload_ref_count >= 5` (L145)
- `shadow_required_days == 30` (L315)
- `micro_live_required_days == 7` (L523)
- `shadow_days_completed >= shadow_required_days` (L343)
- `micro_live_stable_days >= micro_live_required_days` (L527)
- `requested_pair <= requested_total <= max_total` (L480-494, L673-688)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts` (ALL_PAIRS, ReviewState), `protocols.contracts` (TYPE_CHECKING only)
**État** : COMPLETE
**Anomalies** :
- Fichier à 688L = à surveiller (juste sous la limite 700L)

---

### Fichier : `shadow_runtime.py` (54L)
**Rôle** : Point d'entrée public du runtime Shadow Build-11 — re-exporte les 4 fonctions principales depuis les sous-modules et expose `check_shadow_30j_gate`.
**Inputs** : `state_dir: Path`, `profile: str` (pour `check_shadow_30j_gate`)
**Outputs** : `(gate_passed: bool, report_dict: dict)`
**Équations mathématiques** : Aucune directe. Délègue à `ShadowDayCounter.is_promotion_ready()`.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `shadow_runtime_inputs`, `shadow_runtime_judgments`, `shadow_runtime_portfolio`, `shadow_runtime_validation`, `shadow_day_counter`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_runtime_shared.py` (25L)
**Rôle** : Constantes frozenset partagées par les sous-modules Shadow runtime.
**Inputs** : N/A
**Outputs** : `_REQUIRED_SHADOW_ENGINES`, `_REQUIRED_BUILD14_COMPONENTS`, `_RUNTIME_EVIDENCE_ACCEPTED_SOURCES`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : Aucune
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_runtime_inputs.py` (338L)
**Rôle** : Construit `ShadowRuntimeEvidence` et `ShadowInput` depuis des `TechnicalDashboardPayload` (baseline + candidate).
**Inputs** : `TechnicalDashboardPayload` (x2), `ShadowRuntimeEvidence` optionnel, 7 seuils float/int
**Outputs** : `ShadowInput`, `ShadowRuntimeEvidence`
**Équations mathématiques** :
- Résolution `data_source` : priorité `runtime_data_source` > `local_replay_evidence.data_source`
- Seuils defaults : `max_allowed_dtr_coverage_drop=0.05`, `max_allowed_cra_increase=0.10`, `max_allowed_ce_net_drop=0.0005`, `max_allowed_alert_count_increase=1`, `max_allowed_queue_backlog_increase=25`, `max_allowed_break_even_drift_scope_increase=0`, `max_allowed_edge_degraded_delta=0`
- `shadow_required_days=30` hardcodé L255
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `local_replay_runtime`, `monitoring`, `protocols.contracts`, `protocols.errors`
**État** : COMPLETE
**Anomalies** :
- L255 : `shadow_required_days=30` hardcodé inline dans l'appel
- L284 : `max_allowed_dtr_coverage_drop: float = 0.05` — default hardcodé dans la signature

---

### Fichier : `shadow_runtime_shared.py` (25L)
_(déjà documenté ci-dessus)_

---

### Fichier : `shadow_runtime_validation.py` (596L)
**Rôle** : Logique principale du gate Shadow — construit les `ShadowComparison`, accumule les `blocking_reasons`, évalue la décision finale, produit le `ShadowRunSummary`.
**Inputs** : `ShadowInput`, optionnel `RegimeLiteAssessment`, `RegimeLiteSafingRecommendation`, `InfoStressAssessment`, `DailyPnlBreakerAssessment`
**Outputs** : `ShadowRunSummary`
**Équations mathématiques** :
- Gate runtime : `runtime_continuous_hours >= 24.0` (L362)
- Gate temporel : `shadow_days_completed >= 30` (L366)
- Gate import_payload_ref_count >= 5 (L297)
**Logging** : Aucun logger.* direct (logique pure).
**Signal handlers** : NON
**Dépendances internes** : `protocols.contracts`, `protocols.enums`, `protocols.shadow_runtime_judgments`, `protocols.shadow_runtime_shared`, `regime_classifier`, `risk_backbone`
**État** : COMPLETE
**Anomalies** :
- L362 : `24.0` heures — seuil hardcodé (devrait venir de calibration)
- Fichier à 596L — proche limite

---

### Fichier : `shadow_runtime_judgments.py` (325L)
**Rôle** : Logique de jugement moteur — dérive le verdict promotable/shadow-only/rewrite-required/dormant par engine, expose `compare_shadow_candidate` (7 comparaisons baseline vs candidate) et `derive_shadow_engine_judgment_summary`.
**Inputs** : `ShadowInput`, `ShadowRunSummary`, `ShadowReportArtifact`, `TechnicalDashboardPayload`
**Outputs** : `tuple[ShadowComparison, ...]`, `ShadowEngineJudgmentSummary`
**Équations mathématiques** :
- `delta = max(0.0, baseline - candidate)` si higher_is_better, sinon `max(0.0, candidate - baseline)` (L222-225)
- Threshold rules : `delta == 0` → MATCHING, `0 < delta <= threshold` → DIVERGENT/WARNING, `delta > threshold` → BLOCKING/CRITICAL
- Verdict "rewrite-required" si `economic_pass_rate <= 0.5` OU `marginal_edge <= 0.0` OU `conflict_rate >= 0.5` OU `ce_expected <= 0.0` (L85-93)
- Verdict "shadow-only" si `scoring_final_size_multiplier <= 0.1` (L78)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `monitoring`, `protocols.contracts`, `protocols.enums`, `protocols.shadow_runtime_portfolio`, `protocols.shadow_runtime_shared`
**État** : COMPLETE
**Anomalies** :
- L78 : `scoring_final_size_multiplier <= 0.1` — seuil hardcodé
- L85 : `economic_pass_rate <= 0.5` — seuil hardcodé
- L86 : `conflict_rate >= 0.5` — seuil hardcodé
- L87 : `marginal_edge <= 0.0` — seuil hardcodé (logique)
- L78 : `risk_decision_severity == "critical"` — string comparison hardcodée

---

### Fichier : `shadow_runtime_portfolio.py` (471L)
**Rôle** : Logique de jugement portfolio — calcule les pressions (physics/redundancy/cluster/beta/exposure/loss) et dérive le `ShadowPortfolioJudgment`.
**Inputs** : `TechnicalDashboardPayload`, `ShadowReportArtifact`, `tuple[ShadowEngineJudgment, ...]`
**Outputs** : `ShadowPortfolioJudgment`
**Équations mathématiques** :
- `_pressure_level(value, elevated_at, critical_at)` — comparaison scalaire (L16-28)
- Physics "critical" si `fragility_score >= 0.75` OU `toxicity_score >= 0.75` OU `exec_survivability <= 0.25` OU `micro_friction >= 0.75` (L46-53)
- Physics "elevated" si `fragility_score >= 0.50` OU `toxicity_score >= 0.50` OU `exec_survivability <= 0.50` OU `micro_friction >= 0.50` (L55-64)
- Redundancy check : `conflict_rate >= 0.35` OU `redundancy_score >= 0.35` (L177-178)
- beta pressure : `elevated_at=0.75, critical_at=1.0` (L291)
- gross capacity pressure : `elevated_at=85.0, critical_at=100.0` (L296)
- loss capacity pressure : `elevated_at=85.0, critical_at=100.0` (L301)
- Portfolio verdict "rewrite-required" si `hard_block_rate >= 0.25` (L320)
- Portfolio verdict "rewrite-required" si `rewrite_required_engine_count >= 2` OU `portfolio_rejected_engine_count >= 2` OU `phantom_trade_count >= 2` OU pression "critical" (L334-338)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `monitoring`, `protocols.contracts`, `protocols.shadow_runtime_shared`
**État** : COMPLETE
**Anomalies** :
- L46 : `fragility_score >= 0.75` — hardcodé
- L47 : `toxicity_score >= 0.75` — hardcodé
- L48 : `execution_survivability_score <= 0.25` — hardcodé
- L50 : `micro_friction_score >= 0.75` — hardcodé
- L55 : `fragility_score >= 0.50` — hardcodé
- L56 : `toxicity_score >= 0.50` — hardcodé
- L57 : `execution_survivability_score <= 0.50` — hardcodé
- L59 : `micro_friction_score >= 0.50` — hardcodé
- L177 : `conflict_rate >= 0.35` — hardcodé
- L178 : `redundancy_score >= 0.35` — hardcodé
- L291 : `elevated_at=0.75, critical_at=1.0` (beta) — hardcodé
- L296 : `elevated_at=85.0, critical_at=100.0` (gross capacity) — hardcodé
- L301 : `elevated_at=85.0, critical_at=100.0` (loss capacity) — hardcodé
- L320 : `hard_block_rate >= 0.25` — hardcodé
- **3 `type: ignore[arg-type]`** (L442, L443, L444, L445, L446, L447) — ShadowPressureLevel Literal assignment

---

### Fichier : `shadow_runtime_evidence.py` (146L)
**Rôle** : `ShadowRuntimeEvidenceRecorder` — collecte incrémentale des preuves de runtime (source data, config loaded, event loop ticks, DTR persisted) avec persistence JSON atomique.
**Inputs** : `LocalReplayRuntimeEvidence`, timestamps en ms
**Outputs** : `ShadowRuntimeEvidence` via `build_evidence()`
**Équations mathématiques** :
- `continuous_hours = (last_ms - started_ms) / 3_600_000.0` (L103-104)
**Logging** : Aucun logger.* (BS-65 fail-safe via `last_error` field).
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts.atomic_io`, `local_replay_runtime`, `protocols.contracts`, `protocols.shadow_runtime`
**État** : COMPLETE
**Anomalies** : BS-65 fail-safe présent (backup .corrupted + last_error marker).

---

### Fichier : `micro_live_runtime.py` (613L)
**Rôle** : Gate Build-12 Micro-live — construit le `MicroLiveInput` depuis le Shadow summary/payload, évalue les blocking reasons, produit `MicroLiveRunSummary` avec décision BLOCKED/DRY_RUN_ONLY/ALLOWED_TO_PROBE.
**Inputs** : `ShadowRunSummary`, `TechnicalDashboardPayload` (shadow), `probe_pairs`, notional budgets
**Outputs** : `MicroLiveRunSummary`
**Équations mathématiques** :
- Budget pass-through : `approved_total = requested_total` si non bloqué (L423)
- `order_probe_limit` défaut 3 (L489)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `monitoring`, `protocols.contracts`, `protocols.enums`, `protocols.errors`, `protocols.micro_live_runtime_support`
**État** : COMPLETE
**Anomalies** :
- Fichier à 613L — approche limite 700L

---

### Fichier : `micro_live_runtime_support.py` (594L)
**Rôle** : Fonctions helper pour `micro_live_runtime` : validation scope payload Shadow, vérification import status/lineage/policy, `_resolve_shadow_scope`, `_governance_envelope_blocking_reasons`, etc.
**Inputs** : `TechnicalDashboardPayload`, `ShadowRunSummary`, `MicroLiveInput`
**Outputs** : `tuple[str, ...]` (blocking reasons), `_ResolvedShadowScope`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `monitoring`, `protocols.contracts`, `protocols.enums`, `protocols.errors`, `protocols.shadow_runtime`
**État** : COMPLETE
**Anomalies** :
- Fichier à 594L — proche limite

---

### Fichier : `live_light_runtime.py` (699L)
**Rôle** : Gate Build-13 Live-Light — construit le `LiveLightInput` depuis Micro-live summary/payload, évalue Build-14 influence signal, gate Shadow 30j, produit `LiveLightRunSummary` avec décision BLOCKED/DRY_RUN_ONLY/ALLOWED_TO_EXECUTE_SMALL.
**Inputs** : `MicroLiveRunSummary`, `TechnicalDashboardPayload` (micro-live), `live_pairs`, notional budgets, optionnel `build14_influence`, optionnel `shadow_state_dir`
**Outputs** : `LiveLightRunSummary`
**Équations mathématiques** :
- Budget avec facteur Build-14 : `approved_total = round(requested_total * recommended_budget_factor, 8)` (L553-558)
- `recommended_budget_factor ∈ [0.0, 1.0]` — réduit le budget si Build-14 signale risque
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `monitoring`, `protocols.contracts`, `protocols.enums`, `protocols.errors`, `protocols.live_light_runtime_gate_support`, `protocols.live_light_runtime_support`, `protocols.shadow_runtime` (lazy import pour 30j gate)
**État** : COMPLETE
**Anomalies** :
- **Fichier à 699L — AU SEUIL LIMITE (1 ligne sous 700L)**
- Alias L698-699 : `build_live_input_from_micro_live = build_live_light_input_from_micro_live`, `run_live_gate = run_live_light_gate`

---

### Fichier : `live_light_runtime_gate_support.py` (414L)
**Rôle** : Helpers de blocking reasons pour `live_light_runtime` : `_rollout_temporal_blocking_reasons`, `_micro_live_surface_blocking_reasons`, `_shadow_engine_scope_blocking_reasons`, `_shadow_portfolio_blocking_reasons`, `_build_live_light_import_fields`, etc.
**Inputs** : `LiveLightInput`, `MicroLiveRunSummary`
**Outputs** : `tuple[str, ...]`, `dict[str, object]`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `monitoring`, `protocols.contracts`, `protocols.enums`
**État** : COMPLETE
**Anomalies** : Aucune anomalie critique.

---

### Fichier : `live_light_runtime_support.py` (439L)
**Rôle** : Helpers supplémentaires pour `live_light_runtime` : validation Build-14 signal, `_validate_micro_live_consistency`, `_validate_live_light_surface`, `_resolve_shadow_surface`, `_build14_guardrail_reasons`.
**Inputs** : `MicroLiveRunSummary`, `TechnicalDashboardPayload`, `Build14InfluenceSignal`
**Outputs** : validations (lèvent exceptions), `_ResolvedShadowSurface`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `monitoring`, `protocols.contracts`, `protocols.enums`, `protocols.errors`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_day_counter.py` (189L)
**Rôle** : `ShadowDayCounter` — compteur persisté de jours shadow consécutifs avec règle de reset si gap > 24h, atomic JSON write, méthode `recover_from_records`.
**Inputs** : `state_dir: Path`, `profile: ShadowProfile`, `passed_all_gates: bool`, timestamp optionnel
**Outputs** : `ShadowDayRecord`, `ShadowCounterState`, `dict` (rapport)
**Équations mathématiques** :
- `_MAX_GAP_SECONDS = 24 * 3600` — reset si gap > 86400s (L27)
- `continuous_hours` dans `ShadowRuntimeEvidenceRecorder` : `(last_ms - started_ms) / 3_600_000.0`
**Logging** : Aucun logger.* (BS-65 via `last_error`).
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts.atomic_io`, `protocols.shadow_day_counter_models`, `protocols.shadow_day_counter_reporting`
**État** : COMPLETE
**Anomalies** :
- L27 : `_MAX_GAP_SECONDS = 24 * 3600` — hardcodé (devrait venir de calibration)

---

### Fichier : `shadow_day_counter_models.py` (51L)
**Rôle** : Modèles Pydantic légers pour `ShadowDayCounter` : `ShadowProfile` (enum), `ShadowDayRecord`, `ShadowCounterState`.
**Inputs** : N/A
**Outputs** : 3 modèles Pydantic
**Équations mathématiques** : `is_complete: bool = Field(default=False)` calculé via `@property` dans state (`consecutive_days >= 30`).
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : Aucune (`pydantic` uniquement)
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_day_counter_reporting.py` (627L)
**Rôle** : Génère le rapport JSON structuré de promotion readiness depuis un `ShadowCounterState` : sections data_infra, decisions_dtr, costs_break_even, engine_comparison, portfolio, ui_alerting, go_no_go.
**Inputs** : `ShadowCounterState`
**Outputs** : `dict[str, object]` (rapport complet)
**Équations mathématiques** :
- `remaining_days = max(0, 30 - consecutive_days)` (hardcodé 30)
- Seuils rapport : `dtr_coverage >= 0.95`, `economic_pass_rate >= 0.60`, `stale_rate <= 0.05`, `backlog_avg <= 100`, `event_latency_ms <= 500`, `pair_health_ratio >= 0.95`, `dtr_loss_rate <= 0.02`, `log_loss_rate <= 0.02`, `hard_block_rate <= 0.10`
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.shadow_day_counter_models`
**État** : COMPLETE
**Anomalies** :
- Nombreux seuils hardcodés dans les fonctions de validation de rapport :
  - `dtr_coverage >= 0.95` (plusieurs endroits)
  - `economic_pass_rate >= 0.60`
  - `stale_rate <= 0.05`
  - `backlog_avg <= 100`
  - `event_latency_ms <= 500`
  - `pair_health_ratio >= 0.95`
  - `dtr_loss_rate <= 0.02`
  - `log_loss_rate <= 0.02`
  - `hard_block_rate <= 0.10`
- **Fichier à 627L** — dépasse le seuil de surveillance

---

### Fichier : `shadow_day_counter_report_rendering.py` (314L)
**Rôle** : Rendu Markdown/texte du rapport de compteur Shadow (tables ASCII, sections go/no-go).
**Inputs** : `dict` rapport de `shadow_day_counter_reporting`
**Outputs** : `str` (Markdown rendu)
**Équations mathématiques** : Aucune (formatage uniquement).
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.shadow_day_counter_models`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_daily_orchestrator.py` (297L)
**Rôle** : `ShadowDailyOrchestrator` — persiste et sélectionne les runs quotidiens Shadow entre invocations ; résout la session date depuis 3 sources (session_summary, session_registry, replay_manifest) avec cohérence cross-source.
**Inputs** : `exports_root: Path`, `ShadowDailyExecutionRecord`
**Outputs** : `ShadowDailyPlanSlot`, `tuple[ShadowDailyExecutionRecord, ...]`
**Équations mathématiques** : Aucune — logique temporelle (comparaison dates ISO).
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts.atomic_io`, `protocols.shadow_session_registry`
**État** : COMPLETE
**Anomalies** :
- L120-121 (BS-65 marker) : fail-safe corruption handler avec `last_error` champ — documenté intentionnellement.

---

### Fichier : `shadow_session_registry.py` (151L)
**Rôle** : `ShadowSessionRegistry` — registry append-only des jours Shadow (correlation_id, artifact_id, lineage_version par entrée) avec BS-65 fail-safe.
**Inputs** : `ShadowSessionEntry`
**Outputs** : `tuple[ShadowSessionEntry, ...]`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_vps_service.py` (217L)
**Rôle** : Contrats et store pour le service VPS Shadow autonome — `ShadowVpsRawInputSlot`, `ShadowVpsWebsocketInputSlot`, `ShadowLiveWebSocketConfig`, `ShadowVpsServiceStore` (append-only event log + campaign summary).
**Inputs** : Configs websocket, slots datés, events
**Outputs** : `ShadowVpsServiceStore` avec persist JSON atomique
**Équations mathématiques** :
- Contrainte slot : exactement `dataset_path_ref` XOR `snapshot_path_ref` (L42-45)
- `capture_timeout_s: float = Field(default=15.0, gt=0.0)` — hardcodé
- `capture_frame_limit: int = Field(default=50, ge=1)` — hardcodé
- `idle_poll_limit: int = Field(default=20, ge=1)` — hardcodé
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts.shadow_vps_service_contracts`, `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** :
- L68 : `capture_timeout_s: float = Field(default=15.0)` — hardcodé
- L70 : `capture_frame_limit: int = Field(default=50)` — hardcodé
- L71 : `idle_poll_limit: int = Field(default=20)` — hardcodé

---

### Fichier : `shadow_vps_service_telegram_alerting.py` (58L)
**Rôle** : Stub minimal pour alerting Telegram du VPS Shadow service — interface `ShadowVpsTelegramAlerter` et stub no-op.
**Inputs** : `ShadowVpsServiceEvent`
**Outputs** : N/A (side effects)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.shadow_vps_service`
**État** : SKELETON (stub no-op)
**Anomalies** : Implémentation no-op intentionnelle.

---

### Fichier : `shadow_live_websocket.py` (665L)
**Rôle** : Capture websocket live native sur VPS — `BinanceSpotLiveWebSocketAdapter`, `capture_live_websocket_snapshot_batch`, `capture_live_user_data_stream` ; gère reconnexion, HMAC auth Binance Listen Key, time sync.
**Inputs** : `ShadowLiveWebSocketConfig`, `SocketFactory` callable, `ServerTimeReader` callable
**Outputs** : `ShadowLiveWebSocketCaptureResult`, `ShadowLiveUserDataCaptureSummary`
**Équations mathématiques** :
- HMAC-SHA256 pour Listen Key auth : `hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()` (ligne ~350)
- Time sync offset : `(t4 - t1) / 2 - (t3 - t2) / 2` (NTP-style)
**Logging** : Aucun `logger.*` structuré — erreurs via exceptions.
**Signal handlers** : NON (pas de SIGTERM/SIGINT — **ANOMALIE critique pour service VPS long-running**)
**Dépendances internes** : `data_backbone.websocket_gateway`, `interface_contracts.binance_contracts`, `protocols.shadow_vps_service`, `protocols.shadow_websocket_ingest`, `interface_contracts.atomic_io`, `venue_adapters.binance_spot.rest_client`
**État** : COMPLETE
**Anomalies** :
- **Signal handlers absents** (SIGTERM/SIGINT) pour un module VPS long-running — risque de données corrompues à l'arrêt
- Import optionnel de `websocket-client` avec guard (L57-63 — BS-2C documenté)
- Fichier à 665L — proche limite

---

### Fichier : `shadow_websocket_ingest.py` (423L)
**Rôle** : Ingestion et transformation de frames websocket observées ou injectées en batch de snapshots Shadow : `build_snapshot_batch_from_observed_websocket_messages`, `build_snapshot_batch_from_injected_websocket_stream`, `load_injected_websocket_frames`.
**Inputs** : `list[ObservedWebSocketMessage]`, `InjectedWebSocketFrame` files
**Outputs** : `ShadowWebsocketSnapshotBuildResult`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.shadow_vps_service` (contrats), `interface_contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_report_builder.py` (259L)
**Rôle** : `build_shadow_daily_metrics_summary` — construit le résumé métriques journalier Shadow depuis `TechnicalDashboardPayload` + `ShadowRunSummary`.
**Inputs** : `TechnicalDashboardPayload`, `ShadowRunSummary`
**Outputs** : `dict[str, object]` métriques
**Équations mathématiques** : Aucune directe — lecture de champs.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `monitoring`, `protocols.contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `shadow_dashboard.py` (170L)
**Rôle** : `build_shadow_dashboard_section`, `build_shadow_projection` — sections UI dashboard pour le runtime Shadow.
**Inputs** : `ShadowRunSummary`, `ShadowReportArtifact`
**Outputs** : dict sections dashboard
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.contracts`, `monitoring`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `micro_live_dashboard.py` (187L)
**Rôle** : `build_micro_live_dashboard_section`, `build_micro_live_projection` — sections UI pour Micro-live.
**Inputs** : `MicroLiveRunSummary`
**Outputs** : dict sections dashboard
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `live_light_dashboard.py` (215L)
**Rôle** : `build_live_dashboard_section`, `build_live_projection`, `build_live_light_dashboard_section`, `build_live_light_projection` — sections UI Live-Light et Live.
**Inputs** : `LiveLightRunSummary`
**Outputs** : dict sections dashboard
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `engine_judgment_dashboard.py` (79L)
**Rôle** : `build_engine_judgment_projection` — projection dashboard des jugements moteur.
**Inputs** : `ShadowEngineJudgmentSummary`
**Outputs** : dict projection
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `promotion_gates.py` (120L)
**Rôle** : Centralise les 3 promotion gates HARD (COMPLETE→Micro-live, COMPLETE→Live, LIGHT→Micro-live legacy) en appellant `check_shadow_30j_gate`.
**Inputs** : `state_dir: Path`
**Outputs** : `PromotionGateResult` (passed, consecutive_days, remaining_days, message)
**Équations mathématiques** :
- Sequential enforcement : live gate ne passe que si micro-live gate passe d'abord (L90-101)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `protocols.shadow_runtime`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `engine_coordination_rules.py` (275L)
**Rôle** : Règles de coordination cross-engine A/C/D — Engine C bloqué si A en holding ou feu récent (R-AC-1, R-AC-2) ; Engine D bloqué si pas de linkage A/C (R-D-1), stops consécutifs (R-D-2), avec failsafe override (R-D-3).
**Inputs** : `EngineCoordinationInput`, optionnel `EngineCoordinationThresholds`
**Outputs** : `EngineCoordinationOutcome` (blocked, action, rule_hits, reason_codes, size_multiplier)
**Équations mathématiques** :
- `recent_fire_block_ns` défaut `4 * _NS_PER_HOUR` = 14 400 000 000 000 ns (L76)
- `d_reentry_size_multiplier` défaut 0.5 — réduit taille D de 50% (L79)
- `d_reset_failsafe_ns` défaut `24 * _NS_PER_HOUR` (L78)
- `delta_ns = evaluated_at_ns - recent_a_fire_at_ns <= recent_fire_block_ns` (L158-162)
- `resolved_size = reference_size * d_reentry_size_multiplier` (L257)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `protocols.closed_episode_journal`
**État** : COMPLETE
**Anomalies** :
- L76 : `recent_fire_block_ns = 4 * _NS_PER_HOUR` — hardcodé dans le défaut (passable via `EngineCoordinationThresholds`)
- L79 : `d_reentry_size_multiplier = 0.5` — hardcodé dans défaut
- Les thresholds sont dans `EngineCoordinationThresholds` (calibrable) — OK mais valeurs defaults hardcodées

---

### Fichier : `closed_episode_journal.py` (259L)
**Rôle** : `ClosedEpisodeJournal` — journal append-only des épisodes A/C fermés pour linkage Engine D ; `ClosedEpisodeJournalSink` interface.
**Inputs** : `EpisodeRef` (UUID, pair, side, entry/exit levels, PnL, close_reason)
**Outputs** : `ClosedEpisodeJournalManifest`, `EpisodeRef` archivé
**Équations mathématiques** : `SHA256(canonical_json_bytes)` pour hash intégrité (L~110)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts`, `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `execution_runtime_bootstrap.py` (287L)
**Rôle** : Bootstrap de l'`ExecutionRuntime` avec les hooks compilés : wiring du `CompiledArtifactRegistryStore`, no-trade filter bridge, projection bridge (rate limit / spread guard / slippage models), `ReconciliationScheduler`.
**Inputs** : `ExecutionVenueAdapter`, `BinanceCredentials`, `BinanceAdapterConfig`, optionnels `compiled_registry_state_dir`, `reconciliation_circuit_breaker`
**Outputs** : `ExecutionRuntimeBootstrapBundle` ou `ExecutionRuntime`
**Équations mathématiques** :
- `default_fee_rate: float = 0.001` (défaut 0.1% — hardcodé L53)
- `max_recon_age_s: float = 60.0` (défaut 60s — hardcodé L54)
**Logging** : Aucun.
**Signal handlers** : NON
**Dépendances internes** : `execution_backbone`, `risk_backbone.emergency_kill_switch`, `scoring_backbone`, `venue_adapters.binance_spot`, `protocols.compiled_artifact_registry_store`, `protocols.execution_no_trade_filter_bridge`, `protocols.execution_runtime_projection_bridge`
**État** : COMPLETE
**Anomalies** :
- L53 : `default_fee_rate: float = 0.001` — hardcodé (devrait venir de calibration)
- L54 : `max_recon_age_s: float = 60.0` — hardcodé

---

### Fichiers hooks moteurs (80–93L chacun)

#### `engine_a_hooks.py` (80L) · `engine_b_hooks.py` (93L) · `engine_c_hooks.py` (84L) · `engine_d_hooks.py` (93L)
**Rôle** : Chaque fichier expose `load_engine_X_hook_payload(hook_plan_doc)` et `run_engine_X_hook(hook_input)` — bridge entre le plan compilé et l'hook runtime du moteur.
**Inputs** : `CompiledHookPlanDocument`, `EngineX[Pre/Sweep/Void/Reentry]HookPlanPayload`
**Outputs** : résultat hook (PERMIT/BLOCK/SIZE_REDUCE selon moteur)
**Équations mathématiques** : Aucune dans ces fichiers (déléguées aux bridges).
**Signal handlers** : NON
**État** : COMPLETE
**Anomalies** : Aucune.

#### `execution_hooks.py` (34L) · `risk_hooks.py` (80L) · `scoring_hooks.py` (71L) · `portfolio_hooks.py` (72L)
**Rôle** : Même pattern — hooks compilés pour les composantes execution (no-trade), risk (micro-friction), scoring (soft-penalty), portfolio (relative-rank).
**Signal handlers** : NON
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichiers bridges validation (195–204L chacun)

#### `engine_a_pre_entry_confirmation_bridge.py` (195L)
#### `engine_b_sweep_validation_bridge.py` (199L)
#### `engine_c_void_validation_bridge.py` (196L)
#### `engine_d_reentry_validation_bridge.py` (199L)
#### `risk_micro_friction_precheck_bridge.py` (203L)
#### `scoring_soft_penalty_layer_bridge.py` (198L)
#### `portfolio_relative_rank_adjustment_bridge.py` (204L)
#### `execution_no_trade_filter_bridge.py` (206L)

**Rôle** : Chaque bridge expose une classe `XBridge` (runtime singleton) et `XBridgeStatus` + `inspect_X_bridge()` (inspection hors hot-path). Bridge le `CompiledArtifactRegistryStore` snapshot vers l'évaluation runtime de l'hook.
**Inputs** : `CompiledArtifactRegistryStore`, signal candidat (type moteur-spécifique)
**Outputs** : décision bridge (block/permit/size-reduce)
**Signal handlers** : NON
**État** : COMPLETE (tous les 8 bridges)
**Anomalies** : Aucune.

---

### Fichier : `execution_runtime_projection_bridge.py` (181L)
**Rôle** : `load_execution_runtime_consumer_models` — charge les modèles de projection runtime (rate_limit, spread_guard, slippage) depuis un fichier JSON ; `inspect_execution_runtime_projection_bridge`.
**Inputs** : `projection_path: str | Path`
**Outputs** : `(rate_limit_model, spread_guard_model, slippage_model)` tuple
**Équations mathématiques** : Aucune.
**Signal handlers** : NON
**Dépendances internes** : `execution_backbone` (consumer model types)
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `execution_runtime_dashboard.py` (258L)
**Rôle** : Fonctions dashboard pour bridges execution runtime — `build_execution_no_trade_bridge_projection`, `build_execution_runtime_projection_bridge_projection`, `build_runtime_hook_bridge_projections`.
**Inputs** : `ExecutionNoTradeFilterBridgeStatus`, `ExecutionRuntimeProjectionBridgeStatus`, statuts bridges hooks
**Outputs** : dict projections dashboard
**Équations mathématiques** : Aucune.
**Signal handlers** : NON
**Dépendances internes** : `protocols` bridges
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `compiled_artifact_registry_store.py` (219L)
**Rôle** : `CompiledArtifactRegistryStore` — store persisté de snapshots d'artifacts compilés (hook plans) avec atomic swap, pointer courant, historique publié.
**Inputs** : `state_dir: Path`, `CompiledArtifactPublishResult`
**Outputs** : `CompiledArtifactRegistrySnapshot`
**Équations mathématiques** : Aucune.
**Signal handlers** : NON
**Dépendances internes** : `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `compiled_hook_plan_loader.py` (158L)
**Rôle** : `load_compiled_hook_plan`, `select_current_compiled_hook_plan` — charge et sélectionne le plan compilé d'hooks courant depuis le registry store.
**Inputs** : `CompiledArtifactRegistryStore`, optionnel `artifact_id`
**Outputs** : `CompiledHookPlanDocument`, `CompiledHookPlanLoadStatus`, `CompiledHookPlanSelection`
**Équations mathématiques** : Aucune.
**Signal handlers** : NON
**Dépendances internes** : `protocols.compiled_artifact_registry_store`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `artifact_action_composer.py` (139L)
**Rôle** : `compose_artifact_hook_actions` — compose les actions d'effets d'hooks (publish/unpublish) depuis un `ArtifactHookActionInput`.
**Inputs** : `ArtifactHookActionInput` (artifact_id, lineage_version, hook_plan bindings)
**Outputs** : `ComposedArtifactHookEffect`
**Équations mathématiques** : Aucune.
**Signal handlers** : NON
**Dépendances internes** : `protocols.compiled_artifact_registry_store`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `execution_no_trade_hook.py` (84L)
**Rôle** : `run_execution_no_trade_hook` — évalue si un signal doit être bloqué par la politique no-trade compilée.
**Inputs** : `ExecutionNoTradeHookInput`
**Outputs** : `ExecutionNoTradeHookOutcome`
**Équations mathématiques** : Aucune.
**Signal handlers** : NON
**Dépendances internes** : `protocols.compiled_hook_plan_loader`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `engine_coordination_rules.py` (275L)
_(déjà documenté ci-dessus)_

---

### Fichiers restants (petits, < 120L)

#### `execution_hooks.py` (34L) — wrapper minimal, voir hooks moteurs
#### `execution_runtime_projection_bridge.py` (181L) — déjà documenté
#### `shadow_day_counter_models.py` (51L) — déjà documenté

---

## Synthèse Groupe B

### Signal handlers manquants

| Fichier | Problème | Sévérité |
|---------|----------|----------|
| `shadow_live_websocket.py` | SIGTERM/SIGINT absents — service VPS long-running, risque de corruption des captures en cours | **P0** |
| `shadow_vps_service.py` | Store VPS sans signal handler — event log peut être tronqué | **P1** |
| Tous les runtimes (`micro_live_runtime`, `live_light_runtime`, etc.) | Pas de signal handler — mais ces modules sont des fonctions pures (gates), pas des services long-running. Acceptable. | N/A |

**Note** : Le fichier `2026-04-19_shadow_vps_service_graceful_signal_shutdown.md` existe déjà dans `update_audit/` — ce P0 est connu et en cours.

---

### Hardcoded thresholds à déplacer vers calibration_loader

| Emplacement | Valeur | Description |
|-------------|--------|-------------|
| `shadow_runtime_portfolio.py` L46 | `fragility_score >= 0.75` | Physics pressure critical |
| `shadow_runtime_portfolio.py` L47 | `toxicity_score >= 0.75` | Physics pressure critical |
| `shadow_runtime_portfolio.py` L48 | `execution_survivability_score <= 0.25` | Physics pressure critical |
| `shadow_runtime_portfolio.py` L50 | `micro_friction_score >= 0.75` | Physics pressure critical |
| `shadow_runtime_portfolio.py` L55-59 | `>=0.50` et `<=0.50` | Physics pressure elevated |
| `shadow_runtime_portfolio.py` L177-178 | `conflict_rate >= 0.35`, `redundancy_score >= 0.35` | Redundancy detection |
| `shadow_runtime_portfolio.py` L291 | `elevated_at=0.75, critical_at=1.0` | Beta pressure |
| `shadow_runtime_portfolio.py` L296,L301 | `elevated_at=85.0, critical_at=100.0` | Capacity pressure (%) |
| `shadow_runtime_portfolio.py` L320 | `hard_block_rate >= 0.25` | Portfolio rewrite threshold |
| `shadow_runtime_judgments.py` L78 | `scoring_final_size_multiplier <= 0.1` | Engine size cap |
| `shadow_runtime_judgments.py` L85 | `economic_pass_rate <= 0.5` | Economic viability |
| `shadow_runtime_judgments.py` L86 | `conflict_rate >= 0.5` | Conflict ceiling |
| `shadow_runtime_validation.py` L362 | `24.0` heures | Runtime evidence minimum |
| `shadow_day_counter.py` L27 | `_MAX_GAP_SECONDS = 24 * 3600` | Reset trigger |
| `shadow_day_counter_reporting.py` | `dtr_coverage >= 0.95`, `economic_pass_rate >= 0.60`, etc. | Rapport go/no-go |
| `contracts_shadow.py` L200-206 | 0.05, 0.10, 0.0005, 1, 25 | Tolérances Shadow input |
| `engine_coordination_rules.py` L76-79 | `4h`, `24h`, `0.5×` | Coordination thresholds |
| `execution_runtime_bootstrap.py` L53-54 | `0.001`, `60.0` | Fee rate, recon age |

---

### Fichiers à splitter (>700L ou proches)

| Fichier | LOC | Statut |
|---------|-----|--------|
| `live_light_runtime.py` | **699L** | **AU SEUIL EXACT — doit être splitté avant tout ajout** |
| `shadow_day_counter_reporting.py` | 627L | À surveiller |
| `shadow_live_websocket.py` | 665L | À surveiller |
| `micro_live_runtime.py` | 613L | À surveiller |
| `micro_live_runtime_support.py` | 594L | À surveiller |
| `shadow_runtime_validation.py` | 596L | À surveiller |
| `shadow_runtime_portfolio.py` | 471L | OK pour l'instant |
| `contracts_validation_support.py` | 688L | **Proche seuil — à surveiller** |

---

### Anomalies critiques

| ID | Fichier | Ligne | Anomalie | Priorité |
|----|---------|-------|----------|----------|
| A1 | `shadow_live_websocket.py` | — | Signal handlers SIGTERM/SIGINT absents pour service VPS long-running | P0 |
| A2 | `live_light_runtime.py` | 699 | Fichier au seuil exact 700L — tout ajout futur déclenche la violation | P1 |
| A3 | `shadow_runtime_portfolio.py` | 46-59, 177, 291, 296, 301, 320 | 10+ seuils physics pressure hardcodés, aucun vers calibration_loader | P1 |
| A4 | `shadow_runtime_judgments.py` | 78, 85, 86 | Seuils économiques hardcodés (pass_rate, conflict_rate, size_multiplier) | P1 |
| A5 | `shadow_day_counter_reporting.py` | multiple | Seuils rapport go/no-go hardcodés (dtr>=0.95, pass_rate>=0.60, etc.) | P2 |
| A6 | `contracts_shadow.py` | 200-206 | 5 tolérances Shadow hardcodées dans le contrat Pydantic | P2 |
| A7 | `contracts_validation_support.py` | — | 688L — proche seuil critique | P2 |
| A8 | `execution_runtime_bootstrap.py` | 53-54 | `default_fee_rate=0.001`, `max_recon_age_s=60.0` hardcodés | P2 |

---

### Patterns notables (non anomalies)

- **BS-65 pattern** systématique : tous les stores avec persistence JSON ont un `.corrupted` backup + `last_error` champ — pattern sain et cohérent sur 6+ fichiers.
- **Atomic writes** : usage de `atomic_write_json` partout (interface_contracts.atomic_io) — bonne pratique.
- **`type: ignore[arg-type]`** présents dans `shadow_runtime_portfolio.py` (affectation `ShadowPressureLevel` Literal) — non bloquant, lié à la limitation Pydantic/Literal.
- **Pas de `except Exception`** bare dans tout le package — pattern de capture d'exceptions ciblé.
- **Pas de TODO/FIXME** actifs dans les fichiers lus.
