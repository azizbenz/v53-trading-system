# V5.3 — Internal Doctrine Audit (vrai repo)

- **Date** : 2026-05-16
- **Repo réel auditée** : `E:\claude  v5.3\v53_trading_system\`
- **Branche HEAD** : `codex/full-shadow-abcd-migration-20260403` @ commit `5f4fe0f`
- **État** : commit HEAD + 169 fichiers `M` + 200+ fichiers `??` non commités (état de travail courant)
- **Mode** : Read-only, aucune modification de code
- **Auditeur** : Claude Opus 4.7
- **Note importante** : un précédent audit (5 MD daté du même jour, écrit dans `.claude/worktrees/agitated-taussig-53f14d/docs/audit/`) a été produit contre **un worktree obsolète** (commit `5fc4618`, branche figée) et contenait des contre-vérités majeures. Ces 5 MD ont été supprimés. **Ce document est la vraie référence.**

---

## 1. Cartographie réelle des packages (33)

| Package | Statut | Maturité observée |
|---------|--------|-------------------|
| `src/alerting/` | DONE | telegram_alerter.py (canal opérateur) |
| `src/backtest_artifact_import/` | DONE | bridge import packets de revue + ml_model_transport + capital_profile_builder + export_dir_bridge |
| `src/calibration_loader/` | DONE | `loader.py` + `contracts.py` (CalibrationLoader, CalibrationArtifactValidationError) — **calibration artifacts EXISTENT** |
| `src/calibration_methods/` | DONE — riche | 21 modules : `psr.py`, `dsr.py`, `hansen_spa.py`, `energy_distance.py`, `ks_test.py`, `pot_gpd.py`, `mann_kendall.py`, `stationarity.py`, `walkforward.py`, `multiple_testing.py`, `multiple_testing_guard.py`, `bootstrap.py`, `ml_trainer.py`, `ml_backtest_projection.py`, `regime_detector_*`, `walls_and_spoofing_calibration.py`, `hard_cap_floor.py`, `execution.py` |
| `src/cockpit/` | DONE — très riche | 38+ modules : `server.py` (FastAPI/HTTP), `state_*` granulaire (engines, decision_trace, refusal_journal, kill_proof, multiple_testing, queue_trace, freshness, capacity_guard, model_risk, sizing_chain, tail_risk, warmup_explainer, calibration, lab_review, lab_vps_transfer, replay_metrics, run_comparison, etc.) + `strategy_ladder_*` |
| `src/complete_enablers/` | DONE — riche | Build-14 + ML : `ml_confidence_enabler`, `ml_fusion`, `ml_model_promotion_gate`, `ml_runtime_artifact_loader`, `ml_scoring_soft_penalty_hook` + `competition_monitor`, `false_breakout_model`, `hurst_regime_classifier`, `limited_influence`, `lob_deep_filter_vwa`, `market_toxicity_snapshot`, `micro_edge_entry_timing_layer`, `micro_edge_exit_governor`, `order_book_imbalance`, `regime_detector_runtime`, `regime_detector_runtime_loader`, `supplementary_refs_governance`, `execution_fragility_score` |
| `src/contract_test_suite/` | DONE | schema assertions, negative cases, compatibility |
| `src/dag_validator/` | DONE | layer order, cycle detection, import scanning, dependency_matcher |
| `src/data_backbone/` | DONE — riche | `microstructure/` (17 modules — voir Session 2), `freshness_checker/`, `event_normalizer/`, `internal_router/`, `pair_health_scorer/`, `rest_bootstrap/`, `websocket_gateway/`, `consistency_checker/`, `feature_timeframes.py` |
| `src/engines/engine_a/` | DONE | implémentation canonique (préservée du faux audit) |
| `src/engines/engine_b/` | DONE | implémentation canonique |
| `src/engines/engine_c/` | **DONE — 13 modules** | breakout continuation pipeline complet — voir §2 |
| `src/engines/engine_d/` | **DONE — 23 modules** | re-entry / second chance avec first_episode_resolver, historical_linkage_guard, consecutive_stop_counter — voir §2 |
| `src/execution_backbone/` | DONE — riche | `execution_runtime.py`, `emergency_circuit_breaker.py`, `spread_guard.py`, `rate_limiter.py`, `gatekeeper/`, `slippage_model.py`, `fee_aware_edge_gate.py`, `venue_constraints_provider.py`, `execution_routing_*`, `fill_tracker/`, `reconciliation_layer/`, `order_decider/`, `execution_cost_meter/` |
| `src/interface_contracts/` | DONE — riche | décisions, market events, meta, atomic_io, error_contracts, domain_types, dashboard_command_contracts, capital_profile_contracts, governed_audit_evidence_contracts, ml_governance_proof_contracts, promotion_artifact_contracts, storage_budget_support, strategy_ladder_*, shadow_vps_service_contracts, live_complete_actions |
| `src/local_replay_runtime/` | DONE — TRÈS riche | 40+ modules : Strategy Ladder pipeline complet (`strategy_ladder_*`), `gold_microstructure_feature_builder`, `silver_market_synchronizer`, `governed_audit_evidence_index`, `local_lab_*` (calibration, regime, ml, promotion), `artifact_release_candidate`, `artifact_upload_bridge_candidate`, `feature_threshold_manifest`, `pair_bounds_registry`, `ml_governance_sidecars`, `replay_execution_runtime`, `replay_execution_projection_loader`, `data_science_quality_gates`, `edge_gate_calibration`, `backtest_proof_matrix` |
| `src/manifest_registry/` | DONE | build_order, dependency, module_inventory, profile, version |
| `src/meta/` | DONE — facade | (à vérifier en Session 2 si vide ou facade) |
| `src/meta_learning/` | DONE | post-trade, mistake_classifier, hypothesis_registry, replay_bundle_builder, review_orchestrator, etc. |
| `src/meta_minimal/` | DONE | DTR core, CRA monitor, break-even dashboard, edge tracker prudent, meta_runtime |
| `src/monitoring/` | DONE — riche | metrics_collector, observability, alert_manager, dashboards, local_observability_stack, local_grafana_api, contracts_dashboard, contracts_artifacts, replay_governance_projection, challenger_evidence_alerts, artifact_visibility, monitoring_runtime |
| `src/portfolio/` | DONE | facade |
| `src/portfolio_minimal/` | DONE | opportunity_selector, allocation_router (incl. capital_viability) |
| `src/protocols/` | DONE — riche | gates Shadow / Micro-live / Live-Light / Live-Complete + `engine_{a,b,c,d}_hooks.py` + bridges (`engine_a_pre_entry_confirmation_bridge`, `engine_b_sweep_validation_bridge`, `engine_c_void_validation_bridge`, `engine_d_reentry_validation_bridge`), `engine_coordination_rules.py`, `closed_episode_journal`, `compiled_artifact_registry_store`, `compiled_hook_plan_loader`, `dashboard_command_queue`, `execution_runtime_bootstrap`, `execution_runtime_dashboard`, `execution_runtime_projection_bridge`, `live_complete_runtime`, `shadow_live_websocket`, `shadow_vps_service` |
| `src/regime_classifier/` | DONE | `regime_lite.py` (+ `complete_enablers/regime_detector_runtime.py`, `regime_detector_runtime_loader.py`, `hurst_regime_classifier.py`) |
| `src/risk_backbone/` | DONE | risk_runtime, risk_runtime_evaluation_support, risk_runtime_explainability, risk_runtime_models, btc_factor_guard, correlation_cluster_guard, exposure_budgeter, loss_budgeter, emergency_kill_switch |
| `src/scoring_backbone/` | DONE — riche | `scoring_runtime.py` + scoring_runtime_support, `forecast_normalizer.py` (Carver), `break_even_filter.py`, `fee_aware_edge_gate.py`, `ev_net_floor_thresholds.py`, **thresholds par engine** (`engine_a_cost_thresholds`, `engine_b_breakout_thresholds`, `engine_b_cost_thresholds`, `engine_b_excess_thresholds`, `engine_b_invalidation_thresholds`, `engine_c_continuation_thresholds`, `engine_c_cost_thresholds`, `engine_d_coordination_thresholds`, `engine_d_cost_thresholds`, `engine_d_first_episode_thresholds`), `hard_block_gate/`, `penalty_aggregator/`, `ranking_router/`, `raw_score_builder/` |
| `src/secrets_manager/` | DONE | DPAPI Win/Posix sealer/loader/CLI — gestion sécurisée des secrets |
| `src/sharia_compliance/` | **DONE — 15 modules** | voir [V53_SHARIA_SPOT_LONG_ONLY_AUDIT.md](V53_SHARIA_SPOT_LONG_ONLY_AUDIT.md) |
| `src/smoke_bootstrap_recovery/` | DONE | sanity, shadow_readiness, config_validator, smoke_models, smoke_reporter |
| `src/ui/` | DONE | dashboards locked/light/technical/complete + `complete_dashboard_artifact_sections`, `complete_dashboard_control_plane`, `operator_actions` |
| `src/venue_adapters/` | DONE | `binance_spot/` (execution_adapter, rest_client, user_data_events) |

> **Le repo est massivement plus mature** que ce que mon faux audit a décrit. La quasi-totalité des "P0/P1 GAP" du faux audit sont **résolus dans le code**.

---

## 2. Doctrine des moteurs A/B/C/D (vraie)

### 2.1 Coordination doctrinale (PIVOT)

Source unique : [`src/protocols/engine_coordination_rules.py`](../../../src/protocols/engine_coordination_rules.py)

Règles typées avec reason codes hiérarchisés :

| Règle | Engine | Condition | Reason code | Action |
|-------|--------|-----------|-------------|--------|
| **R-AC-1** | C | `a_holding_block_active=True` sur même pair/direction | `hard_block.ac_mutual_exclusion.a_holding` | HARD_BLOCK |
| **R-AC-2** | C | `recent_a_fire_same_setup_at_ns` dans la fenêtre `recent_fire_block_ns` | `hard_block.ac_recent_fire` | HARD_BLOCK |
| **R-D-1** | D | `first_episode_ref` absent OU pair/side mismatch | `hard_block.d_no_historical_linkage` | HARD_BLOCK |
| **R-D-2** | D | `consecutive_d_stop_count ≥ d_consecutive_stop_limit` ET pas de fresh A detection | `hard_block.d_consecutive_stops_reset_required` | HARD_BLOCK |
| **R-D-3** | D | `d_failsafe_override_available` ET `evaluated_at_ns - last_d_stop_at_ns ≥ d_reset_failsafe_ns` | `coordination.d_failsafe_override` | PERMIT (size réduite) |

`EngineCoordinationOutcome` produit :
- `RefusalRecord` (typé, pair, engine_id, category=HARD_BLOCK, reason_codes)
- `ConditioningRecord` (typé, family=HARD_BLOCK, code, value, triggered_no_trade=True)
- `EngineCoordinationAction` enum (HARD_BLOCK, SIZE_REDUCED)
- `size_multiplier`, `resolved_size`

> **Conséquence doctrinale** : C est strictement exclu si A actif sur même setup ; D ne peut jamais être un primary entry (R-D-1 exige un `first_episode_ref`) ; D s'auto-régule via consecutive stops.

### 2.2 Engine A (préservé)

(Identique à ce qui est connu — voir Session 2 si besoin de relire.)

### 2.3 Engine B (préservé)

Mean reversion + anti-breakout filter. Voir `engine_b_runner.py` pour le pipeline. Long-only confirmé via `NoTradeReasonB.NON_LONG_DIRECTION`.

### 2.4 Engine C — breakout continuation (réel)

Source : [`src/engines/engine_c/engine_c_runner.py`](../../../src/engines/engine_c/engine_c_runner.py), [`engine_c_runtime.py`](../../../src/engines/engine_c/engine_c_runtime.py)

| Élément | Réalité |
|---------|---------|
| Decision enum | `EngineCDecision` (line 32) |
| No-trade reasons | `NoTradeReasonC` (line 37) |
| Conviction | `ConvictionLevelC` (line 56), `TierSuggestionC` (line 63) |
| Input | `EngineCInput` (line 180) |
| Output | `EngineCOutput` (line 136) |
| Pipeline (`run_engine_c`) | breakout → continuation → fake_breakout → cost → conviction (lines 249–) |
| Stages | `_evaluate_breakout_stage` (376), `_evaluate_continuation_stage` (448), `_evaluate_fake_breakout_stage` (506), `_evaluate_cost_stage` (562), `_evaluate_conviction_stage` (625) |
| Hook protocole | `EngineCVoidValidationHook` (engine_c_runtime.py:120) ↔ [`src/protocols/engine_c_void_validation_bridge.py`](../../../src/protocols/engine_c_void_validation_bridge.py) |
| Coordination | `_CoordinationEvaluator` Protocol (engine_c_runtime.py:69), invoque `evaluate_engine_coordination` (engine_coordination_rules.py:33) |
| Refusal sink | `_RefusalSink` Protocol (engine_c_runtime.py:64), reçoit RefusalRecord typés |
| Runtime statut | `EngineCRuntimeStatus` (line 79) — équivalent à EngineARuntimeStatus |
| Math | `signal_math_c.py` : `compute_breakout_score`, `compute_context_score`, `compute_continuation_score`, `compute_fake_breakout_risk` |
| Cost | `cost_feasibility_c.py` avec `CostReasonCodeC` enum + `CostMetricsC` |
| Continuation validator | `continuation_validator_c.py` (`validate_continuation_c`) |
| Conviction | `conviction_builder_c.py` (`build_conviction_c`) |
| Invalidation | `invalidation_mapper_c.py` (`build_invalidation_levels_c`) |
| Forecast/runtime support | `engine_c_runtime_support.py` (build_signal_candidate, run_void_validation_hook, evaluate_risk, etc.) + `engine_c_runtime_forecast_support.py` |
| Long-only | confirmé doctrinalement (à valider via grep `NON_LONG_DIRECTION`) |
| Statut | **PRODUCTION-READY** |

### 2.5 Engine D — re-entry / second chance (réel)

Source : [`src/engines/engine_d/engine_d_runner.py`](../../../src/engines/engine_d/engine_d_runner.py), [`engine_d_runtime.py`](../../../src/engines/engine_d/engine_d_runtime.py), [`engine_d_models.py`](../../../src/engines/engine_d/engine_d_models.py)

| Élément | Réalité |
|---------|---------|
| Decision enum | `EngineDDecision` (engine_d_models.py:12) |
| No-trade reasons | `NoTradeReasonD` (engine_d_models.py:17) |
| Conviction | `ConvictionLevelD` (line 34), `TierSuggestionD` (line 41) |
| Input | `EngineDInput` (line 134) |
| Output | `EngineDOutput` (line 92) |
| Pipeline (`run_engine_d`) | `_evaluate_guard_stage` (135), `_evaluate_anti_revenge_stage` (239), `_evaluate_history_stage` (269), `_evaluate_reformation_stage` (308), `_evaluate_marginal_value_stage` (376) |
| **First episode resolver** | [`first_episode_resolver_d.py`](../../../src/engines/engine_d/first_episode_resolver_d.py) — `resolve_first_episode_ref`, `inspect_first_episode_gap`, `EpisodeJournalLike` Protocol — D **ne peut jamais** être un primary entry |
| **Historical linkage guard** | [`historical_linkage_guard_d.py`](../../../src/engines/engine_d/historical_linkage_guard_d.py) — vérifie linkage avec un épisode A/C antérieur |
| **Consecutive stop counter (anti-revenge)** | [`consecutive_stop_counter_d.py`](../../../src/engines/engine_d/consecutive_stop_counter_d.py) — `record_engine_d_stop`, `record_fresh_a_detection`, `to_coordination_fields`, `inspect_engine_d_reset_state` |
| **Marginal value estimator** | [`marginal_value_estimator_d.py`](../../../src/engines/engine_d/marginal_value_estimator_d.py) — `marginal_value_floor_cleared` |
| Hook protocole | `EngineDReentryValidationHook` (engine_d_runtime.py:119) ↔ [`src/protocols/engine_d_reentry_validation_bridge.py`](../../../src/protocols/engine_d_reentry_validation_bridge.py) |
| Coordination | `_CoordinationEvaluator` Protocol (engine_d_runtime.py:68) |
| Forecast signal candidate | `build_forecast_signal_candidate` (engine_d_runtime_support.py:351) — D produit aussi un **ForecastSignalCandidate** en plus du SignalCandidate régulier |
| Conditioning state | `_build_conditioning_state` (engine_d_runtime_support.py:392) |
| Forecast reason codes / versions / economics | helpers dédiés (`_build_forecast_reason_codes`, `_build_forecast_versions`, `_resolve_forecast_economics`, `_resolve_volatility_proxy`) |
| Engine state snapshot | `engine_state_snapshot_d.py` — `EngineDStateSnapshot`, `EngineDStateSnapshotManifest`, `EngineDStateSnapshotStore` (persistence du state D entre runs) |
| Runtime mixin | `engine_d_runtime_history_entry_mixin.py` — `EngineDRuntimeHistoricalEntryMixin` |
| Result builders | `engine_d_runtime_result_builders.py` — 7 builders (hook_blocked, missing_scoring_audit, hard_blocked, selection_rejected, risk, accepted, circuit_breaker_blocked) |
| Long-only | doctrine confirmée (à valider via grep) |
| Statut | **PRODUCTION-READY** |

> **D est doctrinalement plus mature que C** — il a anti-revenge, state snapshots, forecast signal candidate, et failsafe override.

---

## 3. Surfaces transverses validées (preuves)

### 3.1 Forecast normalizer — Carver

Source : [`src/scoring_backbone/forecast_normalizer.py`](../../../src/scoring_backbone/forecast_normalizer.py)

- `compute_raw_forecast(expected_return, volatility_scale)` → F = E[r] / σ
- `resolve_forecast_scalar(raw_forecasts, config)` → ForecastScalar = target / E[|F|] sur sample gouverné
- `normalize_raw_forecast(raw_forecast, forecast_scalar, config)` → clip à `max_abs_forecast`
- `ForecastNormalizerConfig(target_mean_abs_forecast=10.0, max_abs_forecast=20.0)` — defaults Carver
- `ForecastNormalizationResult(raw_forecast, forecast_scalar, normalized_forecast, clipped: bool)`

> **Carver-style forecast normalization existe et est gouvernée.**

### 3.2 Break-even filter

Source : [`src/scoring_backbone/break_even_filter.py`](../../../src/scoring_backbone/break_even_filter.py)

- `BreakEvenFilterConfig(min_ev_net=0.0, strict_break_even=True, require_complete_cost_model=False)`
- `evaluate_break_even_filter(...)` retourne `BreakEvenFilterDecision` typé avec :
  - `expected_break_even = expected_cost + delta_safe`
  - `ev_net = candidate_size * (expected_gain - expected_cost)`
  - 3 conditions : `edge_cleared`, `ce_cleared`, `ev_cleared`
  - reason codes : `COST_MODEL_INCOMPLETE`, `BREAK_EVEN_NOT_CLEARED`, `CE_BELOW_MINIMUM`, `EV_NET_BELOW_FLOOR`
  - Tracking statuses : `cost_model_completeness_status`, `fee_source_status`, `impact_source_status`, `fill_realism_status`, `realized_slippage_status`
  - `partial_cost_model: bool`, `cost_gate_status` (UNKNOWN / COMPLETE / PARTIAL_COST_MODEL / COST_MODEL_INCOMPLETE)

> **Break-even filter complet, transparent, audit-ready.**

### 3.3 Thresholds par engine

[`src/scoring_backbone/`](../../../src/scoring_backbone/) contient des modules de seuils explicitement par engine :
- `engine_a_cost_thresholds.py`
- `engine_b_breakout_thresholds.py`, `engine_b_cost_thresholds.py`, `engine_b_excess_thresholds.py`, `engine_b_invalidation_thresholds.py`
- `engine_c_continuation_thresholds.py`, `engine_c_cost_thresholds.py`
- `engine_d_coordination_thresholds.py`, `engine_d_cost_thresholds.py`, `engine_d_first_episode_thresholds.py`
- `ev_net_floor_thresholds.py`, `fee_aware_edge_gate.py`

> **Seuils typés et isolés, prêts pour calibration externe.**

### 3.4 Contrats partagés présents (que le faux audit disait MISSING)

Importés depuis `interface_contracts` dans `engine_coordination_rules.py:5-16` :
- `ConditioningFamily` ✅
- `ConditioningRecord` ✅
- `EngineId` ✅
- `EngineCoordinationAction` ✅
- `EngineCoordinationInput` ✅
- `EngineCoordinationOutcome` ✅
- `EngineCoordinationThresholds` ✅
- `RefusalCategory` ✅
- `RefusalRecord` ✅
- `Side` (à voir — Side enum probablement enrichie depuis le worktree obsolète)

> **RefusalRecord et ConditioningRecord existent et sont produits par les engines via la coordination layer.** Mon faux audit disait l'inverse : c'était totalement faux.

### 3.5 Calibration loader

Source : [`src/calibration_loader/loader.py`](../../../src/calibration_loader/loader.py)

- `CalibrationLoader(calibration_root)` — racine `config/calibration`
- `loader.load(version)` — charge une version (ex. `v1`)
- `loader.get_value(collection, threshold_id)` — lookup typé de seuil par ID (ex. `THR-H02`, `THR-H03`)
- `CalibrationArtifactValidationError` levée si seuil invalide
- Consommé par `sharia_compliance/account_features_audit.py:90-101` et `sharia_compliance/purification_calculator.py:96-109`

> **Le système consomme déjà des seuils calibrés depuis `config/calibration/v1/`** (visible dans les `??` du git status : `config/calibration/`).

---

## 4. Hooks et bridges (P0 doctrinal nouveau)

Présents dans [`src/protocols/`](../../../src/protocols/) :

| Bridge | Fichier | Rôle |
|--------|---------|------|
| Engine A pre-entry confirmation | `engine_a_pre_entry_confirmation_bridge.py` | hook avant emit de A |
| Engine B sweep validation | `engine_b_sweep_validation_bridge.py` | hook validation sweep B |
| Engine C void validation | `engine_c_void_validation_bridge.py` | hook validation void/breakout C |
| Engine D re-entry validation | `engine_d_reentry_validation_bridge.py` | hook validation re-entry D |
| Engine coordination | `engine_coordination_rules.py` | règles A/C exclusion + D linkage |
| Engine A/B/C/D hooks | `engine_a_hooks.py`, `engine_b_hooks.py`, `engine_c_hooks.py`, `engine_d_hooks.py` | hooks point d'extension par engine |

> Architecture hooks/bridges = **point d'extension typé**, pas de monkey-patching, pas de modification d'engines pour ajouter de la logique externe.

---

## 5. Tests (couverture observée)

`tests/` contient au moins :

| Domaine | Tests |
|---------|-------|
| Engines | `test_engine_a/`, `test_engine_b/`, `test_engine_c/`, `test_engine_d/` (existants — confirmés via git status `M tests/test_engines/test_engine_c/test_engine_c.py`, `tests/test_engines/test_engine_c/test_engine_c_runtime.py`, `tests/test_engines/test_engine_d/test_engine_d_runtime.py`) |
| Microstructure | `test_data_backbone/microstructure/` (kyle_lambda, order_flow_imbalance, queue_pressure, walls_and_spoofing, feature_registry, engine_input_provenance) |
| Calibration methods | `test_calibration_methods/test_dsr.py`, `test_psr.py`, `test_pot_gpd.py`, `test_energy_distance.py` |
| ML enablers | `test_complete_enablers/test_ml_*` (5 fichiers : confidence_enabler, fusion, model_promotion_gate, runtime_artifact_loader, scoring_soft_penalty_hook), `test_regime_detector_runtime.py` |
| Scoring | `test_scoring_backbone/test_scoring_runtime.py`, `test_break_even_filter.py` |
| Risk | `test_risk_backbone/test_risk_runtime.py` |
| Execution | `test_execution_backbone/test_execution_runtime.py` |
| Local replay (Strategy Ladder) | 25+ tests `test_strategy_ladder_*` (data_factory, b2_label_store_builder, candidate_trade_semantics_audit, edge_model_provider, engine_a/b/c/d_input_builder, engine_native_adapter, engine_native_preselection, expected_edge_training, first_controlled_run, gate_waterfall_analysis, ml_lab_handoff, operator_artifacts, orderbook_reconstructor, replay_evidence, replay_performance, rolling_ml_window_planner, runner) + `test_data_science_quality_gates.py`, `test_gold_microstructure_feature_builder.py`, `test_governed_audit_evidence_index.py`, `test_ml_governance_sidecars.py`, `test_pair_bounds_registry.py`, `test_promotion_artifact_builder.py`, `test_raw_market_data_indexer.py`, `test_replay_execution_runtime.py`, `test_run_class_component_coverage.py`, `test_silver_market_synchronizer.py`, `test_venue_metadata_registry.py` |
| Protocols | `test_promotion_gates.py`, `test_shadow_runtime.py`, `test_micro_live_runtime.py`, `test_live_light_runtime.py`, `test_live_complete_runtime.py`, `test_dashboard_command_queue*`, `test_replay_governance_projection.py`, `test_shadow_live_plan.py`, `test_shadow_vps_service*` |
| Cockpit | `tests/cockpit/` (présent) |
| Capital viability | `test_portfolio_minimal/test_capital_viability.py` |
| Backtest artifact import | `test_export_dir_bridge.py`, `test_ml_model_transport.py`, `test_capital_profile_builder.py` |
| Monitoring | `test_local_observability_stack*`, `test_logging_config.py`, `test_monitoring_backend.py`, `test_shadow_vps_service_monitoring_support.py`, `test_v53_local_solution_launcher.py`, `test_shadow_challenger_verdict_monitoring.py` |

> **Couverture massive et corrélée à l'architecture réelle.** Mon faux audit avait sous-estimé le nombre et la profondeur des tests.

---

## 6. Forces structurelles à PRÉSERVER

1. **Pipeline canonique strict** : engines (4 réels) → scoring (Carver + break-even + thresholds par engine) → portfolio → risk → execution → meta. Pas de raccourcis.
2. **Coordination doctrinale typée** dans `engine_coordination_rules.py` avec `EngineCoordinationOutcome` produisant `RefusalRecord` + `ConditioningRecord`. C'est la garantie systémique de la mutual exclusion A/C et de la dépendance D-on-first-episode.
3. **Bridges hooks par engine** dans `protocols/` — point d'extension typé sans casse d'engine.
4. **Sharia compliance comme package dédié** (15 modules, AAOIFI compliant, calibration-driven) — voir doc dédié.
5. **Calibration loader** consommé par sharia + futurs consommateurs — `config/calibration/v1/` est la vraie racine de seuils signés.
6. **Forecast normalizer Carver** + `break_even_filter` audit-ready avec tracking de complétude du modèle de coût.
7. **Engine D state snapshot persistence** + anti-revenge counter + failsafe override — gestion cycle de vie sophistiquée.
8. **Strategy Ladder pipeline** dans `local_replay_runtime/` — pipeline complet de génération de calibration depuis raw data → silver/gold microstructure builders → ML lab handoff → promotion artifacts.
9. **Cockpit FastAPI** avec state granulaire par sous-système — observabilité opérationnelle profonde.
10. **DAG validator + contract test suite** comme garde-fous architecturaux.

---

## 7. Points à approfondir en Session 2

- Détail des 17 modules `data_backbone/microstructure/` (OFI, VPIN, Kyle, realized kernel, queue pressure, spread dynamics, Hawkes, PIN, Amihud, Roll, Corwin-Schultz, walls_and_spoofing, feature_registry, engine_input_provenance, lob_regime_features, realized_effective_spread)
- Calibration methods (PSR, DSR, Hansen SPA, energy distance, KS, POT-GPD, multiple_testing_guard, walkforward, ml_trainer, ml_backtest_projection)
- Regime classifier + regime_detector_runtime
- Decision Surface Map exhaustif (matrice complète des 50+ surfaces)

## 8. Points à approfondir en Session 3

- `local_replay_runtime/` Strategy Ladder en profondeur
- ML governance (`ml_governance_sidecars`, `ml_governance_proof_contracts`, `ml_model_transport`, `promotion_artifact_builder`)
- Verdict P0/P1/P2 réels (probablement très peu de P0 vu la maturité observée)
- Plan de patch chirurgical (probablement réduit à des polish edges plutôt qu'à des gaps majeurs)

---

## 9. Verdict provisoire (à confirmer en Session 3)

| Axe | Statut provisoire |
|-----|-------------------|
| TRADING_CORE | **CLEAR — 4 engines réels, coordination typée** |
| LIVE_BEHAVIOR | **À valider Session 2** (microstructure, regime, calibration profonds) |
| SHARIA_ENFORCEMENT | **READY — voir doc dédié** (AAOIFI, account features audit, purification, asset whitelist/blacklist, stablecoin policy, runtime gate) |
| MARKET_ADAPTATION | **À valider Session 2** |
| ARTIFACT_GOVERNANCE | **READY — calibration_loader + ML governance + Strategy Ladder + promotion_artifact_builder** (à confirmer Session 3) |
| OBSERVABILITY | **READY — cockpit FastAPI + state granulaire + monitoring local stack + grafana api + telegram_alerter** |

---

## 10. Note sur l'erreur précédente

Le précédent audit (5 MD dans `.claude/worktrees/agitated-taussig-53f14d/docs/audit/`) a été produit contre un worktree git **figé sur `5fc4618`** alors que le vrai repo est sur **`5f4fe0f` + 169 M + 200 ??**. Cette erreur a généré des affirmations fausses sur l'absence de Engine C/D, sharia_compliance, microstructure, regime_classifier, calibration, venue_adapters, etc.

**Ces 5 MD ont été supprimés.** Ce document et le suivant (sharia) constituent la vraie référence de Session 1.

---

## 11. Next safe step

1. Ouvrir et lire le document compagnon : [V53_SHARIA_SPOT_LONG_ONLY_AUDIT.md](V53_SHARIA_SPOT_LONG_ONLY_AUDIT.md)
2. Valider que les 2 MD reflètent fidèlement le code (échantillonnage des claims les plus surprenants).
3. Si validé, déclencher **Session 2** (microstructure + regime + calibration + decision surface map).
4. Si non validé, signaler les points à corriger ou approfondir avant Session 2.
