# Cartographie Groupe C — Backbone & Contrats
**Date** : 2026-04-19
**Agent** : Claude Sonnet 4.6
**Packages couverts** : `interface_contracts/`, `regime_classifier/`, `risk_backbone/`, `scoring_backbone/`, `execution_backbone/`
**Racine** : `v53_trading_system/src/`

---

## 1. `interface_contracts/`

### Fichier : `__init__.py` (128L)
**Rôle** : Re-export central de tous les types contractuels ; version de contrat `1.0.0`.
**Inputs** : N/A (module init)
**Outputs** : re-exports via `__all__` (128 symboles)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Tous les sous-modules du package.
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `domain_types.py` (272L)
**Rôle** : Types métier élémentaires — enums, NewTypes, PairId, TimestampedModel, constantes paires.
**Inputs** : N/A (module de types)
**Outputs** : Enums, modèles Pydantic, frozensets
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `EngineId` : A, B, C, D
- `RegimeId` : TRENDING_UP/DOWN, RANGE_BOUND, HIGH_VOLATILITY, LOW_VOLATILITY, BREAKOUT, UNKNOWN
- `ProfileId` : LIGHT, COMPLETE
- `RuntimeMode` : LOCAL_REPLAY, SHADOW, MICRO_LIVE, LIVE
- `DeploymentState` : OFFLINE, BOOTSTRAP, SHADOW, MICRO_LIVE, LIVE_LIGHT, LIVE_COMPLETE, DEGRADED, HALTED, ROLLBACK
- `LIGHT_PAIRS` : 6 paires (BTC/ETH/BNB/SOL/XRP/LINK)
- `ALL_PAIRS` : 12 paires
- `V53_MULTIPAIR_7` : 7 paires canoniques Phase-1
- `PairId` : `symbol: str`, `tier: Tier` (frozen, validé contre ALL_PAIRS)
- `TimestampedModel` : `timestamp_ms: int` (ge=1_000_000_000_000, le=9_999_999_999_999)

---

### Fichier : `decision_contracts.py` (185L)
**Rôle** : Structures de la chaîne de décision signal → score → risk → execution → portfolio.
**Inputs** : N/A (types)
**Outputs** : Dataclasses Pydantic
**Équations mathématiques** :
- `expected_risk_reward = |take_profit - entry_price| / |entry_price - stop_loss|` (L86-93)
- `slippage_bps = |filled_price - target_price| / target_price * 10_000` (L164-167)
- `fill_ratio = filled_size / size` (L158-161)
**Logging** : Aucun.
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : `_EPSILON_RISK = 1e-6` hardcodé L73 (guard division nulle — acceptable).
**Champs clés** :
- `SignalCandidate` : `pair, engine_id, signal_type, side, confidence [0,1], regime, entry_price, stop_loss?, take_profit?, max_hold_ms?`
- `ScorePayload` : `pair, engine_id, raw_score [0,1], penalty_total [0,1], final_score [0,1], rank, hard_blocked, penalties, block_reasons, estimated_cost_bps?`
- `RiskDecision` : `pair, engine_id, verdict, requested_size, approved_size, exposure_used_pct, loss_budget_used_pct, block_reasons, btc_beta?, cluster_exposure?`
- `ExecutionIntent` : `pair, engine_id, side, size, target_price, order_type (limit|market), status, order_id?, filled_size?, filled_price?, fill_latency_ms?, execution_cost_bps?`
- `PortfolioDecision` : `pair, engine_id, action, score_rank, reason?, replaced_by?, deferred_until_ms?`

---

