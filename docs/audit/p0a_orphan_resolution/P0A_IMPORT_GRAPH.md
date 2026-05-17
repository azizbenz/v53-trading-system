# P0-A Import Graph
Evidence base: `docs/audit/chatgpt_upload/00_TRIAGE_SUMMARY.md`, `docs/audit/chatgpt_upload/01_P0_ORPHAN_RESOLUTION_QUEUE.md`, `docs/audit/chatgpt_upload/07_NEXT_PATCH_ORDER.md`, plus direct AST import scan over mandatory P0 python files and all repo python importers.
## Domain Summary
| Domain | Files | Imports To | Imported By | Owner Mix | Artifact Readers | Artifact Writers |
|---|---:|---|---|---|---:|---:|
| scripts | 1 | scripts (17), interface_contracts (2), protocols (1) | none | runtime-only producer -> VPS (1) | 1 | 1 |
| backtest_artifact_import | 16 | backtest_artifact_import (35), local_replay_runtime (19), interface_contracts (14), meta_minimal (1), calibration_loader (1), monitoring (1) | backtest_artifact_import (35), scripts (8) | cockpit owner page -> Backtest (10); lab-only producer -> IA Lab (5); cockpit owner page -> Observability (1) | 3 | 1 |
| calibration_methods | 21 | calibration_methods (28), interface_contracts (5) | calibration_methods (28), local_replay_runtime (11), scripts (1) | cockpit owner page -> Backtest (16); lab-only producer -> IA Lab (5) | 0 | 0 |
| data_backbone/microstructure | 17 | data_backbone/microstructure (37), interface_contracts (2) | data_backbone/microstructure (37), engines (3), scripts (1), complete_enablers (1), data_backbone (1), local_replay_runtime (1) | cockpit owner page -> Trading (17) | 0 | 0 |
| engines | 64 | engines (131), scoring_backbone (55), interface_contracts (32), risk_backbone (18), data_backbone (12), data_backbone/microstructure (3) | engines (131), scripts (6), protocols (4) | cockpit owner page -> Trading (64) | 1 | 1 |
| execution_backbone | 48 | execution_backbone (108), interface_contracts (9), calibration_loader (5), sharia_compliance (4) | execution_backbone (108), protocols (13), venue_adapters (6), scripts (2), monitoring (2), risk_backbone (1) | cockpit owner page -> Trading (24); cockpit owner page -> VPS (19); non-cockpit core contract -> Trading / VPS (5) | 1 | 1 |
| interface_contracts | 33 | interface_contracts (62) | interface_contracts (62), protocols (59), scripts (43), local_replay_runtime (35), engines (32), monitoring (25) | non-cockpit core contract -> Trading / Backtest (15); non-cockpit core contract -> Backtest / IA Lab (10); non-cockpit core contract -> Shadow / VPS (8) | 0 | 0 |
| local_replay_runtime | 61 | local_replay_runtime (166), interface_contracts (35), meta_minimal (25), calibration_methods (11), meta_learning (3), data_backbone (2) | local_replay_runtime (166), backtest_artifact_import (19), scripts (13), protocols (4) | cockpit owner page -> Backtest (34); lab-only producer -> IA Lab (26); cockpit owner page -> VPS (1) | 10 | 4 |
| secrets_manager | 8 | secrets_manager (11), interface_contracts (2) | secrets_manager (11), alerting (1), venue_adapters (1), scripts (1) | non-cockpit core contract -> Shadow / VPS (8) | 2 | 1 |
| venue_adapters | 15 | venue_adapters (26), interface_contracts (16), execution_backbone (6), data_backbone (3), sharia_compliance (1), secrets_manager (1) | venue_adapters (26), scripts (5), protocols (4) | runtime-only producer -> Shadow / VPS (15) | 2 | 0 |

## scripts
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `scripts/run_shadow_vps_service.py` | __init__.py, __init__.py, shadow_vps_service_campaign_support.py, shadow_vps_service_cli_support.py, +16 more | none | none | coded_not_displayed |

