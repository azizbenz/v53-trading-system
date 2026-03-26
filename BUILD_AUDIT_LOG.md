# V5.3 Trading System — Build Audit Log

> **Document purpose**: Third-party audit reference.
> Each build lists every source file, every test file, merge-gate audit findings, patches applied, and final test counts.
> This document is the single source of truth for build closure status.

---

## Project Metadata

| Key | Value |
|-----|-------|
| Project | `v53-trading-system` |
| Version | `5.3.0` |
| Python | `>=3.12` (developed on 3.13.1) |
| Framework | Pydantic 2.x frozen models, StrEnum, sync-only |
| Test runner | pytest 8.x with `pythonpath = ["src"]` |
| Total tests | **956 passing** |
| Repository | `github.com/azizbenz/v53-trading-system` |

---

## Build-1 — Dependency Architecture

**Status**: MERGEABLE
**Tests**: 332

### Source Files

#### `interface_contracts/` (6 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `domain_types.py` | Base Pydantic types: `TimestampedModel`, `Pair`, `EngineId` |
| `market_event_contracts.py` | Market event data contracts |
| `decision_contracts.py` | Decision/signal contracts between modules |
| `error_contracts.py` | Error envelope contracts |
| `meta_contracts.py` | Meta/health contracts |

#### `manifest_registry/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `build_order_registry.py` | Build dependency graph (Build-1→2→3→...) |
| `dependency_registry.py` | Module-level dependency declarations |
| `module_inventory.py` | Full module inventory with layer assignment |
| `profile_registry.py` | Light (6 pairs) vs Complete (12 pairs) profiles |
| `version_registry.py` | Version tracking per module |

#### `contract_test_suite/` (7 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `contract_models.py` | Contract definition models |
| `schema_assertions.py` | Schema validation assertions |
| `contract_test_runner.py` | Contract test execution engine |
| `contract_reporter.py` | Contract test reporting |
| `compatibility_checker.py` | Cross-module compatibility checks |
| `negative_case_runner.py` | Negative/edge case contract tests |

#### `dag_validator/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `import_scanner.py` | Static import analysis |
| `cycle_detector.py` | Circular dependency detection |
| `dependency_matcher.py` | Declared vs actual dependency matching |
| `layer_validator.py` | Layer hierarchy enforcement |
| `report_builder.py` | DAG validation report generation |

#### `smoke_bootstrap_recovery/` (7 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `smoke_models.py` | Smoke test data models |
| `config_validator.py` | Configuration validation |
| `bootstrap_runner.py` | Bootstrap sequence runner |
| `recovery_runner.py` | Recovery sequence runner |
| `smoke_reporter.py` | Smoke test reporting |
| `state_sanity_checker.py` | State sanity checks |

### Test Files (332 tests)
| File | Tests |
|------|-------|
| `test_interface_contracts/test_all_contracts.py` | Domain types, market events, decisions, errors, meta |
| `test_manifest_registry/test_build_order.py` | Build dependency ordering |
| `test_manifest_registry/test_dependencies.py` | Module dependency declarations |
| `test_manifest_registry/test_inventory.py` | Module inventory completeness |
| `test_manifest_registry/test_profiles.py` | Light/Complete profile definitions |
| `test_manifest_registry/test_version_registry.py` | Version tracking |
| `test_contract_test_suite/test_schema_assertions.py` | Schema assertion logic |
| `test_contract_test_suite/test_runner_and_reporter.py` | Test runner + reporter |
| `test_contract_test_suite/test_compatibility.py` | Compatibility checks |
| `test_contract_test_suite/test_negative_runner.py` | Negative case runner |
| `test_contract_test_suite/test_real_contracts.py` | Real contract validation |
| `test_dag_validator/test_import_scanner.py` | Import scanning |
| `test_dag_validator/test_cycle_detector.py` | Cycle detection |
| `test_dag_validator/test_dependency_matcher.py` | Dependency matching |
| `test_dag_validator/test_layer_validator.py` | Layer validation |
| `test_dag_validator/test_report_and_pipeline.py` | Report + pipeline |
| `test_smoke_bootstrap_recovery/test_config_validator.py` | Config validation |
| `test_smoke_bootstrap_recovery/test_bootstrap_runner.py` | Bootstrap runner |
| `test_smoke_bootstrap_recovery/test_recovery_runner.py` | Recovery runner |
| `test_smoke_bootstrap_recovery/test_smoke_reporter.py` | Smoke reporter |
| `test_smoke_bootstrap_recovery/test_state_sanity.py` | State sanity |