### Fichier : `forecast_contracts.py` (286L)
**Rôle** : Contrat enrichi Narang-grade pour le signal canonique ; additive sur `SignalCandidate` (ne remplace pas).
**Inputs** : N/A (types)
**Outputs** : `ForecastSignalCandidate`, helpers de construction
**Équations mathématiques** : Aucune (validation mathématique : `expected_ce` et `expected_gain` doivent être finis).
**Logging** : Aucun.
**Dépendances internes** : `decision_contracts`, `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `ForecastSignalCandidate` (frozen, extra=forbid) : `strategy_id, engine_id, pair, side, forecast_direction [-1,1], forecast_strength [0,20], forecast_horizon_class, forecast_target_class, bet_structure, confidence_band [0,1]?, conditioning_state (tuple non vide), expected_cost, expected_break_even, expected_ce, expected_gain, invalidation_ref?, reason_codes, versions`
- `ConditioningRecord` (frozen) : `family (ConditioningFamily), code, value?, triggered_no_trade`
- `ConditioningFamily` : ENGINE_INTERNAL, SCORING, HARD_BLOCK, PORTFOLIO

---

### Fichier : `market_event_contracts.py` (159L)
**Rôle** : Structures de données de marché normalisées (klines, trades, depth, heartbeat, snapshot).
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic
**Équations mathématiques** :
- `spread_bps = (ask - bid) / mid * 10_000` (L75-79, L151-156)
- `body_ratio = |close - open| / (high - low)` (L118-122)
- `notional_usdt = price * quantity` (L23, L114-115)
**Logging** : Aucun.
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : GEM-01 crossed book guard L56-63 (protection book croisé).
**Champs clés** :
- `KlineEvent` : `pair, timeframe, open/high/low/close_price, volume, close_time_ms?, trade_count?, is_closed`
- `DepthEvent` : `pair, bids (min 1), asks (min 1), last_update_id?` (bids décroissant, asks croissant, no cross)
- `TradeEvent` : `pair, price, quantity, side, trade_id, is_maker`
- `SnapshotEvent` : `pair, last_price, bid, ask, volume_24h, high_24h?, low_24h?, funding_rate?`

---

### Fichier : `error_contracts.py` (238L)
**Rôle** : Hiérarchie d'erreurs métier standardisées V5.3.
**Inputs** : N/A (exceptions)
**Outputs** : Classes d'exception avec `to_dict()`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.
**Classes** : `V53BaseError`, `DataStaleError` (ERR_DATA_STALE), `PairSuspendedError`, `DependencyViolationError`, `ContractViolationError`, `RiskBudgetExceededError`, `InvalidProfileActivationError`, `EngineNotAllowedError`, `ReconciliationError`, `BootstrapError`

---

### Fichier : `meta_contracts.py` (157L)
**Rôle** : Objets d'observabilité — DTR records, alertes, coûts, santé paire, edge estimates.
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic
**Équations mathématiques** :
- `net_pnl_usdt = pnl_usdt - entry_price * (cost_total_bps / 10_000)` (L75-78)
- `net_edge_bps = gross_edge_bps - cost_drag_bps` (validé L130-138)
- `total_cost_bps = fee_bps + spread_cost_bps + slippage_bps` (validé L106-114)
**Logging** : Aucun.
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `DTRRecord` : `dtr_id, pair, engine_id, regime, signal_confidence, raw_score, final_score, hard_blocked, risk_verdict, outcome, entry/exit_price?, pnl_usdt?, cost_total_bps?, hold_duration_ms?`
- `AlertRecord` : `alert_id, severity, category, message, pair?, engine_id?, module?, resolved, resolved_ms?`
- `CostRecord` : `pair, engine_id, fee_bps, spread_cost_bps, slippage_bps, total_cost_bps, notional_usdt, expected_cost_bps?, cost_surprise_bps?`
- `EdgeEstimate` : `pair, engine_id, gross_edge_bps, cost_drag_bps, net_edge_bps, sample_size, confidence_level, win_rate?, profit_factor?, ce_ratio?`

---

### Fichier : `numeric_contracts.py` (169L)
**Rôle** : Arithmétique Decimal exacte pour valeurs d'exécution (prix, quantité, notionnel). Contexte 28 chiffres, ROUND_HALF_EVEN.
**Inputs** : `Decimal | float | str`
**Outputs** : `Decimal | float | str`
**Équations mathématiques** :
- `quantize_down = floor(value / step) * step` (L107-108)
- `quantize_up = ceil(value / step) * step` (L126-127)
- `abs_loss = |decimal_value - Decimal.from_float(float(decimal_value))|` (L133-134)
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : `EXECUTION_DECIMAL_CONTEXT_PRECISION = 28` hardcodé L19 (intentionnel et documenté).

---

### Fichier : `operator_contracts.py` (66L)
**Rôle** : Contrats de safing opérateur pour downgrade/halt runtime.
**Inputs** : N/A (types)
**Outputs** : `OperatorSafingRequest` (TimestampedModel)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `OperatorSafingAction` : SET_HALTED, DOWNGRADE_TO_MICRO_LIVE, DOWNGRADE_TO_SHADOW
- `OperatorSafingRequest` : `request_id, action, source_runtime_mode, target_runtime_mode?, requested_by, ui_channel, reason` (interdit depuis LOCAL_REPLAY)

---

### Fichier : `build14_contracts.py` (252L)
**Rôle** : Contrats Build-14 enablers — jamais autonomes, shadow-only par défaut.
**Inputs** : N/A (types)
**Outputs** : `Build14EnablerContract`, `Build14ObservationInput`, `Build14EnablerSnapshot`, etc.
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `Build14EnablerContract` (frozen) : `correlation_id, signal_family, summary, classification=BUILD14_ENABLER, hard_state, live_promotion_eligible=False, can_override_engines=False, can_bypass_risk=False, can_trade_autonomously=False`

---

### Fichier : `engine_validation_contracts.py` (78L)
**Rôle** : Contrats d'entrée/sortie pour hooks de validation Engine C (void) et D (reentry).
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic frozen
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `EngineCVoidValidationInput` : `context_id, pair, engine_id, scoring_version, breakout_type, continuation_context, raw_score, penalized_score, expected_cost, expected_ce, conviction, tier`
- `EngineDReentryValidationInput` : + `link_type, structure_reformed_detected, consecutive_stop_count, last_stop_at_ns?, last_fresh_a_detection_at_ns?, anti_revenge_state`
- Outcomes : `accepted, reason_codes, detail` (+ `episode_reference_id, anti_revenge_state, observability_tags` pour D)

---

### Fichier : `shadow_vps_service_contracts.py` (337L)
**Rôle** : Contrats de service VPS Shadow — état, preuves runtime, résumés campagne, événements.
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : `last_execution_telemetry_status: str = "not_configured"` — sentinel hardcodé (documenté).
**Champs clés** :
- `ShadowVpsServiceState` : 40+ champs de refs (str) pour replay, captures, snapshots, alertes Telegram, bootstrap, assessments regime/info-stress
- `ShadowVpsRuntimeEvidenceBundle` (frozen) : `session_date, local_replay_evidence, shadow_runtime_evidence, runtime_evidence_bundle_ref, execution_telemetry_ref, ...`

---

### Fichier : `feature_lock_contracts.py` (335L)
**Rôle** : Vocabulaire canonique pour le dictionnaire features Build-L0 et le transform whitelist.
**Inputs** : N/A (types + constantes)
**Outputs** : Dicts de features canoniques, fonctions de validation
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : `CANONICAL_FEATURE_SET_VERSION = "1.0.0"` et `CANONICAL_TRANSFORM_SET_VERSION = "1.0.0"` — constantes voulues.

---

### Fichier : `binance_contracts.py` (231L)
**Rôle** : Contrats typed pour l'adaptateur Binance Spot (credentials, exchange info, symbols, rate limits).
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic frozen
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `pair_catalog.py` (199L)
**Rôle** : Catalogue immutable des filtres venue Binance pour les 7 paires V5.3 canoniques (tick_size, step_size, min_notional). Doit être refreshé au bootstrap depuis `get_exchange_info()`.
**Inputs** : `BinanceExchangeInfo` (pour `from_exchange_info`), ou hardcoded defaults
**Outputs** : `PairCatalog`, `PairEntry`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `binance_contracts`
**État** : COMPLETE
**Anomalies** : Valeurs hardcodées (tick_size, step_size, min_notional) dans `V53_PAIR_CATALOG` sont des defaults de bootstrap — la doc précise explicitement qu'elles doivent être refreshées en prod.

---

### Fichier : `strategy_identity.py` (81L)
**Rôle** : Tuple d'identité stratégie pour promotion, refus et agrégation PnL.
**Inputs** : N/A (types)
**Outputs** : `StrategyIdentity` avec `canonical_key`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `domain_types`, `forecast_contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `refusal_records.py` (56L)
**Rôle** : Journal entry pour chemins de refus gouvernés (anti-survivorship-bias).
**Inputs** : N/A (types)
**Outputs** : `RefusalRecord`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `domain_types`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `artifact_contracts.py` (18L)
**Rôle** : Thin compatibility re-export depuis `artifact_contracts_models`.
**Inputs** : N/A
**Outputs** : re-exports
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `artifact_contracts_models`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `artifact_contracts_models.py` (590L)
**Rôle** : Modèles complets pour les contrats d'artifacts gouvernés — enums de cycle de vie, politiques, trust store, governance evaluation.
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic, fonctions de validation
**Équations mathématiques** : Aucune (logique de validation contractuelle).
**Logging** : Aucun.
**Dépendances internes** : `feature_lock_contracts`
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `ArtifactSignatureEnvelope` (frozen) : `artifact_id, version, sha256_hex, signed_at_utc, signer_id, hook_ids (tuple HookId)`
- `CompiledArtifactRegistryPolicy` (frozen) : `conflict_mode, score_conflict_aggregation, size_reduce_mode, rank_adjust_mode, concurrency_model, atomicity_mode`
- `ArtifactRuntimeGovernanceEvaluation` : `accepted, active_hooks, rejected_reasons, trust_status, proof_status`

