# Cartographie src/ V5.3 — 2026-04-19

> Produite par lecture réelle de chaque fichier source. Référentiel pour Opus et les sprints Codex suivants.
> Chemin src : `E:\claude  v5.3\v53_trading_system\src`

---

## Métriques globales

- **Total fichiers .py** : 599 (hors `__pycache__`)
- **Total packages** : 31 packages + sous-packages
- **Architecture** : DAG strict, validé par `dag_validator`
- **Framework contrats** : Pydantic v2, modèles `frozen=True` partout où applicable
- **Précision numérique** : `Decimal` (28 chiffres, ROUND_HALF_EVEN) pour exécution ; `float` (IEEE-754 binary64) pour analytics

### Liste des packages (dans l'ordre de couverture)

1. `interface_contracts/` — 21 fichiers, ~4 074 L
2. `engines/engine_a/` — 12 fichiers
3. `engines/engine_b/` — 12 fichiers
4. `engines/engine_c/` — 10 fichiers
5. `engines/engine_d/` — 16 fichiers
6. `calibration_methods/` — 14 fichiers
7. `calibration_loader/` — 3 fichiers
8. `regime_classifier/` — 2 fichiers
9. `execution_backbone/` — ~38 fichiers
10. `protocols/` — ~93 fichiers
11. `risk_backbone/` — ~39 fichiers
12. `scoring_backbone/` — ~27 fichiers
13. `data_backbone/` — ~57 fichiers
14. `venue_adapters/` — sous-packages binance_spot
15. `monitoring/` — ~41 fichiers
16. `alerting/` — 2 fichiers
17. `sharia_compliance/` — 15 fichiers
18. `portfolio/` — 1 fichier (`__init__.py`)
19. `portfolio_minimal/` — 12 fichiers
20. `meta/` — à vérifier
21. `meta_learning/` — 3 fichiers
22. `meta_minimal/` — 18 fichiers
23. `local_replay_runtime/` — grand package (~50+ fichiers)
24. `manifest_registry/` — 5 sous-fichiers
25. `backtest_artifact_import/` — 15 fichiers
26. `complete_enablers/` — ~12 fichiers
27. `dag_validator/` — 6 fichiers
28. `contract_test_suite/` — 4 fichiers
29. `secrets_manager/` — 6 fichiers
30. `smoke_bootstrap_recovery/` — 2 fichiers
31. `ui/` — à vérifier

---

## Package : `interface_contracts/`

### Fichier : `__init__.py` (128L)
**Rôle** : Façade publique du package ; re-exporte tout le vocabulaire canonique.
**Inputs** : N/A (module import)
**Outputs** : `__all__` complet avec 120+ symboles
**Équations mathématiques** : Aucune
**Dépendances internes** : Tous les sous-modules du package
**État** : COMPLETE
**Anomalies** : Aucune

---

### Fichier : `domain_types.py` (272L)
**Rôle** : Définit tous les enums canoniques et types de base (NewType, PairId, TimestampedModel).
**Inputs** : N/A
**Outputs** :
- `EngineId` {A, B, C, D}
- `RegimeId` {TRENDING_UP, TRENDING_DOWN, RANGE_BOUND, HIGH_VOLATILITY, LOW_VOLATILITY, BREAKOUT, UNKNOWN}
- `ProfileId` {LIGHT, COMPLETE}
- `RuntimeMode` {LOCAL_REPLAY, SHADOW, MICRO_LIVE, LIVE}
- `DeploymentState`, `ModuleLayer`, `ModuleStatus`, `Tier`, `Side`, `Timeframe`
- `PairId(symbol, tier)` — Pydantic frozen model avec validation contre `ALL_PAIRS`
- `TimestampedModel(timestamp_ms: int [1e12, 1e13])`
- Constantes : `LIGHT_PAIRS` (6 paires), `COMPLETE_ADDITIONAL_PAIRS` (6 paires), `ALL_PAIRS` (12), `V53_MULTIPAIR_7` (7), `ENGINE_PAIR_MAP`, `PAIR_TIER_MAP`
**Équations mathématiques** : `timestamp_dt = fromtimestamp(timestamp_ms / 1000.0, UTC)`
**Dépendances internes** : Aucune
**État** : COMPLETE
**Anomalies** : Encodage `Ã©` visible dans commentaires (UTF-8 mal lu) — cosmétique uniquement

---

### Fichier : `market_event_contracts.py` (159L)
**Rôle** : Structures de données de marché normalisées (trades, depth, klines, heartbeat, snapshot).
**Inputs** : Données de marché brutes
**Outputs** :
- `TradeEvent(pair, price, quantity, side, trade_id, is_maker)` — `notional_usdt = price * quantity`
- `DepthLevel(price, quantity)` frozen
- `DepthEvent(pair, bids, asks, last_update_id)` — validation crossed book (GEM-01)
- `KlineEvent(pair, timeframe, OHLCV, close_time_ms, trade_count, is_closed)` — `body_ratio = |close-open|/(high-low)`
- `HeartbeatEvent(source, pair, latency_ms)`
- `SnapshotEvent(pair, last_price, bid, ask, volume_24h, funding_rate)`
**Équations mathématiques** :
- `spread_bps = (ask - bid) / mid * 10_000`
- `body_ratio = |close - open| / (high - low)`
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune

---

### Fichier : `decision_contracts.py` (185L)
**Rôle** : Structures de décision signal → score → risk → execution → portfolio.
**Inputs** : Résultats d'engine
**Outputs** :
- `SignalCandidate(pair, engine_id, signal_type, side, confidence [0,1], regime, entry_price, stop_loss, take_profit, max_hold_ms)` — méthode `is_expired(now_ms)`, propriété `expected_risk_reward`
- `ScorePayload(pair, engine_id, raw_score, penalty_total, final_score, rank, hard_blocked, penalties, block_reasons, estimated_cost_bps)`
- `RiskDecision(pair, engine_id, verdict, requested_size, approved_size, exposure/loss_budget_used_pct, block_reasons, btc_beta, cluster_exposure)` — validation : `approved_size <= requested_size` ; `approved_size == 0` si HARD_BLOCKED
- `ExecutionIntent(pair, engine_id, side, size, target_price, order_type, status, filled_size/price, execution_cost_bps)` — `slippage_bps = |filled_price - target_price| / target_price * 10_000`
- `PortfolioDecision(pair, engine_id, action, score_rank)`
- Enums : `SignalType`, `BlockReason` (12 valeurs), `RiskVerdict`, `ExecutionStatus`, `PortfolioAction`
**Équations mathématiques** :
- `expected_risk_reward = |take_profit - entry_price| / |entry_price - stop_loss|`
- `slippage_bps = |filled_price - target_price| / target_price * 10_000`
- `fill_ratio = filled_size / size`
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : `_EPSILON_RISK = 1e-6` hardcodé (GEM-02) — acceptable comme guard numérique

---

### Fichier : `forecast_contracts.py` (286L)
**Rôle** : Contrat de signal enrichi Narang-grade (additive, sans remplacer le contrat décision canonique).
**Inputs** : `DecisionSignalCandidate` + méta-données forecast
**Outputs** :
- `ForecastSignalCandidate(strategy_id, engine_id, pair, side, forecast_direction [-1,1], forecast_strength [0,20], forecast_horizon_class, forecast_target_class, bet_structure, conditioning_state, expected_cost, expected_break_even, expected_ce, expected_gain, versions)` — frozen, extra=forbid
- `ConditioningRecord(family, code, value, triggered_no_trade)` — 4 familles : ENGINE_INTERNAL, SCORING, HARD_BLOCK, PORTFOLIO
- Fonctions utilitaires : `merge_reason_codes()`, `build_scoring_conditioning_records()`, `build_forecast_versions()`
- Enums : `ForecastTargetClass`, `ForecastHorizonClass`, `BetStructure`, `ConditioningFamily`
**Équations mathématiques** : `expected_ce` et `expected_gain` doivent être finis (math.isfinite)
**Dépendances internes** : `decision_contracts`, `domain_types`
**État** : COMPLETE
**Anomalies** : `conditioning_state` obligatoire non-vide — bon garde-fou

---

### Fichier : `numeric_contracts.py` (169L)
**Rôle** : Arithmétique Decimal prod-safe pour valeurs d'exécution exactes (prix, quantité, fee, notionnel).
**Inputs** : `Decimal | SupportsFloat | str`
**Outputs** :
- `execution_decimal(value)` → `Decimal` fini
- `multiply_exact(left, right)` → `Decimal` (precision=28, ROUND_HALF_EVEN)
- `divide_exact_or_zero(numerator, denominator)` → `Decimal` (ZeroDivisionError si denom=0)
- `sum_exact(values)` → `Decimal`
- `quantize_down_to_step(value, step)` → ROUND_DOWN vers le step inférieur
- `quantize_up_to_step(value, step)` → ROUND_CEILING vers le step supérieur
- `decimal_to_float64(value, max_abs_loss=None)` → `float` avec garde perte de précision
- `decimal_to_float64_abs_loss(value)` → perte absolue de précision
**Équations mathématiques** : Pas d'équations finance, primitives arithmétiques Decimal
**Dépendances internes** : Aucune
**État** : COMPLETE
**Anomalies** : `EXECUTION_DECIMAL_CONTEXT_PRECISION = 28` hardcodé (intentionnel, documenté)

---

### Fichier : `feature_lock_contracts.py` (335L)
**Rôle** : Dictionnaire canonique des features physics, whitelist de transforms, verrous de lignage.
**Inputs** : Feature IDs, transform IDs
**Outputs** :
- `PhysicsFeatureFamily` (19 familles dont OFI, VPIN, DELTA_PROXY, ABSORPTION, FALSE_BREAKOUT…)
- `TransformWhitelistId` (13 transforms : CLIP01, ZPLUS, CAPRATIO, DELTA_PROXY_SOFT/SIGN, SWEEP_SCORE_V1, FRAGILITY/TOXICITY/EXECUTION_SURVIVABILITY/MICRO_FRICTION_SCORE_V1…)
- `CANONICAL_PHYSICS_FEATURE_DICTIONARY` — 10 features nommées avec equation_id (ex: `"P2.3.delta_proxy_soft"`, `"P2.5.sweep_score"`)
- `FeatureLineageRecord` — audit trail pour chaque feature dérivée
- `FeatureLineageLock` — verrou de version
- Fonctions : `validate_feature_lineage_lock()`, `validate_transform_whitelist_lock()`
**Équations mathématiques** : Références d'équations en tags (P2.x) mais pas inline
**Dépendances internes** : Aucune
**État** : COMPLETE
**Anomalies** : `TOXICITY_FRAGILITY_SURVIVABILITY` a une typo dans la valeur enum `"toxcity_fragility_survivability"` (manque le `i`) — BUG potentiel si comparé par valeur string

---

