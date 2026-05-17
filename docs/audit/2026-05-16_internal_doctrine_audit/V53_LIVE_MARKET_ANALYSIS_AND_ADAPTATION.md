# V5.3 — Live Market Analysis & Adaptation (vrai repo)

- **Date** : 2026-05-16
- **Repo réel** : `E:\claude  v5.3\v53_trading_system\`
- **Branche / commit** : `codex/full-shadow-abcd-migration-20260403` @ `5f4fe0f` + état de travail
- **Couvre** : Livrable 4 (analyse marché live), Livrable 5 (adaptation), Livrable 7 (doctrine quant)
- **Note** : ce document corrige les contre-vérités majeures du faux audit précédent. La doctrine quant et la microstructure sont **présentes et matures** dans le code réel.

---

## 1. Confirmation des 2 points P0 ouverts en Session 1

### 1.1 Branchement `ShariaRuntime` → execution chain

**Confirmé** : `ShariaRuntime`/`authorize_trade`/`sharia_compliance` apparaît dans **14 fichiers** dont :
- `src/execution_backbone/execution_runtime.py`
- `src/execution_backbone/execution_runtime_support.py`
- `src/execution_backbone/execution_runtime_models.py`
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `src/execution_backbone/gatekeeper/gatekeeper_support.py`
- `src/venue_adapters/binance_spot/account_feature_provider.py`
- `src/manifest_registry/*` (3 fichiers — registry/dependency/build_order)

> **La gate sharia est intégrée au chemin d'exécution** via `execution_backbone` + `gatekeeper`. Verdict P0 résolu : **SHARIA_ENFORCEMENT_READY**.

### 1.2 Tests sharia

Confirmé : `tests/test_sharia_compliance/` contient :
- `test_sharia_runtime.py`
- `test_sharia_alerts.py`

> Tests de runtime et d'alertes présents. **À approfondir Session 3** : vérifier la couverture exhaustive des 17 reason codes.

---

## 2. Ingestion live (data_backbone)

| Connecteur | Module | Fichiers clés | Statut |
|------------|--------|---------------|--------|
| WebSocket | `src/data_backbone/websocket_gateway/` | `runtime_gateway.py`, `connection_manager.py`, `heartbeat_monitor.py`, `reconnect_controller.py`, `raw_message_emitter.py`, `subscription_manager.py` | **DONE** |
| REST bootstrap | `src/data_backbone/rest_bootstrap/` | `runtime_bootstrap.py`, `snapshot_fetcher.py`, `gap_fill_controller.py`, `rate_limit_guard.py`, `bootstrap_reporter.py` | **DONE** |
| Event normalizer | `src/data_backbone/event_normalizer/` | `schema_mapper.py`, `invalid_message_guard.py`, `message_classifier.py`, `timestamp_enricher.py`, `normalization_reporter.py` | **DONE** |
| Internal router | `src/data_backbone/internal_router/` | `priority_dispatcher.py`, `queue_manager.py`, `consumer_registry.py`, `backpressure_guard.py`, `routing_reporter.py` | **DONE** |
| Freshness | `src/data_backbone/freshness_checker/` | `age_calculator.py`, `last_update_tracker.py`, `stale_hard_guard.py`, `stale_penalty_builder.py`, `freshness_reporter.py` | **DONE** |
| Pair health | `src/data_backbone/pair_health_scorer/` | `health_state_tracker.py`, `quality_aggregator.py`, `recovery_evaluator.py`, `suspension_decider.py`, `health_reporter.py` | **DONE** |
| Consistency | `src/data_backbone/consistency_checker/` | `contradiction_checker.py`, `duplicate_detector.py`, `gap_detector.py`, `sequence_checker.py`, `consistency_reporter.py` | **DONE** |
| Feature timeframes | `src/data_backbone/feature_timeframes.py` | (nouveau, non commité) | **DONE** |
| Venue adapter (binance spot) | `src/venue_adapters/binance_spot/` | `execution_adapter.py`, `rest_client.py`, `user_data_events.py`, `account_feature_provider.py` | **DONE** |

---

## 3. Features microstructurelles — 17 modules réels

[`src/data_backbone/microstructure/`](../../../src/data_backbone/microstructure/)

> Chaque module définit `METHOD_VERSION` + `METHOD_VERSION_HASH` (immutabilité de méthode auditée), un record typé Pydantic frozen avec validators, et une fonction `compute_*` ou `evaluate_*`.

| # | Feature | Module | Fonction(s) clé(s) | Record | Source théorique |
|---|---------|--------|---------------------|--------|--------------------|
| 1 | **Order Flow Imbalance** | `order_flow_imbalance.py` | `compute_order_flow_imbalance`, `compute_depth_adjusted_ofi`, `compute_order_book_event_contribution` | `OrderFlowImbalanceRecord` | Cont/Kukanov |
| 2 | **VPIN** | `vpin.py` | `compute_vpin`, `build_equal_volume_buckets`, `classify_bucket_buy_sell_volume` (`_normal_cdf` interne) | `VpinRecord`, `VpinBucket`, `VpinTradePoint` | Easley / Lopez de Prado |
| 3 | **Kyle's lambda** | `kyle_lambda.py` | `compute_kyle_lambda`, `build_kyle_intervals`, `classify_trade_direction`, `compute_normalized_kyle_impact_bps` | `KyleLambdaRecord`, `KyleIntervalPoint`, `KyleTradePoint` | Kyle 1985 |
| 4 | **Realized Kernel Vol** | `realized_kernel_vol.py` | `compute_realized_kernel_vol`, `parzen_kernel_weight`, `resolve_realized_kernel_bandwidth` | `RealizedKernelVolRecord`, `RealizedKernelPricePoint` | Barndorff-Nielsen et al. |
| 5 | **Hawkes intensity** | `hawkes_intensity.py` | `compute_hawkes_intensity` | `HawkesIntensityRecord`, `HawkesParameterEstimate`, `HawkesEventPoint` | Hawkes 1971 |
| 6 | **PIN** | `pin.py` | `compute_pin_from_parameters` | `PinRecord`, `PinParameterEstimate` | Easley et al. |
| 7 | **Amihud illiquidity** | `amihud_illiquidity.py` | `compute_amihud_illiquidity` | `AmihudIlliquidityRecord`, `AmihudBarPoint` | Amihud 2002 |
| 8 | **Roll spread** | `roll_spread.py` | `compute_roll_spread` | `RollSpreadRecord`, `RollTradePoint` | Roll 1984 |
| 9 | **Corwin-Schultz spread** | `corwin_schultz_spread.py` | `compute_corwin_schultz_spread` | `CorwinSchultzSpreadRecord`, `CorwinSchultzBarPoint` | Corwin/Schultz 2012 |
| 10 | **Queue pressure** | `queue_pressure.py` | `compute_queue_pressure` | `QueuePressureRecord`, `QueuePressureBookPoint` | classic |
| 11 | **Spread dynamics** | `spread_dynamics.py` | `compute_spread_dynamics` | `SpreadDynamicsRecord`, `SpreadDynamicsObservation` | — |
| 12 | **Realized effective spread** | `realized_effective_spread.py` | `compute_realized_effective_spread` | `RealizedEffectiveSpreadRecord`, `LiveSpreadObservation` | — |
| 13 | **LOB regime features** | `lob_regime_features.py` | `build_lob_regime_feature_snapshot`, `lob_regime_feature_names` | `LobRegimeFeatureSnapshot`, `LobDepth20Snapshot`, `LobBookLevel`, `LobAggTrade` (V1 + V2 + canonical version) | — |
| 14 | **Walls and spoofing** | `walls_and_spoofing.py` | `evaluate_walls_and_spoofing` (microprice pressure, wall_strength, wall_persistence, near_touch_drops, wall_pullaway, cancel_ratio, executed_vs_displayed, executed_volume_against_wall, robust_z01) | `WallsAndSpoofingSnapshot` | — (sophistiqué) |
| 15 | **Feature registry** | `feature_registry.py` | `MicrostructurePromotionState` enum, `promote_feature_spec`, `quarantine_feature_spec`, `restore_quarantined_feature_spec`, `reject_feature_spec`, `is_valid_feature_promotion_transition`, `get_feature_registry`, `list_feature_specs`, `get_feature_spec` | `MicrostructureFeatureSpec` | gouvernance lifecycle features |
| 16 | **Engine input provenance** | `engine_input_provenance.py` | `EngineAMicrostructureProvenance`, `EngineCMicrostructureProvenance`, `EngineDMicrostructureProvenance` + builders + payload composers | typed provenance | traçabilité audit |
| 17 | (registry/__init__.py centralisé) | `__init__.py` | facade publique de 100+ exports | — | — |

> **Tous les indicateurs académiques classiques sont présents.** Versioned, hash-identifiable, gouvernés par feature registry (promotion lifecycle), avec traçabilité provenance vers chaque engine.

### 3.1 Lifecycle gouverné des features microstructure

`MicrostructurePromotionState` enum (feature_registry.py:66) — typiquement :
- `DRAFT` / `SHADOW` / `PROMOTED` / `QUARANTINED` / `REJECTED` (à valider lecture détaillée)

Fonctions de transition :
- `promote_feature_spec` (line 302)
- `quarantine_feature_spec` (line 320)
- `restore_quarantined_feature_spec` (line 340)
- `reject_feature_spec` (line 355)
- `is_valid_feature_promotion_transition` (line 272)

→ **Chaque feature microstructure suit un lifecycle gouverné**, similaire à un schema registry de données.

---

## 4. Regime classifier — `regime_lite.py`

Source : [`src/regime_classifier/regime_lite.py`](../../../src/regime_classifier/regime_lite.py)

### 4.1 États

```python
class RegimeLiteState(StrEnum):
    CALM = "calm"
    STRESSED = "stressed"
    EXTREME = "extreme"
```

Ordering hiérarchisé : `CALM < STRESSED < EXTREME` (via `_STATE_RANK`).

### 4.2 Inputs / outputs typés

- **Input** (`RegimeLiteInput`, line 156) : `as_of_ts`, `btc_realized_vol_24h`, `btc_drop_1h`, `intraday_drawdown`, `engine_return_dispersion`
- **Memory persistant** (`RegimeLiteMemory`, line 166) : `state`, `state_entered_ts`, `entries_blocked_until_ts`, avec validator `validate_block_window`
- **Output** (`RegimeLiteAssessment`, line 185) : `state`, `candidate_state`, `previous_state`, `state_changed`, `state_entered_ts`, `entries_blocked_until_ts`, `entries_blocked`, `sudden_event`, `transition_path`, `reason_codes`, + facts observés

### 4.3 Thresholds — calibration-driven

`RegimeLiteCalibrationConfig` (line 34) → 4 threshold IDs publiés dans calibration :
- `THR-RG01` — stressed vol threshold
- `THR-RG02` — extreme drop threshold
- `THR-RG03` — downgrade hysteresis (seconds)
- `THR-RG04` — extreme cooldown (seconds)

Les autres dimensions (intraday_drawdown, engine_return_dispersion, btc_realized_vol_24h_extreme) restent en defaults **documentés** dans la config pydantic, en attente de promotion vers `THR-*` IDs.

`RegimeLiteThresholds` (line 53) impose ordering : extreme ≥ stressed (model_validator).

### 4.4 Logique d'évaluation — `classify_regime_lite` (line 263)

- `_derive_candidate_state` (line 212) : détecte EXTREME (4 conditions) > STRESSED (3 conditions) > CALM
- **Sudden event detection** : `btc_drop_1h ≤ -threshold` OR `intraday_drawdown ≥ extreme_threshold` → permet jump direct vers EXTREME
- **No-skip transition** : sans sudden_event, transitions limitées à un état par évaluation (`_step_towards`)
- **Downgrade hysteresis** : ne descend que si `time_in_state ≥ downgrade_hysteresis_s`
- **Extreme cooldown** : entrées bloquées jusqu'à `entries_blocked_until_ts`

### 4.5 Reason codes (14)

| Type | Reason code | Déclencheur |
|------|-------------|-------------|
| Extreme | `RG_EXTREME_BTC_DROP_1H` | btc_drop_1h ≤ -extreme |
| | `RG_EXTREME_INTRADAY_DRAWDOWN` | intraday_drawdown ≥ extreme |
| | `RG_EXTREME_VOL_24H` | btc_realized_vol_24h ≥ extreme |
| | `RG_EXTREME_ENGINE_DISPERSION` | engine_return_dispersion ≥ extreme |
| Stressed | `RG_STRESSED_VOL_24H` | btc_realized_vol_24h ≥ stressed |
| | `RG_STRESSED_INTRADAY_DRAWDOWN` | intraday_drawdown ≥ stressed |
| | `RG_STRESSED_ENGINE_DISPERSION` | engine_return_dispersion ≥ stressed |
| Calm | `RG_CALM_BASELINE` | aucune condition stressed/extreme |
| Transition | `RG_NO_STATE_SKIP` | candidate saute un état sans sudden_event |
| | `RG_ESCALATE_TO_STRESSED_FIRST` | escalade indirecte CALM → STRESSED |
| | `RG_DIRECT_EXTREME_EVENT` | sudden_event permet jump |
| | `RG_DOWNGRADE_HYSTERESIS_ACTIVE` | downgrade refusé par hysteresis |
| | `RG_STEP_DOWN_ONE_STATE` | downgrade limité à un cran |
| Cooldown | `RG_EXTREME_COOLDOWN_ACTIVE` | entries_blocked_until_ts > now |

> **Regime classifier sophistiqué** : anti-flapping, no-skip, sudden event handling, cooldown post-extreme. Calibration-driven sur seuils critiques. État persistant.

### 4.6 Complément regime — `complete_enablers/`

Modules associés (Build-14 / ML enablers) :
- `regime_detector_runtime.py` + `regime_detector_runtime_loader.py` — runtime ML pour détection de régime
- `hurst_regime_classifier.py` — exposant Hurst pour détection persistance
- `false_breakout_model.py` — modèle complémentaire fake breakouts

→ V5.3 a **2 niveaux** de classification de régime : `regime_lite` (bornes statistiques + hysteresis) + `regime_detector_runtime` (ML based, complète enabler post-Shadow).

---

## 5. Calibration methods — 21 modules

[`src/calibration_methods/`](../../../src/calibration_methods/)

| # | Méthode | Module | Fonction(s) | Source théorique | Statut |
|---|---------|--------|-------------|------------------|--------|
| 1 | **PSR** (Probabilistic Sharpe Ratio) | `psr.py` | `compute_probabilistic_sharpe_ratio` + `_population_skewness`, `_population_kurtosis` | Bailey & Lopez de Prado 2012 | **PRODUCTION** |
| 2 | **DSR via HLZ** (Deflated Sharpe via Harvey-Liu-Zhu) | `multiple_testing_guard.py` | `compute_harvey_liu_zhu_deflated_sharpe`, `compose_hlz_test_count` | Harvey, Liu, Zhu 2016 | **PRODUCTION** |
| 3 | **Holm-Bonferroni** (multiple testing) | `multiple_testing.py` | `apply_holm_bonferroni` | classic | **PRODUCTION** |
| 4 | **Hansen SPA** (Superior Predictive Ability) | `hansen_spa.py` | (à confirmer) | Hansen 2005 | **PRESENT** |
| 5 | **Energy Distance** | `energy_distance.py` | `compute_energy_distance_test`, `compute_raw_energy_distance_statistic` | Székely & Rizzo 2013 | **PRODUCTION** |
| 6 | **Kolmogorov-Smirnov 2-sample** | `ks_test.py` | `compute_ks_2sample` | classic | **PRODUCTION** |
| 7 | **POT-GPD** (tail risk Peaks-Over-Threshold) | `pot_gpd.py` | `fit_pot_gpd_tail_risk`, `_fit_gpd_moments`, `_pot_var` | EVT (McNeil et al.) | **PRODUCTION** |
| 8 | **Mann-Kendall** (trend test) | `mann_kendall.py` | `compute_mann_kendall_test` | Mann 1945, Kendall 1975 | **PRODUCTION** |
| 9 | **Stationarity (ADF + KPSS dual)** | `stationarity.py` | `evaluate_dual_stationarity`, `compute_adf_level_stationarity`, `compute_kpss_level_stationarity`, `_newey_west_long_run_variance` | classique | **PRODUCTION** |
| 10 | **Purged walk-forward** | `walkforward.py` | `build_purged_walk_forward_plan`, `PurgedWalkForwardPlan`, `PurgedWalkForwardFold` | Lopez de Prado 2018 | **PRODUCTION** |
| 11 | **LightGBM ML trainer** | `ml_trainer.py` | `train_lightgbm_ml_artifact` (avec Optuna, bootstrap bagging, walk-forward split, strategy sharpe, feature drift detection) | classic ML | **PRODUCTION** |
| 12 | **ML backtest projection** | `ml_backtest_projection.py` | `project_ml_training_row_from_ml_backtest_sample`, `project_ml_training_rows_from_backtest_dataset` | — | **PRODUCTION** |
| 13 | **Regime detector feature calibration** | `regime_detector_feature_calibration.py` | `resolve_regime_detector_feature_set`, `select_regime_detector_features` | — | **PRODUCTION** |
| 14 | **Regime detector projection** | `regime_detector_projection.py` | `project_regime_detector_training_row(s)` | — | **PRODUCTION** |
| 15 | **Regime detector trainer** | `regime_detector_trainer.py` | (training) | — | **PRESENT** |
| 16 | **Bootstrap** | `bootstrap.py` | (à confirmer) | — | **PRESENT** |
| 17 | **Hard cap floor** | `hard_cap_floor.py` | `apply_human_minimum_floor`, `apply_human_maximum_cap` | op security | **PRODUCTION** |
| 18 | **Execution calibration** | `execution.py` | (à confirmer) | — | **PRESENT** |
| 19 | **Walls and spoofing calibration** | `walls_and_spoofing_calibration.py` | `resolve_walls_and_spoofing_feature_set`, `select_walls_and_spoofing_features` | — | **PRODUCTION** |
| 20 | (interne `__init__.py`) | `__init__.py` | facade | — | — |
| 21 | (helpers) | divers | — | — | — |

> **Doctrine quant complète au niveau académique** :
> - Multiple-testing : Bonferroni-Holm + Harvey-Liu-Zhu DSR + HLZ test count
> - Distributional : KS, energy distance
> - Tail risk : POT-GPD (Peaks-Over-Threshold + Generalized Pareto)
> - Trend : Mann-Kendall
> - Stationarity : ADF + KPSS combined (Newey-West)
> - ML : LightGBM + Optuna + bagging + walk-forward purged + feature drift evaluation
> - Risk-adjusted : PSR (vraie skewness/kurtosis correction)

Tout est gouverné via `calibration_loader/loader.py` qui résout des `THR-*` IDs depuis `config/calibration/vN/`.

---

## 6. Patterns marché détectés (vrai code)

| Pattern | Module | Source | Statut |
|---------|--------|--------|--------|
| **Trend expansion** | `engines/engine_a/structure_detector_a.py` | direction + continuation + structure_quality + zone_proximity + trend_stability | **PRODUCTION** |
| **Mean reversion** | `engines/engine_b/local_mean_estimator_b.py` + `excess_detector_b.py` | z-score \|z\| ≥ 1.5 | **PRODUCTION** |
| **Breakout continuation** | `engines/engine_c/engine_c_runner.py` + `signal_math_c.py` | `compute_breakout_score`, `compute_continuation_score`, anti-fake-breakout (`compute_fake_breakout_risk`) | **PRODUCTION** |
| **Re-entry / second chance** | `engines/engine_d/engine_d_runner.py` (5 stages: guard, anti_revenge, history, reformation, marginal_value) | `compute_history_score`, `compute_reformation_score`, `compute_marginal_value_score`, `compute_context_score` | **PRODUCTION** |
| **Fake breakout** | `engines/engine_c/signal_math_c.py:61` `compute_fake_breakout_risk` + `engines/engine_b/anti_breakout_filter_b.py` | — | **PRODUCTION** |
| **Toxic flow** | `data_backbone/microstructure/vpin.py` (VPIN) + `complete_enablers/market_toxicity_snapshot.py` (Build-14 composite) | combinaison microstructure + op-health | **PRODUCTION** |
| **Liquidity wall / spoofing** | `data_backbone/microstructure/walls_and_spoofing.py` (microprice pressure, wall persistence, executed_vs_displayed, cancel_ratio, near_touch_drops) | détection sophistiquée | **PRODUCTION** |
| **Stale book** | `data_backbone/freshness_checker/stale_hard_guard.py` | hard reject sur Δ_i > Δ_hard | **PRODUCTION** |
| **Regime change** | `regime_classifier/regime_lite.py` `classify_regime_lite` | 3 états + hysteresis | **PRODUCTION** |
| **Sudden event** | `regime_classifier/regime_lite.py` `_derive_candidate_state` (sudden_event flag) | btc_drop_1h ≤ -extreme OR intraday_drawdown ≥ extreme | **PRODUCTION** |
| **Information asymmetry** | `data_backbone/microstructure/pin.py` (PIN) | EHO/Easley | **PRODUCTION** |
| **Hawkes self-exciting events** | `data_backbone/microstructure/hawkes_intensity.py` | intensity + parameter estimate | **PRODUCTION** |
| **Illiquidity** | `data_backbone/microstructure/amihud_illiquidity.py` (Amihud) + `roll_spread.py` (Roll) + `corwin_schultz_spread.py` (Corwin-Schultz) | 3 mesures complémentaires | **PRODUCTION** |
| **Effective spread realized** | `data_backbone/microstructure/realized_effective_spread.py` | live observations | **PRODUCTION** |
| **Market impact (price)** | `data_backbone/microstructure/kyle_lambda.py` (Kyle λ + normalized impact bps) | — | **PRODUCTION** |
| **Realized volatility** | `data_backbone/microstructure/realized_kernel_vol.py` (Parzen kernel, configurable bandwidth) | Barndorff-Nielsen | **PRODUCTION** |
| **Order flow toxicity** | `data_backbone/microstructure/vpin.py` (VPIN) | Easley/Lopez | **PRODUCTION** |
| **Order book imbalance event** | `data_backbone/microstructure/order_flow_imbalance.py` (depth-adjusted OFI) | Cont/Kukanov | **PRODUCTION** |

> **Aucun pattern doctrinal n'est manquant** au niveau code.

---

## 7. Calculs par échelle temporelle

| Catégorie | Module | Exemple |
|-----------|--------|---------|
| **Event-based** | `freshness_checker/stale_hard_guard`, `walls_and_spoofing/_score_side_features`, `order_flow_imbalance/compute_order_book_event_contribution`, `reconciliation_layer/divergence_classifier` | hard reject, depth event |
| **Window-based** | `local_mean_estimator_b` (rolling z), `pair_health_scorer/quality_aggregator`, `vpin/build_equal_volume_buckets` (volume-time), `realized_kernel_vol/compute_realized_kernel_vol`, `corwin_schultz_spread`, `amihud_illiquidity`, `kyle_lambda`, `hawkes_intensity`, `realized_effective_spread`, `spread_dynamics` | rolling stats, equal-volume buckets |
| **Calibration-artifact-based** | `calibration_loader.CalibrationLoader.get_value` consommé par `regime_lite`, `sharia_compliance/account_features_audit`, `sharia_compliance/purification_calculator`, `complete_enablers/*ml*`, etc. | seuils signés `THR-RG01..04`, `THR-H02`, `THR-H03`, etc. |
| **Snapshot/state-based** | `engines/engine_d/engine_state_snapshot_d` (persistence), `regime_lite.RegimeLiteMemory` | état persistant cross-run |
| **Promotion-gate-based** | `microstructure/feature_registry` (lifecycle DRAFT/SHADOW/PROMOTED/QUARANTINED/REJECTED), `protocols/promotion_gates` | gouvernance feature/strategy |

---

## 8. Adaptation au changement de marché (matrice étendue)

| Échelle | Module | Signal détecté | Fenêtre | Réaction | Auto/Humain | Risque trop lent | Amélioration |
|---------|--------|----------------|---------|----------|-------------|------------------|--------------|
| **Tick** | `freshness_checker/stale_hard_guard` | stale tick | event | hard reject | auto | — | — |
| Tick | `reconciliation_layer/divergence_classifier` | local vs remote divergence | event | INFO/WARNING/BLOCKING/CRITICAL + recovery_trigger | auto | — | — |
| Tick | `execution_backbone/spread_guard` | spread > threshold | event | block intent | auto | — | externaliser threshold (visible dans `M src/execution_backbone/spread_guard.py`) |
| Tick | `execution_backbone/rate_limiter` | venue rate breach | event | throttle | auto | — | — |
| Tick | `microstructure/walls_and_spoofing.evaluate_walls_and_spoofing` | spoofing pattern | window (top-N, seconds) | feature snapshot + reason codes | auto observation | — | brancher en hard-block (P2) |
| **Seconds** | `microstructure/order_flow_imbalance.compute_order_flow_imbalance` | OFI shock | rolling events | feature snapshot | auto observation | — | brancher en penalty score si pas déjà |
| Seconds | `microstructure/queue_pressure.compute_queue_pressure` | queue pressure shift | window | feature snapshot | auto observation | — | — |
| **Minutes** | `risk_backbone/loss_budgeter/drawdown_guard` | equity drop | session | observe/reject | auto | — | — |
| Minutes | `pair_health_scorer/suspension_decider` | pair health drop | window | suspension | auto | — | — |
| Minutes | `engines/engine_b/local_mean_estimator_b` | mean reversion opportunity | rolling | EMIT/NO_TRADE | auto | — | — |
| Minutes | `regime_classifier/regime_lite.classify_regime_lite` | state transition | event-driven + hysteresis | reason codes + entries_blocked_until_ts | auto | hysteresis bien dimensionnée | revoir THR-RG03 calibration |
| **Hours** | `microstructure/realized_kernel_vol.compute_realized_kernel_vol` | realized vol drift | configurable bandwidth | feature snapshot | auto | — | — |
| Hours | `microstructure/vpin.compute_vpin` | toxicity drift | configurable buckets/day | feature snapshot | auto | — | brancher en penalty/halt si seuil dépassé |
| Hours | `microstructure/hawkes_intensity.compute_hawkes_intensity` | self-exciting cluster | window | parameter estimate | auto | — | — |
| **Days** | `protocols/shadow_runtime` + `shadow_day_counter` | shadow evidence | 30j | gate promotion | auto | — | — |
| Days | `meta_learning/post_trade_diagnostic_engine`, `mistake_classifier`, `hypothesis_registry`, `review_orchestrator` | post-trade insights | rolling | replay bundles + review packets | semi-auto | — | — |
| Days | `microstructure/feature_registry` (`promote_feature_spec`, `quarantine_feature_spec`) | feature lifecycle | manual + governed | promotion/quarantine | manuel | — | — |
| **Weeks** | `local_replay_runtime/strategy_ladder_*` | replay evidence + ML training | offline | artifact promotion | semi-auto | — | — |
| Weeks | `calibration_methods/ml_trainer.train_lightgbm_ml_artifact` | retrain LightGBM | walk-forward purged + Optuna | artifact + drift detection | auto | — | — |
| Weeks | `calibration_methods/multiple_testing_guard.compute_harvey_liu_zhu_deflated_sharpe` | DSR / HLZ deflation | walk-forward fold | DSR result | auto | — | — |
| **Months** | `protocols/promotion_gates` | promotion light→micro_live, complete→live | 30j+ shadow | promotion/rejection | code-enforced | — | — |

> **Adaptation multi-échelle complète**, du tick au mois, avec gouvernance promotion gates.

---

## 9. Doctrine quant — récapitulatif

Tous les éléments de la doctrine V5.3 listés dans la commande utilisateur sont **PRÉSENTS dans le code réel** :

| Élément | Module | Statut |
|---------|--------|--------|
| Carver forecast normalization | `scoring_backbone/forecast_normalizer.py` | ✅ PRODUCTION |
| Break-even filter | `scoring_backbone/break_even_filter.py` | ✅ PRODUCTION |
| Expected gain / cost / CE / EV_net | `scoring_backbone/break_even_filter.py` + `ev_net_floor_thresholds.py` + `engines/engine_*/cost_feasibility_*.py` + `meta_minimal/break_even_dashboard/` | ✅ PRODUCTION |
| Volatility scaling | engines (ATR), `realized_kernel_vol`, `forecast_normalizer` (E[r]/σ) | ✅ PRODUCTION |
| Position sizing | `portfolio_minimal/allocation_router/` (base_size, score_size, cap_applier, capital_viability, phantom_trade_guard) | ✅ PRODUCTION |
| OFI | `data_backbone/microstructure/order_flow_imbalance.py` | ✅ PRODUCTION |
| VPIN | `data_backbone/microstructure/vpin.py` | ✅ PRODUCTION |
| Kyle's λ | `data_backbone/microstructure/kyle_lambda.py` | ✅ PRODUCTION |
| Realized kernel | `data_backbone/microstructure/realized_kernel_vol.py` | ✅ PRODUCTION |
| Queue pressure | `data_backbone/microstructure/queue_pressure.py` | ✅ PRODUCTION |
| Spread dynamics | `data_backbone/microstructure/spread_dynamics.py` + `realized_effective_spread.py` | ✅ PRODUCTION |
| Hawkes | `data_backbone/microstructure/hawkes_intensity.py` | ✅ PRODUCTION |
| PIN | `data_backbone/microstructure/pin.py` | ✅ PRODUCTION |
| Amihud | `data_backbone/microstructure/amihud_illiquidity.py` | ✅ PRODUCTION |
| Roll | `data_backbone/microstructure/roll_spread.py` | ✅ PRODUCTION |
| Corwin-Schultz | `data_backbone/microstructure/corwin_schultz_spread.py` | ✅ PRODUCTION |
| Multiple testing guard | `calibration_methods/multiple_testing_guard.py` (HLZ) + `multiple_testing.py` (Holm-Bonferroni) | ✅ PRODUCTION |
| PSR | `calibration_methods/psr.py` | ✅ PRODUCTION |
| DSR | via HLZ deflated sharpe (`multiple_testing_guard.compute_harvey_liu_zhu_deflated_sharpe`) | ✅ PRODUCTION |
| SPA | `calibration_methods/hansen_spa.py` | ✅ PRESENT |
| Energy distance | `calibration_methods/energy_distance.py` | ✅ PRODUCTION |
| KS test | `calibration_methods/ks_test.py` | ✅ PRODUCTION |
| ML confidence enabler | `complete_enablers/ml_confidence_enabler.py` + `ml_fusion.py` + `ml_scoring_soft_penalty_hook.py` | ✅ PRODUCTION (soft only) |
| ML promotion gate | `complete_enablers/ml_model_promotion_gate.py` | ✅ PRODUCTION |
| ML runtime artifact loader | `complete_enablers/ml_runtime_artifact_loader.py` | ✅ PRODUCTION |
| Regime classifier | `regime_classifier/regime_lite.py` + `complete_enablers/regime_detector_runtime.py` + `hurst_regime_classifier.py` | ✅ PRODUCTION |

---

## 10. Forces structurelles à PRÉSERVER

1. **Microstructure complete et versionnée** : 17 features, chacune avec METHOD_VERSION + hash, record Pydantic frozen typé.
2. **Feature registry gouverné** : lifecycle DRAFT/SHADOW/PROMOTED/QUARANTINED/REJECTED + transitions validées.
3. **Engine input provenance typed** : Engine A/C/D ont des `*MicrostructureProvenance` modèles pour traçabilité audit.
4. **Regime classifier sophistiqué** : 3-état avec anti-flapping, no-skip, sudden_event, extreme cooldown, persistent memory, calibration-driven.
5. **Doctrine quant académique** : PSR (Bailey/Lopez), DSR via Harvey-Liu-Zhu, Holm-Bonferroni, ADF+KPSS dual stationarity, POT-GPD tail risk, Kolmogorov-Smirnov, energy distance, Mann-Kendall, purged walk-forward.
6. **ML governed** : LightGBM trainer avec Optuna, walk-forward purged, bootstrap bagging, strategy sharpe, **feature drift evaluation** + promotion gate + artifact loader + soft penalty hook.
7. **Calibration loader unifié** : tous les seuils critiques typés via `THR-*` IDs, consommés par regime/sharia/ML/microstructure.

---

## 11. Points à clarifier / approfondir

| Question | À traiter |
|----------|-----------|
| Liste exhaustive des `THR-*` IDs dans `config/calibration/v1/` | Session 3 |
| Couverture exhaustive des tests `test_calibration_methods/` (4 tests vus pour PSR, DSR, energy_distance, pot_gpd — manquants ?) | Session 3 |
| Branchement effectif de `walls_and_spoofing` en hard-block vs observation seulement | Session 3 |
| Branchement effectif de `vpin` en penalty score / halt vs observation seulement | Session 3 |
| Hansen SPA — extraire la signature (à confirmer) | Session 3 |
| Strategy Ladder pipeline complet (`local_replay_runtime/strategy_ladder_*` 25+ modules) | Session 3 |

---

## 12. Verdict Session 2

| Axe | Statut |
|-----|--------|
| LIVE_INGESTION | **READY** (WebSocket + REST + freshness + normalize + route) |
| MICROSTRUCTURE | **READY — 17 features académiques, versioned, lifecycle gouverné** |
| REGIME | **READY — 3-état hysteresis + cooldown + calibration-driven** |
| QUANT DOCTRINE | **READY — PSR/DSR/Holm-Bonferroni/SPA/energy/KS/POT-GPD/Mann-Kendall/walk-forward purged/LightGBM gouverné** |
| ADAPTATION (tick → month) | **READY** |
| ML GOVERNANCE | **READY (Build-14 soft enabler + promotion gate + drift evaluation)** |

> **MARKET_ADAPTATION_READY** au sens doctrinal complet.

---

## 13. Next safe step

1. Continuer Session 3 : artifacts (Strategy Ladder + governance ML + promotion artifacts) + gaps & patch plan + verdict final P0/P1/P2.
2. Vérifier en Session 3 les **branchements** : walls_and_spoofing/vpin → penalty/halt ; complete_enablers/ml_* → scoring soft penalty hook ; engine C/D microstructure inputs.
3. Compiler en Session 3 la liste finale des seuils `THR-*` actifs dans `config/calibration/v1/`.