---

### Fichier : `artifact_contracts_runtime.py` (172L)
**Rôle** : Runtime helpers pour charger et valider artifacts depuis disque.
**Inputs** : `Path`, `ArtifactExportBundle`
**Outputs** : Bundle validé, erreurs typées
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `artifact_contracts_models`, `feature_lock_contracts`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `atomic_io.py` (65L)
**Rôle** : Écriture JSON atomique via fichier temporaire + rename (GEM-19).
**Inputs** : `Path | str`, `dict | list`
**Outputs** : `None` (effet de bord fichier)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

---

## 2. `regime_classifier/`

### Fichier : `__init__.py` (25L)
**Rôle** : Re-exports `regime_lite.py`.
**État** : COMPLETE

---

### Fichier : `regime_lite.py` (386L)
**Rôle** : Classificateur de régime trois états (CALM/STRESSED/EXTREME) avec hysteresis anti-flapping et cooldown post-EXTREME. Calibration artifact-governed via seam THR-RG01..04.
**Inputs** : `RegimeLiteInput` (`as_of_ts, btc_realized_vol_24h, btc_drop_1h, intraday_drawdown, engine_return_dispersion`), `RegimeLiteThresholds`, `RegimeLiteMemory?`
**Outputs** : `RegimeLiteAssessment` (état, transitions, reason_codes, entries_blocked)
**Équations mathématiques** :
- Classification multi-critères : `btc_drop_1h <= -btc_drop_1h_extreme` → EXTREME (sudden) (L219)
- Dégradation par step : un seul saut d'état max sans sudden event (L294-300)
- Hysteresis descente : `time_in_state_s < downgrade_hysteresis_s` → maintien état (L304-308)
- Cooldown EXTREME : `entries_blocked_until_ts = max(carried, as_of_ts + extreme_cooldown_s)` (L318-321)
**Logging** : Aucun.
**Dépendances internes** : `calibration_loader`, `calibration_loader.contracts`, `calibration_loader.loader`
**État** : COMPLETE
**Anomalies** :
- Defaults documentés hardcodés dans `from_documented_defaults()` : `btc_realized_vol_24h_stressed=0.04` (L86), `extreme=0.08` (L87), `btc_drop_1h_extreme=0.05` (L88), `intraday_drawdown_stressed=0.01` (L89), `extreme=0.02` (L90), `dispersion_stressed=0.02` (L91), `dispersion_extreme=0.05` (L92), `downgrade_hysteresis_s=7200` (L93), `extreme_cooldown_s=86400` (L94) — **defaults documentés, pas seam calibration (THR-RG01..04 couvre seulement 4 d'entre eux)**.
- Dims secondaires sans seam calibration : `btc_realized_vol_24h_extreme`, `intraday_drawdown_*`, `engine_return_dispersion_*` restent sur defaults jusqu'à promotion explicite (L43-50 config + L84-95 defaults).

---

## 3. `risk_backbone/`

### Fichier : `__init__.py` (69L)
**Rôle** : Re-exports du package risk_backbone.
**État** : COMPLETE

---

### Fichier : `risk_runtime.py` (59L)
**Rôle** : Re-export de convenance depuis `risk_runtime_runtime` et `risk_runtime_models`.
**Inputs** : N/A
**Outputs** : re-exports
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `risk_runtime_runtime`, `risk_runtime_models`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `risk_runtime_models.py` (270L)
**Rôle** : Modèles publics et Protocol hooks pour le runtime risque Build-4.
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic frozen
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : Sous-modules btc_factor_guard, correlation_cluster_guard, exposure_budgeter, loss_budgeter
**État** : COMPLETE
**Anomalies** : `beta_mapping_max_age_s: float = 86_400.0` hardcodé L32 (1 jour, documenté).
**Champs clés** :
- `RiskLimits` (frozen) : `gross_cap, position_cap, loss_cap, beta_cap, cluster_cap, beta_mapping_max_age_s=86400, drawdown_warning_threshold_pct=0.02, drawdown_observe_threshold_pct=0.04`
- `RiskCandidate` (frozen) : `pair, engine_id, size, planned_loss?, pair_beta?, side, execution_fragility, market_toxicity, spread_regime_penalty, participation_penalty, spread_bps?, reference_spread_bps?, depth_ratio?, order_cancellation_rate?, taker_imbalance?, micro_vol_divergence?`
- `RiskEvaluation` (frozen) : `action, accepted, reasons, reason_details, dominant_reason_code, explain_summary, explainability, gross_result, loss_result, beta_projection, beta_result, cluster_results, drawdown_result`
- `RiskExplainability` (frozen) : `blocked_guard_codes, blocked_guard_categories, blocked_guard_count, drawdown_state_code, decision_severity, physics_pressure_state, fragility_score, toxicity_score, execution_survivability_score, micro_friction_score, summary`
- Protocol hooks (4) : `RiskMicroFrictionPrecheckHook`, `RiskDailyPnlPrecheckHook`, `RiskRegimePrecheckHook`, `RiskInfoStressPrecheckHook`

---

### Fichier : `risk_runtime_runtime.py` (375L)
**Rôle** : Runtime Build-4 stateful — enregistrement positions, évaluation candidats, gestion equity/session_peak.
**Inputs** : `RiskLimits`, `RiskCandidate`, positions Dict
**Outputs** : `RiskEvaluation`
**Équations mathématiques** : Agrège tous les guards (gross/loss/beta/cluster/drawdown) via `evaluate_candidate_support`.
**Logging** : Aucun structlog direct (délégué aux sous-modules).
**Dépendances internes** : `btc_factor_guard.*`, `correlation_cluster_guard.*`, `exposure_budgeter.*`, `loss_budgeter.*`, `risk_runtime_evaluation_support`, `risk_runtime_explainability`, `risk_runtime_models`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `risk_runtime_evaluation_support.py` (553L)
**Rôle** : Support d'évaluation — snapshot guards, construction reason_details, hooks optionnels (daily_pnl, regime, info_stress, micro_friction).
**Inputs** : `RiskRuntime` (via TYPE_CHECKING), `RiskCandidate`, guards results
**Outputs** : `RiskEvaluation`, `_RiskGuardSnapshot`
**Équations mathématiques** : Agrégation booléenne multi-guards → action (ACCEPT/REJECT/REDUCE).
**Logging** : Aucun.
**Dépendances internes** : `btc_factor_guard.*`, `correlation_cluster_guard.*`, `exposure_budgeter.*`, `loss_budgeter.*`, `risk_runtime_explainability`, `risk_runtime_models`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `risk_runtime_explainability.py` (295L)
**Rôle** : Construction des objets `RiskExplainability`, `RiskPhysicsScores` et normalisation état equity.
**Inputs** : Guards results, `RiskCandidate`
**Outputs** : `RiskExplainability`, `RiskPhysicsScores`, `RiskReasonDetail` tuple
**Équations mathématiques** :
- `fragility_score_v1`, `toxicity_score_v1`, `execution_survivability_score_v1`, `micro_friction_score_v1` (délégué à `data_backbone.market_physics_math`)
**Logging** : Aucun.
**Dépendances internes** : `data_backbone.market_physics_math`, sous-modules guards
**État** : COMPLETE
**Anomalies** : Fonctions prefixées `_` exportées (utilisées par evaluation_support) — design interne acceptable.

---

### Fichier : `risk_runtime_drawdown_calibration.py` (142L)
**Rôle** : Seam calibration optionnelle pour seuils drawdown alert THR-W01 (warning=2%) et THR-W02 (observe=4%). Distinct du breaker hard (THR-R01).
**Inputs** : `RiskDrawdownCalibrationConfig?`, calibration artifacts
**Outputs** : `RiskDrawdownThresholds`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `calibration_loader`
**État** : COMPLETE
**Anomalies** :
- `hard_cap_warning_pct = 0.05` L33 — hard cap codé (calibration peut réduire, pas augmenter au-delà).
- `hard_cap_observe_pct = 0.10` L34 — idem.
- `drawdown_warning_threshold_pct=0.02`, `observe_threshold_pct=0.04` defaults L46-47 (documentés).

---

### Fichier : `info_stress_monitor.py` (258L)
**Rôle** : Détecteur d'information-stress par paire — classifie NORMAL/ELEVATED/EXTREME selon 5 métriques microstructure, avec cooldown.
**Inputs** : `pair, now, spread_bps?, reference_spread_bps?, depth_ratio?, order_cancellation_rate?, taker_imbalance?, micro_vol_divergence?`
**Outputs** : `InfoStressAssessment` (level, alert_count, entries_blocked, entries_blocked_until_ts)
**Équations mathématiques** :
- `spread_ratio = spread_bps / reference_spread_bps` → alert si `>= spread_ratio_alert_threshold` (5.0 default)
- `depth_ratio < depth_ratio_min_threshold` (0.10 default) → alert
- `cancellation_rate >= 0.80` → alert
- `|taker_imbalance| >= 0.90` → alert
- `micro_vol_divergence >= 3.0` → alert
- `alert_count >= extreme_alert_count` (3 default) → EXTREME + cooldown
**Logging** : Aucun.
**Dépendances internes** : `risk_runtime` (Protocol hooks)
**État** : COMPLETE
**Anomalies** : **Hardcoded thresholds dans `InfoStressThresholds` defaults** :
- `spread_ratio_alert_threshold = 5.0` (L24)
- `depth_ratio_min_threshold = 0.10` (L25)
- `cancellation_rate_alert_threshold = 0.80` (L26)
- `taker_imbalance_alert_threshold = 0.90` (L27)
- `micro_vol_divergence_alert_threshold = 3.0` (L28)
- `extreme_alert_count = 3` (L29)
- `cooldown_s = 600` (L30) — **pas de seam calibration, pas de THR-ID. P2 : à connecter au calibration loader.**

---

### Fichier : `daily_pnl_breaker_entry_gate.py` (47L)
**Rôle** : Bridge entre `DailyPnlBreaker` et le Protocol hook `RiskDailyPnlPrecheckHook`.
**Inputs** : `DailyPnlBreaker`, `DailyPnlBreakerThresholds?`
**Outputs** : `RiskDailyPnlPrecheckHook` (closure)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `loss_budgeter`, `risk_runtime`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `regime_lite_entry_gate.py` (40L)
**Rôle** : Bridge entre `RegimeLiteAssessment` et le Protocol hook `RiskRegimePrecheckHook`.
**Inputs** : `RegimeLiteAssessment`
**Outputs** : `RiskRegimePrecheckHook` (closure)
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `regime_classifier`, `risk_runtime`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `regime_lite_safing.py` (97L)
**Rôle** : Traduit un `RegimeLiteAssessment` en `RegimeLiteSafingRecommendation` — HALT_RECOMMENDED (EXTREME) ou ENTRY_BLOCK_ONLY (cooldown) ou NONE. Jamais auto-appliqué.
**Inputs** : `RegimeLiteAssessment`, `source_runtime_mode, timestamp_ms`
**Outputs** : `RegimeLiteSafingRecommendation`
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `interface_contracts`, `regime_classifier`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Sous-package `loss_budgeter/`

#### `daily_pnl_breaker.py` (422L)
**Rôle** : Breaker journalier avec persistance disque — THR-R01 calibrated seam, shadow lock same-day.
**Inputs** : `session_date, current_equity, session_peak_equity, DailyPnlBreakerThresholds?`
**Outputs** : `DailyPnlBreakerAssessment` (verdict, drawdown_pct, should_force_shadow, circuit_breaker_tripped)
**Équations mathématiques** :
- `drawdown_pct = max(0, (session_peak_equity - current_equity) / session_peak_equity)`
- Breach si `drawdown_pct >= intraday_drawdown_breach_pct` → SHADOW_RECOMMENDED puis SHADOW_LOCKED
**Logging** : Aucun structlog direct.
**Dépendances internes** : `calibration_loader`, `interface_contracts.atomic_io`, `emergency_kill_switch.circuit_breaker`
**État** : COMPLETE
**Anomalies** :
- `hard_cap_drawdown_pct = 0.02` L30 (hard cap breaker — intentionnel).
- `intraday_drawdown_breach_pct = 0.02` default L40 (documenté).

#### `drawdown_guard.py` (81L)
**Rôle** : Guard drawdown intraday minimal — ACCEPTED / REDUCE_EXPOSURE / OBSERVE_ONLY.
**Inputs** : `current_equity, session_peak_equity, warning_threshold_pct=0.02, observe_threshold_pct=0.04`
**Outputs** : `DrawdownGuardResult`
**Équations mathématiques** :
- `drawdown_pct = max(0, (session_peak_equity - current_equity) / session_peak_equity)`
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** :
- `warning_threshold_pct=0.02` L33 par défaut (hardcodé, mais aussi documenté dans `RiskLimits` et calibration seam THR-W01).
- `observe_threshold_pct=0.04` L34 (idem, THR-W02).

#### `loss_cap_guard.py` (74L)
**Rôle** : Guard budget de perte — refuse si `current_budget + L_new > LB_max` ou si `L_i` absent (fail-closed).
**Inputs** : `pair, candidate_loss?, current_budget, loss_cap`
**Outputs** : `LossCapResult`
**Équations mathématiques** : `projected = current_budget + candidate_loss`
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

#### `aggregate_loss_budgeter.py` (54L)
**Rôle** : Agrège les positions pour calculer le budget total utilisé.
**État** : COMPLETE

#### `position_loss_estimator.py` (53L)
**Rôle** : Estime la perte planifiée d'une position.
**État** : COMPLETE

#### `projected_loss_checker.py` (41L)
**Rôle** : Vérification projetée avant ajout de position.
**État** : COMPLETE

#### `loss_reporter.py` (70L)
**Rôle** : Agrège et reporte les statistiques de perte.
**État** : COMPLETE

---

### Sous-package `exposure_budgeter/`

#### `gross_cap_guard.py` (80L)
**Rôle** : Guard double — position cap (`projected_pair > position_cap`) et gross cap (`projected > gross_cap`).
**Inputs** : `pair, candidate_size, current_gross, position_cap, gross_cap, current_pair_exposure`
**Outputs** : `GrossCapResult`
**Équations mathématiques** :
- `projected_pair = current_pair_exposure + candidate_size`
- `projected = current_gross + candidate_size`
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

#### `gross_exposure_calculator.py` (49L)
**Rôle** : Calcule l'exposition brute totale du portfolio.
**État** : COMPLETE

#### `position_cap_guard.py` (53L), `exposure_reporter.py` (84L), `projected_exposure_checker.py` (41L)
**État** : COMPLETE (tous)

---

### Sous-package `btc_factor_guard/`

#### `portfolio_beta_calculator.py` (56L)
**Rôle** : Calcule `β_port = Σ w_j * β_j` où `w_j = x_j / Σ x_k`.
**Inputs** : `positions: dict[str, float]`, `betas: dict[str, float]`
**Outputs** : `PortfolioBeta` (`beta_port, total_exposure, position_count, contributions`)
**Équations mathématiques** : `β_port = Σ (x_j / Σ x_k) * β_j`
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Raise ValueError si beta manquant pour une paire (fail-closed).

#### `projected_beta_checker.py` (55L)
**Rôle** : `|β_port_proj| ≤ B_max` — vérifie si ajout d'un candidat respecte le budget beta.
**Inputs** : `current_positions, betas, candidate_pair, candidate_size, candidate_beta, beta_cap`
**Outputs** : `ProjectedBeta`
**Équations mathématiques** : `|β_port_proj| ≤ B_max`
**Dépendances internes** : `portfolio_beta_calculator`
**État** : COMPLETE
**Anomalies** : Aucune.

#### `beta_cap_guard.py` (55L)
**Rôle** : `|β_port_proj| ≤ B_max` verdict ACCEPTED/REJECTED.
**État** : COMPLETE

#### `pair_beta_registry.py` (70L), `beta_reporter.py` (65L)
**État** : COMPLETE (tous)

---

### Sous-package `correlation_cluster_guard/`

#### `cluster_cap_guard.py` (73L)
**Rôle** : Guard cluster — fail-closed si `cluster_id is None`, reject si `projected > cluster_cap`.
**Équations mathématiques** : `projected = current_exposure + candidate_size`
**État** : COMPLETE
**Anomalies** : Fail-closed intentionnel (pas de cluster = reject).

#### `cluster_exposure_calculator.py` (67L), `cluster_registry.py` (76L), `cluster_reporter.py` (75L), `projected_cluster_checker.py` (42L)
**État** : COMPLETE (tous)

---

### Sous-package `emergency_kill_switch/`

#### `circuit_breaker.py` (17L)
**Rôle** : Compatibility surface — re-export depuis `execution_backbone.emergency_circuit_breaker`.
**Dépendances internes** : `execution_backbone.emergency_circuit_breaker`
**État** : COMPLETE
**Anomalies** : Ce fichier est une coquille vide de re-export : la logique réelle est dans `execution_backbone`. Couplage bidirectionnel risk ↔ execution (via cette indirection) — acceptable si l'ownership reste à execution.

---

## 4. `scoring_backbone/`

### Fichier : `__init__.py` (127L)
**Rôle** : Re-exports du package scoring_backbone.
**État** : COMPLETE

---

### Fichier : `scoring_runtime.py` (399L)
**Rôle** : Runtime Build-5 stateful — round complet scoring : raw score → penalties → hard block → ranking → sélection.
**Inputs** : `tuple[ScoringCandidateInput, ...]`, `PortfolioState`, `max_selections: int`, `now?: float`
**Outputs** : `ScoringRoundResult`
**Équations mathématiques** : Délégué aux sous-modules (raw_score = Σ αm·Fm, penalties, ranking).
**Logging** : Aucun structlog.
**Dépendances internes** : Tous les sous-packages scoring
**État** : COMPLETE
**Anomalies** :
- `max_score_penalty=3.0` L67 hardcodé (default — configurable à l'init mais pas via calibration seam).
- `min_size_multiplier=0.05` L68 hardcodé (idem).
- `anomaly_low=-10.0`, `anomaly_high=10.0` L69-70 hardcodés (bounds de score anormaux).

---

### Fichier : `scoring_runtime_support.py` (473L)
**Rôle** : Contrats support du runtime Build-5 — `ScoringCandidateInput`, Protocol hooks, fonctions utilitaires (physics, economics).
**Inputs** : N/A (types + helpers)
**Outputs** : Modèles Pydantic, closures
**Équations mathématiques** :
- `fragility_score_v1`, `toxicity_score_v1`, `execution_survivability_score_v1`, `micro_friction_score_v1` (via `data_backbone.market_physics_math`)
**Logging** : Aucun.
**Dépendances internes** : `data_backbone.market_physics_math`, sous-packages scoring
**État** : COMPLETE
**Anomalies** : Aucune.
**Champs clés** :
- `ScoringCandidateInput` (frozen) : `engine_id, pair, raw_features, allowed_features, weights, scoring_version, raw_score_multiplier, raw_score_add, raw_score_cap?, score_penalties, size_penalties, blocker_conditions, expected_cost, expected_ce, projected_size, projected_loss, projected_beta_impact, cluster_id, corr_penalty, risk_penalty, execution_fragility, market_toxicity, spread_regime_penalty, participation_penalty`

---

### Fichier : `break_even_filter.py` (109L)
**Rôle** : Filtre économique additive doc20 — gate break-even / CE / EV-net.
**Inputs** : `expected_gain, expected_cost, candidate_size, delta_safe=0, expected_ce?, ce_min?, config?`
**Outputs** : `BreakEvenFilterDecision`
**Équations mathématiques** :
- `expected_break_even = expected_cost + delta_safe`
- `ev_net = candidate_size * (expected_gain - expected_cost)`
- Gate : `expected_gain > expected_break_even` (strict) ou `>=` (non-strict)
- CE gate : `expected_ce >= ce_min` si les deux fournis
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : `min_ev_net=0.0` default L13 (configurable, pas hardcode critique).

---

### Fichier : `forecast_normalizer.py` (107L)
**Rôle** : Normalisation Carver-style des forecasts — `F_norm = clip(F_raw * ForecastScalar, ±max_abs_forecast)`.
**Inputs** : `raw_forecast, forecast_scalar, config?`
**Outputs** : `ForecastNormalizationResult`
**Équations mathématiques** :
- `raw_forecast = expected_return / volatility_scale` (F ∝ E[r]/σ)
- `ForecastScalar = target_mean_abs_forecast / E[|F|]`
- `F_norm = clip(F_raw * ForecastScalar, -max_abs_forecast, +max_abs_forecast)`
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** :
- `target_mean_abs_forecast=10.0` L16 (valeur Carver canonique — intentionnel).
- `max_abs_forecast=20.0` L17 (valeur Carver canonique — intentionnel).

---

### Fichier : `fee_aware_edge_gate.py` (19L)
**Rôle** : Re-export de `execution_backbone.fee_aware_edge_gate` (compatibility surface).
**État** : COMPLETE
**Anomalies** : Même pattern que `risk_backbone/emergency_kill_switch/circuit_breaker.py` — ownership à `execution_backbone`.

---

### Sous-package `raw_score_builder/`

#### `raw_score_calculator.py` (119L)
**Rôle** : `S_i^raw = Σ α_m · F_{i,m}` avec multiplicateur, add, cap optionnels.
**Inputs** : `engine_id, pair, features, weights, scoring_version, raw_score_multiplier, raw_score_add, raw_score_cap?`
**Outputs** : `RawScoreResult`
**Équations mathématiques** :
- `base_raw_score = Σ w[m] * features[m]`
- `raw_score = base_raw_score * multiplier + add`
- `raw_score = min(raw_score, cap)` si cap défini
**État** : COMPLETE
**Anomalies** : Aucune.

#### `feature_selector.py` (51L), `score_component_breakdown.py` (61L), `score_reporter.py` (93L)
**État** : COMPLETE (tous)

---

### Sous-package `hard_block_gate/`

#### `blocker_evaluator.py` (50L)
**Rôle** : Évalue les conditions de hard-block (toutes les conditions booléennes).
**État** : COMPLETE

#### `blocker_decision_builder.py` (45L), `blocker_reason_encoder.py` (44L), `blocker_registry.py` (76L), `blocker_reporter.py` (51L)
**État** : COMPLETE (tous)

---

### Sous-package `penalty_aggregator/`

#### `score_penalty_builder.py` (54L)
**Rôle** : Construit les pénalités score (réduction multiplicative du score brut).
**État** : COMPLETE

#### `size_penalty_builder.py` (59L)
**Rôle** : Construit les pénalités taille (réduction du size_multiplier).
**État** : COMPLETE

#### `penalty_cap_guard.py` (83L), `penalty_registry.py` (86L), `penalty_reporter.py` (63L)
**État** : COMPLETE (tous)

---

### Sous-package `ranking_router/`

#### `ranking_score_builder.py` (94L)
**Rôle** : Score de ranking composite — pondération de final_score, expected_ce, risk, correlation.
**État** : COMPLETE

#### `candidate_pool_builder.py` (55L), `portfolio_compatibility_checker.py` (103L), `ranking_reporter.py` (60L), `selection_resolver.py` (106L)
**État** : COMPLETE (tous)

---

### Threshold files scoring_backbone :

#### `engine_a_cost_thresholds.py` (111L), `engine_b_cost_thresholds.py` (111L), `engine_c_cost_thresholds.py` (111L)
**Rôle** : Résolution calibration des seuils de coût par engine (séquences THR-C01..03 / THR-B01..03 etc.).
**État** : COMPLETE

#### `engine_b_breakout_thresholds.py` (117L), `engine_b_excess_thresholds.py` (181L), `engine_b_invalidation_thresholds.py` (146L), `engine_c_continuation_thresholds.py` (146L)
**État** : COMPLETE (tous)

---

## 5. `execution_backbone/`

### Fichier : `__init__.py` (109L)
**Rôle** : Re-exports du package execution_backbone.
**État** : COMPLETE

---

### Fichier : `execution_runtime.py` (556L)
**Rôle** : Runtime Build-3 adapter-backed — soumet ordres, gère fills, coûts, réconciliation, timeouts. Pivot central de l'exécution réelle.
**Inputs** : `ExecutionVenueAdapter`, `ExecutionOpportunity`, `VenueOrderEvent`, `RemoteExecutionState`
**Outputs** : `ExecutionSubmission`, `RuntimeProcessingSummary`, `RuntimeReconciliationResult`
**Équations mathématiques** : Délégué aux sous-modules (coûts, slippage, adverse selection, fills).
**Logging** : `logging.getLogger(__name__)` — clés : `execution_submission_rate_limited` (L177-184).
**Dépendances internes** : Presque tous les sous-packages execution_backbone, `venue_adapters.binance_spot.rate_limiter` (optional import), `sharia_compliance`
**État** : COMPLETE
**Anomalies** :
- `default_fee_rate=0.001` L85 hardcodé (0.1% — Binance taker, configurable à l'init).
- `max_recon_age_s=60.0` L86 hardcodé (configurable).
- `terminal_order_retention=2048` L87 hardcodé (configurable).
- `try/except ImportError` L41-44 pour `BinanceApiRateLimitExceededError` — pattern acceptable pour adapter optionnel.

---

### Fichier : `execution_runtime_support.py` (612L)
**Rôle** : Mixin support pour `ExecutionRuntime` — méthodes internes privées (slippage, spread guard, fee gate, sharia, rate limit, venue constraints, logging gatekeeper).
**Inputs** : `ExecutionOpportunity`, `ExecutionPermit`
**Outputs** : Guards decisions, logging effets de bord
**Équations mathématiques** : Délégué aux sous-modules slippage/spread/fee.
**Logging** : Via `logger` de `execution_runtime.py`.
**Dépendances internes** : `fee_aware_edge_gate`, `rate_limiter`, `spread_guard`, `slippage_model`, `gatekeeper.*`, `order_decider.*`
**État** : COMPLETE
**Anomalies** : Aucune critique.

---

### Fichier : `execution_runtime_models.py` (252L)
**Rôle** : Modèles et Protocol pour le runtime d'exécution — `ExecutionOpportunity`, `ExecutionVenueAdapter`, `ShariaTradeAuthorizer`, etc.
**Inputs** : N/A (types)
**Outputs** : Modèles Pydantic
**Équations mathématiques** : Aucune.
**Logging** : Aucun.
**Dépendances internes** : `sharia_compliance.contracts`, `interface_contracts`, sous-modules execution
**État** : COMPLETE
**Anomalies** :
- `safety_margin: float = 0.0005` L40 (`ExecutionOpportunity`) — hardcodé, configurable par appel.
- `pair_health_min: float = 0.3` L43 — hardcodé.
- `profile: str = "COMPLETE"` L50 — sentinel BS-49 (LIGHT removed).

---

### Fichier : `emergency_circuit_breaker.py` (183L)
**Rôle** : Kill switch persistant (GEM-10/QWEN-07) — survit au redémarrage process, flag fichier externe, reset explicite opérateur.
**Inputs** : `KillSwitchReason`, `Path` (state_file, external_flag)
**Outputs** : `KillSwitchRecord`, `bool` (is_trading_allowed)
**Équations mathématiques** : Aucune.
**Logging** : Aucun structlog (effets de bord fichier).
**Dépendances internes** : `interface_contracts.atomic_io`
**État** : COMPLETE
**Anomalies** :
- `_DEFAULT_STATE_FILE = "kill_switch_state.json"` L50 hardcodé (overridable).
- `_DEFAULT_EXTERNAL_FLAG = "KILL_SWITCH_ACTIVE"` L51 hardcodé (overridable).

---

### Fichier : `fee_aware_edge_gate.py` (140L)
**Rôle** : Gate d'edge fee-aware — `expected_edge_bps >= max(edge_multiplier * cost_bps, min_absolute_edge_bps)`. Résout THR-E01 et THR-E02 via calibration loader.
**Inputs** : `expected_edge_bps, expected_cost (fractional), config?`
**Outputs** : `FeeAwareEdgeDecision`
**Équations mathématiques** :
- `expected_cost_bps = expected_cost * 10_000`
- `threshold_bps = max(edge_multiplier * expected_cost_bps, min_absolute_edge_bps)`
- Gate : `expected_edge_bps >= threshold_bps`
**Logging** : Aucun.
**Dépendances internes** : `calibration_loader`
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `rate_limiter.py` (65L)
**Rôle** : Guard quota ratio THR-X03 — bloque si `current_quota_ratio >= quota_ratio_ceiling`.
**Inputs** : `ExecutionRateLimitModel`, `current_quota_ratio`
**Outputs** : `ExecutionRateLimitDecision`
**Équations mathématiques** : `current_quota_ratio < quota_ratio_ceiling` → PASS
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `spread_guard.py` (65L)
**Rôle** : Guard spread THR-X04 — bloque si `current_spread_bps > max_spread_bps`.
**Inputs** : `ExecutionSpreadGuardModel`, `current_spread_bps`
**Outputs** : `ExecutionSpreadGuardDecision`
**Équations mathématiques** : `current_spread_bps <= max_spread_bps` → PASS
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `slippage_model.py` (65L)
**Rôle** : Modèle slippage THR-X05 — `predicted_slippage_bps = intercept + sqrt_coeff * sqrt(size_value)`.
**Inputs** : `ExecutionSlippageModel`, `size_value`
**Outputs** : `ExecutionSlippageEstimate`
**Équations mathématiques** :
- `predicted_slippage_bps = max(0, intercept_bps + sqrt_size_coefficient * sqrt(size_value))`
- `cost_addition = predicted_slippage_bps / 10_000`
**Logging** : Aucun.
**Dépendances internes** : Aucune.
**État** : COMPLETE
**Anomalies** : Aucune.

---

### Fichier : `venue_constraints_provider.py` (235L)
**Rôle** : Provider optionnel de contraintes venue (tick_size, step_size, min_notional) via API REST Binance avec cache disque.
**Inputs** : `pair`, `BinanceExchangeInfo` (ou fetch live)
**Outputs** : `VenueConstraintSnapshot`
**Équations mathématiques** : Aucune.
**Logging** : `logging.getLogger(__name__)` — clé `venue_constraints_fetch_failed`.
**Dépendances internes** : `interface_contracts`, `order_decider.intent_builder`
**État** : COMPLETE
**Anomalies** : `urlopen` direct L13 — acceptable pour fetch HTTP simple sans dépendance externe.

---

### Sous-package `gatekeeper/`

#### `gatekeeper.py` (685L)
**Rôle** : Gatekeeper canonique Build-3 — chaîne de guards ordonnée (suspended → data_stale → risk → infra → health → spread → fee_edge → sharia → rate_limit → venue_constraints → no_trade_filter → order_type).
**Inputs** : `ExecutionOpportunityLike`
**Outputs** : `ExecutionPermit | ExecutionRefusal`
**Équations mathématiques** : Aucune (logique booléenne séquentielle).
**Logging** : Aucun direct.
**Dépendances internes** : `order_decider.*`, `rate_limiter`, `spread_guard`, `gatekeeper_support`
**État** : COMPLETE
**Anomalies** : Fichier le plus long du package (685L). Pas de FILE_TOO_LONG en `src/` — doit être splitté si > 700L. **Actuellement à 685L — surveillance requise**.

#### `audit_logger.py` (131L), `gatekeeper_support.py` (97L)
**État** : COMPLETE (tous)

---

### Sous-package `order_decider/`

#### `intent_builder.py` (127L)
**Rôle** : Construit un `ExecutionIntent` depuis une opportunité validée et des contraintes venue.
**État** : COMPLETE

#### `execution_guard.py` (85L), `order_type_selector.py` (82L), `timeout_policy_selector.py` (65L), `decision_reporter.py` (136L)
**État** : COMPLETE (tous)

---

### Sous-package `fill_tracker/`

#### `order_state_tracker.py` (179L)
**Rôle** : Tracking stateful des états d'ordres (PENDING → PARTIAL → FILLED/CANCELLED/REJECTED/TIMEOUT).
**État** : COMPLETE

#### `fill_aggregator.py` (130L), `fill_reporter.py` (103L), `latency_meter.py` (122L), `order_terminal_state_resolver.py` (79L)
**État** : COMPLETE (tous)

---

### Sous-package `execution_cost_meter/`

#### `cost_aggregator.py` (148L)
**Rôle** : Agrège fee + spread + slippage + adverse_selection → `CostAggregate`.
**État** : COMPLETE

#### `adverse_selection_meter.py` (106L)
**Rôle** : Mesure adverse selection post-fill — comparaison prix fill vs prix post-délai.
**État** : COMPLETE

#### `fee_meter.py` (72L), `elw_meter.py` (75L), `partial_fill_cost_meter.py` (77L)
**État** : COMPLETE (tous)

---

### Sous-package `reconciliation_layer/`

#### `scheduler.py` (308L)
**Rôle** : Scheduler de réconciliation périodique avec backoff et circuit breaker.
**État** : COMPLETE
**Anomalies** : Fichier le plus long du sous-package.

#### `divergence_classifier.py` (168L)
**Rôle** : Classifie les divergences local/exchange (missing/phantom/qty_mismatch/price_mismatch).
**État** : COMPLETE

#### `fill_reconciler.py` (77L), `order_reconciler.py` (91L), `position_reconciler.py` (86L), `recovery_trigger.py` (124L)
**État** : COMPLETE (tous)

---

## Synthèse Groupe C

### Contrats interface (champs clés)

| Modèle | Champs critiques |
|--------|-----------------|
| `SignalCandidate` | pair, engine_id, confidence [0,1], regime, entry_price, max_hold_ms?, GEM-11 expiry |
| `ForecastSignalCandidate` | forecast_direction [-1,1], forecast_strength [0,20], conditioning_state (non vide), versions dict |
| `ScorePayload` | raw_score, penalty_total, final_score ([0,1]), rank, hard_blocked |
| `RiskDecision` | verdict (APPROVED/REDUCED/HARD_BLOCKED), approved_size ≤ requested_size, 0 si HARD_BLOCKED |
| `ExecutionIntent` | order_type (limit|market), size > 0, status |
| `ExecutionOpportunity` | profile="COMPLETE" (BS-49), safety_margin=0.0005, pair_health_min=0.3 |
| `RiskLimits` | gross_cap, position_cap, loss_cap, beta_cap, cluster_cap, drawdown_warning=0.02, drawdown_observe=0.04 |
| `ScoringCandidateInput` | raw_features, allowed_features, weights, scoring_version (requis non vide) |

---

### Hardcoded thresholds risk_backbone

| Valeur | Fichier | Ligne | Type | Seam calibration ? |
|--------|---------|-------|------|-------------------|
| `drawdown_warning=0.02` | `drawdown_guard.py` | L33 | Default arg | OUI — THR-W01 via `risk_runtime_drawdown_calibration.py` |
| `drawdown_observe=0.04` | `drawdown_guard.py` | L34 | Default arg | OUI — THR-W02 |
| `drawdown_warning=0.02` | `risk_runtime_models.py` | L34 | Champ RiskLimits | Via `RiskDrawdownCalibrationConfig` |
| `drawdown_observe=0.04` | `risk_runtime_models.py` | L35 | Champ RiskLimits | Via `RiskDrawdownCalibrationConfig` |
| `hard_cap_warning=0.05` | `risk_runtime_drawdown_calibration.py` | L33 | Hard cap max | NON — borne dure intentionnelle |
| `hard_cap_observe=0.10` | `risk_runtime_drawdown_calibration.py` | L34 | Hard cap max | NON — borne dure intentionnelle |
| `intraday_drawdown_breach=0.02` | `daily_pnl_breaker.py` | L40 | From_defaults | OUI — THR-R01 |
| `hard_cap_drawdown=0.02` | `daily_pnl_breaker.py` | L30 | Hard cap | NON — borne dure intentionnelle |
| `beta_mapping_max_age_s=86400` | `risk_runtime_models.py` | L32 | RiskLimits field | NON — à connecter |
| `spread_ratio_alert=5.0` | `info_stress_monitor.py` | L24 | Default champ | **NON — P2 à calibrer** |
| `depth_ratio_min=0.10` | `info_stress_monitor.py` | L25 | Default champ | **NON — P2 à calibrer** |
| `cancellation_rate=0.80` | `info_stress_monitor.py` | L26 | Default champ | **NON — P2 à calibrer** |
| `taker_imbalance=0.90` | `info_stress_monitor.py` | L27 | Default champ | **NON — P2 à calibrer** |
| `micro_vol_divergence=3.0` | `info_stress_monitor.py` | L28 | Default champ | **NON — P2 à calibrer** |
| `extreme_alert_count=3` | `info_stress_monitor.py` | L29 | Default champ | **NON — P2 à calibrer** |
| `cooldown_s=600` | `info_stress_monitor.py` | L30 | Default champ | **NON — P2 à calibrer** |
| `btc_realized_vol_stressed=0.04` | `regime_lite.py` | L86 | from_documented_defaults | OUI — THR-RG01 |
| `btc_realized_vol_extreme=0.08` | `regime_lite.py` | L87 | Config/defaults | PARTIEL — bounded, pas de THR propre |
| `btc_drop_1h_extreme=0.05` | `regime_lite.py` | L88 | from_documented_defaults | OUI — THR-RG02 |
| `downgrade_hysteresis_s=7200` | `regime_lite.py` | L93 | from_documented_defaults | OUI — THR-RG03 |
| `extreme_cooldown_s=86400` | `regime_lite.py` | L94 | from_documented_defaults | OUI — THR-RG04 |
| `intraday_drawdown_stressed=0.01` | `regime_lite.py` | L89 | Config fallback | **NON — pas de THR dédié** |
| `intraday_drawdown_extreme=0.02` | `regime_lite.py` | L90 | Config fallback | **NON** |
| `dispersion_stressed=0.02` | `regime_lite.py` | L91 | Config fallback | **NON** |
| `dispersion_extreme=0.05` | `regime_lite.py` | L92 | Config fallback | **NON** |

---

### Fichiers SKELETON ou PARTIAL

Aucun. Tous les fichiers lus sont COMPLETE.

---

### Anomalies critiques

| Priorité | Fichier | Nature |
|----------|---------|--------|
| **P2** | `info_stress_monitor.py` L24-30 | 7 thresholds sans seam calibration — à connecter THR-IS01..07 |
| **P2** | `regime_lite.py` L89-92 | 4 dims secondaires sans THR propre (intraday_drawdown, engine_return_dispersion) — partielle calibration seam |
| **P2** | `risk_runtime_models.py` L32 | `beta_mapping_max_age_s=86400` sans THR propre |
| **P3** | `gatekeeper/gatekeeper.py` (685L) | Proche limite 700L — surveiller avant prochain sprint |
| **INFO** | `risk_backbone/emergency_kill_switch/circuit_breaker.py` | Thin re-export → `execution_backbone.emergency_circuit_breaker` — couplage inter-package intentionnel |
| **INFO** | `scoring_backbone/fee_aware_edge_gate.py` | Idem — thin re-export → `execution_backbone.fee_aware_edge_gate` |
| **INFO** | `execution_runtime_models.py` L40-43 | `safety_margin=0.0005`, `pair_health_min=0.3` hardcodés — valeurs défensives sans THR ; acceptables pour Shadow |
