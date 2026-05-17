# V5.3 — Artifact Placement Matrix (vrai repo)

- **Date** : 2026-05-16
- **Repo réel** : `E:\claude  v5.3\v53_trading_system\`
- **Couvre** : Livrable 8 (logs/journals/artefacts produits) + Livrable 9 (placement des artefacts uploadés)

> **Correction majeure du faux audit** : V5.3 produit déjà **des calibration artifacts signés** (`CalibrationArtifactSignatureError` raised si `"signature"` absent, [calibration_loader/loader.py:77-80](../../../src/calibration_loader/loader.py)), avec `config/calibration/v1/thresholds.yml` en production.

---

## 1. Artefacts PRODUITS par V5.3 — inventaire réel

### A. Décisions et refusals (audit trail core)

| # | Artefact | Producteur (file_path) | Format | Immutable | Signé | Stocké | Cycle |
|---|---------|------------------------|--------|-----------|-------|--------|-------|
| 1 | `SignalCandidate` / `ForecastSignalCandidate` | engines (A/B/C/D) via `engine_*_runtime` | Pydantic frozen | ✅ | — | DTR | per-evaluation |
| 2 | `RefusalRecord` typé | `protocols/engine_coordination_rules.py` (+ refusal sinks dans engines C/D `_RefusalSink` Protocol) | Pydantic frozen | ✅ | — | journal | per-refusal |
| 3 | `ConditioningRecord` typé | `engine_coordination_rules.py` + engines | Pydantic frozen | ✅ | — | journal | per-condition |
| 4 | `DTRRecord` | `meta_minimal/dtr_core/dtr_record_builder.py` | Pydantic frozen | ✅ | — | `trace_persistence_layer` JSON | per-decision |
| 5 | `EngineALogEntry` / `EngineBLogEntry` / `EngineCLogEntry` / `EngineDLogEntry` | engines runners | Pydantic frozen | ✅ | — | structured log | per-stage |
| 6 | `DecisionEvent` (trade / no-trade) | `execution_backbone/order_decider/decision_reporter.py` | typed | ✅ | — | structured log | event |
| 7 | `BlockerDecision` | `scoring_backbone/hard_block_gate/blocker_decision_builder.py` | typed | ✅ | — | blocker_reporter | per-candidate |
| 8 | `EngineCoordinationOutcome` | `protocols/engine_coordination_rules.py` | typed | ✅ | — | hooked to refusal/conditioning | per-evaluation |

### B. Sharia compliance audit trail

| # | Artefact | Producteur | Format | Immutable | Signé | Stocké | Cycle |
|---|---------|------------|--------|-----------|-------|--------|-------|
| 9 | `ShariaPermit` / `ShariaRejection` | `sharia_compliance/sharia_runtime.authorize_trade` | Pydantic frozen | ✅ | — | `PolicyAuditLogger` (append-only) | per-trade |
| 10 | `ShariaAuditEvent` | `policy_audit_logger.PolicyAuditLogger.record` | Pydantic frozen | ✅ | — | append-only log | per-decision |
| 11 | `AaoifiPairScreeningResult` | `sharia_compliance/pair_screening.evaluate_pair_screening` | Pydantic frozen | ✅ | — | embed in result | per-screen |
| 12 | `AaoifiPairScreeningAuditReport` | `pair_screening_audit.audit_traded_pairs_against_screening` | Pydantic frozen | ✅ | — | audit pack | periodic |
| 13 | `AccountFeaturesAuditReport` | `account_features_audit.audit_account_features` | Pydantic frozen | ✅ | — | audit pack | calibration-driven interval (THR-H02) |
| 14 | `PurificationEstimate` | `purification_calculator.calculate_purification` / `estimate_stablecoin_purification` | Pydantic frozen | ✅ | — | accounting | per-event / periodic |

### C. Risk / Execution

| # | Artefact | Producteur | Format | Immutable | Signé | Stocké | Cycle |
|---|---------|------------|--------|-----------|-------|--------|-------|
| 15 | `RiskEvaluation` | `risk_backbone/risk_runtime.py` | Pydantic frozen | ✅ | — | DTR + reporter | per-candidate |
| 16 | Risk explainability | `risk_backbone/risk_runtime_explainability.py` | typed | ✅ | — | log | per-decision |
| 17 | Exposure / loss / beta / cluster events | `risk_backbone/*_reporter.py` (4 reporters) | structured fields | ✅ | — | structured log | event |
| 18 | `ExecutionIntent` | `execution_backbone/execution_runtime.py` | Pydantic frozen | ✅ | — | order log | per-intent |
| 19 | Fill records | `execution_backbone/fill_tracker/order_state_tracker.py`, `fill_aggregator.py` | typed | ✅ | — | fill log | per-fill |
| 20 | Reconciliation divergence | `execution_backbone/reconciliation_layer/divergence_classifier.py` | typed (INFO/WARNING/BLOCKING/CRITICAL) | ✅ | — | divergence log | event |
| 21 | Cost meter (ELW, adverse selection) | `execution_backbone/execution_cost_meter/` | typed | ✅ | — | cost report | per-fill |

### D. Microstructure features (versioned + hashed)

| # | Artefact | Producteur | Format | Immutable | Method version hash | Cycle |
|---|---------|------------|--------|-----------|---------------------|-------|
| 22 | `OrderFlowImbalanceRecord` | `microstructure/order_flow_imbalance.py` | Pydantic frozen | ✅ | `ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH` | event/window |
| 23 | `VpinRecord` | `microstructure/vpin.py` | Pydantic frozen | ✅ | `VPIN_METHOD_VERSION_HASH` | bucket-rolling |
| 24 | `KyleLambdaRecord` | `microstructure/kyle_lambda.py` | Pydantic frozen | ✅ | `KYLE_LAMBDA_METHOD_VERSION_HASH` | interval |
| 25 | `RealizedKernelVolRecord` | `microstructure/realized_kernel_vol.py` | Pydantic frozen | ✅ | `REALIZED_KERNEL_METHOD_VERSION_HASH` | bucket |
| 26 | `HawkesIntensityRecord` | `microstructure/hawkes_intensity.py` | Pydantic frozen | ✅ | `HAWKES_METHOD_VERSION_HASH` | window |
| 27 | `PinRecord` | `microstructure/pin.py` | Pydantic frozen | ✅ | `PIN_METHOD_VERSION_HASH` | parameter-based |
| 28 | `AmihudIlliquidityRecord` | `microstructure/amihud_illiquidity.py` | Pydantic frozen | ✅ | `AMIHUD_METHOD_VERSION_HASH` | window |
| 29 | `RollSpreadRecord` | `microstructure/roll_spread.py` | Pydantic frozen | ✅ | `ROLL_SPREAD_METHOD_VERSION_HASH` | window |
| 30 | `CorwinSchultzSpreadRecord` | `microstructure/corwin_schultz_spread.py` | Pydantic frozen | ✅ | `CORWIN_SCHULTZ_METHOD_VERSION_HASH` | bar |
| 31 | `QueuePressureRecord` | `microstructure/queue_pressure.py` | Pydantic frozen | ✅ | `QUEUE_PRESSURE_METHOD_VERSION_HASH` | book event |
| 32 | `SpreadDynamicsRecord` | `microstructure/spread_dynamics.py` | Pydantic frozen | ✅ | `SPREAD_DYNAMICS_METHOD_VERSION_HASH` | horizon |
| 33 | `RealizedEffectiveSpreadRecord` | `microstructure/realized_effective_spread.py` | Pydantic frozen | ✅ | `REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH` | observation |
| 34 | `LobRegimeFeatureSnapshot` | `microstructure/lob_regime_features.py` | Pydantic frozen | ✅ | `LOB_REGIME_METHOD_VERSION_HASH` (V1+V2) | window |
| 35 | `WallsAndSpoofingSnapshot` | `microstructure/walls_and_spoofing.py` | Pydantic frozen | ✅ | `WALLS_AND_SPOOFING_METHOD_VERSION_HASH` | window |
| 36 | `MicrostructureFeatureSpec` registry | `microstructure/feature_registry.py` | typed registry | ✅ | per-feature method hash | lifecycle promoted/quarantined/rejected |
| 37 | `EngineAMicrostructureProvenance` / `EngineCMicrostructureProvenance` / `EngineDMicrostructureProvenance` | `microstructure/engine_input_provenance.py` | Pydantic frozen | ✅ | propagate method hashes | per-engine-call |

### E. Regime + Build-14 enablers

| # | Artefact | Producteur | Format | Immutable | Cycle |
|---|---------|------------|--------|-----------|-------|
| 38 | `RegimeLiteAssessment` + `RegimeLiteMemory` (persisted) | `regime_classifier/regime_lite.py` | Pydantic frozen | ✅ | per-evaluation, memory cross-run |
| 39 | `Build14EnablerSnapshot` (toxicity, fragility) | `complete_enablers/market_toxicity_snapshot.py`, `execution_fragility_score.py` | Pydantic frozen | ✅ | per-eval |
| 40 | `Build14InfluenceReport` / `Build14InfluenceSignal` | `complete_enablers/limited_influence.py` | Pydantic frozen | ✅ | per-eval |
| 41 | ML artifacts | `complete_enablers/ml_runtime_artifact_loader.py` | typed | ✅ | loaded from signed artifacts |
| 42 | ML promotion gate results | `complete_enablers/ml_model_promotion_gate.py` | typed | ✅ | per-promotion |
| 43 | ML scoring soft penalty | `complete_enablers/ml_scoring_soft_penalty_hook.py` | typed | ✅ | per-decision |
| 44 | Order book imbalance | `complete_enablers/order_book_imbalance.py` | typed | ✅ | per-snapshot |
| 45 | Micro edge entry timing / exit governor | `complete_enablers/micro_edge_*.py` | typed | ✅ | per-decision |
| 46 | Hurst regime classifier | `complete_enablers/hurst_regime_classifier.py` | typed | ✅ | window |
| 47 | Regime detector runtime | `complete_enablers/regime_detector_runtime.py` | typed | ✅ | window |

### F. Calibration (SIGNED artifacts)

| # | Artefact | Producteur / Path | Format | Signature | Validation |
|---|---------|--------------------|--------|-----------|-------------|
| 48 | **Calibration artifact (signed)** | `config/calibration/v{N}/*.yml` ou `*.json` | YAML/JSON with `signature` field | **REQUIRED** (raise `CalibrationArtifactSignatureError` si absent) | `CalibrationArtifactValidationError` + pydantic `CalibrationArtifact` model |
| 49 | `CalibrationArtifactCollection` | `calibration_loader.load_calibration_collection(path)` | typed collection | propagated | typed |
| 50 | `CalibrationThresholdEntry` (par `threshold_id` THR-*) | `calibration_loader.CalibrationLoader.get_entry/get_value` | typed (bool/int/float/str) | from artifact | typed |
| 51 | `config/calibration/v1/thresholds.yml` | actuellement déployé | YAML signé | ✅ | actif |

Threshold IDs **observés** consommés en code :
- `THR-RG01` — stressed vol threshold (regime_lite)
- `THR-RG02` — extreme drop threshold (regime_lite)
- `THR-RG03` — downgrade hysteresis s (regime_lite)
- `THR-RG04` — extreme cooldown s (regime_lite)
- `THR-H02` — account features audit interval s (sharia)
- `THR-H03` — stablecoin purification annual rate (sharia)
- (et probablement d'autres pour ML, microstructure → à confirmer Session 3)

### G. Local replay runtime + Strategy Ladder + Local Lab

| # | Artefact | Producteur (file) | Type |
|---|---------|---------------------|------|
| 52 | `ArtifactManifest` | `local_replay_runtime/artifact_manifest.py` | manifest |
| 53 | `ReplayRunManifest` (avec `artifact_hash` SHA256) | `local_replay_runtime/replay_run_manifest.py` | manifest |
| 54 | `ReplayBundle` | `local_replay_runtime/contracts.py` | bundle |
| 55 | `RuntimeEvidence` | `local_replay_runtime/runtime_evidence.py` | typed |
| 56 | `EnginePromotionArtifact` (per-engine local status) | `local_replay_runtime/promotion_artifact_builder.py` | typed + `engine_promotion_artifact_hash` |
| 57 | `PairPromotionArtifact` | idem | typed + `pair_promotion_artifact_hash` |
| 58 | `StrategyPromotionArtifact` | idem | typed + `strategy_promotion_artifact_hash` |
| 59 | `SampleSizeSurvivalArtifact` | idem | typed + `sample_size_survival_artifact_hash` |
| 60 | `ReplayPromotionArtifactBundle` (bundle des 4 types) | idem | bundle frozen |
| 61 | Promotion criteria status sets (executed_return, drawdown, sample, fill, cost, depth) | `promotion_artifact_builder._PROMOTION_READY_*` | sets de critères |
| 62 | `EngineCPromotionLocalStatus`, `EngineDPromotionLocalStatus` | `interface_contracts/promotion_artifact_contracts.py` | enums |
| 63 | `ArtifactProofSummary` | `local_replay_runtime/artifact_proof_summary_builder.py` | typed |
| 64 | `ArtifactReleaseCandidate` | `local_replay_runtime/artifact_release_candidate.py` | typed |
| 65 | `ArtifactUploadBridgeCandidate` | `local_replay_runtime/artifact_upload_bridge_candidate.py` | typed |
| 66 | `ArtifactAblationStudy` | `local_replay_runtime/artifact_ablation_study.py` | typed |
| 67 | `BacktestProofMatrix` | `local_replay_runtime/backtest_proof_matrix.py` | typed |
| 68 | `DataScienceQualityGates` | `local_replay_runtime/data_science_quality_gates.py` | typed |
| 69 | `EdgeGateCalibration` | `local_replay_runtime/edge_gate_calibration.py` | typed |
| 70 | `FeatureThresholdManifest` | `local_replay_runtime/feature_threshold_manifest.py` | typed |
| 71 | `GoldMicrostructureFeatureBuilder` | `local_replay_runtime/gold_microstructure_feature_builder.py` | builder |
| 72 | `SilverMarketSynchronizer` | `local_replay_runtime/silver_market_synchronizer.py` | builder |
| 73 | `RawMarketDataIndexer` | `local_replay_runtime/raw_market_data_indexer.py` | indexer |
| 74 | `GovernedAuditEvidenceIndex` | `local_replay_runtime/governed_audit_evidence_index.py` | typed |
| 75 | `MlGovernanceSidecars` | `local_replay_runtime/ml_governance_sidecars.py` | typed |
| 76 | `MlFinalAuditReport` | `local_replay_runtime/ml_final_audit_report.py` | typed |
| 77 | `MlModelTransport` | `local_replay_runtime/ml_model_transport.py` | typed |
| 78 | `LocalLabPromotionReadiness` | `local_replay_runtime/local_lab_promotion_readiness.py` | typed |
| 79 | `LocalLabRecalibrationPlan` | `local_replay_runtime/local_lab_recalibration_plan.py` | typed |
| 80 | `LocalLabReplayCandidateQueue` | `local_replay_runtime/local_lab_replay_candidate_queue.py` | typed |
| 81 | `LocalLabReplayDispatchPlan` | `local_replay_runtime/local_lab_replay_dispatch_plan.py` | typed |
| 82 | `LocalLabReplayTicketIndex` | `local_replay_runtime/local_lab_replay_ticket_index.py` | typed |
| 83 | `LocalLabReplayWorkflowLoader` / `Manifest` | `local_replay_runtime/local_lab_replay_workflow_*.py` | typed |
| 84 | `LocalLabExecutionReview` / `Telemetry` / `Projection` | `local_replay_runtime/local_lab_execution_*.py` | typed |
| 85 | `LocalLabCalibrationMethodsReview` / `NormalizedReport` | `local_replay_runtime/local_lab_calibration_*.py` | typed |
| 86 | `LocalLabMultipleTestingReview` | `local_replay_runtime/local_lab_multiple_testing_review.py` | typed |
| 87 | `LocalLabTailRiskReview` | `local_replay_runtime/local_lab_tail_risk_review.py` | typed |
| 88 | `LocalLabResearchPriority` | `local_replay_runtime/local_lab_research_priority.py` | typed |
| 89 | `LocalLabScopeMatrix` | `local_replay_runtime/local_lab_scope_matrix.py` | typed |
| 90 | `LocalLabMlArtifactTraining` | `local_replay_runtime/local_lab_ml_artifact_training.py` | typed |
| 91 | `LocalLabRegimeDetectorArtifactTraining` | `local_replay_runtime/local_lab_regime_detector_artifact_training.py` | typed |
| 92 | `LocalLabLossSurrogate` | `local_replay_runtime/local_lab_loss_surrogate.py` | typed |
| 93 | `StrategyLadderRunner` + composants (~25 modules) | `local_replay_runtime/strategy_ladder_*.py` | pipeline complet |
| 94 | `StrategyLadderEconomicProvenance` | `local_replay_runtime/strategy_ladder_economic_provenance.py` | provenance |
| 95 | `StrategyLadderB2LabelStoreBuilder` | `local_replay_runtime/strategy_ladder_b2_label_store_builder.py` | builder |
| 96 | `StrategyLadderEdgeModelProvider` | `local_replay_runtime/strategy_ladder_edge_model_provider.py` | provider |
| 97 | `StrategyLadderEngine{A,B,C,D}InputBuilder` | `local_replay_runtime/strategy_ladder_engine_{a,b,c,d}_input_builder.py` | builder |
| 98 | `StrategyLadderEngineNativeAdapter` / `Preselection` | `local_replay_runtime/strategy_ladder_engine_native_*.py` | adapter |
| 99 | `StrategyLadderExpectedEdgeTraining` | `local_replay_runtime/strategy_ladder_expected_edge_training.py` | training |
| 100 | `StrategyLadderFirstControlledRun` | `local_replay_runtime/strategy_ladder_first_controlled_run.py` | runner |
| 101 | `StrategyLadderGateWaterfallAnalysis` | `local_replay_runtime/strategy_ladder_gate_waterfall_analysis.py` | analysis |
| 102 | `StrategyLadderMlLabHandoff` | `local_replay_runtime/strategy_ladder_ml_lab_handoff.py` | handoff |
| 103 | `StrategyLadderOperatorArtifacts` | `local_replay_runtime/strategy_ladder_operator_artifacts.py` | typed |
| 104 | `StrategyLadderOrderbookReconstructor` | `local_replay_runtime/strategy_ladder_orderbook_reconstructor.py` | reconstructor |
| 105 | `StrategyLadderReplayEvidence` / `PerformanceProfile` | `local_replay_runtime/strategy_ladder_replay_*.py` | evidence |
| 106 | `StrategyLadderRollingMlWindowPlanner` | `local_replay_runtime/strategy_ladder_rolling_ml_window_planner.py` | planner |
| 107 | `StrategyLadderWindowCache` / `Index` | `local_replay_runtime/strategy_ladder_window_*.py` | typed |
| 108 | `VenueMetadataRegistry` | `local_replay_runtime/venue_metadata_registry.py` | typed |
| 109 | `PairBoundsRegistry` | `local_replay_runtime/pair_bounds_registry.py` | typed |
| 110 | `BybitHistoricalMetadata` | `local_replay_runtime/bybit_historical_metadata.py` | typed |
| 111 | `IaLabFeatureDatasetAdapter` | `local_replay_runtime/ia_lab_feature_dataset_adapter.py` | adapter |
| 112 | `BacktestReplayDatasetAdapter` | `local_replay_runtime/backtest_replay_dataset_adapter.py` | adapter |
| 113 | `RunClassComponentCoverage` | `local_replay_runtime/run_class_component_coverage.py` | typed |
| 114 | `StorageBudgetReport` | `local_replay_runtime/storage_budget_report.py` | typed |
| 115 | `RawDataProcessingContracts` | `local_replay_runtime/raw_data_processing_contracts.py` | typed |
| 116 | `ReplayExecutionRuntime` / `ProjectionLoader` / `Contracts` | `local_replay_runtime/replay_execution_*.py` | typed |
| 117 | `CapitalProfileBuilder` (replay + backtest_artifact_import) | `local_replay_runtime/capital_profile_builder.py` + `backtest_artifact_import/capital_profile_builder.py` | builder |

### H. Protocols / Gates

| # | Artefact | Producteur | Format |
|---|---------|------------|--------|
| 118 | `ShadowRuntimeEvidence` | `protocols/shadow_runtime.py`, `shadow_runtime_evidence.py` | Pydantic frozen |
| 119 | `ShadowDayCounter` state | `protocols/shadow_day_counter.py` | persisted state |
| 120 | `MicroLiveResult` | `protocols/micro_live_runtime.py` | typed |
| 121 | `LiveLightResult` | `protocols/live_light_runtime.py` | typed |
| 122 | `LiveCompleteResult` | `protocols/live_complete_runtime.py` | typed |
| 123 | `PromotionGateResult` | `protocols/promotion_gates.py` | frozen dataclass |
| 124 | `ClosedEpisodeJournal` entries | `protocols/closed_episode_journal.py` | append-only |
| 125 | `CompiledArtifactRegistryStore` | `protocols/compiled_artifact_registry_store.py` | typed |
| 126 | `CompiledHookPlanLoader` | `protocols/compiled_hook_plan_loader.py` | typed |
| 127 | `DashboardCommandQueue` events | `protocols/dashboard_command_queue.py` | typed |
| 128 | `ShadowLivePlan` | `protocols/shadow_live_plan.py` | typed |
| 129 | `ShadowVpsService` | `protocols/shadow_vps_service.py` | typed service |
| 130 | `ReplayGovernanceProjection` | `protocols/replay_governance_projection.py` + `monitoring/replay_governance_projection.py` | typed |

### I. Backtest artifact import (bridge)

| # | Artefact | Producteur |
|---|---------|------------|
| 131 | `ArtifactImportSummary` | `backtest_artifact_import/contracts.py` |
| 132 | Import validators | `backtest_artifact_import/validators.py` (refuse `bypass_runtime_gates_requested`, `automatic_promotion_requested`) |
| 133 | `ExportDirBridge` | `backtest_artifact_import/export_dir_bridge.py` |
| 134 | `MlModelTransport` (import side) | `backtest_artifact_import/ml_model_transport.py` |
| 135 | `CapitalProfileBuilder` (import side) | `backtest_artifact_import/capital_profile_builder.py` |

### J. Monitoring / Observability artifacts

| # | Artefact | Producteur |
|---|---------|------------|
| 136 | `MetricSample` Prometheus-style | `monitoring/metrics_collector.py`, `observability.py` |
| 137 | Alerts | `monitoring/alert_manager.py` |
| 138 | Technical / health / complete / light dashboard payloads | `monitoring/*_dashboard_backend.py`, `local_observability_stack.py`, `local_grafana_api.py` |
| 139 | `ContractsArtifacts` | `monitoring/contracts_artifacts.py` |
| 140 | `ContractsDashboardPayloads` | `monitoring/contracts_dashboard_payloads.py` |
| 141 | `ArtifactVisibility` | `monitoring/artifact_visibility.py` |
| 142 | `ChallengerEvidenceAlerts` | `monitoring/challenger_evidence_alerts.py` |
| 143 | `ShadowChallengerVerdictMonitoring` | tests reflètent un monitoring shadow challenger |
| 144 | `LoggingConfig` | `monitoring/logging_config.py` |
| 145 | `LocalObservabilityStack` | `monitoring/local_observability_stack.py` |

### K. Meta learning (post-trade artefacts)

| # | Artefact | Producteur |
|---|---------|------------|
| 146 | `MistakeClassifier` outputs | `meta_learning/mistake_classifier.py` |
| 147 | `HypothesisRegistry` entries | `meta_learning/hypothesis_registry.py` |
| 148 | `ImprovementCandidate` | `meta_learning/improvement_candidate_builder.py` |
| 149 | `ReplayBundle` (post-trade) | `meta_learning/replay_bundle_builder.py` |
| 150 | `ReviewPacket` (orchestrator) | `meta_learning/review_orchestrator.py` (+ governance, queue, resolution) |
| 151 | `BreakdownReport` | `meta_learning/breakdown_report_builder.py` |
| 152 | `LearningMemoryStore` | `meta_learning/learning_memory_store.py` |
| 153 | `LearningReviewExporter` | `meta_learning/learning_review_exporter.py` |
| 154 | `ChecklistGenerator` | `meta_learning/checklist_generator.py` |
| 155 | `CapacityGuard` | `meta_learning/capacity_guard.py` |
| 156 | `LifecycleRegistry` | `meta_learning/lifecycle_registry.py` |
| 157 | `MonitoringProjection` | `meta_learning/monitoring_projection.py` |
| 158 | `NearMissAnalyzer` | `meta_learning/near_miss_analyzer.py` |
| 159 | `PersistenceStore` | `meta_learning/persistence_store.py` |
| 160 | `PostTradeDiagnosticEngine` | `meta_learning/post_trade_diagnostic_engine.py` |
| 161 | `RetentionPolicy` | `meta_learning/retention_policy.py` |
| 162 | `ReviewGovernance` / `Queue` / `Resolution` | `meta_learning/review_*.py` |

### L. Cockpit state artifacts (38+)

| # | Artefact (state) | Producteur |
|---|------------------|------------|
| 163 | Engine state | `cockpit/state_engines.py`, `state_engine_why.py` |
| 164 | Decision trace | `cockpit/state_decision_trace.py` |
| 165 | Refusal journal | `cockpit/state_refusal_journal.py` |
| 166 | Kill proof | `cockpit/state_kill_proof.py` |
| 167 | Multiple testing | `cockpit/state_multiple_testing.py` |
| 168 | Queue trace | `cockpit/state_queue_trace.py` |
| 169 | Freshness | `cockpit/state_freshness.py` |
| 170 | Capacity guard | `cockpit/state_capacity_guard.py` |
| 171 | Model risk | `cockpit/state_model_risk.py` |
| 172 | Sizing chain | `cockpit/state_sizing_chain.py` |
| 173 | Tail risk | `cockpit/state_tail_risk.py` |
| 174 | Warmup explainer | `cockpit/state_warmup_explainer.py` |
| 175 | Calibration | `cockpit/state_calibration.py` |
| 176 | Lab review | `cockpit/state_lab_review.py` |
| 177 | Lab VPS transfer | `cockpit/state_lab_vps_transfer.py` |
| 178 | Replay metrics | `cockpit/state_replay_metrics.py` |
| 179 | Run comparison | `cockpit/state_run_comparison.py` |
| 180 | Service liveness | `cockpit/state_service_liveness.py` |
| 181 | System flow | `cockpit/state_system_flow.py` |
| 182 | Feature bridge | `cockpit/state_feature_bridge.py` |
| 183 | Economic sterilization | `cockpit/state_economic_sterilization.py` |
| 184 | Data quality | `cockpit/state_data_quality.py` |
| 185 | Disk growth | `cockpit/state_disk_growth.py` |
| 186 | Build1 core health | `cockpit/state_build1_core_health.py` |
| 187 | Strategy ladder component coverage | `cockpit/strategy_ladder_component_coverage_support.py` |
| 188 | Strategy ladder ML handoff | `cockpit/strategy_ladder_ml_handoff_support.py` |
| 189 | Strategy ladder workflow | `cockpit/strategy_ladder_workflow_support.py` |

### M. Alerting

| # | Artefact | Producteur |
|---|---------|------------|
| 190 | Telegram alert | `alerting/telegram_alerter.py` |
| 191 | Sharia alerts | `sharia_compliance/sharia_alerts.py` → telegram |

### N. Manifest registry

| # | Artefact | Producteur |
|---|---------|------------|
| 192 | Build order registry | `manifest_registry/build_order_registry.py` |
| 193 | Dependency registry | `manifest_registry/dependency_registry.py` |
| 194 | Module inventory | `manifest_registry/module_inventory.py` |
| 195 | Profile registry | `manifest_registry/profile_registry.py` |
| 196 | Version registry | `manifest_registry/version_registry.py` |

### O. Secrets

| # | Artefact | Producteur |
|---|---------|------------|
| 197 | Sealed secrets | `secrets_manager/sealer.py` + DPAPI Windows/Posix |
| 198 | Secrets loader | `secrets_manager/loader.py` |

> **Inventaire : ~200 artefacts typés**, frozen, hashed (méthode + données), versionnés. **Calibration artifacts signés** au sens crypto/structural via champ `signature` obligatoire.

---

## 2. Config / racines artefacts effectivement présentes

| Racine | Contenu observé |
|--------|------------------|
| `config/calibration/v1/thresholds.yml` | **calibration signée déployée** (consommée par regime_lite, sharia, etc.) |
| `config/sharia/` | sharia policy YAML (consommée par `policy_loader.load_sharia_policy`) |
| `config/settings_light.yaml`, `settings_complete.yaml` | profils LIGHT et COMPLETE |
| `config/logging.yaml` | logging config |
| `config/binance_adapter.yml` | venue adapter config |
| `config/engineering_guardrails_baseline.json`, `engineering_guardrails_policy.json` | guardrails |
| `config/systemd/` | services systemd |

---

## 3. Matrice de placement des artefacts UPLOADÉS (Livrable 9)

> Les artefacts conversationnels (MD ChatGPT, screenshots, bundles uploadés) ne sont **jamais source de vérité par défaut**.

### Règles strictes (rappel doctrine V5.3)

1. **Ne pas placer dans `src/`** sauf si c'est du code Python.
2. **Ne pas créer `src/local_ai_lab/`** (interdit doctrinalement). ✅ Confirmé absent.
3. **Convertir d'abord** en audit pack ou plan d'action, puis valider contre le code.
4. **Screenshots** : orientent l'inspection, ne concluent jamais.

### Table de placement

| Type d'artefact uploadé | Repo ? | Chemin recommandé | Statut canonique | Risque si mal placé |
|--------------------------|--------|-------------------|------------------|----------------------|
| MD doctrine V5.3 master final | OUI (existant) | `docs/specs/` | source canonique | drift vs code |
| Audit pack ChatGPT | OUI **après conversion** | `docs/audit/{YYYY-MM-DD}_{topic}/` | support, pas source | confusion source de vérité |
| Rapport ultrareview multi-agent | OUI | `docs/audit/` | support / historique | sur-poids des recommandations |
| Plan de production / runbook | OUI | `docs/production_deployment_plan/update_audit/` | plan opérationnel | confusion avec audit historique |
| **Calibration evidence (replay export validé)** | OUI | `build/replay_exports/` OU promu vers `config/calibration/v{N}/` une fois signé | **donnée brute** ou seuils production | **JAMAIS dans src/** |
| Shadow daily evidence | OUI | `build/shadow_evidence/` | donnée brute | — |
| **Calibration artefact signé (vN)** | OUI | `config/calibration/v{N}/` (avec champ `signature`) | **source de seuils live** | source de vérité critique |
| Backtest artifact (revue acceptée) | déjà couvert | input : `build/replay_exports/`, bridge : `src/backtest_artifact_import/` | bridge | — |
| Screenshots dashboard | NON par défaut | hors repo OU `docs/audit/{date}/screenshots/` | indicatif seulement | confusion preuves |
| Discussion / draft / brainstorm | NON | hors repo OU `docs/audit/drafts/` | à éliminer après synthèse | pollution doctrinale |
| Brouillons de patch (diffs MD non appliqués) | NON | hors repo | à transformer en commit/PR | confusion code/intention |
| Bundle de logs live (anonymisé) | OUI si utile audit | `docs/audit/{date}/log_extracts/` | preuve datée T0 | privacy/secrets |
| Doctrine externe (papers académiques) | NON dans repo | `docs/references/` | référence | pollution |
| ML model artifacts | OUI | `build/ml_artifacts/` (gitignored si lourd) + manifest dans `local_replay_runtime` | binaire/poids | versioning Git LFS si gros |

---

## 4. Cycle de vie des artefacts uploadés

```
[artefact externe : MD, screenshot, bundle, run output]
        │
        ▼
[transformation en audit pack MD structuré dans docs/audit/{YYYY-MM-DD}_{topic}/]
        │
        ▼  (validation manuelle vs code en HEAD)
[issue / action plan / PR proposé]
        │
        ▼  (passage par les seams existants)
[patch chirurgical OU rejet OU conservation comme historique]
        │
        ▼  (si calibration)
[promotion vers config/calibration/v{N}/ avec signature]
        │
        ▼
[chargé en runtime via CalibrationLoader, consommé par regime/sharia/ML/microstructure]
```

> **Jamais** : artefact uploadé → consommé directement par un module live.

---

## 5. Forces structurelles à PRÉSERVER

1. **Calibration artifacts signés** au niveau du loader — refus structurel des artefacts non signés.
2. **Method version hashing** sur chaque feature microstructure (immutabilité de méthode).
3. **Promotion artifacts typés** (`EnginePromotionArtifact`, `PairPromotionArtifact`, `StrategyPromotionArtifact`, `SampleSizeSurvivalArtifact`) avec hash function dédiés.
4. **Promotion criteria** explicites en 6 sets (executed_return, drawdown, sample, fill, cost, depth) — tous obligatoires pour PROMOTED.
5. **Strategy Ladder pipeline** complet : raw → silver → gold → engine inputs → expected edge training → ML lab handoff → promotion artifacts.
6. **`backtest_artifact_import/validators`** refusent `bypass_runtime_gates_requested` et `automatic_promotion_requested`.
7. **Cockpit state granulaire** (38+ modules) pour audit live.
8. **DPAPI sealed secrets** (Windows native + Posix fallback) pour gestion sécurisée.

---

## 6. Points à clarifier (résiduels)

| Question | À traiter |
|----------|-----------|
| TTL / staleness des calibration artifacts | `FeatureThresholdManifest` ou `GovernedAuditEvidenceIndex` — vérifier mécanisme d'expiry |
| Liste exhaustive `THR-*` actifs dans `thresholds.yml` | lecture directe du YAML production |
| Signature crypto : algorithme (HMAC ? GPG ? RSA ?) | `CalibrationArtifact` model_validate à inspecter |
| Rotation / régénération des secrets sealed | `secrets_manager/sealer.py` workflow |

→ Tout à compléter dans **V53_GAPS_AND_PATCH_PLAN.md** (point P1/P2 si gaps).

---

## 7. Next safe step

Consulter `V53_GAPS_AND_PATCH_PLAN.md` (verdict final + plan d'action P0/P1/P2).