### Fichier : `error_contracts.py` (238L)
**Rôle** : Hiérarchie d'exceptions métier standardisées.
**Inputs** : N/A
**Outputs** :
- `V53BaseError(message, code, module, pair, details)` avec `to_dict()`
- Sous-classes : `DataStaleError`, `PairSuspendedError`, `DependencyViolationError`, `ContractViolationError`, `RiskBudgetExceededError`, `InvalidProfileActivationError`, `EngineNotAllowedError`, `ReconciliationError`, `BootstrapError`
**Équations mathématiques** : Aucune
**Dépendances internes** : Aucune
**État** : COMPLETE
**Anomalies** : Aucune

---

### Fichier : `meta_contracts.py` (157L)
**Rôle** : Objets d'observabilité (DTR, santé paire, coût, edge, alerte).
**Inputs** : Données d'exécution post-trade
**Outputs** :
- `DTRRecord(dtr_id, pair, engine_id, regime, confidence, scores, verdict, outcome, entry/exit_price, pnl, cost_bps, hold_ms)` — `net_pnl_usdt = pnl - entry_price * (cost_bps / 10_000)`
- `PairHealthStatus(pair, health, freshness_ms, stale_count_5m, ws_connected)`
- `CostRecord(fee_bps, spread_cost_bps, slippage_bps, total_cost_bps)` — validation `total = fee + spread + slippage`
- `EdgeEstimate(gross_edge_bps, cost_drag_bps, net_edge_bps)` — validation `net = gross - cost`
- `AlertRecord(alert_id, severity, category, message)`
- Enums : `DTROutcome` (7 valeurs dont PHANTOM), `AlertSeverity`, `AlertCategory`, `PairHealthLevel`
**Équations mathématiques** :
- `net_pnl_usdt = pnl_usdt - entry_price * (cost_total_bps / 10_000)`
- `net_edge_bps = gross_edge_bps - cost_drag_bps`
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune

---

### Fichiers restants interface_contracts (résumé)

**`artifact_contracts.py` (18L)** : Façade re-exportant `artifact_contracts_models` + `artifact_contracts_runtime`. **État** : COMPLETE

**`artifact_contracts_models.py` (590L)** : Enums et modèles pour les artefacts gouvernés (ArtifactActivationStage, HookId, ArtifactActionKind, etc.). Contient `CANONICAL_ARTIFACT_CONFLICT_POLICY`, `CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY`, `evaluate_artifact_runtime_governance()`. **État** : COMPLETE

**`artifact_contracts_runtime.py` (172L)** : Modèles runtime pour artefacts (ArtifactTtlStatus, ArtifactDriftStatus, ArtifactRuntimeGovernanceEvaluation, ArtifactExportBundle). **État** : COMPLETE

**`atomic_io.py` (65L)** : Helpers pour écriture atomique de fichiers (temp + rename). **État** : COMPLETE

**`binance_contracts.py` (231L)** : Modèles Binance normalisés (BinanceCredentials avec SecretStr, BinanceSymbolInfo, BinanceExchangeInfo avec rate limits et symbols). **État** : COMPLETE

**`build14_contracts.py` (252L)** : Contrats Build-14 enabler — règles de gouvernance strictes : `can_override_engines=False`, `can_bypass_risk=False`, `can_trade_autonomously=False`. **État** : COMPLETE

**`engine_validation_contracts.py` (78L)** : Inputs/outcomes de validation pour hooks Engine C (void validation) et Engine D (reentry validation). **État** : COMPLETE

**`operator_contracts.py` (66L)** : `OperatorSafingAction`, `OperatorSafingRequest` pour actions opérateur. **État** : COMPLETE

**`pair_catalog.py` (199L)** : `PairEntry`, `PairCatalog`, `V53_PAIR_CATALOG` — catalogue complet des paires avec méta-données (Tier, description, engine eligibility). **État** : COMPLETE

**`refusal_records.py` (56L)** : `RefusalCategory`, `RefusalRecord` — journalisation des refus (Taleb quadruple filter). **État** : COMPLETE

**`shadow_vps_service_contracts.py` (337L)** : `ShadowVpsServiceState` (état persisté ~50 champs de référence), `ShadowVpsRuntimeEvidenceBundle`, `ShadowVpsCampaignSummary`, `ShadowVpsServiceEvent`. **État** : COMPLETE

**`strategy_identity.py` (81L)** : `StrategyIdentity(strategy_id, engine_id, classification, version)` — identité canonique d'une stratégie. **État** : COMPLETE

---

## Package : `engines/engine_a/`

### Fichier : `engine_a_runtime.py` (~200L)
**Rôle** : Runtime Build-6 d'Engine A — orchestre le chemin complet signal → scoring → ranking → risk.
**Inputs** : `EngineARuntimeInput(engine_inputs, timestamp_ms, portfolio, projected_size/loss, current/peak_equity, pair_beta, cluster_id, score_penalties, blocker_conditions, peer_candidates)`
**Outputs** : `EngineARuntimeStatus` (NO_TRADE, CIRCUIT_BREAKER_BLOCKED, HOOK_BLOCKED, HARD_BLOCKED, REJECTED_RANKING, REJECTED_PORTFOLIO, RISK_REJECTED/REDUCED/OBSERVE_ONLY, ACCEPTED) + `ForecastSignalCandidate`
**Équations mathématiques** : Délègue à sous-modules
**Logging** : `EngineALogEntry` (structured, event/pair/raw_score/conviction/tier/invalidation/reasons)
**Dépendances internes** : `execution_backbone.execution_runtime_models`, `risk_backbone.risk_runtime`, `scoring_backbone.scoring_runtime`, `engine_a_runner`, `engine_a_runtime_support`, `conviction_builder_a`
**État** : COMPLETE
**Anomalies** : Aucune

---

### Fichier : `structure_detector_a.py` (~100L)
**Rôle** : Détecte une structure trend/expansion exploitable.
**Inputs** : `StructureInput(pair, direction_score[-1,1], continuation_score[0,1], structure_quality[0,1], zone_proximity[0,1], trend_stability[0,1], realized_kernel_vol_scale)`
**Outputs** : `StructureResult(verdict, structure_score, direction_strength, continuation_strength)`
**Équations mathématiques** :
```
structure_score = 0.30·|direction| + 0.25·continuation + 0.20·quality + 0.10·zone_proximity + 0.15·stability
```
Thresholds : favorable > 0.60, marginal > 0.30, min_direction = 0.20
**Calibration** : `engine_a_structure.to_calibrate.v1` — statut `TO_CALIBRATE`
**Dépendances internes** : `data_backbone` (TO_CALIBRATE constant)
**État** : PARTIAL — thresholds et poids marqués `TO_CALIBRATE`, en attente calibration signée

---

### Fichier : `context_validator_a.py` (~100L)
**Rôle** : Valide que le contexte ne contredit pas le signal structurel.
**Inputs** : `ContextInput(pair, regime_favorability[0,1], regime_confidence[0,1], pair_health[0,1], data_freshness[0,1], flow_coherence[0,1])`
**Outputs** : `ContextResult(verdict: CONFIRMING|NEUTRAL|DEGRADED|FATAL, context_score)`
**Équations mathématiques** :
```
context_score = 0.30·regime_favorability + 0.20·regime_confidence + 0.20·pair_health + 0.15·data_freshness + 0.15·flow_coherence
```
Thresholds : fatal < 0.15, degraded < 0.35, confirming >= 0.65
**État** : PARTIAL — poids et thresholds `TO_CALIBRATE`

---

### Fichier : `conviction_builder_a.py` (~200L)
**Rôle** : Construit le niveau de conviction Engine A à partir des composantes.
**Inputs** : `ConvictionInput(structure_score, context_score, flow_score, ofi_flow_score, cost_preference_score, delta_confirmation[0,1], execution_fragility, market_toxicity, spread_regime_penalty, competition_density)`
**Outputs** : `ConvictionResult(raw_score, conviction: HIGH|MEDIUM|LOW|NONE, tier_suggestion, is_emittable, block_scores)`
**Équations mathématiques** :
```
legacy_raw = 0.40·structure + 0.25·context + 0.15·flow + 0.20·cost_preference
delta_adjustment = 0.12·(delta_confirmation - 0.5)
competition_adjustment = 0.08·(competition_support - 0.5)
execution_penalty = 0.10·fragility_score_v1(...)
toxicity_penalty = 0.08·toxicity_score_v1(...)
spread_penalty = 0.07·micro_friction_score_v1(...)
raw_score = clip01(legacy_raw + delta_adjustment + competition_adjustment - execution_penalty - toxicity_penalty - spread_penalty)
```
Thresholds : HIGH >= 0.70, MEDIUM >= 0.45, LOW >= 0.25
**Dépendances internes** : `data_backbone.market_physics_math`
**État** : PARTIAL — poids `TO_CALIBRATE`, logique de calcul COMPLETE

---

### Fichier : `cost_feasibility_a.py` (~80L)
**Rôle** : Évalue la faisabilité du trade par rapport aux coûts.
**Inputs** : `CostInput(pair, expected_cost_bps, signal_edge_bps)`
**Outputs** : `CostResult(verdict: FEASIBLE|MARGINAL|INFEASIBLE, cost_edge_ratio)`
**Équations mathématiques** : `cost_edge_ratio = expected_cost_bps / signal_edge_bps` si edge > 0
**Calibration** : `ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE`
**État** : PARTIAL — thresholds `TO_CALIBRATE`

---

### Fichier : `engine_a_runner.py` (~200L)
**Rôle** : Orchestrateur Engine A — appelle structure_detector → context_validator → cost_feasibility → conviction_builder → signal_reporter.
**Inputs** : `EngineAInput` (agrégation des inputs de sous-composants)
**Outputs** : `EngineAOutput(decision: EMIT|NO_TRADE, signal_candidate, log_entries)`
**Dépendances internes** : tous les sous-composants engine_a
**État** : COMPLETE

---

### Fichier : `invalidation_mapper_a.py` (~60L)
**Rôle** : Mappe les conditions d'invalidation du signal (stop conditions contextuelles).
**Outputs** : `InvalidationMap(conditions, reason_codes)`
**État** : COMPLETE

---

### Fichier : `signal_reporter_a.py` (~60L)
**Rôle** : Formate le rapport de décision finale Engine A.
**Outputs** : `SignalDecision`, `NoTradeReason`
**État** : COMPLETE

---

### Fichiers support engine_a (résumé)

**`engine_a_runner_support.py`** : Helpers pour construction de log entries, raisons de branch. **État** : COMPLETE
**`engine_a_runtime_support.py`** : Helpers pour construction de ForecastSignalCandidate, RefusalRecord, résolution d'audit. **État** : COMPLETE

---

## Package : `engines/engine_b/`

**Rôle global** : Engine B — mean reversion sur z-score local (Build-7).