### Audit Findings
- No blockers found at closure.

---

## Build-2 — Data Backbone

**Status**: MERGEABLE
**Tests**: 137

### Source Files

#### `data_backbone/websocket_gateway/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `connection_manager.py` | WebSocket connection lifecycle management |
| `heartbeat_monitor.py` | Heartbeat detection with late threshold |
| `raw_message_emitter.py` | Raw message emission to consumers |
| `reconnect_controller.py` | Reconnection logic with backoff |
| `subscription_manager.py` | Pair/stream subscription management |

#### `data_backbone/rest_bootstrap/` (4 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `snapshot_fetcher.py` | REST snapshot fetching |
| `rate_limit_guard.py` | Rate limit enforcement |
| `gap_fill_controller.py` | Gap detection and fill orchestration |
| `bootstrap_reporter.py` | Bootstrap event tracking, failure_rate metric |

#### `data_backbone/event_normalizer/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `schema_mapper.py` | `map_raw_to_event()`: EventType enum, NormalizedEvent subtypes (Trade/Depth/Kline/Heartbeat/Snapshot) |
| `timestamp_enricher.py` | `compute_drift()`, `enrich_timestamp()` with drift+latency |
| `message_classifier.py` | MessageClass enum, `classify_message()` with stream_type_hint priority |
| `invalid_message_guard.py` | RejectionReason enum, `validate_raw_message()` |
| `normalization_reporter.py` | NormalizationReporter, reject_rate = N_reject/N_raw |

#### `data_backbone/internal_router/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `consumer_registry.py` | ConsumerPriority (CRITICAL/HIGH/NORMAL/LOW), priority-sorted dispatch |
| `priority_dispatcher.py` | `dispatch_event()` with blocked_consumers support |
| `queue_manager.py` | Bounded deques, enqueue/dequeue/stats, utilization metric |
| `backpressure_guard.py` | `evaluate_backpressure()`: critical never dropped, normal/low DROP above threshold |
| `routing_reporter.py` | RoutingReporter with drop_rate |

#### `data_backbone/freshness_checker/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `last_update_tracker.py` | Per pair+stream timestamp tracking |
| `age_calculator.py` | `calculate_age()`: Δ_i = t_decision - t_last_update |
| `stale_penalty_builder.py` | `compute_stale_penalty()`: pen_stale(Δ) = λ·max(0, Δ - Δ_max) |
| `stale_hard_guard.py` | StaleVerdict (FRESH/DEGRADED/HARD_STALE), soft+hard thresholds |
| `freshness_reporter.py` | FreshnessReporter: max_age, by_pair verdicts |

#### `data_backbone/consistency_checker/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `sequence_checker.py` | Disorder event tracking per pair+stream |
| `gap_detector.py` | GapRate = N_gaps/N_expected |
| `duplicate_detector.py` | DupRate = N_dup/N_events |
| `contradiction_checker.py` | Timestamp reversal, bid/ask cross detection |
| `consistency_reporter.py` | `compute_consistency_score()`: 1 - (w1·Gaps + w2·Dup + w3·Disorder + w4·Contradictions) |

#### `data_backbone/pair_health_scorer/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `quality_aggregator.py` | `compute_health_score()`: H_j = weighted sum of freshness/consistency/latency/recovery |
| `suspension_decider.py` | `evaluate_suspension()`: health threshold, hard_stale, consistency_failed triggers |
| `recovery_evaluator.py` | `evaluate_recovery()`: hysteresis with required_consecutive healthy checks |
| `health_state_tracker.py` | PairHealthState (ACTIVE/DEGRADED/SUSPENDED/RECOVERING), explicit transitions |
| `health_reporter.py` | HealthReporter with HealthSummary aggregation |