## backtest_artifact_import
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/backtest_artifact_import/__init__.py` | compatibility_policy.py, contracts.py, errors.py, export_dir_bridge.py, +6 more | local_replay_shadow_import_support.py, local_replay_shadow_models.py, local_replay_shadow_payloads.py, local_replay_shadow_session_support.py | scripts (4) | coded_not_displayed |
| `src/backtest_artifact_import/compatibility_policy.py` | __init__.py, artifact_manifest.py, contracts.py | __init__.py, validators.py | backtest_artifact_import (2) | coded_not_displayed |
| `src/backtest_artifact_import/contracts.py` | __init__.py, artifact_manifest.py, enums.py | __init__.py, compatibility_policy.py, export_dir_bridge.py, export_dir_bridge_models.py, +8 more | backtest_artifact_import (12) | coded_not_displayed |
| `src/backtest_artifact_import/ed25519_verifier.py` | none | signature_policy.py | backtest_artifact_import (1) | coded_not_displayed |
| `src/backtest_artifact_import/errors.py` | __init__.py | __init__.py | backtest_artifact_import (1) | coded_not_displayed |
| `src/backtest_artifact_import/export_dir_bridge.py` | __init__.py, __init__.py, contracts.py, export_dir_bridge_models.py, +2 more | __init__.py, local_lab_upload_bridge_candidate.py, local_lab_upload_bridge_candidate_support.py, ml_model_transport.py, +4 more | backtest_artifact_import (5), scripts (3) | runtime_only |
| `src/backtest_artifact_import/export_dir_bridge_models.py` | __init__.py, __init__.py, contracts.py | export_dir_bridge.py | backtest_artifact_import (1) | coded_not_displayed |
| `src/backtest_artifact_import/export_dir_bridge_support.py` | __init__.py, __init__.py, contracts.py, dtr_record_builder.py, +2 more | export_dir_bridge.py | backtest_artifact_import (1) | coded_not_displayed |
| `src/backtest_artifact_import/local_lab_upload_bridge_candidate.py` | __init__.py, artifact_release_candidate.py, artifact_upload_bridge_candidate.py, export_dir_bridge.py, +1 more | run_local_lab_analysis_bundle.py | scripts (1) | coded_not_displayed |
| `src/backtest_artifact_import/local_lab_upload_bridge_candidate_support.py` | __init__.py, artifact_release_candidate.py, artifact_upload_bridge_candidate.py, contracts.py, +7 more | local_lab_upload_bridge_candidate.py | backtest_artifact_import (1) | coded_not_displayed |
| `src/backtest_artifact_import/ml_model_transport.py` | __init__.py, __init__.py, atomic_io.py, contracts.py, +1 more | __init__.py | backtest_artifact_import (1) | runtime_only |
| `src/backtest_artifact_import/monitoring_projection.py` | contracts.py, contracts.py | __init__.py | backtest_artifact_import (1) | coded_not_displayed |
| `src/backtest_artifact_import/regime_detector_transport.py` | __init__.py, __init__.py, atomic_io.py, contracts.py, +1 more | __init__.py | backtest_artifact_import (1) | runtime_only |
| `src/backtest_artifact_import/signature_policy.py` | __init__.py, artifact_manifest.py, contracts.py, ed25519_verifier.py | __init__.py, local_lab_upload_bridge_candidate_support.py, validators.py | backtest_artifact_import (3) | coded_not_displayed |
| `src/backtest_artifact_import/upload_bridge.py` | contracts.py | __init__.py, export_dir_bridge.py, local_lab_upload_bridge_candidate_support.py | backtest_artifact_import (3) | coded_not_displayed |
| `src/backtest_artifact_import/validators.py` | __init__.py, artifact_manifest.py, compatibility_policy.py, contracts.py, +2 more | __init__.py, local_lab_upload_bridge_candidate_support.py | backtest_artifact_import (2) | coded_not_displayed |

## calibration_methods
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/calibration_methods/__init__.py` | bootstrap.py, dsr.py, energy_distance.py, execution.py, +16 more | edge_gate_calibration.py, local_lab_calibration_methods_review.py, local_lab_execution_review.py, local_lab_ml_artifact_training.py, +6 more | local_replay_runtime (9), scripts (1) | coded_not_displayed |
| `src/calibration_methods/bootstrap.py` | none | __init__.py, hansen_spa.py | calibration_methods (2) | coded_not_displayed |
| `src/calibration_methods/dsr.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/energy_distance.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/execution.py` | hard_cap_floor.py | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/hansen_spa.py` | bootstrap.py | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/hard_cap_floor.py` | none | __init__.py, execution.py | calibration_methods (2) | coded_not_displayed |
| `src/calibration_methods/ks_test.py` | none | __init__.py, ml_trainer.py, regime_detector_trainer.py | calibration_methods (3) | coded_not_displayed |
| `src/calibration_methods/mann_kendall.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/ml_backtest_projection.py` | __init__.py, ml_trainer.py | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/ml_trainer.py` | ks_test.py, ml_model_artifact.py | __init__.py, ml_backtest_projection.py | calibration_methods (2) | coded_not_displayed |
| `src/calibration_methods/multiple_testing.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/multiple_testing_guard.py` | domain_types.py | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/pot_gpd.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/psr.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/regime_detector_feature_calibration.py` | walls_and_spoofing_calibration.py | __init__.py, local_lab_regime_detector_artifact_training.py, regime_detector_projection.py | calibration_methods (2), local_replay_runtime (1) | coded_not_displayed |
| `src/calibration_methods/regime_detector_projection.py` | __init__.py, regime_detector_feature_calibration.py, regime_detector_trainer.py | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/regime_detector_trainer.py` | __init__.py, ks_test.py | __init__.py, local_lab_regime_detector_artifact_training.py, regime_detector_projection.py | calibration_methods (2), local_replay_runtime (1) | coded_not_displayed |
| `src/calibration_methods/stationarity.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/walkforward.py` | none | __init__.py | calibration_methods (1) | coded_not_displayed |
| `src/calibration_methods/walls_and_spoofing_calibration.py` | none | __init__.py, regime_detector_feature_calibration.py | calibration_methods (2) | coded_not_displayed |

## data_backbone/microstructure
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/data_backbone/microstructure/__init__.py` | amihud_illiquidity.py, corwin_schultz_spread.py, engine_input_provenance.py, feature_registry.py, +12 more | __init__.py, regime_detector_dataset_builder.py, regime_detector_runtime.py, runtime_input_assembler_d.py, +1 more | scripts (1), complete_enablers (1), data_backbone (1), engines (1) | insufficient_evidence |
| `src/data_backbone/microstructure/amihud_illiquidity.py` | none | __init__.py, feature_registry.py | data_backbone/microstructure (2) | insufficient_evidence |
| `src/data_backbone/microstructure/corwin_schultz_spread.py` | none | __init__.py, feature_registry.py | data_backbone/microstructure (2) | insufficient_evidence |
| `src/data_backbone/microstructure/engine_input_provenance.py` | kyle_lambda.py, order_flow_imbalance.py, queue_pressure.py, realized_kernel_vol.py, +1 more | __init__.py | data_backbone/microstructure (1) | insufficient_evidence |
| `src/data_backbone/microstructure/feature_registry.py` | amihud_illiquidity.py, corwin_schultz_spread.py, hawkes_intensity.py, kyle_lambda.py, +8 more | __init__.py | data_backbone/microstructure (1) | insufficient_evidence |
| `src/data_backbone/microstructure/hawkes_intensity.py` | none | __init__.py, feature_registry.py | data_backbone/microstructure (2) | insufficient_evidence |
| `src/data_backbone/microstructure/kyle_lambda.py` | none | __init__.py, engine_input_provenance.py, feature_registry.py | data_backbone/microstructure (3) | insufficient_evidence |
| `src/data_backbone/microstructure/lob_regime_features.py` | order_flow_imbalance.py, regime_detector_artifact.py, walls_and_spoofing.py | __init__.py, walls_and_spoofing.py | data_backbone/microstructure (2) | insufficient_evidence |
| `src/data_backbone/microstructure/order_flow_imbalance.py` | none | __init__.py, engine_input_provenance.py, feature_registry.py, lob_regime_features.py | data_backbone/microstructure (4) | insufficient_evidence |
| `src/data_backbone/microstructure/pin.py` | none | __init__.py, feature_registry.py | data_backbone/microstructure (2) | insufficient_evidence |
| `src/data_backbone/microstructure/queue_pressure.py` | none | __init__.py, engine_input_provenance.py, feature_registry.py | data_backbone/microstructure (3) | insufficient_evidence |
| `src/data_backbone/microstructure/realized_effective_spread.py` | domain_types.py | __init__.py, feature_registry.py, spread_dynamics.py | data_backbone/microstructure (3) | insufficient_evidence |
| `src/data_backbone/microstructure/realized_kernel_vol.py` | none | __init__.py, engine_d_runtime_history_entry_mixin.py, engine_input_provenance.py, feature_registry.py, +1 more | data_backbone/microstructure (3), engines (2) | insufficient_evidence |
| `src/data_backbone/microstructure/roll_spread.py` | none | __init__.py, feature_registry.py | data_backbone/microstructure (2) | insufficient_evidence |
| `src/data_backbone/microstructure/spread_dynamics.py` | realized_effective_spread.py | __init__.py | data_backbone/microstructure (1) | insufficient_evidence |
| `src/data_backbone/microstructure/vpin.py` | none | __init__.py, engine_input_provenance.py, feature_registry.py | data_backbone/microstructure (3) | insufficient_evidence |
| `src/data_backbone/microstructure/walls_and_spoofing.py` | lob_regime_features.py | __init__.py, feature_registry.py, lob_regime_features.py | data_backbone/microstructure (3) | insufficient_evidence |