### Fichier : `engine_b_runtime.py` (~250L)
**Rôle** : Runtime Build-7 Engine B — même pipeline A/B/C/D avec scoring/ranking/risk.
**Inputs** : `EngineBRuntimeInput` (identique à A en structure)
**Outputs** : `EngineBRuntimeStatus` + `ForecastSignalCandidate`
**Logging** : `EngineBLogEntry`
**Dépendances internes** : Même stack que engine_a_runtime + `EngineBSweepValidationInput` hook
**État** : COMPLETE

---

### Fichier : `local_mean_estimator_b.py` (~90L)
**Rôle** : Estime la moyenne et la dispersion locales pour la détection de mean-reversion.
**Inputs** : `LocalMeanInput(pair, current_price, local_mean, local_std)`
**Outputs** : `LocalMeanResult(z_score, deviation, valid, abs_z)`
**Équations mathématiques** :
```
deviation = current_price - local_mean
z_t = deviation / local_std    (si local_std > min_std = 1e-12)
```
**Calibration** : `engine_b_local_mean.to_calibrate.v1`
**État** : PARTIAL — logique complète, thresholds TO_CALIBRATE

---

### Fichier : `excess_detector_b.py` (~160L)
**Rôle** : Détecte un excès local exploitable pour mean-reversion (|z_t| > z*).
**Inputs** : `ExcessInput(pair, z_score, z_score_valid, structure_is_range, recent_expansion, vpin_current, toxic_flow_correlation)`
**Outputs** : `ExcessResult(verdict: EXPLOITABLE|MARGINAL|NO_EXCESS|INVALID, excess_score)`
**Équations mathématiques** :
```
Condition entrée : |z_t| > z_star (default z_star = 1.5, TO_CALIBRATE)
z_marginal = 1.0, z_max = 4.0 (clamp)
Rejet si vpin_current > vpin_toxic (default 0.35)
```
Thresholds identifiés : `THR-B05` (z_marginal), `THR-B06` (z_star), `THR-B07` (z_max), `THR-B08` (vpin_toxic), `THR-B09` (max_intra_family_correlation)
**État** : PARTIAL — thresholds TO_CALIBRATE

---

### Fichier : `anti_breakout_filter_b.py` (~80L)
**Rôle** : Filtre anti-breakout — rejette les trades mean-reversion en cas de vrai breakout.
**État** : PARTIAL

---

### Fichier : `conviction_builder_b.py`, `cost_feasibility_b.py`, `invalidation_mapper_b.py`, `signal_reporter_b.py` (~80L chacun)
**État** : PARTIAL (thresholds TO_CALIBRATE, logique présente)

---

### Fichiers support engine_b (résumé)

**`engine_b_runner.py`** : Orchestrateur B. **État** : COMPLETE
**`engine_b_runner_support.py`**, **`engine_b_runtime_support.py`**, **`engine_b_runtime_forecast_support.py`** : Helpers. **État** : COMPLETE

---

## Package : `engines/engine_c/`

**Rôle global** : Engine C — continuation de breakout (Build-7).

### Fichier : `signal_math_c.py` (76L)
**Rôle** : Helpers de scoring pur pour Engine C.
**Équations mathématiques** :
```
breakout_score    = clamp(0.35·breakout_strength + 0.25·range_quality + 0.20·compression_quality + 0.20·volume_confirmation)
context_score     = clamp(0.35·regime_favorability + 0.25·pair_health + 0.20·data_freshness + 0.20·flow_coherence)
continuation_score = clamp(0.45·followthrough_room + 0.25·(1-extension_pct) + 0.30·context_score)
fake_breakout_risk = clamp(0.45·retrace_risk + 0.30·rejection_wick_ratio + 0.25·(1-volume_confirmation))
```
**État** : COMPLETE

---

### Fichier : `engine_c_runtime.py` (~250L)
**Rôle** : Runtime Engine C avec hook `engine_c_void_validation` via `EngineCVoidValidationInput`.
**Dépendances internes** : `protocols.engine_coordination_rules`, `risk_backbone.risk_runtime`, scoring_backbone
**État** : COMPLETE

---

### Fichiers restants engine_c (résumé)

**`structure_resolver_c.py`** : Résout la structure breakout/range. **État** : PARTIAL
**`continuation_validator_c.py`** : Valide continuation du breakout. **État** : PARTIAL
**`conviction_builder_c.py`** : Conviction Engine C. **État** : PARTIAL
**`cost_feasibility_c.py`** : Faisabilité coût. **État** : PARTIAL
**`invalidation_mapper_c.py`** : Invalidation. **État** : COMPLETE
**`output_payload_builder_c.py`** : Builder de payload. **État** : COMPLETE
**`engine_c_runner.py`** : Orchestrateur. **État** : COMPLETE
**`engine_c_runner_support.py`**, **`engine_c_runtime_support.py`**, **`engine_c_runtime_forecast_support.py`** : Helpers. **État** : COMPLETE

---

## Package : `engines/engine_d/`

**Rôle global** : Engine D — re-entry / reformation après stop (Build-7).

### Fichier : `signal_math_d.py` (~70L)
**Rôle** : Helpers de scoring pur Engine D.
**Équations mathématiques** :
```
history_score     = clamp(0.55·prior_trade_quality + 0.25·pair_health + 0.20·data_freshness)
context_score     = clamp(0.35·regime_favorability + 0.25·pair_health + 0.20·data_freshness + 0.20·flow_coherence)
reformation_score = clamp(0.45·reformation_quality + 0.30·pullback_quality + 0.25·context_score)
marginal_value    = clamp(0.35·marginal_edge + 0.30·continuation_room + 0.20·concentration_headroom + 0.15·(1-reentry_lateness))
```
**État** : COMPLETE

---

### Fichier : `engine_d_runtime.py` (~270L)
**Rôle** : Runtime Engine D avec hook `engine_d_reentry_validation` + coordination inter-engines.
**Dépendances internes** : `protocols.engine_coordination_rules`, `risk_backbone.risk_runtime`, `consecutive_stop_counter_d`, `historical_linkage_guard_d`
**État** : COMPLETE

---

### Fichiers spécifiques engine_d (résumé)

**`engine_d_models.py`** : Modèles internes. **État** : COMPLETE
**`engine_d_runtime_history_entry_mixin.py`** : Mixin pour historique de trades. **État** : COMPLETE
**`engine_d_runtime_support_refusal.py`** : Support refusal journal. **État** : COMPLETE
**`engine_state_snapshot_d.py`** : Snapshot d'état Engine D. **État** : COMPLETE
**`consecutive_stop_counter_d.py`** : Compteur de stops consécutifs. **État** : COMPLETE
**`historical_linkage_guard_d.py`** : Garde de linkage historique (anti-survivorship). **État** : COMPLETE
**`first_episode_resolver_d.py`** : Résolution du premier épisode. **État** : COMPLETE
**`context_resolver_d.py`** : Résolution de contexte. **État** : PARTIAL
**`conviction_builder_d.py`** : Conviction D. **État** : PARTIAL
**`coordination_input_assembler_d.py`** : Assembleur input coordination. **État** : COMPLETE
**`cost_feasibility_d.py`** : Faisabilité coût. **État** : PARTIAL
**`invalidation_mapper_d.py`** : Invalidation. **État** : COMPLETE
**`output_payload_builder_d.py`** : Builder payload. **État** : COMPLETE
**`runtime_input_assembler_d.py`** : Assembleur input runtime. **État** : COMPLETE
**`engine_d_runner.py`**, **`engine_d_runner_support.py`**, **`engine_d_runtime_support.py`** : Orchestrateur + helpers. **État** : COMPLETE

---

## Package : `calibration_methods/`

### Fichier : `psr.py` (~150L)
**Rôle** : Probabilistic Sharpe Ratio (Bailey & López de Prado 2012) — teste si SR_hat > SR* avec statistique.
**Inputs** : `Iterable[float]` (returns), `benchmark_sharpe=0.0`, `acceptance_floor`
**Outputs** : `ProbabilisticSharpeRatioResult(n, sr_hat, skewness, kurtosis, psr, passes_floor)`
**Équations mathématiques** :
```
PSR(SR*) = Φ( (SR_hat - SR*) · √(n-1) / √(1 - γ₃·SR_hat + ((γ₄-1)/4)·SR_hat²) )
```
Utilisé par gates shadow : G2.1 PSR(0) >= 0.60, G2.2 >= 0.85, G2.3 >= 0.95
**Dépendances internes** : Aucune (stdlib seulement)
**État** : COMPLETE

---

### Fichier : `dsr.py` (~130L)
**Rôle** : Deflated Sharpe Ratio — ajuste le SR pour le biais de sélection multiple (`trial_count` tentatives).
**Inputs** : `Iterable[float]`, `trial_count: int`, `acceptance_floor=0.95`
**Outputs** : `DeflatedSharpeRatioResult(sr, skewness, kurtosis, sharpe_variance, benchmark_sharpe, dsr, passes_floor)`
**Équations mathématiques** :
```
denominator = 1 - γ₃·SR + ((γ₄-1)/4)·SR²
sharpe_variance = denominator / (n-1)
benchmark_sharpe = E[max SR | N trials] ≈ √(sharpe_variance) · Φ⁻¹((1 - 1/trial_count))  (approx)
z_score = (SR - benchmark_sharpe) · √(n-1) / √(denominator)
DSR = Φ(z_score)
```
**État** : COMPLETE

---

### Fichier : `bootstrap.py` (~180L)
**Rôle** : Stationary block bootstrap (Politis & Romano 1994) — inférence robuste sur séries temporelles autocorrélées.
**Inputs** : `Iterable[float]`, `StationaryBootstrapConfig(bootstrap_samples=10_000, confidence_level=0.95, expected_block_length, rng_seed=53)`
**Outputs** : `StationaryBootstrapInterval(point_estimate, ci_lower, ci_upper, block_length, confidence_level)`
**Équations mathématiques** :
```
block_length_auto = f(max_autocorrelation_lag)   // autocorrelation truncation
bootstrap_replicate = sample T_i ~ Geometric(1/block_length) blocks until length n reached
CI : [p(α/2), p(1-α/2)] du bootstrap distribution
```
**État** : COMPLETE

---

### Fichier : `hansen_spa.py` (~200L)
**Rôle** : Hansen SPA test (2005) — teste si le meilleur candidat parmi N est significatif une fois l'effet sélection contrôlé.
**Inputs** : `Mapping[str, Iterable[float]]` (loss differentials par candidat), `acceptance_ceiling=0.10`
**Outputs** : `HansenSpaResult(selected_candidate_id, omega_hat, test_statistic, p_value, passes_floor)`
**Équations mathématiques** :
```
H0 : best candidate is not significantly better than benchmark
d_it = loss_benchmark - loss_candidate_i  (loss differential)
ω̂_i = variance estimator via stationary bootstrap
T̂ = max_i (mean(d_i) / √(ω̂_i))   (test statistic)
recentering : d_i* ← d_i - max(mean(d_i), 0)  (positive-part adjustment)
p-value = P(T̂_bootstrap > T̂)
```
**Dépendances internes** : `calibration_methods.bootstrap`
**État** : COMPLETE