### Test Files (137 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_data_backbone/test_websocket_gateway.py` | 22 | connection_manager, heartbeat, raw_emitter, reconnect, subscription |
| `test_data_backbone/test_rest_bootstrap.py` | 16 | snapshot_fetcher, rate_limit, gap_fill, bootstrap_reporter |
| `test_data_backbone/test_event_normalizer.py` | 22 | schema_mapper, timestamp_enricher, message_classifier, invalid_guard, reporter |
| `test_data_backbone/test_internal_router.py` | 17 | consumer_registry, priority_dispatch, queue_manager, backpressure, reporter |
| `test_data_backbone/test_freshness_checker.py` | 15 | last_update_tracker, age_calc, stale_penalty, stale_hard_guard, reporter |
| `test_data_backbone/test_consistency_checker.py` | 19 | sequence, gap, duplicate, contradiction, consistency_score |
| `test_data_backbone/test_pair_health_scorer.py` | 26 | quality_agg, suspension, recovery, state_tracker, health_reporter |

### Audit Findings & Patches
| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `connection_manager.py` | Unused imports (`TimestampedModel`, `Any`) | Removed unused imports |
| 2 | `test_websocket_gateway.py` | 12 test failures — tests assumed wrong API signatures | Rewrote 22 tests to match actual API: `cm.register_endpoint()`, `reg.subscribe("pair","stream","endpoint")`, `HeartbeatMonitor(heartbeat_interval_s=, late_threshold_s=)`, `hm.check_status()` |

---

## Build-3 — Execution Backbone

**Status**: MERGEABLE
**Tests**: 88

### Source Files

#### `execution_backbone/order_decider/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `intent_builder.py` | Build order intent from decision signal |
| `order_type_selector.py` | Select order type (LIMIT/MARKET) based on context |
| `execution_guard.py` | Pre-execution safety checks |
| `timeout_policy_selector.py` | Timeout policy based on order type/market conditions |
| `decision_reporter.py` | Order decision reporting |

#### `execution_backbone/fill_tracker/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `order_state_tracker.py` | OrderState lifecycle (PENDING→SENT→ACKED→PARTIALLY_FILLED→FILLED/CANCELLED/EXPIRED/REJECTED), weighted average fill price, TERMINAL_STATES |
| `fill_aggregator.py` | FillEvent model, per-order fill aggregation |
| `latency_meter.py` | Submit-to-ack, submit-to-first-fill, submit-to-full-fill, ack-to-first-fill latency |
| `order_terminal_state_resolver.py` | TerminalCategory: FULL_FILL, PARTIAL_FILL_CANCELLED, ZERO_FILL_CANCELLED, EXPIRED_WITH/NO_FILLS, REJECTED |
| `fill_reporter.py` | Fill statistics: fill rate, partial rate, expired rate |

#### `execution_backbone/execution_cost_meter/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `fee_meter.py` | `compute_fee()`, `estimate_fee()` |
| `elw_meter.py` | ELW_i = \|P_exec - Mid\|/Mid, implicit round-trip cost |
| `adverse_selection_meter.py` | AS_i(Δ) = sign(side)·(Mid_{t+Δ} - P_exec)/P_exec |
| `partial_fill_cost_meter.py` | Price variance + unfilled opportunity cost |
| `cost_aggregator.py` | c_i = f_i + c_impl + AS_i + PF_i, break-even calculation |

#### `execution_backbone/reconciliation_layer/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `order_reconciler.py` | LOCAL_ONLY/REMOTE_ONLY/STATE_MISMATCH divergence detection |
| `fill_reconciler.py` | Qty diff with tolerance |
| `position_reconciler.py` | PosDiff = \|Pos_local - Pos_remote\| |
| `divergence_classifier.py` | Severity: INFO/WARNING/BLOCKING/CRITICAL |
| `recovery_trigger.py` | RecoveryAction (NONE/SOFT_RESYNC/HARD_RESYNC/HALT_TRADING), Δ_recon staleness |