## engines
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/engines/__init__.py` | none | none | none | coded_not_displayed |
| `src/engines/engine_a/__init__.py` | engine_a_runner.py, engine_a_runtime.py | engine_a_hooks.py, engine_a_pre_entry_confirmation_bridge.py, local_replay_shadow_engines.py, run_build9_core_smoke.py | scripts (2), protocols (2) | coded_not_displayed |
| `src/engines/engine_a/context_validator_a.py` | __init__.py | engine_a_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/conviction_builder_a.py` | market_physics_math.py | engine_a_runner.py, engine_a_scoring_candidate_builder.py, signal_reporter_a.py | engines (3) | coded_not_displayed |
| `src/engines/engine_a/cost_feasibility_a.py` | __init__.py | engine_a_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/engine_a_runner.py` | __init__.py, context_validator_a.py, conviction_builder_a.py, cost_feasibility_a.py, +4 more | __init__.py, engine_a_runtime.py, engine_a_runtime_support.py, engine_a_scoring_candidate_builder.py, +1 more | engines (5) | coded_not_displayed |
| `src/engines/engine_a/engine_a_runner_support.py` | none | engine_a_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/engine_a_runtime.py` | __init__.py, blocker_evaluator.py, circuit_breaker.py, engine_a_runner.py, +8 more | __init__.py, engine_a_scoring_candidate_builder.py | engines (2) | coded_not_displayed |
| `src/engines/engine_a/engine_a_runtime_support.py` | __init__.py, __init__.py, engine_a_runner.py, forecast_contracts.py, +2 more | engine_a_runtime.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/engine_a_scoring_candidate_builder.py` | conviction_builder_a.py, engine_a_runner.py, engine_a_runtime.py, scoring_runtime.py | engine_a_runtime.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/invalidation_mapper_a.py` | __init__.py | engine_a_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/signal_candidate_adapter.py` | break_even_filter.py, decision_contracts.py, domain_types.py, engine_a_runner.py, +2 more | none | none | coded_not_displayed |
| `src/engines/engine_a/signal_reporter_a.py` | conviction_builder_a.py | engine_a_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_a/structure_detector_a.py` | __init__.py | engine_a_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_b/__init__.py` | engine_b_runner.py, engine_b_runtime.py | engine_b_hooks.py, engine_b_sweep_validation_bridge.py, local_replay_shadow_engines.py, run_build9_core_smoke.py | scripts (2), protocols (2) | coded_not_displayed |
| `src/engines/engine_b/anti_breakout_filter_b.py` | __init__.py | engine_b_runner.py, engine_b_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_b/conviction_builder_b.py` | market_physics_math.py | engine_b_runner.py, engine_b_runner_support.py, engine_b_runtime_support.py, signal_reporter_b.py | engines (4) | coded_not_displayed |
| `src/engines/engine_b/cost_feasibility_b.py` | __init__.py | engine_b_runner.py, engine_b_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_b/engine_b_runner.py` | anti_breakout_filter_b.py, conviction_builder_b.py, cost_feasibility_b.py, engine_b_runner_support.py, +3 more | __init__.py, engine_b_runner_support.py, engine_b_runtime.py, engine_b_runtime_forecast_support.py, +2 more | engines (6) | coded_not_displayed |
| `src/engines/engine_b/engine_b_runner_support.py` | anti_breakout_filter_b.py, conviction_builder_b.py, cost_feasibility_b.py, engine_b_runner.py, +3 more | engine_b_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_b/engine_b_runtime.py` | __init__.py, blocker_evaluator.py, circuit_breaker.py, engine_b_runner.py, +7 more | __init__.py, engine_b_runtime_forecast_support.py, engine_b_runtime_support.py | engines (3) | coded_not_displayed |
| `src/engines/engine_b/engine_b_runtime_forecast_support.py` | __init__.py, __init__.py, engine_b_runner.py, engine_b_runtime.py, +3 more | engine_b_runtime_support.py | engines (1) | coded_not_displayed |
| `src/engines/engine_b/engine_b_runtime_support.py` | __init__.py, circuit_breaker.py, conviction_builder_b.py, engine_b_runner.py, +6 more | engine_b_runtime.py | engines (1) | coded_not_displayed |
| `src/engines/engine_b/excess_detector_b.py` | __init__.py | engine_b_runner.py, engine_b_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_b/invalidation_mapper_b.py` | __init__.py | engine_b_runner.py, engine_b_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_b/local_mean_estimator_b.py` | __init__.py | engine_b_runner_support.py | engines (1) | coded_not_displayed |
| `src/engines/engine_b/signal_candidate_adapter.py` | break_even_filter.py, decision_contracts.py, domain_types.py, engine_b_runner.py, +2 more | none | none | coded_not_displayed |
| `src/engines/engine_b/signal_reporter_b.py` | conviction_builder_b.py | engine_b_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_c/__init__.py` | continuation_validator_c.py, cost_feasibility_c.py, engine_c_runner.py, engine_c_runtime.py | local_replay_shadow_engines.py | scripts (1) | coded_not_displayed |
| `src/engines/engine_c/continuation_validator_c.py` | signal_math_c.py | __init__.py, engine_c_runner.py, engine_c_runner_support.py | engines (3) | coded_not_displayed |
| `src/engines/engine_c/conviction_builder_c.py` | none | engine_c_runner.py, engine_c_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_c/cost_feasibility_c.py` | none | __init__.py, engine_c_runner.py, engine_c_runner_support.py | engines (3) | coded_not_displayed |
| `src/engines/engine_c/engine_c_runner.py` | continuation_validator_c.py, conviction_builder_c.py, cost_feasibility_c.py, engine_c_runner_support.py, +4 more | __init__.py, engine_c_runner_support.py, engine_c_runtime.py, engine_c_runtime_forecast_support.py, +3 more | engines (7) | coded_not_displayed |
| `src/engines/engine_c/engine_c_runner_support.py` | continuation_validator_c.py, conviction_builder_c.py, cost_feasibility_c.py, engine_c_runner.py, +3 more | engine_c_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_c/engine_c_runtime.py` | __init__.py, blocker_evaluator.py, circuit_breaker.py, engine_c_runner.py, +8 more | __init__.py, engine_c_runtime_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_c/engine_c_runtime_forecast_support.py` | __init__.py, __init__.py, engine_c_runner.py, forecast_contracts.py, +2 more | engine_c_runtime_support.py | engines (1) | coded_not_displayed |
| `src/engines/engine_c/engine_c_runtime_support.py` | __init__.py, engine_c_runner.py, engine_c_runtime.py, engine_c_runtime_forecast_support.py, +4 more | engine_c_runtime.py | engines (1) | coded_not_displayed |
| `src/engines/engine_c/invalidation_mapper_c.py` | none | engine_c_runner.py, engine_c_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_c/output_payload_builder_c.py` | none | engine_c_runner.py, engine_c_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_c/signal_math_c.py` | engine_c_runner.py | continuation_validator_c.py, engine_c_runner.py | engines (2) | coded_not_displayed |
| `src/engines/engine_c/structure_resolver_c.py` | engine_c_runner.py | engine_c_runner.py, engine_c_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/__init__.py` | consecutive_stop_counter_d.py, coordination_input_assembler_d.py, cost_feasibility_d.py, engine_d_runner.py, +6 more | local_replay_shadow_engines.py | scripts (1) | coded_not_displayed |
| `src/engines/engine_d/consecutive_stop_counter_d.py` | none | __init__.py, coordination_input_assembler_d.py, engine_d_runtime.py, engine_d_runtime_history_entry_mixin.py, +4 more | engines (8) | coded_not_displayed |
| `src/engines/engine_d/context_resolver_d.py` | engine_d_runner.py | engine_d_runner.py, engine_d_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/conviction_builder_d.py` | none | engine_d_runner_late_stages.py | engines (1) | coded_not_displayed |
| `src/engines/engine_d/coordination_input_assembler_d.py` | __init__.py, consecutive_stop_counter_d.py, first_episode_resolver_d.py, historical_linkage_guard_d.py | __init__.py, runtime_input_assembler_d.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/cost_feasibility_d.py` | none | __init__.py, engine_d_models.py, engine_d_runner_late_stages.py | engines (3) | coded_not_displayed |
| `src/engines/engine_d/engine_d_models.py` | cost_feasibility_d.py | engine_d_runner.py, engine_d_runner_late_stages.py, engine_d_runner_support.py, engine_d_runtime_result_builders.py | engines (4) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runner.py` | context_resolver_d.py, engine_d_models.py, engine_d_runner_late_stages.py, engine_d_runner_support.py, +2 more | __init__.py, context_resolver_d.py, engine_d_runtime.py, engine_d_runtime_history_entry_mixin.py, +4 more | engines (8) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runner_late_stages.py` | conviction_builder_d.py, cost_feasibility_d.py, engine_d_models.py, engine_d_runner_support.py, +2 more | engine_d_runner.py | engines (1) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runner_support.py` | context_resolver_d.py, engine_d_models.py, invalidation_mapper_d.py, output_payload_builder_d.py | engine_d_runner.py, engine_d_runner_late_stages.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runtime.py` | __init__.py, blocker_evaluator.py, circuit_breaker.py, consecutive_stop_counter_d.py, +12 more | __init__.py, engine_d_runtime_history_entry_mixin.py, engine_d_runtime_result_builders.py, engine_d_runtime_support.py, +1 more | engines (5) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py` | blocker_evaluator.py, consecutive_stop_counter_d.py, engine_d_runner.py, engine_d_runtime.py, +6 more | engine_d_runtime.py | engines (1) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runtime_result_builders.py` | __init__.py, circuit_breaker.py, consecutive_stop_counter_d.py, engine_d_models.py, +6 more | engine_d_runtime.py | engines (1) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runtime_support.py` | __init__.py, __init__.py, engine_d_runner.py, engine_d_runtime.py, +5 more | engine_d_runtime.py, engine_d_runtime_result_builders.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/engine_d_runtime_support_refusal.py` | __init__.py, engine_d_runner.py, forecast_contracts.py, risk_runtime.py, +1 more | engine_d_runtime_support.py | engines (1) | coded_not_displayed |
| `src/engines/engine_d/engine_state_snapshot_d.py` | __init__.py, atomic_io.py, consecutive_stop_counter_d.py | __init__.py | engines (1) | runtime_only |
| `src/engines/engine_d/first_episode_resolver_d.py` | __init__.py | __init__.py, coordination_input_assembler_d.py, engine_d_runtime.py, engine_d_runtime_result_builders.py, +1 more | engines (5) | coded_not_displayed |
| `src/engines/engine_d/historical_linkage_guard_d.py` | __init__.py, consecutive_stop_counter_d.py | __init__.py, coordination_input_assembler_d.py, engine_d_runtime.py | engines (3) | coded_not_displayed |
| `src/engines/engine_d/invalidation_mapper_d.py` | none | engine_d_runner_late_stages.py, engine_d_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/marginal_value_estimator_d.py` | none | __init__.py, engine_d_runner.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/output_payload_builder_d.py` | none | engine_d_runner_late_stages.py, engine_d_runner_support.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/runtime_input_assembler_d.py` | __init__.py, __init__.py, blocker_evaluator.py, consecutive_stop_counter_d.py, +9 more | __init__.py, engine_d_runtime_history_entry_mixin.py | engines (2) | coded_not_displayed |
| `src/engines/engine_d/signal_math_d.py` | engine_d_runner.py | engine_d_runner.py | engines (1) | coded_not_displayed |