---

### Fichier : `multiple_testing.py` (~120L)
**Rôle** : Correction Holm-Bonferroni step-down pour tests multiples simultanés.
**Inputs** : `Iterable[tuple[str, float]]` (hypothesis_id, p_value), `family_alpha=0.05`
**Outputs** : `HolmBonferroniResult(any_rejected, all_rejected, adjusted_hypotheses)`
**Équations mathématiques** :
```
Sort p-values p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
Reject H_(k) si p_(k) ≤ α / (m - k + 1)
```
**État** : COMPLETE

---

### Fichier : `multiple_testing_guard.py` (~100L)
**Rôle** : Garde Harvey-Liu-Zhu pour deflation de Sharpe sous tests multiples.
**État** : PARTIAL — à vérifier en détail

---

### Fichier : `pot_gpd.py` (~180L)
**Rôle** : Peaks-Over-Threshold avec ajustement GPD (Extreme Value Theory) pour tail risk.
**Inputs** : `losses: Iterable[float]`, `PotGpdConfig(threshold_quantile=0.90, var_confidence=0.995, min_exceedances=30)`
**Outputs** : `PotGpdResult(xi_hat, beta_hat, var_estimate, var_ci_lower, var_ci_upper, bootstrap_dispersion_ratio, passes_dispersion)`
**Équations mathématiques** :
```
Threshold u = quantile(losses, threshold_quantile)
Exceedances X = {x : x > u}
GPD fit : P(X > x+u | X > u) ≈ (1 + ξ·x/β)^(-1/ξ)   [Method of Moments]
VaR_p = u + (β/ξ)·((n/Nu·(1-p))^(-ξ) - 1)   où Nu = |exceedances|
Bootstrap CI via resampling des exceedances
```
**État** : COMPLETE

---

### Fichier : `energy_distance.py` (~100L)
**Rôle** : Test de distance d'énergie pour vérifier si deux distributions sont identiques.
**État** : COMPLETE

---

### Fichier : `ks_test.py` (~80L)
**Rôle** : Test KS (Kolmogorov-Smirnov) pour stationnarité/shift de distribution.
**État** : COMPLETE

---

### Fichier : `mann_kendall.py` (~80L)
**Rôle** : Test Mann-Kendall pour détection de tendance non-paramétrique dans les séries de performance.
**État** : COMPLETE

---

### Fichier : `stationarity.py` (~80L)
**Rôle** : Tests de stationnarité (ADF/KPSS via statsmodels ou implémentation interne).
**État** : PARTIAL — vérifier dépendances externes (statsmodels)

---

### Fichier : `hard_cap_floor.py` (~60L)
**Rôle** : Application de caps et floors absolus sur métriques calibrées.
**État** : COMPLETE

---

### Fichier : `walkforward.py` (~100L)
**Rôle** : Validation walk-forward — split temporel IS/OOS pour calibration hors-échantillon.
**État** : PARTIAL

---

### Fichier : `execution.py` (~80L)
**Rôle** : Helpers de calibration liés à l'exécution (spread, slippage).
**État** : PARTIAL

---

### Fichier : `__init__.py` (~30L)
**Rôle** : Re-exports publics. **État** : COMPLETE

---

## Package : `calibration_loader/`

### Fichier : `loader.py` (~180L)
**Rôle** : Charge et valide des artefacts de calibration signés depuis disque (JSON/YAML).
**Inputs** : `path: Path | str`
**Outputs** : `CalibrationArtifact`, `CalibrationArtifactCollection`, via `load_calibration_artifact()` et `load_calibration_collection()`
**Comportement clé** :
- Vérifie existence, format (.json/.yaml), signature obligatoire (`"signature"` key)
- Lève : `CalibrationArtifactNotFoundError`, `CalibrationArtifactFormatError`, `CalibrationArtifactValidationError`, `CalibrationArtifactSignatureError`, `CalibrationThresholdNotFoundError`
**Dépendances internes** : `calibration_loader.contracts`
**État** : COMPLETE
**Anomalies** : Aucune

---

### Fichier : `contracts.py` (~80L)
**Rôle** : `CalibrationArtifact(profile_id, version, signed_at, signature, thresholds: list[CalibrationThresholdEntry])`, `CalibrationThresholdEntry(threshold_id, value, unit, notes)`.
**État** : COMPLETE

---

## Package : `regime_classifier/`

### Fichier : `regime_lite.py` (~250L)
**Rôle** : Classificateur de régime 3 états (CALM/STRESSED/EXTREME) avec hystérèse et cooldown.
**Inputs** : `RegimeLiteInput(btc_realized_vol_24h, btc_drop_1h, intraday_drawdown, engine_return_dispersion)`
**Outputs** : `RegimeLiteAssessment(state, memory, thresholds_used)`, `RegimeLiteMemory`
**Équations mathématiques** :
```
État STRESSED si btc_realized_vol_24h > THR-RG01 OU intraday_drawdown > stressed_thr
État EXTREME  si btc_realized_vol_24h > THR-RG02 OU btc_drop_1h > extreme_drop_thr OU intraday_drawdown > extreme_thr
Hystérèse : downgrade_hysteresis_s secondes avant rétrogradation
Cooldown  : extreme_cooldown_s secondes en EXTREME avant retour possible
```
Thresholds calibrables : `THR-RG01` (vol stressed), `THR-RG02` (drop extreme), `THR-RG03` (hysteresis), `THR-RG04` (extreme cooldown)
**Dépendances internes** : `calibration_loader`
**État** : PARTIAL — logique présente, certains paramètres secondaires sur valeurs documentées par défaut en attente de calibration seam formelle

---

## Package : `execution_backbone/`

### Fichier : `__init__.py` (110L)
**Rôle** : Façade publique — re-exporte ExecutionRuntime, ExecutionGatekeeper, RateLimiter, SpreadGuard, SlippageModel, VenueConstraintProvider.
**État** : COMPLETE

---

### Fichier : `slippage_model.py` (66L)
**Rôle** : Consomme le modèle THR-X05 (régression sqrt-size) pour prédire le slippage.
**Inputs** : `ExecutionSlippageModel(intercept_bps, sqrt_size_coefficient, r_squared, mean_absolute_error_bps, reference_size)`, `size_value`
**Outputs** : `ExecutionSlippageEstimate(predicted_slippage_bps, cost_addition)`
**Équations mathématiques** :
```
predicted_slippage_bps = max(0, intercept_bps + sqrt_size_coefficient · √size_value)
```
**État** : COMPLETE

---

### Fichier : `spread_guard.py` (~80L)
**Rôle** : Évalue si le spread actuel est acceptable pour une execution.
**Outputs** : `ExecutionSpreadGuardDecision(allowed, spread_bps, threshold_bps)`
**État** : COMPLETE

---

### Fichier : `rate_limiter.py` (~80L)
**Rôle** : Contrôle le débit d'ordres (rate limit Binance).
**Outputs** : `ExecutionRateLimitDecision(allowed, current_weight, max_weight)`
**État** : COMPLETE

---

### Fichier : `emergency_circuit_breaker.py` (~150L)
**Rôle** : Circuit breaker d'urgence — bloque toutes les nouvelles exécutions si conditions critiques.
**Inputs** : Perte journalière, drawdown, nombre d'échecs consécutifs
**Outputs** : `EmergencyCircuitBreaker`, `KillSwitchState`, `KillSwitchRecord(reason, triggered_at_ms)`
**État** : COMPLETE

---

### Sous-package `execution_backbone/execution_cost_meter/`

**`elw_meter.py` (76L)** : Effective Liquidity Width — `ELW_i = |P_exec - Mid| / Mid`, `c_impl ≈ ELW_entry + ELW_exit`. **État** : COMPLETE

**`fee_meter.py` (~60L)** : Calcul des fees (taker/maker). **État** : COMPLETE

**`adverse_selection_meter.py` (~80L)** : Mesure de l'adverse selection post-fill. **État** : COMPLETE

**`partial_fill_cost_meter.py` (~80L)** : Coût des fills partiels. **État** : COMPLETE

**`cost_aggregator.py` (~80L)** : Agrège fee + spread + slippage + adverse selection en coût total. **État** : COMPLETE

---

### Sous-package `execution_backbone/fill_tracker/`

**`order_state_tracker.py` (~100L)** : Suit l'état des ordres (PENDING→SENT→PARTIAL→FILLED/CANCELLED). **État** : COMPLETE

**`fill_aggregator.py` (~80L)** : Agrège les fills partiels. **État** : COMPLETE

**`latency_meter.py` (~60L)** : Mesure la latence fill. **État** : COMPLETE

**`order_terminal_state_resolver.py` (~80L)** : Résout l'état terminal d'un ordre. **État** : COMPLETE

**`fill_reporter.py` (~60L)** : Rapport de fill structuré. **État** : COMPLETE

---

### Sous-package `execution_backbone/gatekeeper/`

**`gatekeeper.py` (~200L)** : Gate d'exécution à N passes — spread, rate limit, sharia, coordinations. **État** : COMPLETE

**`gatekeeper_support.py` (~100L)** : Helpers. **État** : COMPLETE

**`audit_logger.py` (~80L)** : Logger audit structuré pour décisions gatekeeper. **État** : COMPLETE

---

### Sous-package `execution_backbone/order_decider/`

**`intent_builder.py` (~80L)** : Construit `ExecutionIntent` depuis `RiskDecision` + `ScorePayload`. **État** : COMPLETE

**`order_type_selector.py` (~80L)** : Sélectionne type d'ordre (limit vs market). **État** : COMPLETE

**`execution_guard.py` (~80L)** : Garde finale avant envoi. **État** : COMPLETE

**`timeout_policy_selector.py` (~60L)** : Politique de timeout. **État** : COMPLETE

**`decision_reporter.py` (~60L)** : Rapport de décision. **État** : COMPLETE

---

### Sous-package `execution_backbone/reconciliation_layer/`

**`order_reconciler.py` (~100L)** : Réconciliation ordres local vs exchange. **État** : COMPLETE

**`fill_reconciler.py` (~80L)** : Réconciliation fills. **État** : COMPLETE

**`position_reconciler.py` (~100L)** : Réconciliation positions. **État** : COMPLETE

**`divergence_classifier.py` (~80L)** : Classification des divergences. **État** : COMPLETE

**`recovery_trigger.py` (~60L)** : Déclenchement de récupération. **État** : COMPLETE

**`scheduler.py` (~60L)** : Scheduling des réconciliations périodiques. **État** : COMPLETE

---

### Fichiers divers execution_backbone