### Test Files (88 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_execution_backbone/test_order_decider.py` | 19 | intent_builder, order_type_selector, execution_guard, timeout_policy, reporter |
| `test_execution_backbone/test_fill_tracker.py` | 25 | order_state, fill_aggregator, latency_meter, terminal_resolver, fill_reporter |
| `test_execution_backbone/test_execution_cost_meter.py` | 19 | fee_meter, elw_meter, adverse_selection, partial_fill_cost, cost_aggregator |
| `test_execution_backbone/test_reconciliation_layer.py` | 25 | order_reconciler, fill_reconciler, position_reconciler, divergence_classifier, recovery_trigger |

### Audit Findings & Patches (Re-audit cycle)
| # | File | Bug | Severity | Fix |
|---|------|-----|----------|-----|
| 1 | `latency_meter.py` | **Truthiness bug**: `if sent_time and ack_time` treated `0.0` as False | BLOCKER | Changed to `if sent_time is not None and ack_time is not None` for all 4 latency computations. Also removed double `_measurements` initialization (`= {}` then `= []`). |
| 2 | `fill_reporter.py` | **EXPIRED partial fills**: EXPIRED orders with `had_partial_fills=True` counted only as expiration, not partial | BLOCKER | Added `had_partial_fills` branch for EXPIRED (same pattern as CANCELLED). |
| 3 | `adverse_selection_meter.py` | **Docstring inversion**: docstring said "positive AS = unfavorable for buy" but formula gives positive AS when mid rises after buy (favorable) | BLOCKER | Fixed docstring only — formula `AS_i(Δ) = sign(side)·(Mid_{t+Δ} - P_exec)/P_exec` and code unchanged. Positive AS = favorable, Negative AS = adverse. |

**Post-patch**: 6 tests added to cover re-audit fixes. All 88 tests green.

---

## Build-4 — Risk Backbone

**Status**: MERGEABLE
**Tests**: 116

### Source Files

#### `risk_backbone/exposure_budgeter/` (5 files)
| File | Role | Invariant |
|------|------|-----------|
| `__init__.py` | Package init | |
| `gross_exposure_calculator.py` | Position model, `calculate_gross_exposure()` | GrossExp = Σ x_i |
| `projected_exposure_checker.py` | `check_projected_exposure()` | GrossExp + x_new ≤ X_gross,max |
| `position_cap_guard.py` | `check_position_cap()` | x_i ≤ x_max,pos |
| `gross_cap_guard.py` | `evaluate_gross_cap()`: combined position+gross cap | projected_pair = current_pair_exposure + candidate_size |
| `exposure_reporter.py` | ExposureReporter, utilization = GrossExp/X_gross,max | |

#### `risk_backbone/loss_budgeter/` (5 files)
| File | Role | Invariant |
|------|------|-----------|
| `__init__.py` | Package init | |
| `position_loss_estimator.py` | `estimate_position_loss()` | L_i = size × \|entry - stop\| / entry |
| `aggregate_loss_budgeter.py` | `aggregate_loss_budget()` | LossBudget = Σ L_i, LossUtil = LossBudget/LB_max |
| `projected_loss_checker.py` | `check_projected_loss()` | LossBudget + L_new ≤ LB_max |
| `loss_cap_guard.py` | `evaluate_loss_cap()` | REJECTED_NO_LOSS_ESTIMATE if L_i is None |
| `loss_reporter.py` | LossReporter, budget tracking | |

#### `risk_backbone/btc_factor_guard/` (5 files)
| File | Role | Invariant |
|------|------|-----------|
| `__init__.py` | Package init | |
| `pair_beta_registry.py` | PairBetaRegistry, default_beta=0.8 fallback | |
| `portfolio_beta_calculator.py` | `calculate_portfolio_beta()` | β_port = Σ w_j·β_j where w_j = x_j/Σ x_k |
| `projected_beta_checker.py` | `check_projected_beta()` | \|β_port_proj\| ≤ B_max |
| `beta_cap_guard.py` | `evaluate_beta_cap()`: ACCEPTED/REJECTED | |
| `beta_reporter.py` | BetaReporter, utilization = \|β_port\|/B_max | |