## execution_backbone
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/execution_backbone/__init__.py` | __init__.py, execution_runtime.py, hybrid_router.py, hybrid_router_calibration.py, +6 more | run_build9_core_smoke_support.py | scripts (1) | insufficient_evidence |
| `src/execution_backbone/emergency_circuit_breaker.py` | atomic_io.py | circuit_breaker.py, scheduler.py | execution_backbone (1), risk_backbone (1) | orphan_candidate |
| `src/execution_backbone/execution_cost_meter/__init__.py` | none | none | none | insufficient_evidence |
| `src/execution_backbone/execution_cost_meter/adverse_selection_meter.py` | none | execution_runtime.py, execution_runtime_support.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/execution_cost_meter/cost_aggregator.py` | none | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/execution_cost_meter/elw_meter.py` | none | execution_runtime.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/execution_cost_meter/fee_meter.py` | __init__.py | execution_runtime.py | execution_backbone (1) | orphan_candidate |
| `src/execution_backbone/execution_cost_meter/partial_fill_cost_meter.py` | none | execution_runtime.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/execution_routing_bridge.py` | execution_routing_features.py, execution_runtime_models.py, hybrid_router_calibration.py, hybrid_router_metrics.py | execution_routing_bridge.py, execution_runtime.py | execution_backbone (1), protocols (1) | insufficient_evidence |
| `src/execution_backbone/execution_routing_features.py` | none | execution_routing_bridge.py, execution_routing_features.py, execution_runtime.py, execution_runtime_models.py, +3 more | execution_backbone (6), protocols (1) | insufficient_evidence |
| `src/execution_backbone/execution_runtime.py` | __init__.py, __init__.py, adverse_selection_meter.py, cost_aggregator.py, +28 more | __init__.py, execution_runtime_bootstrap.py, scheduler.py | execution_backbone (2), protocols (1) | orphan_candidate |
| `src/execution_backbone/execution_runtime_models.py` | __init__.py, __init__.py, contracts.py, cost_aggregator.py, +12 more | execution_adapter.py, execution_no_trade_filter_bridge.py, execution_opportunity_bridge.py, execution_routing_bridge.py, +4 more | execution_backbone (3), protocols (3), venue_adapters (2) | orphan_candidate |
| `src/execution_backbone/execution_runtime_support.py` | __init__.py, __init__.py, adverse_selection_meter.py, contracts.py, +7 more | execution_runtime.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/fee_aware_edge_gate.py` | contracts.py, loader.py | execution_runtime.py, execution_runtime_support.py, fee_aware_edge_gate.py, gatekeeper.py, +1 more | execution_backbone (4), scoring_backbone (1) | orphan_candidate |
| `src/execution_backbone/fill_tracker/__init__.py` | none | none | none | insufficient_evidence |
| `src/execution_backbone/fill_tracker/fill_aggregator.py` | __init__.py | execution_runtime.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/fill_tracker/fill_reporter.py` | order_state_tracker.py | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | orphan_candidate |
| `src/execution_backbone/fill_tracker/latency_meter.py` | none | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/fill_tracker/order_state_tracker.py` | none | execution_runtime.py, execution_runtime_support.py, fill_reporter.py, order_terminal_state_resolver.py | execution_backbone (4) | insufficient_evidence |
| `src/execution_backbone/fill_tracker/order_terminal_state_resolver.py` | order_state_tracker.py | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/gatekeeper/__init__.py` | audit_logger.py, gatekeeper.py | __init__.py, execution_runtime.py, execution_runtime_bootstrap.py, execution_runtime_models.py, +1 more | execution_backbone (4), protocols (1) | insufficient_evidence |
| `src/execution_backbone/gatekeeper/audit_logger.py` | gatekeeper.py | __init__.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/gatekeeper/gatekeeper.py` | contracts.py, execution_guard.py, fee_aware_edge_gate.py, gatekeeper_support.py, +5 more | __init__.py, audit_logger.py | execution_backbone (2) | orphan_candidate |
| `src/execution_backbone/gatekeeper/gatekeeper_support.py` | contracts.py, execution_guard.py, fee_aware_edge_gate.py, intent_builder.py, +3 more | gatekeeper.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/order_decider/__init__.py` | none | none | none | insufficient_evidence |
| `src/execution_backbone/order_decider/decision_reporter.py` | intent_builder.py | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | orphan_candidate |
| `src/execution_backbone/order_decider/execution_guard.py` | none | execution_runtime_models.py, gatekeeper.py, gatekeeper_support.py | execution_backbone (3) | insufficient_evidence |
| `src/execution_backbone/order_decider/hybrid_router.py` | execution_routing_features.py, hybrid_router_calibration.py, hybrid_router_equations.py, hybrid_router_metrics.py, +2 more | __init__.py, execution_runtime.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/order_decider/hybrid_router_calibration.py` | loader.py | __init__.py, execution_routing_bridge.py, hybrid_router.py, hybrid_router_equations.py | execution_backbone (4) | insufficient_evidence |
| `src/execution_backbone/order_decider/hybrid_router_equations.py` | execution_routing_features.py, hybrid_router_calibration.py | hybrid_router.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/order_decider/hybrid_router_metrics.py` | hybrid_router_types.py | execution_routing_bridge.py, execution_runtime.py, hybrid_router.py, hybrid_router_metrics.py, +1 more | execution_backbone (4), monitoring (1) | orphan_candidate |
| `src/execution_backbone/order_decider/hybrid_router_sanitization.py` | hybrid_router_types.py | hybrid_router.py | execution_backbone (1) | insufficient_evidence |
| `src/execution_backbone/order_decider/hybrid_router_shadow.py` | execution_routing_features.py, hybrid_router_metrics.py, hybrid_router_types.py | __init__.py, execution_runtime.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/order_decider/hybrid_router_types.py` | none | __init__.py, execution_runtime.py, hybrid_router.py, hybrid_router_metrics.py, +3 more | execution_backbone (6), monitoring (1) | insufficient_evidence |
| `src/execution_backbone/order_decider/intent_builder.py` | __init__.py | decision_reporter.py, execution_adapter.py, execution_opportunity_bridge.py, execution_runtime.py, +8 more | execution_backbone (9), venue_adapters (2), protocols (1) | orphan_candidate |
| `src/execution_backbone/order_decider/order_type_selector.py` | intent_builder.py | gatekeeper.py, gatekeeper_support.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/order_decider/timeout_policy_selector.py` | intent_builder.py | gatekeeper.py | execution_backbone (1) | orphan_candidate |
| `src/execution_backbone/rate_limiter.py` | none | __init__.py, execution_runtime.py, execution_runtime_projection_bridge.py, execution_runtime_support.py, +2 more | execution_backbone (5), protocols (1) | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/__init__.py` | none | none | none | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/divergence_classifier.py` | none | execution_runtime.py, execution_runtime_models.py, recovery_trigger.py | execution_backbone (3) | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/fill_reconciler.py` | none | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/order_reconciler.py` | none | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/position_reconciler.py` | none | execution_runtime.py, execution_runtime_models.py | execution_backbone (2) | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/recovery_trigger.py` | divergence_classifier.py | execution_runtime.py, execution_runtime_models.py, scheduler.py | execution_backbone (3) | insufficient_evidence |
| `src/execution_backbone/reconciliation_layer/scheduler.py` | __init__.py, emergency_circuit_breaker.py, execution_runtime.py, loader.py, +1 more | execution_runtime_bootstrap.py, run_build9_core_smoke_support.py | scripts (1), protocols (1) | insufficient_evidence |
| `src/execution_backbone/slippage_model.py` | none | __init__.py, execution_runtime.py, execution_runtime_projection_bridge.py, execution_runtime_support.py | execution_backbone (3), protocols (1) | insufficient_evidence |
| `src/execution_backbone/spread_guard.py` | none | __init__.py, execution_runtime.py, execution_runtime_projection_bridge.py, execution_runtime_support.py, +2 more | execution_backbone (5), protocols (1) | insufficient_evidence |
| `src/execution_backbone/venue_constraints_provider.py` | __init__.py, atomic_io.py, intent_builder.py | __init__.py, bootstrap.py, execution_adapter.py, execution_runtime.py, +1 more | execution_backbone (2), venue_adapters (2), protocols (1) | insufficient_evidence |

## interface_contracts
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/interface_contracts/__init__.py` | artifact_contracts.py, binance_contracts.py, build14_contracts.py, closed_episode_contracts.py, +25 more | __init__.py, action_support.py, alert_manager.py, artifact_action_composer.py, +170 more | protocols (44), local_replay_runtime (26), engines (17), monitoring (16) | insufficient_evidence |
| `src/interface_contracts/artifact_contracts.py` | __init__.py, artifact_contracts_models.py, artifact_contracts_runtime.py | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/artifact_contracts_models.py` | feature_lock_contracts.py | artifact_contracts.py, artifact_contracts_runtime.py | interface_contracts (2) | orphan_candidate |
| `src/interface_contracts/artifact_contracts_runtime.py` | artifact_contracts_models.py | artifact_contracts.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/atomic_io.py` | none | action_support.py, artifact_exporter.py, closed_episode_journal.py, compiled_artifact_registry_store.py, +50 more | scripts (20), protocols (10), local_replay_runtime (7), monitoring (3) | insufficient_evidence |
| `src/interface_contracts/binance_contracts.py` | none | __init__.py, bootstrap.py, credential_loader.py, error_classifier.py, +11 more | venue_adapters (9), scripts (2), interface_contracts (2), protocols (2) | orphan_candidate |
| `src/interface_contracts/build14_contracts.py` | domain_types.py | __init__.py, contracts.py, enums.py | complete_enablers (2), interface_contracts (1) | orphan_candidate |
| `src/interface_contracts/closed_episode_contracts.py` | domain_types.py, forecast_contracts.py | __init__.py, engine_coordination_contracts.py | interface_contracts (2) | insufficient_evidence |
| `src/interface_contracts/dashboard_command_contracts.py` | domain_types.py | __init__.py, run_shadow_credential_seed.py, shadow_vps_service_contracts.py, vps_recovery_contracts.py | interface_contracts (3), scripts (1) | insufficient_evidence |
| `src/interface_contracts/decision_contracts.py` | domain_types.py | __init__.py, forecast_contracts.py, signal_candidate_adapter.py, signal_candidate_adapter.py | engines (2), interface_contracts (2) | orphan_candidate |
| `src/interface_contracts/domain_types.py` | none | __init__.py, artifact_release_candidate.py, build14_contracts.py, closed_episode_contracts.py, +26 more | interface_contracts (17), scripts (2), engines (2), local_replay_runtime (2) | insufficient_evidence |
| `src/interface_contracts/engine_coordination_contracts.py` | closed_episode_contracts.py, domain_types.py, forecast_contracts.py, refusal_records.py | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/engine_validation_contracts.py` | none | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/error_contracts.py` | none | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/feature_lock_contracts.py` | none | __init__.py, artifact_contracts_models.py, market_physics_math.py | interface_contracts (2), data_backbone (1) | insufficient_evidence |
| `src/interface_contracts/forecast_contracts.py` | decision_contracts.py, domain_types.py | __init__.py, closed_episode_contracts.py, engine_a_runtime_support.py, engine_b_runtime.py, +10 more | engines (10), interface_contracts (4) | orphan_candidate |
| `src/interface_contracts/live_complete_actions.py` | none | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/market_event_contracts.py` | domain_types.py | __init__.py | interface_contracts (1) | orphan_candidate |
| `src/interface_contracts/meta_contracts.py` | domain_types.py | __init__.py | interface_contracts (1) | orphan_candidate |
| `src/interface_contracts/ml_backtest_training_contracts.py` | none | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/ml_model_artifact.py` | domain_types.py | __init__.py, ml_trainer.py, registry.py | calibration_methods (1), interface_contracts (1), meta_learning (1) | orphan_candidate |
| `src/interface_contracts/ml_model_transport_contracts.py` | domain_types.py | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/numeric_contracts.py` | none | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/operator_contracts.py` | domain_types.py | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/pair_catalog.py` | binance_contracts.py | __init__.py, shadow_live_plan.py, state.py | cockpit (1), interface_contracts (1), protocols (1) | insufficient_evidence |
| `src/interface_contracts/refusal_records.py` | domain_types.py | __init__.py, engine_coordination_contracts.py, refusal_journal.py | interface_contracts (2), meta_minimal (1) | insufficient_evidence |
| `src/interface_contracts/regime_detector_artifact.py` | domain_types.py | __init__.py, lob_regime_features.py, regime_detector_label_contracts.py, regime_detector_shadow_audit_contracts.py | interface_contracts (3), data_backbone/microstructure (1) | insufficient_evidence |
| `src/interface_contracts/regime_detector_label_contracts.py` | regime_detector_artifact.py | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/regime_detector_shadow_audit_contracts.py` | regime_detector_artifact.py | __init__.py | interface_contracts (1) | orphan_candidate |
| `src/interface_contracts/shadow_vps_service_contracts.py` | dashboard_command_contracts.py, domain_types.py | __init__.py, run_shadow_vps_service.py, runtime_support.py, shadow_vps_redaction.py, +12 more | scripts (7), monitoring (5), interface_contracts (2), cockpit (1) | orphan_candidate |
| `src/interface_contracts/strategy_identity.py` | domain_types.py, forecast_contracts.py | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/venue_error_contracts.py` | none | __init__.py | interface_contracts (1) | insufficient_evidence |
| `src/interface_contracts/vps_recovery_contracts.py` | dashboard_command_contracts.py, domain_types.py, shadow_vps_service_contracts.py | __init__.py | interface_contracts (1) | insufficient_evidence |

