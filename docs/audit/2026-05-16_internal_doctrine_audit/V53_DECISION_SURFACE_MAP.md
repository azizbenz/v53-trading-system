# V5.3 — Decision Surface Map (vrai repo)

- **Date** : 2026-05-16
- **Repo réel** : `E:\claude  v5.3\v53_trading_system\`
- **Branche / commit** : `codex/full-shadow-abcd-migration-20260403` @ `5f4fe0f` + état de travail
- **Couvre** : Livrable 2 (matrice complète des surfaces qui peuvent changer une décision de trading)

Légende :
- **HARD_BLOCK** : refus binaire, jamais d'override (ou override doctrinal explicite)
- **SOFT_FILTER** : pénalité de score / size reduction
- **SCORING** : transformation/agrégation de score
- **RISK** : verdict APPROVED/REDUCED/HARD_BLOCKED
- **EXECUTION** : guard d'exécution avant venue
- **OBSERVABILITY** : enregistrement, n'altère pas la décision
- **GOVERNANCE** : gate (Shadow/Micro-live/Live)

---

## 1. Matrice exhaustive (groupée par couche)

### A. DATA BACKBONE

| # | Surface | Module / file | Type | reason_code | Test |
|---|---------|----------------|------|-------------|------|
| 1 | Data freshness hard | `data_backbone/freshness_checker/stale_hard_guard.py` | HARD_BLOCK | `data_stale` / équivalent | `test_data_backbone/test_freshness_checker.py` |
| 2 | Data freshness soft (penalty) | `data_backbone/freshness_checker/stale_penalty_builder.py` | SOFT_FILTER | — | présent |
| 3 | Event normalizer — invalid msg | `data_backbone/event_normalizer/invalid_message_guard.py` | HARD_BLOCK | malformed reject | `test_event_normalizer.py` |
| 4 | Pair health suspension | `data_backbone/pair_health_scorer/suspension_decider.py` | HARD_BLOCK | `pair_suspended` | `test_pair_health_scorer.py` |
| 5 | Pair health score (penalty) | `data_backbone/pair_health_scorer/quality_aggregator.py` | SOFT_FILTER | — | présent |
| 6 | Consistency — gap detected | `data_backbone/consistency_checker/gap_detector.py` | OBSERVABILITY + alert | gap event | `test_consistency_checker.py` |
| 7 | Consistency — duplicate detected | `data_backbone/consistency_checker/duplicate_detector.py` | OBSERVABILITY | duplicate event | présent |
| 8 | Consistency — sequence break | `data_backbone/consistency_checker/sequence_checker.py` | OBSERVABILITY | sequence event | présent |
| 9 | Consistency — contradiction | `data_backbone/consistency_checker/contradiction_checker.py` | OBSERVABILITY | contradiction event | présent |
| 10 | Internal router backpressure | `data_backbone/internal_router/backpressure_guard.py` | SOFT_FILTER / DROP | backpressure event | `test_internal_router.py` |
| 11 | REST rate limit guard | `data_backbone/rest_bootstrap/rate_limit_guard.py` | HARD_BLOCK / throttle | venue rate breach | `test_rest_bootstrap.py` |
| 12 | WebSocket connection / reconnect | `data_backbone/websocket_gateway/connection_manager.py`, `reconnect_controller.py`, `heartbeat_monitor.py` | EXECUTION (control) | reconnection events | `test_websocket_gateway.py` |

### B. MICROSTRUCTURE (data_backbone/microstructure)

| # | Surface | Module | Type | reason_code | Test |
|---|---------|--------|------|-------------|------|
| 13 | Order Flow Imbalance | `order_flow_imbalance.py` | OBSERVABILITY (input to engines via provenance) | feature snapshot reason codes | `test_order_flow_imbalance.py` |
| 14 | VPIN | `vpin.py` | OBSERVABILITY (toxicity) | feature snapshot | (probable test) |
| 15 | Kyle's lambda | `kyle_lambda.py` | OBSERVABILITY | feature snapshot | `test_kyle_lambda.py` |
| 16 | Realized kernel vol | `realized_kernel_vol.py` | OBSERVABILITY | feature snapshot | (présent) |
| 17 | Queue pressure | `queue_pressure.py` | OBSERVABILITY (input to engine_d provenance) | feature snapshot | `test_queue_pressure.py` |
| 18 | Walls and spoofing | `walls_and_spoofing.py` | OBSERVABILITY + reason codes (`_reason_codes` line 592) | spoofing/wall reason codes | `test_walls_and_spoofing.py` |
| 19 | Hawkes intensity | `hawkes_intensity.py` | OBSERVABILITY | feature snapshot | (présent) |
| 20 | PIN | `pin.py` | OBSERVABILITY | feature snapshot | (présent) |
| 21 | Amihud / Roll / Corwin-Schultz illiquidity | `amihud_illiquidity.py`, `roll_spread.py`, `corwin_schultz_spread.py` | OBSERVABILITY | feature snapshots | (présent) |
| 22 | Spread dynamics / realized effective spread | `spread_dynamics.py`, `realized_effective_spread.py` | OBSERVABILITY (input to scoring/cost) | — | (présent) |
| 23 | LOB regime features | `lob_regime_features.py` | OBSERVABILITY | feature snapshot V1/V2 | (présent) |
| 24 | Feature registry promotion gate | `feature_registry.py` | GOVERNANCE | promotion state transitions | `test_feature_registry.py` |
| 25 | Engine input provenance | `engine_input_provenance.py` | OBSERVABILITY (audit trail) | typed provenance | `test_engine_input_provenance.py` |

> Les indicateurs de microstructure agissent **principalement comme features consommées par les engines** via `engine_*_microstructure_provenance` et `compose_engine_*_input_payload`. Le branchement direct en hard-block (walls_and_spoofing, vpin) est à confirmer en Session 3.

### C. ENGINES (A / B / C / D)

#### Engine A — initial detection (long-only)
| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 26 | Long-only guard (spot-halal) | `engines/engine_a/engine_a_runner.py:145` | HARD_BLOCK local | `NoTradeReason.NON_LONG_DIRECTION` |
| 27 | Structure detection | `engines/engine_a/structure_detector_a.py` | HARD_BLOCK | `STRUCTURE_UNFAVORABLE` |
| 28 | Context validation | `engines/engine_a/context_validator_a.py` | HARD_BLOCK | `CONTEXT_FATAL` |
| 29 | Cost feasibility | `engines/engine_a/cost_feasibility_a.py` | HARD_BLOCK | `COST_INFEASIBLE` |
| 30 | Conviction | `engines/engine_a/conviction_builder_a.py` | HARD_BLOCK | `CONVICTION_NONE` |
| 31 | Invalidation mapping | `engines/engine_a/invalidation_mapper_a.py` | EXECUTION (stop level) | — |
| 32 | Pre-entry confirmation hook | `protocols/engine_a_pre_entry_confirmation_bridge.py` | GOVERNANCE | hook reason codes |

#### Engine B — mean reversion (long-only on dips)
| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 33 | Long-only guard (z > 0 → no trade) | `engines/engine_b/engine_b_runner.py:201` | HARD_BLOCK local | `NoTradeReasonB.NON_LONG_DIRECTION` |
| 34 | Local mean estimator | `engines/engine_b/local_mean_estimator_b.py` | DATA TRANSFORM | `INVALID_DISPERSION` |
| 35 | Excess detector (z ≥ 1.5) | `engines/engine_b/excess_detector_b.py` | HARD_BLOCK | `NO_EXCESS` |
| 36 | Anti-breakout filter | `engines/engine_b/anti_breakout_filter_b.py` | HARD_BLOCK | `BREAKOUT_BLOCKED` |
| 37 | Cost feasibility | `engines/engine_b/cost_feasibility_b.py` | HARD_BLOCK | `COST_INFEASIBLE` |
| 38 | Conviction | `engines/engine_b/conviction_builder_b.py` | HARD_BLOCK | `CONVICTION_NONE` |
| 39 | Sweep validation hook | `protocols/engine_b_sweep_validation_bridge.py` | GOVERNANCE | hook reason codes |

#### Engine C — breakout continuation
| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 40 | Input guards | `engines/engine_c/engine_c_runner_support.py:461` `evaluate_engine_c_input_guards` | HARD_BLOCK | input reasons codes |
| 41 | Breakout stage | `engines/engine_c/engine_c_runner.py:376` `_evaluate_breakout_stage` | HARD_BLOCK | breakout reasons (`NoTradeReasonC`) |
| 42 | Continuation stage | `engines/engine_c/engine_c_runner.py:448` `_evaluate_continuation_stage` | HARD_BLOCK | continuation reasons |
| 43 | Fake breakout stage | `engines/engine_c/engine_c_runner.py:506` `_evaluate_fake_breakout_stage` | HARD_BLOCK | `compute_fake_breakout_risk` reasons |
| 44 | Cost stage | `engines/engine_c/engine_c_runner.py:562` `_evaluate_cost_stage` | HARD_BLOCK | `CostReasonCodeC` |
| 45 | Conviction stage | `engines/engine_c/engine_c_runner.py:625` `_evaluate_conviction_stage` | HARD_BLOCK | conviction reasons |
| 46 | Duplication policy | `engines/engine_c/engine_c_runner_support.py:683` `evaluate_engine_c_duplication_policy` | HARD_BLOCK | local duplication reason codes |
| 47 | Void validation hook | `engines/engine_c/engine_c_runtime.py:120` `EngineCVoidValidationHook` ↔ `protocols/engine_c_void_validation_bridge.py` | GOVERNANCE | hook reason codes |

#### Engine D — re-entry / second chance
| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 48 | Guard stage | `engines/engine_d/engine_d_runner.py:135` `_evaluate_guard_stage` | HARD_BLOCK | guard reasons (`NoTradeReasonD`) |
| 49 | First episode required | `engines/engine_d/first_episode_resolver_d.py` | HARD_BLOCK | `hard_block.d_no_historical_linkage` |
| 50 | Historical linkage guard | `engines/engine_d/historical_linkage_guard_d.py` | HARD_BLOCK | linkage reasons |
| 51 | Anti-revenge (consecutive stops) | `engines/engine_d/consecutive_stop_counter_d.py` + runner:239 `_evaluate_anti_revenge_stage` | HARD_BLOCK | `hard_block.d_consecutive_stops_reset_required` |
| 52 | History stage | `engines/engine_d/engine_d_runner.py:269` `_evaluate_history_stage` | HARD_BLOCK | history reasons |
| 53 | Reformation stage | `engines/engine_d/engine_d_runner.py:308` `_evaluate_reformation_stage` | HARD_BLOCK | reformation reasons |
| 54 | Marginal value floor | `engines/engine_d/marginal_value_estimator_d.py` + runner:376 `_evaluate_marginal_value_stage` | HARD_BLOCK | marginal value reasons |
| 55 | Cost stage | `engines/engine_d/cost_feasibility_d.py` | HARD_BLOCK | `CostReasonCodeD` |
| 56 | Re-entry validation hook | `engines/engine_d/engine_d_runtime.py:119` `EngineDReentryValidationHook` ↔ `protocols/engine_d_reentry_validation_bridge.py` | GOVERNANCE | hook reason codes |
| 57 | Circuit breaker blocked result | `engines/engine_d/engine_d_runtime_result_builders.py:322` `_build_circuit_breaker_blocked_result` | HARD_BLOCK | circuit_breaker reasons |
| 58 | Engine state snapshot | `engines/engine_d/engine_state_snapshot_d.py` | OBSERVABILITY (persist) | — |

#### Coordination (cross-engine)
| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 59 | R-AC-1 : A holding → C blocked | `protocols/engine_coordination_rules.py:42-48` | HARD_BLOCK | `hard_block.ac_mutual_exclusion.a_holding` |
| 60 | R-AC-2 : A recent fire → C blocked | `protocols/engine_coordination_rules.py:50-56` | HARD_BLOCK | `hard_block.ac_recent_fire` |
| 61 | R-D-1 : D no linkage | `protocols/engine_coordination_rules.py:101-118` | HARD_BLOCK | `hard_block.d_no_historical_linkage` |
| 62 | R-D-2 : D consecutive stops | `protocols/engine_coordination_rules.py:122-132` | HARD_BLOCK | `hard_block.d_consecutive_stops_reset_required` |
| 63 | R-D-3 : D failsafe override | `protocols/engine_coordination_rules.py:135-146` | PERMIT (size_reduced) | `coordination.d_failsafe_override` |

### D. SCORING BACKBONE

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 64 | Raw score builder | `scoring_backbone/raw_score_builder/` | SCORING | — |
| 65 | Hard block gate central | `scoring_backbone/hard_block_gate/` (blocker_registry, blocker_evaluator, blocker_decision_builder, blocker_reporter, blocker_reason_encoder) | HARD_BLOCK | `BlockReason` enum (14 valeurs) |
| 66 | Penalty aggregator — score penalties | `scoring_backbone/penalty_aggregator/score_penalty_builder.py` | SOFT_FILTER | penalty IDs |
| 67 | Penalty aggregator — size penalties | `scoring_backbone/penalty_aggregator/size_penalty_builder.py` | SOFT_FILTER (size multiplier) | size penalty IDs |
| 68 | Penalty cap guard | `scoring_backbone/penalty_aggregator/penalty_cap_guard.py` | SCORING (cap) | — |
| 69 | Forecast normalizer (Carver) | `scoring_backbone/forecast_normalizer.py` | SCORING TRANSFORM | clipping events |
| 70 | Break-even filter | `scoring_backbone/break_even_filter.py` | HARD_BLOCK | `COST_MODEL_INCOMPLETE`, `BREAK_EVEN_NOT_CLEARED`, `CE_BELOW_MINIMUM`, `EV_NET_BELOW_FLOOR` |
| 71 | EV_net floor | `scoring_backbone/ev_net_floor_thresholds.py` | HARD_BLOCK (via break-even filter) | `EV_NET_BELOW_FLOOR` |
| 72 | Fee-aware edge gate | `scoring_backbone/fee_aware_edge_gate.py` | HARD_BLOCK | edge gate codes |
| 73 | Thresholds per engine (cost / breakout / excess / invalidation / continuation / coordination / first_episode) | `scoring_backbone/engine_*_thresholds.py` (10 modules) | SCORING (typed thresholds) | — |
| 74 | Ranking router — candidate pool | `scoring_backbone/ranking_router/candidate_pool_builder.py` | SCORING | — |
| 75 | Ranking router — ranking score builder | `scoring_backbone/ranking_router/ranking_score_builder.py` | SCORING | — |
| 76 | Ranking router — selection resolver | `scoring_backbone/ranking_router/selection_resolver.py` | HARD_BLOCK (selection) | `REJECTED_RANKING`, `REJECTED_PORTFOLIO` |
| 77 | Ranking router — portfolio compatibility | `scoring_backbone/ranking_router/portfolio_compatibility_checker.py` | HARD_BLOCK | portfolio compat reasons |

### E. PORTFOLIO

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 78 | Candidate pool | `portfolio_minimal/opportunity_selector/candidate_pool_builder.py` | SCORING | — |
| 79 | Correlation conflict checker | `portfolio_minimal/opportunity_selector/correlation_conflict_checker.py` | HARD_BLOCK | correlation conflict codes |
| 80 | Comparative ranker | `portfolio_minimal/opportunity_selector/comparative_ranker.py` | SCORING | — |
| 81 | Selection resolver | `portfolio_minimal/opportunity_selector/selection_resolver.py` | HARD_BLOCK (selection) | `PortfolioAction` enum |
| 82 | Base size builder | `portfolio_minimal/allocation_router/base_size_builder.py` | SCORING | — |
| 83 | Score size mapper | `portfolio_minimal/allocation_router/score_size_mapper.py` | SCORING (multiplier) | — |
| 84 | Portfolio cap applier | `portfolio_minimal/allocation_router/portfolio_cap_applier.py` | RISK / cap | cap codes |
| 85 | Capital viability | `portfolio_minimal/allocation_router/capital_viability.py` | HARD_BLOCK | capital viability reason |
| 86 | Phantom trade guard | `portfolio_minimal/allocation_router/phantom_trade_guard.py` | HARD_BLOCK | phantom reasons |

### F. RISK BACKBONE

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 87 | Gross exposure cap | `risk_backbone/exposure_budgeter/gross_cap_guard.py` | RISK | gross cap codes |
| 88 | Position cap | `risk_backbone/exposure_budgeter/position_cap_*` | RISK | position cap codes |
| 89 | Loss cap | `risk_backbone/loss_budgeter/loss_cap_guard.py` | RISK | loss cap codes |
| 90 | Drawdown guard (warning/observe) | `risk_backbone/loss_budgeter/drawdown_guard.py` | RISK | drawdown verdict codes |
| 91 | Loss reporter | `risk_backbone/loss_budgeter/loss_reporter.py` | OBSERVABILITY (refusal log) | — |
| 92 | Aggregate loss budgeter | `risk_backbone/loss_budgeter/aggregate_loss_budgeter.py` | RISK | aggregate codes |
| 93 | Projected loss checker | `risk_backbone/loss_budgeter/projected_loss_checker.py` | RISK | projected codes |
| 94 | Position loss estimator | `risk_backbone/loss_budgeter/position_loss_estimator.py` | SCORING | — |
| 95 | BTC beta cap | `risk_backbone/btc_factor_guard/beta_cap_guard.py` | RISK | beta cap codes |
| 96 | Projected beta checker | `risk_backbone/btc_factor_guard/projected_beta_checker.py` | RISK | projected beta |
| 97 | Cluster/correlation cap | `risk_backbone/correlation_cluster_guard/cluster_cap_guard.py` | RISK | cluster cap codes |
| 98 | Emergency kill switch (auto/manual) | `risk_backbone/emergency_kill_switch/circuit_breaker.py` | HARD_BLOCK | kill switch active |
| 99 | Risk runtime explainability | `risk_backbone/risk_runtime_explainability.py` | OBSERVABILITY | explainability records |

### G. EXECUTION BACKBONE

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 100 | Sharia gate (pre-submit) | `sharia_compliance/sharia_runtime.py` + invocation depuis `execution_runtime` / `gatekeeper` | HARD_BLOCK | 12 reason codes sharia (SHORT_FORBIDDEN, NON_SPOT_FORBIDDEN, LEVERAGE_FORBIDDEN, MARGIN_FORBIDDEN, PAIR_BLACKLISTED, ASSET_BLACKLISTED, PAIR_NOT_WHITELISTED, QUOTE_ASSET_FORBIDDEN, PAIR_SCREENING_*) + 3 AAOIFI codes |
| 101 | Order decider — order type selector | `execution_backbone/order_decider/order_type_selector.py` | EXECUTION | order type / no_trade |
| 102 | Order decider — execution guard | `execution_backbone/order_decider/execution_guard.py` | HARD_BLOCK | `pair_suspended`, `pair_health_low`, `risk_budget_exhausted`, `infrastructure_down`, `stale_data`, `cost_too_high` |
| 103 | Order decider — timeout policy | `execution_backbone/order_decider/timeout_policy_selector.py` | EXECUTION (timeout) | timeout reasons |
| 104 | Order decider — intent builder | `execution_backbone/order_decider/intent_builder.py` | EXECUTION (build) | build errors |
| 105 | Order decider — decision reporter | `execution_backbone/order_decider/decision_reporter.py` | OBSERVABILITY | DecisionEvent |
| 106 | Gatekeeper | `execution_backbone/gatekeeper/gatekeeper.py` + support | HARD_BLOCK (final pre-venue gate) | gatekeeper reasons (incl. sharia) |
| 107 | Spread guard | `execution_backbone/spread_guard.py` | HARD_BLOCK | spread too wide |
| 108 | Rate limiter | `execution_backbone/rate_limiter.py` | HARD_BLOCK / throttle | rate limit |
| 109 | Emergency circuit breaker (exec) | `execution_backbone/emergency_circuit_breaker.py` | HARD_BLOCK | exec circuit codes |
| 110 | Slippage model | `execution_backbone/slippage_model.py` | SCORING (cost) | — |
| 111 | Venue constraints provider | `execution_backbone/venue_constraints_provider.py` | EXECUTION | constraint codes |
| 112 | Fee-aware edge gate (exec layer) | `execution_backbone/fee_aware_edge_gate.py` | HARD_BLOCK | edge gate codes |
| 113 | Execution routing | `execution_backbone/execution_routing_bridge.py`, `execution_routing_features.py` | EXECUTION | routing codes |
| 114 | Cost meter (ELW, adverse selection) | `execution_backbone/execution_cost_meter/` (cost_aggregator, elw_meter, adverse_selection_meter) | SCORING (cost) | — |
| 115 | Fill tracker | `execution_backbone/fill_tracker/` (order_state_tracker, fill_aggregator) | OBSERVABILITY + EXECUTION (timeout cancel) | — |
| 116 | Reconciliation divergence | `execution_backbone/reconciliation_layer/divergence_classifier.py`, `position_reconciler.py`, `recovery_trigger.py` | EXECUTION (severity) | INFO / WARNING / BLOCKING / CRITICAL |

### H. ML / BUILD-14 ENABLERS (`complete_enablers/`)

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 117 | ML confidence enabler | `complete_enablers/ml_confidence_enabler.py` | SOFT_FILTER (post-Shadow) | confidence codes |
| 118 | ML fusion | `complete_enablers/ml_fusion.py` | SCORING (fusion) | — |
| 119 | ML model promotion gate | `complete_enablers/ml_model_promotion_gate.py` | GOVERNANCE | promotion codes |
| 120 | ML runtime artifact loader | `complete_enablers/ml_runtime_artifact_loader.py` | GOVERNANCE | artifact loader codes |
| 121 | ML scoring soft penalty hook | `complete_enablers/ml_scoring_soft_penalty_hook.py` | SOFT_FILTER | soft penalty codes |
| 122 | Market toxicity snapshot | `complete_enablers/market_toxicity_snapshot.py` | SOFT_FILTER (post-Shadow) | toxicity severity |
| 123 | Execution fragility score | `complete_enablers/execution_fragility_score.py` | SOFT_FILTER (post-Shadow) | fragility severity |
| 124 | Limited influence governance | `complete_enablers/limited_influence.py` | GOVERNANCE | influence action codes |
| 125 | Order book imbalance | `complete_enablers/order_book_imbalance.py` | SCORING | — |
| 126 | LOB deep filter VWA | `complete_enablers/lob_deep_filter_vwa.py` | SOFT_FILTER | — |
| 127 | Micro edge entry timing layer | `complete_enablers/micro_edge_entry_timing_layer.py` | SOFT_FILTER | timing codes |
| 128 | Micro edge exit governor | `complete_enablers/micro_edge_exit_governor.py` | EXECUTION (exit) | exit codes |
| 129 | False breakout model | `complete_enablers/false_breakout_model.py` | SOFT_FILTER | false breakout codes |
| 130 | Hurst regime classifier | `complete_enablers/hurst_regime_classifier.py` | OBSERVABILITY (regime input) | Hurst exponent state |
| 131 | Regime detector runtime | `complete_enablers/regime_detector_runtime.py` + `regime_detector_runtime_loader.py` | OBSERVABILITY (regime ML) | regime codes |
| 132 | Competition monitor | `complete_enablers/competition_monitor.py` | OBSERVABILITY | competition codes |
| 133 | Supplementary refs governance | `complete_enablers/supplementary_refs_governance.py` | GOVERNANCE | refs codes |

### I. REGIME CLASSIFIER

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 134 | Regime lite — extreme detection | `regime_classifier/regime_lite.py` `_derive_candidate_state` | HARD_BLOCK (entries_blocked) | `RG_EXTREME_*` (4 codes) |
| 135 | Regime lite — stressed detection | idem | SOFT_FILTER | `RG_STRESSED_*` (3 codes) |
| 136 | Regime lite — calm baseline | idem | — | `RG_CALM_BASELINE` |
| 137 | Regime lite — transition guards | regime_lite.py:_step_towards + classify_regime_lite | SCORING (transition) | `RG_NO_STATE_SKIP`, `RG_ESCALATE_TO_STRESSED_FIRST`, `RG_DIRECT_EXTREME_EVENT`, `RG_DOWNGRADE_HYSTERESIS_ACTIVE`, `RG_STEP_DOWN_ONE_STATE` |
| 138 | Regime lite — extreme cooldown | regime_lite.py:317-326 | HARD_BLOCK | `RG_EXTREME_COOLDOWN_ACTIVE` |

### J. PROTOCOLS / GATES

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 139 | Shadow runtime gate | `protocols/shadow_runtime.py` + `shadow_day_counter.py` | GOVERNANCE | shadow input errors |
| 140 | Shadow 30j gate | `protocols/shadow_runtime.py:check_shadow_30j_gate` | GOVERNANCE | shadow 30j |
| 141 | Micro-live runtime gate | `protocols/micro_live_runtime.py` | GOVERNANCE | `MicroLiveInputError` |
| 142 | Live-Light runtime gate | `protocols/live_light_runtime.py` | GOVERNANCE | `LiveLightInputError` |
| 143 | Live-Complete runtime gate | `protocols/live_complete_runtime.py` | GOVERNANCE | live complete errors |
| 144 | Promotion gates | `protocols/promotion_gates.py` (`check_light_to_micro_live`, `check_complete_to_live`) | GOVERNANCE | `PromotionGateResult.passed=False` |
| 145 | Engine A/B/C/D hooks | `protocols/engine_{a,b,c,d}_hooks.py` | GOVERNANCE | hook reasons |
| 146 | Engine A/B/C/D bridges (4) | `protocols/engine_{a_pre_entry_confirmation,b_sweep_validation,c_void_validation,d_reentry_validation}_bridge.py` | GOVERNANCE | bridge reasons |
| 147 | Engine coordination rules | `protocols/engine_coordination_rules.py` | HARD_BLOCK / PERMIT | 5 codes (voir §59-63) |
| 148 | Closed episode journal | `protocols/closed_episode_journal.py` | OBSERVABILITY | episode events |
| 149 | Compiled artifact registry store | `protocols/compiled_artifact_registry_store.py` | GOVERNANCE | registry events |
| 150 | Compiled hook plan loader | `protocols/compiled_hook_plan_loader.py` | GOVERNANCE | plan events |
| 151 | Dashboard command queue | `protocols/dashboard_command_queue.py` (+ execution support, result support) | OBSERVABILITY + GOVERNANCE | command codes |
| 152 | Shadow VPS service | `protocols/shadow_vps_service.py` (+ execution_runtime_bootstrap/dashboard/projection_bridge) | GOVERNANCE | service codes |

### K. OBSERVABILITY (MONITORING)

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 153 | DTR (Decision-Trade Record) | `meta_minimal/dtr_core/dtr_record_builder.py` | OBSERVABILITY | hard_block_reasons |
| 154 | CRA monitor | `meta_minimal/cra_monitor/` | OBSERVABILITY (cost reconciliation) | CRA alerts |
| 155 | Break-even dashboard | `meta_minimal/break_even_dashboard/` | OBSERVABILITY | BE drift |
| 156 | Edge tracker prudent | `meta_minimal/edge_tracker_prudent_minimal/` | OBSERVABILITY | edge classification |
| 157 | Meta learning post-trade | `meta_learning/post_trade_diagnostic_engine.py`, `mistake_classifier.py`, `hypothesis_registry.py`, `replay_bundle_builder.py`, `review_orchestrator.py`, `review_governance.py`, `review_queue.py`, `review_resolution.py`, `improvement_candidate_builder.py`, `lifecycle_registry.py` | OBSERVABILITY + GOVERNANCE | mistake codes, hypothesis IDs |
| 158 | Metrics collector (Prometheus-style) | `monitoring/metrics_collector.py`, `observability.py` (+ `observability_support.py`) | OBSERVABILITY | metrics |
| 159 | Alert manager | `monitoring/alert_manager.py` | OBSERVABILITY | alert codes |
| 160 | Dashboards (technical / health / complete / light) | `monitoring/technical_dashboard_backend.py`, `health_dashboard_backend.py`, `monitoring_runtime.py`, `local_observability_stack.py`, `local_grafana_api.py` | OBSERVABILITY | — |
| 161 | Replay governance projection | `monitoring/replay_governance_projection.py` + `protocols/replay_governance_projection.py` | OBSERVABILITY | replay events |
| 162 | Challenger evidence alerts | `monitoring/challenger_evidence_alerts.py` | OBSERVABILITY | challenger codes |
| 163 | Artifact visibility | `monitoring/artifact_visibility.py` | OBSERVABILITY | artifact events |
| 164 | Cockpit FastAPI server | `cockpit/server.py` + 30+ `state_*` modules | OBSERVABILITY + OPERATOR | — |
| 165 | Logging config | `monitoring/logging_config.py` | OBSERVABILITY | — |

### L. SHARIA COMPLIANCE (détail)

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 166 | Sharia trade type guard | `sharia_compliance/trade_type_guard.py` | HARD_BLOCK | 12 reason codes (voir §A du MD2 sharia) |
| 167 | AAOIFI pair screening | `sharia_compliance/pair_screening.py` | HARD_BLOCK | `AAOIFI_DEBT_RATIO_EXCEEDED`, `AAOIFI_CASH_RATIO_EXCEEDED`, `AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED` |
| 168 | Pair screening audit (registre traded vs screening) | `sharia_compliance/pair_screening_audit.py` + `pair_screening_registry.py` | OBSERVABILITY + alert | audit finding codes |
| 169 | Account features audit (Binance endpoints + balances) | `sharia_compliance/account_features_audit.py` | OBSERVABILITY + alert (P1 : promouvoir hard-block ?) | `FORBIDDEN_ACCOUNT_FEATURE_ENDPOINT`, `FORBIDDEN_ACCOUNT_FEATURE_BALANCE` |
| 170 | Stablecoin policy | `sharia_compliance/stablecoin_policy.py` | HARD_BLOCK (via trade_type_guard) | `QUOTE_ASSET_FORBIDDEN` |
| 171 | Asset whitelist | `sharia_compliance/asset_whitelist.py` | HARD_BLOCK (via trade_type_guard) | `PAIR_NOT_WHITELISTED` |
| 172 | Asset blacklist | `sharia_compliance/asset_blacklist.py` | HARD_BLOCK (via trade_type_guard) | `PAIR_BLACKLISTED`, `ASSET_BLACKLISTED` |
| 173 | Policy audit logger | `sharia_compliance/policy_audit_logger.py` | OBSERVABILITY (append-only) | — |
| 174 | Sharia alerts | `sharia_compliance/sharia_alerts.py` | OBSERVABILITY → `alerting/telegram_alerter.py` | — |
| 175 | Purification calculator | `sharia_compliance/purification_calculator.py` | GOVERNANCE (compute purification amount) | purification codes |

### M. CALIBRATION (statistical)

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 176 | PSR | `calibration_methods/psr.py` | SCORING (audit) | — |
| 177 | DSR / Harvey-Liu-Zhu | `calibration_methods/multiple_testing_guard.py` | SCORING (audit + deflation) | — |
| 178 | Holm-Bonferroni | `calibration_methods/multiple_testing.py` | SCORING (audit) | — |
| 179 | Hansen SPA | `calibration_methods/hansen_spa.py` | SCORING (audit) | — |
| 180 | Energy distance | `calibration_methods/energy_distance.py` | SCORING (audit drift) | — |
| 181 | KS test | `calibration_methods/ks_test.py` | SCORING (audit drift) | — |
| 182 | POT-GPD tail risk | `calibration_methods/pot_gpd.py` | SCORING (tail VaR) | — |
| 183 | Mann-Kendall trend | `calibration_methods/mann_kendall.py` | SCORING (trend) | — |
| 184 | Stationarity (ADF+KPSS) | `calibration_methods/stationarity.py` | SCORING (validity) | — |
| 185 | Walk-forward purged | `calibration_methods/walkforward.py` | GOVERNANCE (training plan) | — |
| 186 | LightGBM trainer | `calibration_methods/ml_trainer.py` | GOVERNANCE (training) | — |
| 187 | Hard cap floor | `calibration_methods/hard_cap_floor.py` | HARD_BLOCK | `HumanHardCapPolicyError` |
| 188 | Walls and spoofing calibration | `calibration_methods/walls_and_spoofing_calibration.py` | GOVERNANCE | — |
| 189 | Regime detector feature calibration | `calibration_methods/regime_detector_feature_calibration.py` | GOVERNANCE | — |
| 190 | Bootstrap | `calibration_methods/bootstrap.py` | SCORING (audit) | — |
| 191 | Execution calibration | `calibration_methods/execution.py` | GOVERNANCE | — |

### N. OPERATOR / UI

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 192 | Operator actions | `ui/operator_actions.py` | GOVERNANCE | operator codes |
| 193 | Complete dashboard control plane | `ui/complete_dashboard_control_plane.py` | GOVERNANCE | control codes |
| 194 | Cockpit operator workflows | `cockpit/action_support.py`, `state_*` modules | OBSERVABILITY + OPERATOR | — |
| 195 | Manual kill switch | `risk_backbone/emergency_kill_switch/circuit_breaker.py` + UI trigger | HARD_BLOCK | kill switch active |

### O. CONFIG / SECRETS / MANIFEST

| # | Surface | Module | Type | reason_code |
|---|---------|--------|------|-------------|
| 196 | Manifest registry | `manifest_registry/build_order_registry.py`, `dependency_registry.py`, `module_inventory.py`, `profile_registry.py`, `version_registry.py` | GOVERNANCE | manifest codes |
| 197 | Smoke bootstrap recovery | `smoke_bootstrap_recovery/state_sanity_checker.py`, `shadow_readiness.py`, `config_validator.py`, `smoke_models.py`, `smoke_reporter.py` | GOVERNANCE | sanity codes |
| 198 | Secrets manager | `secrets_manager/loader.py`, `sealer.py`, `cli.py`, `_dpapi*` | GOVERNANCE (security) | secrets errors |
| 199 | Contract test suite | `contract_test_suite/` | GOVERNANCE | contract failures |
| 200 | DAG validator | `dag_validator/layer_validator.py`, `cycle_detector.py`, `import_scanner.py`, `dependency_matcher.py` | GOVERNANCE | layer order / cycle |
| 201 | Calibration loader | `calibration_loader/loader.py`, `contracts.py` | GOVERNANCE | `CalibrationArtifactValidationError` |
| 202 | Backtest artifact import | `backtest_artifact_import/` | GOVERNANCE | import codes |

---

## 2. Synthèse comparée par couche

| Couche | Surfaces totales | HARD_BLOCK | SOFT_FILTER / SCORING | GOVERNANCE | OBSERVABILITY |
|--------|------------------|-----------|------------------------|------------|---------------|
| Data backbone | 12 | 5 | 2 | — | 5 |
| Microstructure | 13 | 0 | 0 | 1 (feature_registry) | 12 |
| Engine A | 7 | 5 | — | 1 | 1 |
| Engine B | 7 | 5 | — | 1 | 1 |
| Engine C | 8 | 7 | — | 1 | — |
| Engine D | 11 | 9 | — | 1 | 1 |
| Coordination cross-engine | 5 | 4 | — | 1 | — |
| Scoring backbone | 14 | 5 | 7 | — | 2 |
| Portfolio | 9 | 4 | 4 | — | 1 |
| Risk backbone | 13 | 1 | — | — | 1 (+ 11 RISK verdicts) |
| Execution backbone | 17 | 7 | 2 | — | 4 (+ 4 EXECUTION) |
| ML / Build-14 | 17 | 0 | 9 | 4 | 4 |
| Regime classifier | 5 | 2 | 1 | — | 2 |
| Protocols / gates | 14 | — | — | 14 | — |
| Monitoring | 13 | — | — | — | 13 |
| Sharia compliance | 10 | 7 | — | 1 | 2 |
| Calibration methods | 16 | 1 | 10 | 5 | — |
| Operator / UI | 4 | 1 | — | 3 | — |
| Config / secrets / manifest | 7 | — | — | 7 | — |
| **TOTAL** | **~202** | **~63 HARD_BLOCK** | **~35 SOFT/SCORING** | **~40 GOVERNANCE** | **~50 OBSERVABILITY** + **~15 RISK/EXECUTION verdicts** |

> Plus de **200 surfaces de décision distinctes**, dont **~63 hard blocks réels** typés avec reason codes hiérarchisés.

---

## 3. Comportement par cas de marché (Livrable 10)

| # | Cas | Comportement attendu | Comportement réel (code) | Surfaces déclenchées |
|---|-----|---------------------|---------------------------|----------------------|
| 1 | Marché calme | NO_TRADE sélectif | engines NO_TRADE si scores bas + `RG_CALM_BASELINE` | engines + regime |
| 2 | Tendance haussière propre | EMIT long Engine A | Engine A → EMIT `side=BUY` | engine A + scoring + risk + execution + sharia gate |
| 3 | Tendance baissière forte | NO_TRADE (jamais short) | engines → `NON_LONG_DIRECTION` + sharia gate `SHORT_FORBIDDEN` (double rempart) | engines + sharia |
| 4 | Chute BTC cascade | reduce / kill | beta_cap_guard + cluster_cap + drawdown + `RG_EXTREME_BTC_DROP_1H` + extreme cooldown | regime + risk |
| 5 | Range propre | Engine B emit on dips, A no-trade | engine B `z < -threshold` EMIT, engine A NO_TRADE | engines |
| 6 | Fake breakout | Engine B ne fade pas | `anti_breakout_filter_b` BLOCKED + engine C `_evaluate_fake_breakout_stage` | engines B + C |
| 7 | Breakout continuation | Engine C emit | engine C stages breakout + continuation + cost + conviction | engine C + coordination R-AC |
| 8 | Toxic flow spike | reduce / no_trade | `complete_enablers/market_toxicity_snapshot` + VPIN observation + Build-14 soft veto | microstructure + Build-14 |
| 9 | Book thin / spread large | no_trade | `spread_guard` + `order_decider/execution_guard.cost_too_high` | execution |
| 10 | Data stale | hard reject | `freshness_checker/stale_hard_guard` | data backbone |
| 11 | Exchange disconnect | reconnect + suspension | `connection_manager` + `reconnect_controller` + `suspension_decider` | data backbone |
| 12 | Régime EXTREME | reduce / no_trade | `regime_lite` `entries_blocked_until_ts` + `RG_EXTREME_COOLDOWN_ACTIVE` + Build-14 `limited_influence` budget × 0 | regime + Build-14 |
| 13 | Drawdown journalier | reduce / observe / reject | `drawdown_guard` + `aggregate_loss_budgeter` | risk |
| 14 | Corrélation > seuil | reject | `cluster_cap_guard` | risk |
| 15 | Signal long, sharia refuse | NO_TRADE | `ShariaRuntime.authorize_trade` → reject (12 reason codes possibles) | sharia |
| 16 | Signal bearish, spot long-only | NO_TRADE (jamais short) | engines `NON_LONG_DIRECTION` + sharia `SHORT_FORBIDDEN` | engines + sharia |
| 17 | Position ouverte + invalidation | exit/reduce | `invalidation_mapper_*` + execution_runtime exit path | engines + execution |
| 18 | Pas de position + signal bearish | NO_TRADE | NO_TRADE | engines |
| 19 | Re-entry après stop | Engine D second chance | engine D pipeline (5 stages) + R-D-1 first_episode + R-D-2 consecutive stops + R-D-3 failsafe override | engine D + coordination |
| 20 | ML high confidence + engine faible | Engine prime (ML soft) | `complete_enablers/ml_confidence_enabler` ne peut pas créer emit, seulement penalty | Build-14 soft only |
| 21 | Cost > expected_gain | NO_TRADE | `break_even_filter` `BREAK_EVEN_NOT_CLEARED` + `ev_net_floor` + cost_feasibility per engine | scoring + engines |
| 22 | Calibration artifact absent | refuse / mode dégradé | `CalibrationLoader` raise `CalibrationArtifactValidationError` consommée par regime_lite, sharia, ML | calibration loader |
| 23 | Signed artifact stale | refuse | (à confirmer : TTL sur calibration artifacts, dépend de `feature_threshold_manifest`, `governed_audit_evidence_index`) | governance |
| 24 | Manual kill switch | block all new + alert | `circuit_breaker` flag + `emergency_circuit_breaker` exec | risk + execution |
| 25 | Reconciliation divergence | block + alert | `divergence_classifier` INFO/WARNING/BLOCKING/CRITICAL + `recovery_trigger` | execution |
| 26 | Margin endpoint observed (Binance) | alert + audit | `account_features_audit` `FORBIDDEN_ACCOUNT_FEATURE_ENDPOINT` → `sharia_alerts.build_account_feature_audit_alerts` → telegram_alerter | sharia + alerting |
| 27 | AAOIFI pair fails screening | sharia hard block | `pair_screening.evaluate_pair_screening` `passed=False` + `trade_type_guard` `PAIR_SCREENING_FAILED` | sharia |
| 28 | Walls/spoofing pattern detected | observation + reason codes (à confirmer : hard block ?) | `walls_and_spoofing.evaluate_walls_and_spoofing` (`_reason_codes` line 592) | microstructure (P2 : promouvoir en hard-block ?) |
| 29 | High VPIN (toxic flow) | reduce / halt (à confirmer branchement) | `vpin.compute_vpin` + `market_toxicity_snapshot` Build-14 | microstructure + Build-14 |
| 30 | Hawkes intensity spike | observation | `hawkes_intensity.compute_hawkes_intensity` | microstructure (P2 : brancher en penalty ?) |
| 31 | ML model promotion failed | refuse | `ml_model_promotion_gate` | Build-14 governance |
| 32 | Engine A holding + C tries to fire | C blocked | R-AC-1 `hard_block.ac_mutual_exclusion.a_holding` | coordination |
| 33 | Engine A recent fire + C tries | C blocked | R-AC-2 `hard_block.ac_recent_fire` | coordination |
| 34 | Engine D without first episode | D blocked | R-D-1 `hard_block.d_no_historical_linkage` | coordination + engine D |
| 35 | Engine D after consecutive stops | D blocked until reset OR failsafe | R-D-2 + R-D-3 | coordination + engine D |
| 36 | Shadow gate not 30j | promotion refused | `shadow_runtime.check_shadow_30j_gate` + `promotion_gates` | protocols |
| 37 | Micro-live attempt before Shadow accepted | refuse | `micro_live_runtime.MicroLiveInputError` | protocols |
| 38 | Live-Light without Build-14 influence signal | refuse | `live_light_runtime.LiveLightInputError` | protocols |
| 39 | Regime hysteresis active during downgrade attempt | hold | `RG_DOWNGRADE_HYSTERESIS_ACTIVE` | regime |
| 40 | Sudden BTC drop > 5% in 1h | direct EXTREME jump | regime_lite sudden_event flag | regime |

---

## 4. Surfaces résiduelles à clarifier (Session 3)

| Question | Surface concernée | Statut actuel |
|----------|-------------------|----------------|
| Walls and spoofing → hard block ou observation ? | `microstructure/walls_and_spoofing` | reason codes émis, branchement scoring/execution à confirmer |
| VPIN → penalty / halt ou observation ? | `microstructure/vpin` | calcul produit `VpinRecord`, consommé par Build-14 toxicity (composite), pas de hard-block dédié |
| Hansen SPA — usage final | `calibration_methods/hansen_spa.py` | signature à confirmer |
| Calibration artifact TTL / staleness | `feature_threshold_manifest`, `governed_audit_evidence_index` | à confirmer |
| `account_features_audit` action si finding | currently OBSERVABILITY + alert | promouvoir en hard-block ? |
| Strategy Ladder pipeline ↔ live | `local_replay_runtime/strategy_ladder_*` (25+ modules) | gouvernance complète à mapper Session 3 |

---

## 5. Next safe step (vers Session 3)

1. Valider les 4 MD produits (Session 1 + 2).
2. Session 3 :
   - Strategy Ladder pipeline complet (gouvernance ML + promotion artifacts + replay execution)
   - Backtest artifact import bridge approfondi
   - ML governance proof contracts + ml_governance_sidecars + promotion_artifact_builder
   - Vérification TTL/staleness des calibration artifacts
   - Confirmation des branchements résiduels (walls, vpin, hawkes → scoring)
   - Verdict final P0/P1/P2 + plan de patch
   - Tests prioritaires à ajouter