#### `risk_backbone/correlation_cluster_guard/` (5 files)
| File | Role | Invariant |
|------|------|-----------|
| `__init__.py` | Package init | |
| `cluster_registry.py` | DEFAULT_CLUSTERS: btc_majors, eth_ecosystem, alt_l1, payments | |
| `cluster_exposure_calculator.py` | `calculate_cluster_exposures()` | ClusterExp_c = Σ x_i for i∈cluster c |
| `projected_cluster_checker.py` | `check_projected_cluster()` | ClusterExp_c + x_new ≤ X_cluster,c_max |
| `cluster_cap_guard.py` | `evaluate_cluster_cap()`: fail-closed if cluster_id=None | REJECTED_NO_CLUSTER for unmapped pairs |
| `cluster_reporter.py` | ClusterReporter: cluster_exposures, dominant_cluster tracking | |

### Test Files (116 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_risk_backbone/test_exposure_budgeter.py` | 29 | gross_calc, projected_checker, position_cap, gross_cap (incl. projected pair), reporter |
| `test_risk_backbone/test_loss_budgeter.py` | 30 | loss_estimator, aggregate_budget, projected_loss, loss_cap, reporter |
| `test_risk_backbone/test_btc_factor_guard.py` | 28 | beta_registry, portfolio_beta, projected_beta, beta_cap, reporter |
| `test_risk_backbone/test_correlation_cluster_guard.py` | 29 | cluster_registry, cluster_exposure, projected_cluster, cluster_cap (incl. fail-closed), reporter (incl. exposures+dominant) |

### Audit Findings & Patches
| # | File | Bug | Severity | Fix |
|---|------|-----|----------|-----|
| 1 | `gross_cap_guard.py` | Position cap checked `candidate_size` alone, ignoring existing pair exposure | BLOCKER | Added `current_pair_exposure` param (required, no default). Check: `projected_pair = current_pair_exposure + candidate_size > position_cap` |
| 2 | `cluster_cap_guard.py` | Unmapped pair (no cluster) passed silently | BLOCKER | `cluster_id: str \| None`, fail-closed: `REJECTED_NO_CLUSTER` with explicit reason |
| 3 | `cluster_reporter.py` | `get_stats()` returned empty `cluster_exposures` and `dominant_cluster` | BLOCKER | Track sizes per cluster in `record_accepted(size=)`, compute dominant in `get_stats()` |

**Post-patch tests added**:
- `test_projected_pair_exposure_rejected` (80+30 > cap 100)
- `test_projected_pair_exposure_accepted` (80+20 = cap 100)
- `test_no_cluster_rejected` (unmapped pair → REJECTED_NO_CLUSTER)
- `test_stats_cluster_exposures_non_empty`
- `test_stats_dominant_cluster`

---

## Build-5 — Scoring Backbone

**Status**: MERGEABLE
**Tests**: 106

### Source Files

#### `scoring_backbone/raw_score_builder/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `weight_registry.py` | Feature weight definitions |
| `feature_selector.py` | Feature selection for scoring |
| `raw_score_calculator.py` | Raw score computation |
| `score_component_breakdown.py` | Score decomposition by component |
| `score_reporter.py` | Score reporting |

#### `scoring_backbone/penalty_aggregator/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `penalty_registry.py` | Penalty type definitions |
| `score_penalty_builder.py` | Score-based penalty computation |
| `size_penalty_builder.py` | Size-based penalty computation |
| `penalty_cap_guard.py` | Penalty cap enforcement |
| `penalty_reporter.py` | Penalty reporting |

#### `scoring_backbone/hard_block_gate/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `blocker_registry.py` | Blocker rule definitions |
| `blocker_evaluator.py` | Blocker evaluation engine |
| `blocker_reason_encoder.py` | Human-readable blocker reason encoding |
| `blocker_decision_builder.py` | Block/pass decision construction |
| `blocker_reporter.py` | Blocker statistics reporting |

#### `scoring_backbone/ranking_router/` (5 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `candidate_pool_builder.py` | Build candidate pool from scored signals |
| `ranking_score_builder.py` | Final ranking score (raw - penalties) |
| `portfolio_compatibility_checker.py` | Portfolio-level compatibility: beta (abs), cluster (fail-closed) |
| `selection_resolver.py` | Final candidate selection/ordering |
| `ranking_reporter.py` | Ranking statistics reporting |