**`execution_runtime.py` (~350L)** : Runtime d'exécution principal — `ExecutionRuntime` classe stateful gérant submission, timeout sweep, réconciliation. **État** : COMPLETE

**`execution_runtime_models.py` (~150L)** : `ExecutionRefusalSink`, `RemoteExecutionState`, `SubmitReceipt`, `ReplaceReceipt`, `TimeoutSweepResult`. **État** : COMPLETE

**`execution_runtime_support.py` (~100L)** : Helpers runtime. **État** : COMPLETE

**`fee_aware_edge_gate.py` (~80L)** : Gate fee-aware — bloque si edge net < seuil. **État** : COMPLETE

**`venue_constraints_provider.py` (~100L)** : Normalise les contraintes venue (tick_size, step_size, min_notional) depuis BinanceExchangeInfo. **État** : COMPLETE

---

## Package : `protocols/`

> Package très large (~100 fichiers) — les protocoles de runtime Shadow/Micro-live/Live, les bridges d'artefacts, et les contrats de promotion.

### Fichier : `engine_coordination_rules.py` (~100L)
**Rôle** : Règles de coordination inter-engines (C et D partagent ce module).
**Inputs** : `EngineCoordinationInput(engine_id, pair, coordination_peer_signals, thresholds)`
**Outputs** : `EngineCoordinationOutcome(allowed, reason_codes)`
**Équations mathématiques** : Thresholds de compatibilité inter-engine
**État** : COMPLETE

---

### Fichiers bridges (résumé)

Chaque bridge (`engine_a_pre_entry_confirmation_bridge.py`, `engine_b_sweep_validation_bridge.py`, etc.) expose l'interface du hook correspondant vers le registry d'artefacts. **État** : COMPLETE (6 bridges)

---

### Fichiers runtime (résumé)

**`shadow_runtime.py` (~400L)** : Orchestrateur principal du mode Shadow — loop de décision, DTR, journalisation. **État** : COMPLETE
**`micro_live_runtime.py` (~300L)** : Runtime Micro-live avec capital réel minimal. **État** : COMPLETE
**`live_light_runtime.py` (~300L)** : Runtime Live-Light (profil LIGHT). **État** : COMPLETE
**`promotion_gates.py` (~200L)** : Gates G1→G4 avec calcul PSR/DSR/SPA. **État** : COMPLETE
**`shadow_session_registry.py` (~150L)** : Registre des sessions shadow. **État** : COMPLETE
**`shadow_report_builder.py` (~200L)** : Construit les rapports shadow. **État** : COMPLETE
**`shadow_day_counter.py`, `shadow_day_counter_models.py`, `_reporting.py`, `_report_rendering.py`** : Compteur de jours shadow. **État** : COMPLETE
**`shadow_vps_service.py` (~500L)** : Service VPS autonome en boucle. **État** : COMPLETE
**`execution_runtime_bootstrap.py` (~200L)** : Bootstrap du runtime d'exécution. **État** : COMPLETE
**`compiled_artifact_registry_store.py`, `compiled_hook_plan_loader.py`** : Chargement artefacts compilés. **État** : COMPLETE

---

## Package : `risk_backbone/`

### Fichier : `risk_runtime.py` (60L)
**Rôle** : Façade publique — re-exporte `RiskRuntime`, modèles, et helpers de calibration drawdown.
**État** : COMPLETE

---

### Fichier : `risk_runtime_runtime.py` (~300L)
**Rôle** : `RiskRuntime` stateful — évalue candidats contre tous les budgets (exposure, loss, beta, cluster, drawdown).
**Inputs** : `RiskCandidate(pair, engine_id, projected_size, projected_loss, current_equity, session_peak_equity, pair_beta, cluster_id, physics_scores)`
**Outputs** : `RiskEvaluation(verdict, approved_size, block_reasons, explainability)`
**Dépendances internes** : exposure_budgeter, loss_budgeter, btc_factor_guard, correlation_cluster_guard
**État** : COMPLETE

---

### Fichier : `risk_runtime_models.py` (~200L)
**Rôle** : `RiskLimits`, `PortfolioRiskSnapshot`, `RiskEvaluation`, `RiskExplainability`, `RiskPhysicsScores`, hooks (MicroFriction, Regime, DailyPnl, InfoStress).
**État** : COMPLETE

---

### Sous-package `exposure_budgeter/`

**`gross_exposure_calculator.py` (~80L)** : `gross_exposure = sum(|position_size_i|)`. **État** : COMPLETE
**`gross_cap_guard.py` (~80L)** : Limite l'exposition brute totale. **État** : COMPLETE
**`position_cap_guard.py` (~80L)** : Limite par position individuelle. **État** : COMPLETE
**`projected_exposure_checker.py` (~80L)** : Vérifie l'exposition projetée avant trade. **État** : COMPLETE
**`exposure_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `loss_budgeter/`

**`aggregate_loss_budgeter.py` (~100L)** : Budget de perte total journalier. **État** : COMPLETE
**`daily_pnl_breaker.py` (~80L)** : Circuit breaker PnL journalier. **État** : COMPLETE
**`drawdown_guard.py` (~90L)** : Protection drawdown intraday. Thresholds : `warning=2%` (REDUCE_EXPOSURE), `observe=4%` (OBSERVE_ONLY). **État** : COMPLETE — **Anomalie** : thresholds 2%/4% hardcodés sans calibration seam formelle
**`loss_cap_guard.py` (~80L)** : Cap de perte par position. **État** : COMPLETE
**`position_loss_estimator.py` (~80L)** : Estime la perte potentielle. **État** : COMPLETE
**`projected_loss_checker.py` (~80L)** : Vérifie perte projetée. **État** : COMPLETE
**`loss_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `btc_factor_guard/`

**`pair_beta_registry.py` (~80L)** : Registre des betas BTC par paire. **État** : COMPLETE
**`portfolio_beta_calculator.py` (~80L)** : `portfolio_beta = sum(beta_i * weight_i)`. **État** : COMPLETE
**`projected_beta_checker.py` (~80L)** : Vérifie beta projeté. **État** : COMPLETE
**`beta_cap_guard.py` (~80L)** : Cap de beta portfolio. **État** : COMPLETE
**`beta_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `correlation_cluster_guard/`

**`cluster_registry.py` (~80L)** : Registre des clusters de corrélation. **État** : COMPLETE
**`cluster_exposure_calculator.py` (~80L)** : `cluster_exposure = sum(size_i for i in cluster)`. **État** : COMPLETE
**`projected_cluster_checker.py` (~80L)** : Vérifie exposition cluster projetée. **État** : COMPLETE
**`cluster_cap_guard.py` (~80L)** : Cap d'exposition par cluster. **État** : COMPLETE
**`cluster_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Fichiers divers risk_backbone

**`daily_pnl_breaker_entry_gate.py` (~80L)** : Gate d'entrée sur bris PnL journalier. **État** : COMPLETE
**`regime_lite_entry_gate.py` (~80L)** : Gate d'entrée sur régime. **État** : COMPLETE
**`regime_lite_safing.py` (~150L)** : Recommandations de safing selon régime. **État** : COMPLETE
**`info_stress_monitor.py` (~150L)** : Moniteur de stress informationnel. **État** : PARTIAL
**`risk_runtime_drawdown_calibration.py` (~80L)** : Calibration des thresholds drawdown via seam. **État** : COMPLETE
**`risk_runtime_evaluation_support.py` (~100L)** : Helpers évaluation. **État** : COMPLETE
**`risk_runtime_explainability.py` (~80L)** : Explainabilité des décisions risk. **État** : COMPLETE

---

## Package : `scoring_backbone/`

### Fichier : `scoring_runtime.py` (~200L)
**Rôle** : `ScoringRuntime` stateful — orchestre raw score → penalties → hard block → ranking selection.
**Inputs** : `ScoringCandidateInput(signal, projected_size, current_equity, portfolio, score_penalties, size_penalties, blocker_conditions, peer_candidates)`
**Outputs** : `ScoringRoundResult(audits, selection_result, blocked_candidates)`
**État** : COMPLETE

---

### Sous-package `raw_score_builder/`

**`raw_score_calculator.py` (~80L)** : Calcule `raw_score` à partir des features sélectionnées. **État** : COMPLETE
**`feature_selector.py` (~80L)** : Sélectionne les features selon engine_id. **État** : COMPLETE
**`score_component_breakdown.py` (~80L)** : Décomposition du score par composante. **État** : COMPLETE
**`score_reporter.py` (~60L)** : Rapport de score. **État** : COMPLETE

---

### Sous-package `penalty_aggregator/`

**`score_penalty_builder.py` (~80L)** : Construit les pénalités de score (soft). `ScorePenaltyItem(penalty_id, value, reason)`. **État** : COMPLETE
**`size_penalty_builder.py` (~80L)** : Pénalités de taille. `SizePenaltyItem`. **État** : COMPLETE
**`penalty_cap_guard.py` (~80L)** : `PenaltyCapVerdict` — limite la pénalité totale à un cap. **État** : COMPLETE
**`penalty_registry.py` (~80L)** : Registre des pénalités. **État** : COMPLETE
**`penalty_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `hard_block_gate/`

**`blocker_evaluator.py` (~100L)** : `BlockerCondition` + `evaluate_blockers()` — évalue toutes les conditions de blocage. **État** : COMPLETE
**`blocker_registry.py` (~80L)** : Registre des blockers. **État** : COMPLETE
**`blocker_reason_encoder.py` (~60L)** : Encode les raisons en `BlockReason`. **État** : COMPLETE
**`blocker_decision_builder.py` (~80L)** : Construit la décision finale. **État** : COMPLETE
**`blocker_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `ranking_router/`

**`candidate_pool_builder.py` (~80L)** : Construit le pool de candidats. **État** : COMPLETE
**`ranking_score_builder.py` (~80L)** : `RankingWeights` + `compute_ranking_scores()`. **État** : COMPLETE
**`portfolio_compatibility_checker.py` (~100L)** : `PortfolioState` + `check_portfolio_compatibility()`. **État** : COMPLETE
**`selection_resolver.py` (~100L)** : Résout la sélection finale. `SelectionEntry`, `SelectionOutcome`. **État** : COMPLETE
**`ranking_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Fichiers divers scoring_backbone

**`scoring_runtime_support.py` (~200L)** : `ScoringCandidateAudit`, `ScoringCandidateInput`, `ScoringPhysicsProjection`, helpers. **État** : COMPLETE
**`forecast_normalizer.py` (~80L)** : Normalise `forecast_strength` selon Carver ([-20, +20] → [-1, +1]). **État** : COMPLETE
**`break_even_filter.py` (~80L)** : Filtre break-even sur edge net. **État** : COMPLETE
**`fee_aware_edge_gate.py` (~80L)** : Re-export ou adaptation. **État** : COMPLETE
**`engine_a_cost_thresholds.py`**, **`engine_b_*_thresholds.py`**, **`engine_c_continuation_thresholds.py`** : Singletons de thresholds TO_CALIBRATE. **État** : PARTIAL (valeurs défaut, en attente calibration signée)

---

## Package : `data_backbone/`

### Fichier : `__init__.py` (~80L)
**Rôle** : Façade publique + constante `TO_CALIBRATE`. Re-exporte `market_physics_math`, `resolve_delta_confirmation`, etc.
**État** : COMPLETE

---

### Fichier : `market_physics_math.py` (~300L)
**Rôle** : Primitives mathématiques partagées pour les features physics (VPS et Lab).
**Inputs** : scalaires `float`
**Outputs** : `float` (IEEE-754 binary64)
**Équations mathématiques** :
```
clip01(x)        = max(0, min(1, x))
zplus(x, cap=3)  = clip01(max(x, 0) / cap)
capratio(x, cap) = clip01(x / cap)