## local_replay_runtime
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/local_replay_runtime/__init__.py` | __init__.py, artifact_ablation_study.py, artifact_exporter.py, artifact_manifest.py, +47 more | export_dir_bridge.py, export_dir_bridge_models.py, export_dir_bridge_support.py, local_replay_shadow_import_support.py, +11 more | scripts (7), backtest_artifact_import (5), protocols (3) | coded_not_displayed |
| `src/local_replay_runtime/artifact_ablation_study.py` | dtr_record_builder.py | __init__.py, artifact_proof_summary_builder.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/artifact_exporter.py` | atomic_io.py, replay_run_manifest.py | __init__.py, replay_executor.py, replay_orchestrator_resume.py | local_replay_runtime (3) | runtime_only |
| `src/local_replay_runtime/artifact_manifest.py` | __init__.py | __init__.py, compatibility_policy.py, contracts.py, contracts.py, +3 more | backtest_artifact_import (4), local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/artifact_proof_summary_builder.py` | __init__.py, artifact_ablation_study.py, contracts.py, local_lab_calibration_methods_review.py, +4 more | __init__.py | local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/artifact_release_candidate.py` | domain_types.py, local_lab_scope_matrix.py | __init__.py, local_lab_promotion_readiness.py, local_lab_upload_bridge_candidate.py, local_lab_upload_bridge_candidate_support.py | backtest_artifact_import (2), local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/artifact_upload_bridge_candidate.py` | none | local_lab_promotion_readiness.py, local_lab_upload_bridge_candidate.py, local_lab_upload_bridge_candidate_support.py | backtest_artifact_import (2), local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/contracts.py` | __init__.py, artifact_manifest.py, enums.py | __init__.py, local_lab_replay_ticket_index.py, local_lab_upload_bridge_candidate_support.py, orchestrator.py, +2 more | local_replay_runtime (5), backtest_artifact_import (1) | coded_not_displayed |
| `src/local_replay_runtime/edge_gate_calibration.py` | __init__.py, __init__.py, atomic_io.py, decision_state_encoder.py, +1 more | __init__.py, local_lab_calibration_normalized_report.py, local_lab_multiple_testing_review.py | local_replay_runtime (3) | runtime_only |
| `src/local_replay_runtime/enums.py` | none | __init__.py, contracts.py, contracts.py, orchestrator.py, +1 more | local_replay_runtime (3), backtest_artifact_import (2) | coded_not_displayed |
| `src/local_replay_runtime/errors.py` | __init__.py | __init__.py | local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/historical_data_gateway.py` | __init__.py, decision_state_encoder.py | __init__.py, historical_snapshot_loader.py, local_lab_ml_artifact_training.py, ml_backtest_projection.py, +9 more | local_replay_runtime (13) | coded_not_displayed |
| `src/local_replay_runtime/historical_snapshot_loader.py` | __init__.py, decision_state_encoder.py, historical_data_gateway.py | __init__.py, local_lab_execution_telemetry_artifact.py, local_lab_regime_detector_artifact_training.py, regime_detector_dataset_builder.py, +3 more | local_replay_runtime (7) | coded_not_displayed |
| `src/local_replay_runtime/live_complete_operator_audit_report.py` | __init__.py, atomic_io.py, ml_final_audit_report.py, regime_detector_final_audit_report.py | __init__.py, shadow_vps_service_complete_support.py | scripts (1), local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_calibration_methods_review.py` | __init__.py, decision_state_encoder.py, dtr_record_builder.py | __init__.py, artifact_proof_summary_builder.py, local_lab_calibration_normalized_report.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_calibration_normalized_report.py` | dtr_record_builder.py, edge_gate_calibration.py, local_lab_calibration_methods_review.py, local_lab_multiple_testing_review.py, +1 more | __init__.py | local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_execution_review.py` | __init__.py | __init__.py, local_lab_execution_runtime_projection.py, local_lab_execution_telemetry_artifact.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_execution_runtime_projection.py` | domain_types.py, local_lab_execution_review.py | __init__.py, artifact_proof_summary_builder.py, execution_runtime_projection_bridge.py | local_replay_runtime (2), protocols (1) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_execution_telemetry_archive_support.py` | local_lab_execution_telemetry_artifact.py | local_lab_execution_telemetry_artifact.py | local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` | historical_snapshot_loader.py, injected_stream_loader.py, local_lab_execution_review.py, local_lab_execution_telemetry_archive_support.py, +1 more | local_lab_execution_telemetry_archive_support.py, run_local_lab_analysis_bundle.py, shadow_vps_service_telemetry_support.py | scripts (2), local_replay_runtime (1) | runtime_only |
| `src/local_replay_runtime/local_lab_loss_surrogate.py` | decision_state_encoder.py, dtr_record_builder.py, local_lab_scope_matrix.py | __init__.py, local_lab_recalibration_plan.py, local_lab_research_priority.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_ml_artifact_training.py` | __init__.py, __init__.py, dtr_record_builder.py, historical_data_gateway.py, +2 more | __init__.py, ml_final_audit_report.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_multiple_testing_review.py` | __init__.py, edge_gate_calibration.py, local_lab_tail_risk_review.py | __init__.py, artifact_proof_summary_builder.py, local_lab_calibration_normalized_report.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_promotion_readiness.py` | __init__.py, artifact_release_candidate.py, artifact_upload_bridge_candidate.py | run_local_lab_analysis_bundle.py | scripts (1) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_recalibration_plan.py` | contracts.py, local_lab_loss_surrogate.py, local_lab_scope_matrix.py | __init__.py, local_lab_replay_candidate_queue.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_regime_detector_artifact_training.py` | __init__.py, __init__.py, historical_snapshot_loader.py, regime_detector_dataset_builder.py, +2 more | __init__.py, regime_detector_final_audit_report.py, regime_detector_profile_comparison.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_replay_candidate_queue.py` | local_lab_recalibration_plan.py, local_lab_research_priority.py | __init__.py, local_lab_replay_ticket_index.py, local_lab_replay_workflow_loader.py, local_lab_replay_workflow_manifest.py | local_replay_runtime (4) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_replay_dispatch_plan.py` | local_lab_replay_ticket_index.py | __init__.py, local_lab_replay_workflow_loader.py, local_lab_replay_workflow_manifest.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_replay_ticket_index.py` | __init__.py, contracts.py, local_lab_replay_candidate_queue.py | __init__.py, local_lab_replay_dispatch_plan.py, local_lab_replay_workflow_loader.py, local_lab_replay_workflow_manifest.py | local_replay_runtime (4) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_replay_workflow_loader.py` | local_lab_replay_candidate_queue.py, local_lab_replay_dispatch_plan.py, local_lab_replay_ticket_index.py, local_lab_replay_workflow_manifest.py | none | none | runtime_only |
| `src/local_replay_runtime/local_lab_replay_workflow_manifest.py` | local_lab_replay_candidate_queue.py, local_lab_replay_dispatch_plan.py, local_lab_replay_ticket_index.py | __init__.py, local_lab_replay_workflow_loader.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_research_priority.py` | contracts.py, local_lab_loss_surrogate.py, local_lab_scope_matrix.py | __init__.py, local_lab_replay_candidate_queue.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_scope_matrix.py` | __init__.py, dtr_record_builder.py | __init__.py, artifact_release_candidate.py, local_lab_loss_surrogate.py, local_lab_ml_artifact_training.py, +2 more | local_replay_runtime (6) | coded_not_displayed |
| `src/local_replay_runtime/local_lab_tail_risk_review.py` | __init__.py, decision_state_encoder.py, dtr_record_builder.py | __init__.py, local_lab_calibration_normalized_report.py, local_lab_multiple_testing_review.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/ml_backtest_projection.py` | __init__.py, dtr_record_builder.py, historical_data_gateway.py | __init__.py, local_lab_ml_artifact_training.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/ml_final_audit_report.py` | __init__.py, local_lab_ml_artifact_training.py | __init__.py, live_complete_operator_audit_report.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/orchestrator.py` | artifact_manifest.py, contracts.py, enums.py | __init__.py, local_lab_upload_bridge_candidate_support.py | backtest_artifact_import (1), local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/performance_mode_guard.py` | replay_run_manifest.py, replay_session_config.py | __init__.py, replay_orchestrator_execution.py, replay_orchestrator_models.py, replay_orchestrator_resume.py | local_replay_runtime (4) | coded_not_displayed |
| `src/local_replay_runtime/regime_detector_dataset_builder.py` | __init__.py, __init__.py, historical_snapshot_loader.py | __init__.py, local_lab_regime_detector_artifact_training.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/regime_detector_final_audit_report.py` | __init__.py, __init__.py, historical_snapshot_loader.py, local_lab_regime_detector_artifact_training.py, +2 more | __init__.py, live_complete_operator_audit_report.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/regime_detector_profile_comparison.py` | __init__.py, __init__.py, historical_snapshot_loader.py, local_lab_regime_detector_artifact_training.py | __init__.py, regime_detector_final_audit_report.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/regime_detector_shadow_audit_diagnosis.py` | __init__.py | __init__.py, regime_detector_final_audit_report.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/replay_clock.py` | contracts.py, historical_data_gateway.py | __init__.py, replay_orchestrator_execution.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/replay_dtr_exporter.py` | dtr_record_builder.py | __init__.py, replay_executor.py, run_local_lab_post_trade_review.py | local_replay_runtime (2), scripts (1) | runtime_only |
| `src/local_replay_runtime/replay_event_router.py` | __init__.py, historical_data_gateway.py, historical_snapshot_loader.py | __init__.py | local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/replay_executor.py` | artifact_exporter.py, dtr_record_builder.py, replay_dtr_exporter.py, replay_metrics_collector.py, +1 more | __init__.py, replay_orchestrator_execution.py, replay_orchestrator_models.py, replay_orchestrator_resume.py, +1 more | local_replay_runtime (5) | coded_not_displayed |
| `src/local_replay_runtime/replay_metrics_collector.py` | __init__.py, decision_state_encoder.py, dtr_record_builder.py | __init__.py, export_dir_bridge_support.py, replay_executor.py, replay_orchestrator_execution.py, +1 more | local_replay_runtime (4), backtest_artifact_import (1) | coded_not_displayed |
| `src/local_replay_runtime/replay_orchestrator.py` | replay_orchestrator_execution.py, replay_orchestrator_models.py | __init__.py | local_replay_runtime (1) | coded_not_displayed |
| `src/local_replay_runtime/replay_orchestrator_chunking.py` | historical_data_gateway.py, replay_orchestrator_models.py | replay_orchestrator_execution.py, replay_orchestrator_resume.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/replay_orchestrator_execution.py` | __init__.py, atomic_io.py, dtr_record_builder.py, historical_data_gateway.py, +14 more | replay_orchestrator.py | local_replay_runtime (1) | runtime_only |
| `src/local_replay_runtime/replay_orchestrator_io.py` | dtr_record_builder.py, replay_orchestrator_models.py, replay_run_manifest.py, replay_session_config.py | replay_orchestrator_execution.py, replay_orchestrator_resume.py | local_replay_runtime (2) | runtime_only |
| `src/local_replay_runtime/replay_orchestrator_models.py` | __init__.py, historical_data_gateway.py, performance_mode_guard.py, replay_executor.py, +3 more | replay_orchestrator.py, replay_orchestrator_chunking.py, replay_orchestrator_execution.py, replay_orchestrator_io.py, +1 more | local_replay_runtime (5) | coded_not_displayed |
| `src/local_replay_runtime/replay_orchestrator_resume.py` | artifact_exporter.py, atomic_io.py, historical_data_gateway.py, performance_mode_guard.py, +7 more | replay_orchestrator_execution.py | local_replay_runtime (1) | runtime_only |
| `src/local_replay_runtime/replay_run_manifest.py` | __init__.py | __init__.py, artifact_exporter.py, export_dir_bridge_support.py, local_lab_execution_telemetry_artifact.py, +6 more | local_replay_runtime (8), scripts (1), backtest_artifact_import (1) | coded_not_displayed |
| `src/local_replay_runtime/replay_scope_identity.py` | __init__.py, historical_data_gateway.py, replay_session_config.py | __init__.py, replay_orchestrator_execution.py, replay_orchestrator_models.py | local_replay_runtime (3) | coded_not_displayed |
| `src/local_replay_runtime/replay_session_config.py` | __init__.py, replay_run_manifest.py | __init__.py, performance_mode_guard.py, replay_orchestrator_execution.py, replay_orchestrator_io.py, +3 more | local_replay_runtime (7) | coded_not_displayed |
| `src/local_replay_runtime/replay_state_store.py` | __init__.py, atomic_io.py, historical_data_gateway.py, replay_executor.py, +1 more | __init__.py, replay_orchestrator_execution.py, replay_orchestrator_resume.py | local_replay_runtime (3) | runtime_only |
| `src/local_replay_runtime/run_consistency_guard.py` | dtr_record_builder.py | __init__.py, replay_orchestrator_execution.py, replay_orchestrator_models.py, replay_orchestrator_resume.py | local_replay_runtime (4) | coded_not_displayed |
| `src/local_replay_runtime/runtime_evidence.py` | atomic_io.py, contracts.py | __init__.py | local_replay_runtime (1) | runtime_only |
| `src/local_replay_runtime/shadow_execution_simulator.py` | decision_state_encoder.py, dtr_record_builder.py, historical_data_gateway.py, market_physics_math.py | __init__.py, replay_orchestrator_execution.py | local_replay_runtime (2) | coded_not_displayed |
| `src/local_replay_runtime/walk_forward_review.py` | none | __init__.py, artifact_proof_summary_builder.py | local_replay_runtime (2) | coded_not_displayed |

## secrets_manager
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/secrets_manager/__init__.py` | cli.py, loader.py, sealer.py | credential_loader.py, telegram_alerter.py | alerting (1), venue_adapters (1) | coded_not_displayed |
| `src/secrets_manager/__main__.py` | cli.py | none | none | coded_not_displayed |
| `src/secrets_manager/_dpapi.py` | _dpapi_posix.py, _dpapi_windows.py | loader.py, sealer.py | secrets_manager (2) | coded_not_displayed |
| `src/secrets_manager/_dpapi_posix.py` | none | _dpapi.py | secrets_manager (1) | coded_not_displayed |
| `src/secrets_manager/_dpapi_windows.py` | none | _dpapi.py | secrets_manager (1) | coded_not_displayed |
| `src/secrets_manager/cli.py` | loader.py, sealer.py | __init__.py, __main__.py | secrets_manager (2) | coded_not_displayed |
| `src/secrets_manager/loader.py` | _dpapi.py, atomic_io.py | __init__.py, cli.py, sealer.py | secrets_manager (3) | coded_not_displayed |
| `src/secrets_manager/sealer.py` | _dpapi.py, atomic_io.py, loader.py | __init__.py, cli.py, run_shadow_credential_seed.py | secrets_manager (2), scripts (1) | runtime_only |