### Test Files (106 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_scoring_backbone/test_raw_score_builder.py` | — | weight_registry, feature_selector, raw_score_calc, breakdown, reporter |
| `test_scoring_backbone/test_penalty_aggregator.py` | — | penalty_registry, score_penalty, size_penalty, penalty_cap, reporter |
| `test_scoring_backbone/test_hard_block_gate.py` | — | blocker_registry, evaluator, reason_encoder, decision_builder, reporter |
| `test_scoring_backbone/test_ranking_router.py` | — | candidate_pool, ranking_score, portfolio_compat (beta abs + cluster fail-closed), selection, reporter |

### Audit Findings & Patches
| # | File | Bug | Severity | Fix |
|---|------|-----|----------|-----|
| 1 | `portfolio_compatibility_checker.py` | Beta check not symmetric — negative beta of large magnitude could pass | BLOCKER | Applied `abs()` on projected beta impact before comparison |
| 2 | `portfolio_compatibility_checker.py` | Empty/missing `cluster_id` bypassed cluster check | BLOCKER | Fail-closed: empty/None cluster_id → explicit rejection |

**Post-patch tests added**:
- Negative beta exceeding cap → explicit rejection
- Empty cluster_id → explicit rejection

---

## Build-6 — Engine A (Trend/Expansion)

**Status**: MERGEABLE
**Tests**: 40

### Source Files

#### `engines/engine_a/` (8 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `structure_detector_a.py` | Structure detection: direction, continuation, quality, zone_proximity, stability |
| `context_validator_a.py` | Context validation: regime favorability, pair health, data freshness, flow coherence |
| `conviction_builder_a.py` | Conviction: S_A^raw = 0.40*structure + 0.25*context + 0.15*flow + 0.20*cost_pref. Tier 1-3 |
| `cost_feasibility_a.py` | Cost check: E[g] > E[c] + delta_safe (0.0005), CE_A > CE_min |
| `invalidation_mapper_a.py` | Long-only invalidation mapping (spot-halal profile) |
| `signal_reporter_a.py` | Signal stats: emission rate, no-trade reasons, mean raw score |
| `engine_a_runner.py` | **Canonical orchestrator**: 7-step pipeline, structured logs, EngineAOutput |

### Test Files (40 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_engines/test_engine_a/test_engine_a.py` | 40 | structure_detector, context_validator, conviction_builder, cost_feasibility, invalidation_mapper, signal_reporter, E2E runner |

### Audit Findings & Patches
| # | File | Issue | Severity | Fix |
|---|------|-------|----------|-----|
| 1 | (new) `engine_a_runner.py` | Missing canonical orchestrator | P0 | Added full pipeline: structure > context > cost > conviction > invalidation > emit |
| 2 | `signal_reporter_a.py` | `NON_LONG_DIRECTION` missing | P0 | Added to NoTradeReason; runner rejects direction_score <= 0 |
| 3 | `invalidation_mapper_a.py` | Short path implicit | P1 | Engine A documented as long-only (spot-halal). Short direction -> NO_TRADE |
| 4 | All files | Structured logs absent | P0 | Added EngineALogEntry with events: structure/context/cost/conviction/invalidation/emit/no_trade |
| 5 | `structure_detector_a.py` | `zone_proximity` declared but unused | P1 | Now used in score formula: 0.10 weight |

---

## Build-7 — Engine B (Mean Reversion Intraday)

**Status**: MERGEABLE
**Tests**: 50

### Source Files

#### `engines/engine_b/` (8 files)
| File | Role | Key Invariant |
|------|------|---------------|
| `__init__.py` | Package init | |
| `local_mean_estimator_b.py` | Local mean, dispersion, z-score | z_t = (p_t - mu) / sigma |
| `excess_detector_b.py` | Detect exploitable local excess | abs(z_t) > z* = 1.5, z_max = 4.0 |
| `anti_breakout_filter_b.py` | Reject reversion against hostile continuation | BLOCKED if score >= 0.65 |
| `cost_feasibility_b.py` | Cost check (stricter than A) | delta_safe = 0.0008, CE_min = 0.0002 |
| `conviction_builder_b.py` | Conviction building | **Tier 1-2 max, never Tier 3** |
| `invalidation_mapper_b.py` | Mean-reversion invalidation | target=local_mean, stop=entry-1.5*sigma |
| `signal_reporter_b.py` | B-specific stats with z-score tracking | |
| `engine_b_runner.py` | **Canonical orchestrator**: 7-step pipeline | EngineBOutput, long-only |