delta_proxy_soft(O, H, L, C) = (2C - H - L) / (H - L)  si H != L, sinon 0
delta_proxy_sign(O, H, L, C) = sign(C - O)

sweep_score = clip01(0.45·wick_ratio_capratio + 0.35·vol_burst_capratio + 0.20·reject_indicator)
fragility_score = clip01(0.70·base_fragility + 0.20·spread_regime_penalty + 0.10·book_resiliency_penalty)
toxicity_score  = clip01(0.60·base_toxicity + 0.20·fragility + 0.10·spread_regime + 0.10·vol_jump)
execution_survivability = clip01(0.45·fragility + 0.35·toxicity + 0.15·spread_regime + 0.05·participation)
micro_friction  = clip01(0.40·spread_regime + 0.25·fragility + 0.25·toxicity + 0.10·participation)
```
**État** : COMPLETE
**Anomalies** : Poids hardcodés mais documentés dans `*_WEIGHTS` dicts — acceptable car phase TO_CALIBRATE

---

### Sous-package `microstructure/`

**`order_flow_imbalance.py` (~200L)** : OFI Cont-Kukanov-Stoikov — contribution event-driven.
```
OFI_event = (bid_up·q_bid_new) - (bid_down·q_bid_old) - (ask_down·q_ask_new) + (ask_up·q_ask_old)
cumulative_OFI = Σ OFI_event   sur fenêtre glissante
```
Version : `order_flow_imbalance.cont_kukanov.v1`, hash SHA256. **État** : COMPLETE

**`realized_kernel_vol.py` (~250L)** : Réalisé kernel volatilité (Barndorff-Nielsen et al. 2008) avec noyau Parzen.
```
H = ceil(c · n^(3/5))  [bandwidth]
k(x) = 1 - 6x² + 6|x|³  si |x| ≤ 0.5
       2(1-|x|)³           si 0.5 < |x| ≤ 1
RK = Σ_h k(h/H) · Σ_t r_t · r_{t-h}   où r_t = log(p_t/p_{t-1})
```
Version : `realized_kernel_vol.parzen.v1`. **État** : COMPLETE

**`vpin.py` (~200L)** : VPIN Easley-Lopez-O'Hara — probabilité de trade informé.
```
Bucket : volumes égaux (bucket_volume = V_daily / buckets_per_day)
bulk_volume_class_buy = V_bucket · Φ(ΔP / σ_ΔP)
VPIN = (1/n) · Σ_τ |V_buy,τ - V_sell,τ| / V_bucket
```
Version : `vpin.easley_lopez_ohara.v1`. **État** : COMPLETE

**`kyle_lambda.py` (~220L)** : Kyle's lambda — impact prix via OLS rolling.
```
ΔP_t = λ · Σ_signed_volume + ε    [OLS sur intervalles de 1min]
λ = Cov(ΔP, V_signed) / Var(V_signed)
```
Version : `kyle_lambda.rolling_ols.v1`. **État** : COMPLETE

**`hawkes_intensity.py` (~200L)** : Intensité Hawkes univariée (noyau exponentiel).
```
λ(t) = μ + Σ_{t_i < t} α · exp(-β · (t - t_i))
branching_ratio ρ = α / β   (stabilité : ρ < 1)
```
Version : `hawkes_intensity.exponential_univariate.v1`. **État** : COMPLETE

**`amihud_illiquidity.py` (~180L)** : Ratio d'illiquidité Amihud.
```
ILLIQ_t = |R_t| / V_t   où V_t = volume notionnel
ILLIQ_roll = (1/T) · Σ ILLIQ_t
```
**État** : COMPLETE

**`corwin_schultz_spread.py` (~180L)** : Estimateur de spread Corwin-Schultz.
```
β = [log(H/L)]² + [log(H_2day/L_2day)]²   (variances log-range)
γ = [log(H_2day/L_2day)]²
α = (√(2β) - √β) / (3 - 2√2) - √(γ / (3 - 2√2))
S_CS = 2 · (exp(α) - 1) / (1 + exp(α))
```
**État** : COMPLETE

**`pin.py` (~200L)** : PIN (Probability of Informed trading) via MLE.
**État** : PARTIAL — MLE convergence dépend des données

**`queue_pressure.py` (~150L)** : Pression sur la queue bid/ask.
**État** : COMPLETE

**`realized_effective_spread.py` (~150L)** : Spread effectif réalisé (Roll).
**État** : COMPLETE

**`roll_spread.py` (~120L)** : Estimateur Roll (covariable des price changes).
```
S_Roll = 2 · √(-Cov(ΔP_t, ΔP_{t-1}))
```
**État** : COMPLETE

**`spread_dynamics.py` (~150L)** : Dynamiques de spread (élargissement/compression).
**État** : COMPLETE

**`feature_registry.py` (~100L)** : Registre des features microstructure disponibles.
**État** : COMPLETE

**`engine_input_provenance.py` (~80L)** : Traçabilité de la provenance des inputs engine.
**État** : COMPLETE

---

### Sous-packages data_backbone (résumé)

**`websocket_gateway/`** (7 fichiers) : `connection_manager.py`, `heartbeat_monitor.py`, `reconnect_controller.py`, `subscription_manager.py`, `raw_message_emitter.py`, `injected_stream_loader.py`, `runtime_gateway.py`. Gestion WebSocket avec reconnexion, heartbeat, injection de stream (replay). **État** : COMPLETE

**`event_normalizer/`** (5 fichiers) : `message_classifier.py`, `schema_mapper.py`, `invalid_message_guard.py`, `timestamp_enricher.py`, `normalization_reporter.py`. Normalise les messages WS en `KlineEvent/TradeEvent/DepthEvent`. **État** : COMPLETE

**`consistency_checker/`** (5 fichiers) : `gap_detector.py`, `duplicate_detector.py`, `sequence_checker.py`, `contradiction_checker.py`, `consistency_reporter.py`. Détecte gaps, duplicates, séquences invalides. **État** : COMPLETE

**`freshness_checker/`** (6 fichiers) : `age_calculator.py`, `last_update_tracker.py`, `stale_penalty_builder.py`, `stale_hard_guard.py`, `venue_stream_freshness.py`, `freshness_reporter.py`. Fraîcheur des données par paire. **État** : COMPLETE

**`pair_health_scorer/`** (5 fichiers) : `quality_aggregator.py`, `health_state_tracker.py`, `recovery_evaluator.py`, `suspension_decider.py`, `health_reporter.py`. Score de santé agrégé. **État** : COMPLETE

**`internal_router/`** (5 fichiers) : `consumer_registry.py`, `queue_manager.py`, `priority_dispatcher.py`, `backpressure_guard.py`, `routing_reporter.py`. Routage interne des events. **État** : COMPLETE

**`rest_bootstrap/`** (5 fichiers) : `snapshot_fetcher.py`, `gap_fill_controller.py`, `rate_limit_guard.py`, `runtime_bootstrap.py`, `bootstrap_reporter.py`. Bootstrap REST pour remplir les gaps d'historique. **État** : COMPLETE

---

## Package : `venue_adapters/`

### Sous-package `binance_spot/`
**Rôle** : Adapter Binance Spot — authentication, order placement, fills, exchange info.
**Fichiers** : À lister (non explorés en détail)
**Dépendances internes** : `interface_contracts.binance_contracts`, `execution_backbone`
**État** : À auditer (non lu en détail dans cette session)

---

## Package : `monitoring/`

### Fichier : `monitoring_runtime.py` (~200L)
**Rôle** : Runtime de monitoring — collecte métriques, génère alertes.
**État** : COMPLETE

**`observability.py` (~200L)** : API d'observabilité — émet logs structurés, métriques. **État** : COMPLETE
**`metrics_collector.py` (~150L)** : Collecteur de métriques système. **État** : COMPLETE
**`alert_manager.py` (~150L)** : Gestion des alertes avec déduplication. **État** : COMPLETE
**`disk_monitor.py` (~100L)** : Surveillance espace disque. **État** : COMPLETE
**`process_metrics.py` (~100L)** : Métriques process (CPU, RAM). **État** : COMPLETE

**Modules Grafana/Prometheus** :
**`grafana_types.py`**, **`local_grafana_api.py`**, **`local_grafana_dashboard.py`**, **`local_lab_grafana_dashboard.py`**, **`local_prometheus_config.py`**, **`local_prometheus_metrics_bridge.py`** : Intégration Grafana + Prometheus locaux. **État** : COMPLETE

**Modules VPS** :
**`shadow_vps_service_monitoring.py` (~300L)**, **`shadow_vps_scrape_discovery.py`**, **`shadow_vps_service_log_retrieval.py`**, **`shadow_vps_service_scrape_manifest.py`** + supports : Monitoring du service VPS autonome. **État** : COMPLETE

**Modules Lab** :
**`local_lab_bundle_discovery.py`**, **`local_lab_bundle_loader.py`**, **`local_lab_ingestion.py`**, **`local_lab_monitoring_backend.py`**, **`local_lab_monitoring_bundle_manifest.py`**, **`local_lab_monitoring_feed.py`**, **`local_lab_monitoring_projection.py`**, **`local_lab_observability.py`** : Pipeline de monitoring Lab. **État** : COMPLETE

**`health_dashboard_backend.py` (~200L)**, **`technical_dashboard_backend.py` (~200L)**, **`technical_dashboard_backend_support.py`** : Backends dashboard. **État** : COMPLETE

**`contracts.py`**, **`contracts_core.py`**, **`contracts_dashboard.py`**, **`contracts_vps.py`** : Contrats monitoring. **État** : COMPLETE
**`build14_observation.py` (~100L)** : Observation Build-14 dans le monitoring. **État** : COMPLETE
**`log_rotation.py` (~80L)** : Rotation des logs. **État** : COMPLETE
**`observability_io.py`**, **`observability_support.py`** : Support observabilité. **État** : COMPLETE

---

## Package : `alerting/`

### Fichier : `telegram_alerter.py` (~200L)
**Rôle** : Envoi d'alertes Telegram — format, retry, throttle.
**Inputs** : `AlertRecord` + configuration Telegram (token, chat_id)
**Outputs** : Livraison Telegram avec statut
**Anomalies** : Token/chat_id chargés depuis `secrets_manager`
**État** : COMPLETE

---

## Package : `sharia_compliance/`

### Fichier : `purification_calculator.py` (~150L)
**Rôle** : Calcul déterministe de la purification halal.
**Inputs** : asset_received, quantity, unit_price_quote, source (PurificationSourceType), policy (ShariaPolicy)
**Outputs** : `PurificationEstimate(purification_amount_quote, purification_rate)`
**Équations mathématiques** :
```
gross_amount_quote = quantity × unit_price_quote
purification_amount = gross_amount × rate    (rate calibré via THR-H03 pour stablecoins)
```
**Dépendances internes** : `calibration_loader`
**État** : PARTIAL — stablecoin path dépend de `THR-H03` calibration

---

**`pair_screening.py` (~150L)** : Screening halal des paires. **État** : COMPLETE
**`pair_screening_registry.py` (~80L)** : Registre des paires autorisées. **État** : COMPLETE
**`trade_type_guard.py` (~80L)** : Garde sur type de trade (spot uniquement). **État** : COMPLETE
**`asset_whitelist.py`, `asset_blacklist.py`** : Listes blanches/noires. **État** : COMPLETE
**`contracts.py` (~100L)** : `ShariaPolicy`, `PurificationEstimate`, `PurificationSourceType`. **État** : COMPLETE
**`sharia_runtime.py` (~200L)** : Runtime sharia — `ShariaTradeAuthorizer`. **État** : COMPLETE
**`policy_loader.py` (~80L)** : Charge la politique sharia. **État** : COMPLETE
**`policy_audit_logger.py` (~80L)** : Log d'audit sharia. **État** : COMPLETE
**`stablecoin_policy.py` (~80L)** : Politique stablecoin. **État** : COMPLETE
**`account_features_audit.py` (~80L)** : Audit des fonctionnalités compte. **État** : COMPLETE
**`pair_screening_audit.py` (~80L)** : Audit screening. **État** : COMPLETE
**`sharia_alerts.py` (~80L)** : Alertes sharia. **État** : COMPLETE

---

## Package : `portfolio/`

### Fichier : `__init__.py` (~30L)
**Rôle** : Package portfolio — stub ou re-export minimal. Contenu : probablement re-exports de `portfolio_minimal`.
**État** : À vérifier — possiblement SKELETON si vide

---

## Package : `portfolio_minimal/`

### Fichier : `portfolio_orchestrator.py` (~250L)
**Rôle** : Orchestrateur end-to-end allocation (Build-8) — pipeline en 9 étapes.
**Pipeline** :
1. `candidate_pool_builder` → filtre score positif + taille
2. `correlation_conflict_checker` → déduplique par ranking_score
3. `comparative_ranker` → rank par R_i composite
4. `selection_resolver` → sélectionne éligibles
5. `base_size_builder` → taille de base depuis profil
6. `score_size_mapper` → modulation tier + score
7. `portfolio_cap_applier` → caps gross/cluster/loss/beta
8. `phantom_trade_guard` → stérilise allocations non-viables
9. `allocation_reporter` → rapport final
**État** : COMPLETE

---

### Sous-package `opportunity_selector/`

**`candidate_pool_builder.py` (~100L)** : Pool de candidats. `CandidatePoolFreshnessPolicy`. **État** : COMPLETE
**`eligibility_filter.py` (~80L)** : `PortfolioSnapshot` + filtre éligibilité. **État** : COMPLETE
**`comparative_ranker.py` (~80L)** : Ranking comparatif `R_i`. **État** : COMPLETE
**`correlation_conflict_checker.py` (~80L)** : Déduplication par corrélation. **État** : COMPLETE
**`selection_resolver.py` (~80L)** : Résolution sélection. **État** : COMPLETE

---

### Sous-package `allocation_router/`

**`base_size_builder.py` (~80L)** : `SizeProfile` + `compute_base_size()`. **État** : COMPLETE
**`score_size_mapper.py` (~80L)** : Modulation taille par score. **État** : COMPLETE
**`portfolio_cap_applier.py` (~100L)** : `CapApplicationResult` + `apply_caps()`. **État** : COMPLETE
**`phantom_trade_guard.py` (~80L)** : `PhantomVerdict` + `check_phantom()`. **État** : COMPLETE
**`allocation_reporter.py` (~80L)** : `AllocationEntry`, `AllocationReport`, `build_report()`. **État** : COMPLETE

---

## Package : `meta_learning/`

### Fichier : `mistake_classifier.py` (~100L)
**Rôle** : Classifie les erreurs de trading pour apprentissage réflexif.
**État** : PARTIAL

### Fichier : `checklist_generator.py` (~80L)
**Rôle** : Génère des checklists de validation basées sur les erreurs passées.
**État** : PARTIAL

### Fichier : `learning_memory_store.py` (~100L)
**Rôle** : Stocke les patterns d'erreurs et apprentissages.
**État** : PARTIAL

---

## Package : `meta_minimal/`

### Sous-package `dtr_core/`

**`decision_state_encoder.py` (~70L)** : `DecisionState` enum (8 états) + `encode_state()` avec priorité. **État** : COMPLETE
**`cause_chain_assembler.py` (~80L)** : Assemble la chaîne causale d'une décision. **État** : COMPLETE

---

### Sous-package `cra_monitor/`

**`reduction_trace_reader.py` (~80L)** : Lit la trace de réduction de taille. **État** : COMPLETE
**`phantom_risk_estimator.py` (~80L)** : Estime le risque des trades phantoms (capital stérilisé). **État** : COMPLETE
**`sterilization_classifier.py` (~80L)** : Classifie la stérilisation. **État** : COMPLETE
**`cra_reporter.py` (~60L)** : Rapport CRA. **État** : COMPLETE
**`cra_alert_builder.py` (~60L)** : Construit alertes CRA. **État** : COMPLETE

---

### Sous-package `break_even_dashboard/`

**`expected_break_even_calculator.py` (~80L)** : Calcule le break-even attendu. **État** : COMPLETE
**`realized_break_even_calculator.py` (~80L)** : Break-even réalisé. **État** : COMPLETE
**`cost_distribution_aggregator.py` (~80L)** : Distribution des coûts. **État** : COMPLETE
**`motor_pair_break_even_view.py` (~80L)** : Vue par paire/moteur. **État** : COMPLETE
**`break_even_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `edge_tracker_prudent_minimal/`