## venue_adapters
| File | Direct Internal Imports | Reverse Internal Importers | Importer Domains | Current Discovery Status |
|---|---|---|---|---|
| `src/venue_adapters/__init__.py` | none | none | none | coded_not_displayed |
| `src/venue_adapters/binance_spot/__init__.py` | account_feature_provider.py, bootstrap.py, credential_loader.py, error_classifier.py, +9 more | run_sharia_account_audit.py | scripts (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/account_feature_provider.py` | __init__.py | __init__.py | venue_adapters (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/bootstrap.py` | binance_contracts.py, execution_adapter.py, rest_client.py, time_sync.py, +2 more | __init__.py, execution_runtime_bootstrap.py | protocols (1), venue_adapters (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/credential_loader.py` | __init__.py, __init__.py, binance_contracts.py | __init__.py, shadow_vps_service_io_support.py | scripts (1), venue_adapters (1) | runtime_only |
| `src/venue_adapters/binance_spot/error_classifier.py` | binance_contracts.py | __init__.py | venue_adapters (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/execution_adapter.py` | __init__.py, binance_contracts.py, execution_runtime_models.py, intent_builder.py, +5 more | __init__.py, bootstrap.py | venue_adapters (2) | coded_not_displayed |
| `src/venue_adapters/binance_spot/order_translator.py` | __init__.py, binance_contracts.py, intent_builder.py | __init__.py, execution_adapter.py | venue_adapters (2) | coded_not_displayed |
| `src/venue_adapters/binance_spot/orderbook_manager.py` | __init__.py, venue_stream_freshness.py | __init__.py, rest_client.py, ws_client.py | venue_adapters (3) | coded_not_displayed |
| `src/venue_adapters/binance_spot/rate_limiter.py` | __init__.py | __init__.py, rest_client.py | venue_adapters (2) | coded_not_displayed |
| `src/venue_adapters/binance_spot/rest_client.py` | __init__.py, binance_contracts.py, orderbook_manager.py, rate_limiter.py | __init__.py, bootstrap.py, execution_adapter.py, shadow_live_websocket.py, +1 more | venue_adapters (4), protocols (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/time_sync.py` | binance_contracts.py, loader.py | __init__.py, bootstrap.py, execution_adapter.py, execution_runtime_bootstrap.py, +3 more | scripts (3), venue_adapters (3), protocols (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/user_data_events.py` | __init__.py, binance_contracts.py, execution_runtime_models.py | __init__.py, execution_adapter.py, user_data_ws_client.py | venue_adapters (3) | coded_not_displayed |
| `src/venue_adapters/binance_spot/user_data_ws_client.py` | binance_contracts.py, user_data_events.py | __init__.py, bootstrap.py, execution_runtime_bootstrap.py | venue_adapters (2), protocols (1) | coded_not_displayed |
| `src/venue_adapters/binance_spot/ws_client.py` | heartbeat_monitor.py, orderbook_manager.py, rest_client.py, runtime_gateway.py | __init__.py | venue_adapters (1) | coded_not_displayed |