### Engine B vs Engine A
| Property | Engine A (Trend) | Engine B (Mean Reversion) |
|----------|-----------------|--------------------------|
| delta_safe | 0.0005 | 0.0008 |
| CE_min | 0.0001 | 0.0002 |
| Max Tier | Tier 3 | **Tier 2** |
| Default holding | 4h | 2h |
| Long-only guard | direction_score > 0 | z_score < 0 (price below mean) |
| Anti-filter | Structure unfavorable | Anti-breakout (hostile continuation) |

### Pipeline (engine_b_runner.py)
1. Local mean estimation + z-score
2. Long-only guard (z > 0 -> NO_TRADE)
3. Excess detection (abs(z) > z*)
4. Anti-breakout filter
5. Cost feasibility (stricter)
6. Conviction building (Tier 1-2 cap)
7. Invalidation mapping (target = local mean)

### Structured Logs (EngineBLogEntry)
- `engine_b_mean_estimated` / `engine_b_excess_evaluated` / `engine_b_breakout_evaluated`
- `engine_b_cost_checked` / `engine_b_conviction_built` / `engine_b_invalidation_built`
- `engine_b_signal_emitted` / `engine_b_no_trade`

### Test Files (50 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_engines/test_engine_b/test_engine_b.py` | 50 | local_mean (5), excess_detector (7), anti_breakout (5), cost_feasibility (5), conviction (6), invalidation (5), reporter (4), E2E runner (13) |

### Audit Findings
- No blockers found at closure.
- Spec compliance: z-score in output, Tier 3 impossible, long-only enforced, anti-breakout present, cost stricter than A.

---

## Build-8 — Portfolio Minimal

**Status**: MERGEABLE
**Tests**: 70

### Source Files

#### `portfolio_minimal/opportunity_selector/` (6 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `candidate_pool_builder.py` | OpportunityCandidate model, CandidatePool, filter positive score+size |
| `eligibility_filter.py` | PortfolioSnapshot, check gross cap, cluster cap, fail-closed no cluster |
| `comparative_ranker.py` | R_i = 0.35*score + 0.30*CE - 0.20*cost - 0.15*corr_util |
| `correlation_conflict_checker.py` | Duplicate pair dedup (keep best), cluster crowding detection |
| `selection_resolver.py` | Greedy top-down selection under capacity constraints |

#### `portfolio_minimal/allocation_router/` (6 files)
| File | Role |
|------|------|
| `__init__.py` | Package init |
| `base_size_builder.py` | base_size = capital * fraction, clamped to [min, max] |
| `score_size_mapper.py` | Tier multiplier (1.0/0.6/0.0) + score boost (up to +20%) |
| `portfolio_cap_applier.py` | Apply tightest of position/gross/cluster caps |
| `phantom_trade_guard.py` | Reject allocations < min_viable_size (phantom trades) |
| `allocation_reporter.py` | Final report: viable allocations + phantom separations |

### Key Design Decisions
| Decision | Rationale |
|----------|-----------|
| Fail-closed on missing cluster | Consistent with Build-4/5 pattern |
| Greedy top-down selection | Ranked candidates consumed in order, capacity decremented live |
| Duplicate pair dedup | Same pair from two engines -> keep highest penalized_score |
| Phantom trade guard | Prevents economically sterile trades (size < min viable) |
| Tier 2 at 0.6x multiplier | Conservative sizing for lower-conviction signals |
| Score boost capped at +20% | Prevents oversizing on high scores |

### Test Files (54 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_portfolio_minimal/test_portfolio_minimal.py` | 54 | candidate_pool (6), eligibility (5), ranker (5), conflict_checker (6), selection_resolver (5), base_size (5), score_mapper (7), cap_applier (6), phantom_guard (5), reporter (4) |