**`return_aggregator.py` (~80L)** : Agrège les retours par scope (paire/engine). **État** : COMPLETE

**`uncertainty_estimator.py` (~80L)** : Estime l'incertitude autour de l'edge.
```
σ̂² = (1/(N-1)) · Σ(r_i - μ̂)²
SE(μ̂) = σ̂ / √N
Sharpe_per_trade = μ̂ / σ̂
CI_95 ≈ [μ̂ - 2·SE, μ̂ + 2·SE]
```
**État** : COMPLETE

**`sample_size_tracker.py` (~60L)** : Suit la taille d'échantillon. **État** : COMPLETE
**`edge_status_classifier.py` (~80L)** : Classifie le statut d'edge (positif/négatif/incertain). **État** : COMPLETE
**`edge_reporter.py` (~60L)** : Rapport. **État** : COMPLETE

---

### Sous-package `refusal_journal/`
**Rôle** : Journalisation des refus (Taleb — anti-fragility).
**État** : À auditer

---

## Package : `local_replay_runtime/`

> Grand package (~50 fichiers) — infrastructure complète LOCAL_REPLAY + Local Lab.

### Groupes fonctionnels :

**Orchestration replay** :
- `LocalReplayOrchestrator` — orchestrateur principal
- `replay_orchestrator.py` — `orchestrate_local_replay_export()`
- `replay_executor.py` — `execute_local_replay_export()`
- `replay_clock.py` — `HistoricalReplayClock`, `build_replay_clock()`
- `replay_event_router.py` — routage d'événements historiques
- `replay_session_config.py` — config session replay
- `replay_state_store.py` — état session

**Lab analytique** :
- `edge_gate_calibration.py` — calibration edge gates (`THR-*`)
- `local_lab_scope_matrix.py` — matrice de scope
- `local_lab_recalibration_plan.py` — plan de recalibration
- `local_lab_calibration_methods_review.py` — revue méthodes
- `local_lab_execution_review.py` — revue exécution
- `local_lab_tail_risk_review.py` — revue tail risk (POT-GPD)
- `local_lab_multiple_testing_review.py` — revue tests multiples (Holm-Bonferroni)
- `local_lab_loss_surrogate.py` — modèle substitut de perte
- `local_lab_research_priority.py` — priorisation recherche

**Artefacts** :
- `artifact_exporter.py` — export artefacts signés
- `artifact_manifest.py` — manifest d'artefact
- `artifact_proof_summary_builder.py` — résumé proof
- `artifact_ablation_study.py` — étude d'ablation
- `artifact_release_candidate.py` — candidat release

**Métriques** :
- `replay_metrics_collector.py` — `ReplayMetricsSummary`, `build_replay_metrics_summary()`
- `run_consistency_guard.py` — vérification cohérence entre runs

**Données** :
- `historical_data_gateway.py` — gateway données historiques
- `historical_snapshot_loader.py` — chargement snapshots

**Tous ces fichiers** : **État** : COMPLETE (infrastructure mature)

---

## Package : `manifest_registry/`

### Fichier : `__init__.py` (130L)
**Rôle** : Registre canonique de tous les modules V5.3 — inventaire, dépendances, profils, build order, versioning.
**Sous-fichiers** :
- `module_inventory.py` : `MODULES`, `ModuleEntry`, `get_modules_by_*`
- `dependency_registry.py` : `ALLOWED_DEPENDENCIES`, `is_dependency_allowed()`
- `profile_registry.py` : `PROFILE_ENGINES`, `PROFILE_PAIRS`, LIGHT vs COMPLETE
- `build_order_registry.py` : `BUILD_STAGES`, `BuildStage`, `get_modules_in_order()`
- `version_registry.py` : `MANIFEST_VERSION`, `ManifestDiff`, `diff_snapshots()`
**État** : COMPLETE

---

## Package : `backtest_artifact_import/`

**`contracts.py`** : Contrats d'import d'artefacts backtest. **État** : COMPLETE
**`ed25519_verifier.py`** : Vérification signature Ed25519. **État** : COMPLETE
**`compatibility_policy.py`** : Politique de compatibilité. **État** : COMPLETE
**`signature_policy.py`** : Politique de signature. **État** : COMPLETE
**`export_dir_bridge.py`** : Bridge vers répertoire export. **État** : COMPLETE
**`export_dir_bridge_models.py`**, **`export_dir_bridge_support.py`** : Support. **État** : COMPLETE
**`upload_bridge.py`** : Bridge upload Lab→VPS. **État** : COMPLETE
**`local_lab_upload_bridge_candidate.py`**, **`_support.py`** : Candidat upload. **État** : COMPLETE
**`monitoring_projection.py`** : Projection de monitoring. **État** : COMPLETE
**`validators.py`** : Validators artefacts. **État** : COMPLETE
**`errors.py`** : Erreurs. **État** : COMPLETE

---

## Package : `complete_enablers/`

**`competition_monitor.py` (~150L)** : Moniteur de densité de compétition (microstructure). **État** : COMPLETE
**`execution_fragility_score.py` (~150L)** : Score de fragilité d'exécution. **État** : COMPLETE
**`market_toxicity_snapshot.py` (~150L)** : Snapshot toxicité marché. **État** : COMPLETE
**`false_breakout_model.py` (~150L)** : Modèle de faux breakout. **État** : COMPLETE
**`hurst_regime_classifier.py` (~150L)** : Classificateur régime Hurst (H < 0.5 mean-rev, H > 0.5 trending). **État** : COMPLETE
**`limited_influence.py` (~100L)** : Gouvernance limited influence pour enablers. **État** : COMPLETE
**`lob_deep_filter_vwa.py` (~150L)** : Filtre LOB profond (volume-weighted average). **État** : COMPLETE
**`micro_edge_entry_timing_layer.py` (~150L)** : Couche timing entrée micro-edge. **État** : COMPLETE
**`micro_edge_exit_governor.py` (~150L)** : Gouverneur sortie micro-edge. **État** : COMPLETE
**`order_book_imbalance.py` (~100L)** : Imbalance carnet d'ordres. **État** : COMPLETE
**`contracts.py`**, **`enums.py`**, **`errors.py`** : Contrats/enums/erreurs. **État** : COMPLETE

---

## Package : `dag_validator/`

### Fichier : `__init__.py` (140L)
**Rôle** : Point d'entrée unique `validate_architecture()` — scan imports AST → match manifest → cycles → layers → rapport.
**État** : COMPLETE

**`import_scanner.py` (~100L)** : Scan AST des imports Python. **État** : COMPLETE
**`dependency_matcher.py` (~100L)** : Match imports vs `ALLOWED_DEPENDENCIES`. **État** : COMPLETE
**`cycle_detector.py` (~100L)** : Détection de cycles (DFS). **État** : COMPLETE
**`layer_validator.py` (~100L)** : Validation hiérarchie des couches. **État** : COMPLETE
**`report_builder.py` (~100L)** : Construction du rapport. **État** : COMPLETE

---

## Package : `contract_test_suite/`

**`contract_models.py` (~100L)** : Modèles de tests de contrats. **État** : COMPLETE
**`contract_test_runner.py` (~150L)** : Runner de tests de contrats. **État** : COMPLETE
**`contract_reporter.py` (~80L)** : Rapport de tests contrats. **État** : COMPLETE
**`compatibility_checker.py` (~100L)** : Vérification de compatibilité entre versions. **État** : COMPLETE

---

## Package : `secrets_manager/`

**`loader.py` (~100L)** : Charge les secrets chiffrés. **État** : COMPLETE
**`sealer.py` (~80L)** : Scelle les secrets. **État** : COMPLETE
**`_dpapi.py` (~60L)** : Interface DPAPI Windows (chiffrement natif). **État** : COMPLETE
**`cli.py` (~100L)** : Interface CLI. **État** : COMPLETE
**`__main__.py` (~20L)** : Point d'entrée CLI. **État** : COMPLETE

---

## Package : `smoke_bootstrap_recovery/`

**`smoke_models.py` (~80L)** : Modèles pour smoke tests. **État** : COMPLETE
**`smoke_reporter.py` (~80L)** : Rapport smoke tests. **État** : COMPLETE

---

## Package : `ui/`

> Non exploré en détail dans cette session. Probablement une interface CLI ou web dashboard.
**État** : À auditer

---

## Package : `meta/` et `meta_minimal/refusal_journal/`

> `meta/` : Probablement façade de `meta_minimal`. À auditer.
> `refusal_journal/` : Journal de refus (Taleb quadruple filter). À auditer en détail.

---

# Synthèse — Plan d'action pour Opus

## Fichiers SKELETON (à compléter en priorité)

| Package | Fichier | Raison |
|---------|---------|--------|
| `portfolio/` | `__init__.py` | Probablement vide/stub, à vérifier |
| `meta/` | Tous fichiers | Contenu non exploré, potentiellement skeleton |
| `ui/` | Tous fichiers | Non exploré |
| `meta_minimal/refusal_journal/` | Tous fichiers | Non exploré |
| `calibration_methods/stationarity.py` | — | Dépendances statsmodels non confirmées |
| `calibration_methods/walkforward.py` | — | Logique partielle |
| `venue_adapters/binance_spot/` | Tous fichiers | Non exploré en détail |

---

## Fichiers PARTIAL (à compléter)

| Package | Fichier | Ce qui manque |
|---------|---------|---------------|
| `engines/engine_a/structure_detector_a.py` | — | Poids et thresholds TO_CALIBRATE (calibration signée requise) |
| `engines/engine_a/context_validator_a.py` | — | Idem |
| `engines/engine_a/conviction_builder_a.py` | — | Idem |
| `engines/engine_a/cost_feasibility_a.py` | — | Idem |
| `engines/engine_b/excess_detector_b.py` | — | THR-B05..09 TO_CALIBRATE |
| `engines/engine_b/local_mean_estimator_b.py` | — | min_std=1e-12, TO_CALIBRATE |
| `engines/engine_b/anti_breakout_filter_b.py` | — | Logique partielle |
| `engines/engine_c/structure_resolver_c.py` | — | TO_CALIBRATE |
| `engines/engine_c/continuation_validator_c.py` | — | TO_CALIBRATE |
| `engines/engine_c/conviction_builder_c.py` | — | TO_CALIBRATE |
| `engines/engine_d/context_resolver_d.py` | — | TO_CALIBRATE |
| `engines/engine_d/conviction_builder_d.py` | — | TO_CALIBRATE |
| `calibration_methods/stationarity.py` | — | Dépendances externes à confirmer |
| `calibration_methods/multiple_testing_guard.py` | — | Harvey-Liu-Zhu partiel |
| `calibration_methods/walkforward.py` | — | Split IS/OOS partiel |
| `calibration_methods/execution.py` | — | Helpers partiels |
| `regime_classifier/regime_lite.py` | — | Paramètres secondaires hors seam formelle |
| `risk_backbone/info_stress_monitor.py` | — | Logique partielle |
| `scoring_backbone/engine_*_thresholds.py` | (5 fichiers) | Tous TO_CALIBRATE |
| `sharia_compliance/purification_calculator.py` | — | Stablecoin path dépend THR-H03 |
| `meta_learning/mistake_classifier.py` | — | Logique partielle |
| `meta_learning/checklist_generator.py` | — | Logique partielle |
| `meta_learning/learning_memory_store.py` | — | Logique partielle |
| `calibration_methods/pin.py` | — | MLE convergence conditionnelle |

---

## Anomalies critiques

| Sévérité | Fichier | Anomalie |
|----------|---------|---------|
| **BUG** | `interface_contracts/feature_lock_contracts.py:37` | Typo dans valeur enum : `"toxcity_fragility_survivability"` (manque `i`) — si comparé par `.value` string, mismatch garanti |
| **P1** | `risk_backbone/loss_budgeter/drawdown_guard.py` | Thresholds drawdown 2%/4% hardcodés sans calibration seam formelle (TO_CALIBRATE manquant) |
| **P2** | Tous engines conviction/structure/context | Poids calibration hardcodés, marqués TO_CALIBRATE mais jamais chargés depuis artefact calibration en runtime actuel |
| **P2** | `calibration_methods/stationarity.py` | Dépendance `statsmodels` non confirmée dans requirements — risque import error |
| **P2** | `complete_enablers/hurst_regime_classifier.py` | Algorithme Hurst non vérifié en détail — potentiellement basé sur rescaled range (R/S), à confirmer |

---

## Dépendances manquantes

| Module | Import problématique | Statut |
|--------|---------------------|--------|
| `engines/*/conviction_builder_*.py` | `data_backbone.market_physics_math` — présent | OK |
| `protocols/engine_coordination_rules.py` | Utilisé par engines C et D — présent | OK |
| `risk_backbone/emergency_kill_switch/circuit_breaker.py` | Re-export de `execution_backbone.emergency_circuit_breaker` — présent | OK |
| `calibration_methods/hansen_spa.py` | `calibration_methods.bootstrap` — présent | OK |
| `sharia_compliance/purification_calculator.py` | `calibration_loader.loader.CalibrationLoader` — présent | OK |
| `venue_adapters/binance_spot/` | Contenu non vérifié — risque d'imports non satisfaits | À vérifier |
| `ui/` | Dépendances non vérifiées | À vérifier |

---

## Recommandations sprints suivants

### Priorité S32 — Fermeture calibration (pré-G2.1)

1. **Calibrer et signer les seams TO_CALIBRATE** — engines A/B/C/D (structure, context, conviction, cost) sont fonctionnellement complets mais bloqués par l'absence d'artefacts calibration signés. Chaque module a son `profile_id` défini, les IDs de threshold (`THR-B05`, etc.) sont déclarés. Tâche : produire les artefacts YAML signés et les charger via `CalibrationLoader`.

2. **Corriger la typo enum** dans `feature_lock_contracts.py` ligne 37 : `"toxcity_fragility_survivability"` → `"toxicity_fragility_survivability"`. **BUG confirmé, P0 si utilisé comme lookup**.

3. **Formaliser les thresholds drawdown** dans `drawdown_guard.py` via calibration seam (actuellement 2%/4% hardcodés).

4. **Auditer `venue_adapters/binance_spot/`** et `ui/` — non couverts dans cette session.

5. **Auditer `meta/` et `meta_minimal/refusal_journal/`** — non couverts.

### Priorité S33 — Tests gates math

6. **Tests G2.1** : valider PSR, DSR, Hansen SPA sur données shadow réelles.

7. **Tests POT-GPD** : valider `pot_gpd.py` avec données de pertes réelles.

8. **Tests stationarité** : confirmer dépendances `calibration_methods/stationarity.py`.

### Priorité S34 — Shadow promotion

9. **Activer `promotion_gates.py`** avec gates G1→G4 sur sessions shadow accumulées.

10. **Valider `regime_lite.py`** thresholds via calibration THR-RG01..04.

---

*Document produit par lecture directe des fichiers source. Toute modification de src/ invalide partiellement ce document.*
*Prochaine révision recommandée : après fermeture calibration S32.*