### Re-audit Findings & Patches (Post NO-GO audit)
| # | File(s) | Issue | Severity | Fix |
|---|---------|-------|----------|-----|
| P0-1 | `eligibility_filter.py`, `selection_resolver.py` | Selector rejected oversized trades that allocation_router should reduce | P0 | Removed all size-based rejections from selector. Only structural reject: fail-closed no-cluster. allocation_router now handles all capacity reduction. |
| P0-2 | `portfolio_cap_applier.py`, `candidate_pool_builder.py` | Loss budget and beta/BTC budget not enforced | P0 | Added proportional loss_budget and beta_budget caps. `estimated_loss` field added to OpportunityCandidate. Cap applier computes max_size from remaining budget / per-unit rate. |
| P1-1 | (new) `portfolio_orchestrator.py` | No E2E orchestrator | P1 | Added 9-stage pipeline: pool -> conflicts -> rank -> select -> base_size -> modulate -> caps -> phantom -> report |
| P1-2 | `correlation_conflict_checker.py` | Duplicate pair dedup used only penalized_score | P1 | Now uses `ranking_score` (composite: score + CE - cost - corr_util) for economically optimal dedup |
| P1-3 | `portfolio_orchestrator.py` | Phantom sterilization not explicit in flow | P1 | Phantom trades explicitly sterilized before report. Budget decrements skip phantoms. |

**Architecture after patches**:
- `opportunity_selector` decides **what** deserves capital (structural eligibility only)
- `allocation_router` decides **how much** capital (reduces oversized, enforces all 5 caps)
- Only after cap application + phantom check is a trade definitively rejected
- Budgets (gross, cluster, loss, beta) decremented live per viable allocation

### Source Files (post-patch: +1 new)
| File | Change |
|------|--------|
| `portfolio_orchestrator.py` | **NEW**: E2E 9-stage pipeline |
| `eligibility_filter.py` | Removed REJECTED_GROSS_CAP and REJECTED_CLUSTER verdicts |
| `selection_resolver.py` | Removed capacity tracking; only reject no-cluster |
| `portfolio_cap_applier.py` | Added loss_budget + beta_budget proportional caps |
| `candidate_pool_builder.py` | Added `estimated_loss` field |
| `correlation_conflict_checker.py` | Dedup uses `ranking_score` (composite) |

---

## Cumulative Test Summary

| Build | Module | Tests | Status |
|-------|--------|-------|--------|
| Build-1 | Dependency Architecture | 332 | MERGEABLE |
| Build-2 | Data Backbone | 137 | MERGEABLE |
| Build-3 | Execution Backbone | 88 | MERGEABLE |
| Build-4 | Risk Backbone | 116 | MERGEABLE |
| Build-5 | Scoring Backbone | 106 | MERGEABLE |
| Build-6 | Engine A | 40 | MERGEABLE |
| Build-7 | Engine B | 50 | MERGEABLE |
| Build-8 | Portfolio Minimal | 70 | MERGEABLE |
| **Total** | | **956** | **ALL GREEN** |

---

## Remaining Builds (Not Yet Implemented)

| Build | Module | Spec |
|-------|--------|------|
| Build-9 | Meta Minimal | `V5_3_BUILD9_SPECS_META_MINIMAL.md` |
| Build-10 | Monitoring + UI Light | `V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md` |
| Build-11 | Shadow Light | `V5_3_BUILD11_SPEC_SHADOW_LIGHT.md` |
| Build-12 | Micro Live Light | `V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md` |
| Build-13 | Live Light | `V5_3_BUILD13_SPEC_LIVE_LIGHT.md` |
| Build-14 | Complete Enablers | `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md` |
| Build-15 | Engine C | `V5_3_BUILD15_SPECS_MOTEUR_C.md` |
| Build-16 | Engine D | `V5_3_BUILD16_SPECS_MOTEUR_D.md` |
| Build-17 | UI Complete + Live Complete | `V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md` |

---

*Last updated: 2026-03-26*
*Generated for third-party audit purposes.*
