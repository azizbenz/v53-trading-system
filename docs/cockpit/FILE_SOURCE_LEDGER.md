# FILE_SOURCE_LEDGER

## __init__.py

### `src/__init__.py`
- responsibility: production module
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## alerting

### `src/alerting/__init__.py`
- responsibility: Bounded external alert delivery adapters.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/alerting/telegram_alerter.py`
- responsibility: Bounded Telegram alert delivery over existing AlertRecord contracts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: alert, alerts, config, key_path, message_prefix, path, payload, post_func
- outputs: build_telegram_message, load_telegram_alerter_config, load_telegram_alerter_config_from_file
- runtime_files_read: .sealed.json, .sealed.yaml, .sealed.yml
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## backtest_artifact_import

### `src/backtest_artifact_import/__init__.py`
- responsibility: Controlled local->VPS artifact import scaffold.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/compatibility_policy.py`
- responsibility: Bounded compatibility-registry policy for governed artifact intake.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: manifest, registry
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/contracts.py`
- responsibility: Contracts for controlled local->VPS artifact import.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: ArtifactImportSummary, ArtifactPayloadRefBundle
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_version = Field(..., min_length=1)
- thresholds_or_constants: feature_lineage_required = False, feature_lineage_present = False, self.lineage.classification compare self.classification, self.lineage.strategy_version compare self.strategy_version, self.lineage.source_version compare self.source_version
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/ed25519_verifier.py`
- responsibility: Minimal pure-Python Ed25519 verification for governed artifact intake.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: message, public_key_b64, signature_b64
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/backtest_artifact_import/errors.py`
- responsibility: Errors for the controlled artifact import scaffold.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/export_dir_bridge.py`
- responsibility: Typed bridge from governed LOCAL_REPLAY export directories to import/upload contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: activation_stage, allowed_action_kinds, allowed_action_units, allowed_hook_ids, artifact_class, artifact_scope, artifact_version, bundle, candidate_ids, covariance_shrinkage_matrix_ref, distilled_logic_format, drift_score_threshold, export_dir, feature_bridge_ref, feature_set_version, governance_reference_date, import_context, import_decision, lifecycle_policy, local_replay_evidence, observed_drift_score, payload_bundle, proof_summary, regime_features_used, replay_plan, requested_promotion_state, review_state, rules, signature_envelope, target_runtime_mode, training_end, transform_set_version, upload_context, uploaded_by
- outputs: build_artifact_export_bundle_from_replay_import_context, build_feature_locks_from_feature_bridge, build_import_context_from_export_dir, build_import_context_from_replay_plan, build_replay_plan_from_export_dir, build_upload_context_from_replay_import_context, build_upload_request_from_export_dir, build_upload_request_from_replay_plan
- runtime_files_read: feature_bridge.json, parity_diagnostics.json, replay_dtr.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/backtest_artifact_import/export_dir_bridge_models.py`
- responsibility: Typed models shared by the governed LOCAL_REPLAY export-dir bridge.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/export_dir_bridge_support.py`
- responsibility: Support helpers for governed LOCAL_REPLAY export discovery and validation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/backtest_artifact_import/local_lab_upload_bridge_candidate.py`
- responsibility: Dry-run governed bridge builder from Local IA Lab release candidates to VPS import contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: artifact_class, artifact_scope, drift_score_threshold, governance_reference_date, lifecycle_ttl_days, proof_summary, release_candidate, release_gate_summary_ref, rule_half_life_days, source_artifact_summary_ref, training_end, uploaded_by
- outputs: build_local_lab_artifact_upload_dry_run_bridge, build_local_lab_release_gate_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/backtest_artifact_import/local_lab_upload_bridge_candidate_support.py`
- responsibility: Support helpers for Local IA Lab upload bridge assembly.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: source_artifact_path
- outputs: build_local_lab_source_artifact_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/ml_model_transport.py`
- responsibility: Governed supplementary transport helpers for bounded ML model artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: artifact_filename, bundle, export_dir, governance_reference_date, payload_bundle, replay_plan, signature_envelope, source_artifact_ref, summary_filename, transport_artifact_ref, transport_package, upload_context, uploaded_by
- outputs: build_ml_model_source_artifact_summary, build_upload_request_from_replay_plan_with_ml_model_artifact, load_ml_model_artifact
- runtime_files_read: ml_model_artifact.json, ml_model_artifact.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/monitoring_projection.py`
- responsibility: Thin monitoring projection adapters for governed LOCAL_REPLAY imports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: summary
- outputs: build_replay_import_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/regime_detector_transport.py`
- responsibility: Governed supplementary transport helpers for RegimeDetectorML artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: artifact_filename, bundle, export_dir, governance_reference_date, payload_bundle, replay_plan, signature_envelope, source_artifact_ref, summary_filename, transport_artifact_ref, transport_package, upload_context, uploaded_by
- outputs: build_regime_detector_artifact_summary, build_upload_request_from_replay_plan_with_regime_detector_artifact, load_regime_detector_artifact
- runtime_files_read: regime_detector_artifact.json, regime_detector_artifact.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/signature_policy.py`
- responsibility: Governed trust-store and payload-hash policy for artifact signature envelopes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: envelope, expected_payload_hash_sha256, manifest, signature_verifier, trust_store, trusted_entry
- outputs: build_lab_fixture_signature_envelope
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/upload_bridge.py`
- responsibility: Thin governed bridge from upload dry-run payloads to import contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: import_decision, request
- outputs: build_artifact_upload_decision, build_import_request_from_upload_request
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/backtest_artifact_import/validators.py`
- responsibility: Guards for controlled artifact import.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: decision, expected_payload_hash_sha256, manifest, request, signature_verifier
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

## calibration_loader

### `src/calibration_loader/__init__.py`
- responsibility: Shared-core calibration loader for dynamic threshold artifacts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_loader/contracts.py`
- responsibility: Typed contracts for shared dynamic-threshold calibration artifacts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_loader/loader.py`
- responsibility: Shared loader for signed dynamic-threshold calibration artifacts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: path
- outputs: load_calibration_artifact, load_calibration_collection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## calibration_methods

### `src/calibration_methods/__init__.py`
- responsibility: Shared Local IA Lab calibration-method primitives.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/bootstrap.py`
- responsibility: Shared Local IA Lab stationary bootstrap helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: config, estimator, max_block_length, values
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: integrated_autocorrelation = 1.0 + sum(lag * autocorrelation for lag, autocorrelation in positive_autocorrelations), lower_index = int(math.floor(position))
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/dsr.py`
- responsibility: Shared Local IA Lab Deflated Sharpe Ratio helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: acceptance_floor, returns, trial_count
- outputs: compute_deflated_sharpe_ratio
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/energy_distance.py`
- responsibility: Energy distance test for shadow gate distribution drift (Székely & Rizzo, 2004).
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: acceptance_floor, backtest_returns, n_permutations, random_seed, shadow_returns
- outputs: compute_energy_distance_test
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/calibration_methods/execution.py`
- responsibility: Shared Local IA Lab execution-calibration helpers for THR-X01 to THR-X05.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: additive_margin_ms, burst_horizon_minutes, burst_margin_multiplier, candidate_sizes, final_sizes, hampel_k, hampel_window_size, hard_cap_bps, hard_cap_ms, hard_cap_quota_ratio, hard_cap_s, huber_k, interarrival_s, k, min_r_squared, observed_calls_per_minute, offsets_ms, quantile, quota_call_counts, quota_limit_calls_per_minute_values, quota_probe_durations_s, reference_quantile, slippage_bps, spread_bps, values, window_size
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: rate_series = tuple(float(value) for value in observed_calls_per_minute), rate_series = tuple(
            (call_count / duration_s) * 60.0
            for call_count, duration_s in zip(quota_call_counts, quota_probe_durations_s)
        ), threshold = k * scale, new_weights = tuple(
            1.0 if abs(residual) <= threshold else threshold / abs(residual)
            for residual in residuals
        )
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/hansen_spa.py`
- responsibility: Bounded Hansen SPA test for multi-engine shadow promotion.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: acceptance_ceiling, bootstrap_samples, expected_block_length, loss_differentials_by_candidate, rng_seed
- outputs: compute_hansen_spa_test
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/hard_cap_floor.py`
- responsibility: Shared Local IA Lab helpers for human hard-floor / hard-cap publication.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: candidate_value, human_cap, human_floor
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/ks_test.py`
- responsibility: Two-sample Kolmogorov-Smirnov test for shadow gate distribution drift.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: acceptance_floor, backtest_returns, shadow_returns
- outputs: compute_ks_2sample
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/calibration_methods/mann_kendall.py`
- responsibility: Mann-Kendall monotonic trend test for shadow gate drift detection.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: acceptance_floor, values
- outputs: compute_mann_kendall_test
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/calibration_methods/ml_backtest_projection.py`
- responsibility: LAB_ONLY projection from ML backtest contracts into trainer-ready rows.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: dataset, include_route_features, sample
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/ml_trainer.py`
- responsibility: LAB_ONLY LightGBM trainer for the bounded V5.3 ML confidence layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: request
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/multiple_testing.py`
- responsibility: Bounded Local IA Lab multiple-testing helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: family_alpha, hypotheses
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/multiple_testing_guard.py`
- responsibility: Harvey-Liu-Zhu multiple-testing guard helpers for V5.3 promotion gates.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: observation_count, observed_pair_count, pair_count_mode, promotion_pair_floor, raw_sharpe, repo_pair_universe_count
- outputs: compute_harvey_liu_zhu_deflated_sharpe
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: V53_CANONICAL_SHADOW_PAIR_FLOOR = 20, floor_applied = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/pot_gpd.py`
- responsibility: Shared Local IA Lab POT-GPD tail-risk helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: config, losses
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: index = int(math.floor((len(values) - 1) * probability)), ratio = (mean_excess * mean_excess) / variance, xi_hat = 0.5 * (1.0 - ratio)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/psr.py`
- responsibility: Probabilistic Sharpe Ratio — Bailey & López de Prado (2012).
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: acceptance_floor, benchmark_sharpe, returns
- outputs: compute_probabilistic_sharpe_ratio
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/calibration_methods/regime_detector_feature_calibration.py`
- responsibility: Feature-profile selection helpers for RegimeDetectorML training.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: feature_values, profile
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/regime_detector_projection.py`
- responsibility: Projection from Local-Lab regime datasets into trainer rows.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: dataset, feature_profile, sample, selected_feature_names
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/regime_detector_trainer.py`
- responsibility: LAB_ONLY LightGBM trainer for VPS-shadow LOB RegimeDetectorML artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: request
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/stationarity.py`
- responsibility: Shared Local IA Lab stationarity helpers (ADF + KPSS, bounded implementation).
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: series
- outputs: compute_adf_level_stationarity, compute_kpss_level_stationarity
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: critical_value_10pct = 0.347, critical_value_5pct = 0.463, critical_value_1pct = 0.739
- control_flags_or_gates: none
- duplication_notes: none

### `src/calibration_methods/walkforward.py`
- responsibility: Shared Local IA Lab purged walk-forward helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: config, observation_count
- outputs: build_purged_walk_forward_plan
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/calibration_methods/walls_and_spoofing_calibration.py`
- responsibility: Feature-set selection helpers for walls/spoofing ML integration.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: feature_values, profile
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## cockpit

### `src/cockpit/__init__.py`
- responsibility: V5.3 Local Lab Cockpit — minimal HTTP UI to operate the Shadow runtime.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: kill
- duplication_notes: none

### `src/cockpit/action_support.py`
- responsibility: Governed cockpit actions and audited local backtest job helpers.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: vps
- status: runtime_only
- inputs: artifact_id, artifact_kind, artifact_manifest, baseline_export_dir, command_kind, export_dir, feature_profile, feature_set_version, filename, ingress_root, job_kind, jobs_root, limit, lineage_version, operator_reason, payload, python_executable, queue_root, requested_by, review_state, signed_by, target_pair, validation_status
- outputs: CockpitQueuedCommandSummary, load_backtest_job_records
- runtime_files_read: *.json, *.yml, */job.json, edge_gate.yml, job.json, stdout.log
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/cockpit/queue_support.py`
- responsibility: Cockpit-local governed queue helpers with the canonical Build-17 wire format.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: vps
- status: displayed
- inputs: queue_root, request
- outputs: build_dashboard_command_queue_snapshot
- runtime_files_read: *.json, {request.timestamp_ms}_{request.request_id}.request.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `src/cockpit/runtime_support.py`
- responsibility: Typed readers and compact summaries for cockpit runtime surfaces.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: vps
- status: displayed
- inputs: backtest_jobs_root, log_query, monitoring_payload, observability, observability_output_dir, query, queue_root, recent_logs, service_dir
- outputs: ArtifactFamilyComparisonSummary, ArtifactFamilyVisibilitySummary, BacktestJobsSummary, ObservabilityPageSummary, build_cockpit_alerts, read_logs_summary, read_observability_summary, read_runtime_surfaces
- runtime_files_read: local_observability_stack.summary.json, shadow_vps_service.events.jsonl, shadow_vps_service.state.json, shadow_vps_service_monitoring_backend_payload.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/cockpit/server.py`
- responsibility: FastAPI app factory for the V5.3 cockpit operator shell.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: displayed
- inputs: grafana_url, paths, prometheus_url, welcome_message
- outputs: create_app
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/cockpit/source_discovery_support.py`
- responsibility: Read-only source discovery runner for the V5.3 cockpit audit.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: runtime_only
- inputs: artifacts, dashboard_fields, emit_json, file_ledger, formulas, operational_fields, output_dir, pages, repo_root, rows, runtime_files, runtime_root
- outputs: build_argument_parser, build_duplication_audit, build_formula_ledger, build_missing_backlog
- runtime_files_read: build/build11_live_websocket_campaign/live_websocket_config.json, duplication_audit.json, file_source_ledger.json, formula_source_ledger.json, missing_backlog.json, page_surfaces.json, runtime_files.json, thresholds.yml
- formulas_or_derived_metrics: _FORMULA_HINT_PATTERN = re.compile(
    r"\b(threshold|limit|floor|cap|ratio|rate|drawdown|ce_net|exec_rate|sterilization|kill|lineage|warmup)\b",
    re.IGNORECASE,
), _RUNTIME_NAME_HINTS = (
    "warmup",
    "shadow_vps_service",
    "feature_bridge",
    "replay",
    "grafana",
    "prometheus",
    "observability",
    "threshold",
    "model_risk",
    "refusal",
    "queue",
    "lineage",
    "live_complete",
    "capture",
    "snapshot",
    "user_data",
    "review",
    "verdict",
    "artifact",
    "consistency",
    "performance_mode",
    "session_config",
), thresholds = tuple(sorted(set(re.findall(r"\b[A-Z_]*(?:THRESHOLD|LIMIT|PORT|TIMEOUT|INTERVAL)[A-Z_0-9]*\b", text)))), flags = set(
        re.findall(
            r"\b(eligible_to_trade|runtime_mode|review_only|blocked|suspended|halt|kill|gate|queue|control_ready|passed|shadow_only)\b",
            text,
            re.IGNORECASE,
        )
    )
- thresholds_or_constants: "threshold" compare lower, "warmup" compare lower, "rate" compare target_lower
- control_flags_or_gates: blocked, control_ready, eligible_to_trade, gate, halt, kill, passed, queue, review_only, runtime_mode, shadow_only, suspended
- duplication_notes: none

### `src/cockpit/state.py`
- responsibility: Read-only adapters and composite view-models for the V5.3 cockpit.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: displayed
- inputs: current_page, grafana_url, log_query, notice_message, notice_status, paths, pid_file, prometheus_url, selected_pair, welcome_message
- outputs: DashboardViewModel, OperationalProofSnapshot, WarmupSummary, build_dashboard_view_model, read_pair_metrics, read_pair_selector, read_pid, read_service_status, read_warmup_summary
- runtime_files_read: build/build11_live_websocket_campaign/live_websocket_config.json, live_websocket_snapshot_batch.json, shadow_vps_service.state.json, shadow_vps_service_observability_export.json, vps_warmup_run.summary.json
- formulas_or_derived_metrics: warmup = read_warmup_summary(paths), warmup_explainer = read_warmup_explainer(paths, warmup=warmup), run_comparison = read_run_comparison(
        paths.auto_exports_root,
        runtime=runtime,
        warmup=warmup,
    ), system_flow = read_system_flow(
        freshness=freshness,
        warmup=warmup_explainer,
        service_liveness=service_liveness,
        queue_trace=queue_trace,
        engine_why=engine_why,
        economics=economic_sterilization,
        feature_bridge=feature_bridge,
        refusal_journal=refusal_journal,
        kill_proof=kill_proof,
        data_quality=data_quality,
    ), runtime = runtime.model_copy(
        update={
            "alerts": runtime.alerts
            + _build_operational_alerts(
                warmup=warmup_explainer,
                service_liveness=service_liveness,
                queue_trace=queue_trace,
                engine_why=engine_why,
                feature_bridge=feature_bridge,
                refusal_journal=refusal_journal,
                data_quality=data_quality,
                disk_growth=disk_growth,
            )
        }
    )
- thresholds_or_constants: warmup.final_state compare "unknown", warmup.readiness_status compare "passed"
- control_flags_or_gates: blocked, control_ready, eligible_to_trade, kill, passed, queue, queue, runtime_mode
- duplication_notes: none

### `src/cockpit/state_calibration.py`
- responsibility: Phase 2 adapter — EDGE / clock-drift / WS-gap calibration thresholds.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: duplicate_non_owner
- inputs: thresholds_path
- outputs: CalibrationThresholdsSnapshot, read_calibration_thresholds
- runtime_files_read: none
- formulas_or_derived_metrics: generated_at = ""
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=overview,trading

### `src/cockpit/state_capacity_guard.py`
- responsibility: Phase 2 adapter — Capacity guard snapshot.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: duplicate_non_owner
- inputs: build_root, observability_export_path
- outputs: CapacityGuardSnapshot, read_capacity_guard
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: queue_oldest_age_ms = 0, worker_cpu_pct = 0.0, backlog_alert_threshold = 0, backlog_protection_threshold = 0
- control_flags_or_gates: blocked
- duplication_notes: also_consumed_by=trading

### `src/cockpit/state_data_quality.py`
- responsibility: Phase 2.5 adapter - live data freshness, spread, and time-sync visibility.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: shadow
- status: duplicate_non_owner
- inputs: pairs, paths
- outputs: DataQualitySnapshot, read_data_quality_live
- runtime_files_read: live_time_sync_offsets.json, live_websocket_snapshot_batch.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: data_quality
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=trading

### `src/cockpit/state_decision_trace.py`
- responsibility: Phase 2.5 adapter - bounded decision trace from replay DTR or service logs.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: displayed
- inputs: auto_exports_root, max_entries
- outputs: DecisionTraceSnapshot, read_decision_trace
- runtime_files_read: replay_dtr.jsonl
- formulas_or_derived_metrics: ce_net = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/cockpit/state_disk_growth.py`
- responsibility: Phase 2.5 adapter - bounded disk and log growth visibility.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: vps
- status: duplicate_non_owner
- inputs: paths
- outputs: DiskGrowthSnapshot, read_disk_growth
- runtime_files_read: .events.jsonl
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: disk_growth
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_economic_sterilization.py`
- responsibility: Phase 2.5 adapter - thin-sample economic sterilization monitor.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: displayed
- inputs: replay
- outputs: EconomicSterilizationSnapshot, read_economic_sterilization
- runtime_files_read: none
- formulas_or_derived_metrics: exec_rate = 0.0, ce_net = 0.0, ratio = blocked_or_rejected / max(opportunities, 1)
- thresholds_or_constants: slippage_blocked_count = 0, economic_sterilization_ratio = 0.0, ratio compare 0.80, ratio compare 0.50
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/cockpit/state_engine_why.py`
- responsibility: Phase 2.5 adapter - why each engine is active, dormant, suspended, or unknown.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: displayed
- inputs: engines, feature_bridge, replay
- outputs: EngineWhySnapshot, read_engine_why_state
- runtime_files_read: none
- formulas_or_derived_metrics: ce_net = 0.0
- thresholds_or_constants: none
- control_flags_or_gates: blocked, suspended
- duplication_notes: none

### `src/cockpit/state_engines.py`
- responsibility: Phase 2 adapter — Engine A/B/C/D status grid.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: duplicate_non_owner
- inputs: feature_bridge, replay, service_state_path
- outputs: EnginesGridSnapshot, build_engines_grid
- runtime_files_read: none
- formulas_or_derived_metrics: ce_net = 0.0
- thresholds_or_constants: none
- control_flags_or_gates: suspended
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_feature_bridge.py`
- responsibility: Phase 2 adapter — read ``auto_exports/<date>/feature_bridge.json``.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: duplicate_non_owner
- inputs: auto_exports_root
- outputs: FeatureBridgeSnapshot, read_feature_bridge
- runtime_files_read: feature_bridge.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: feature_bridge
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=lab,overview

### `src/cockpit/state_freshness.py`
- responsibility: Phase 2.5 adapter - source freshness and shared read-only source stamps.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: displayed
- inputs: auto_exports_root, index, path, paths, pattern, root, stale_after_seconds, status_if_missing, validator
- outputs: OperationalSourceSnapshot, SourceFreshnessSnapshot, read_json_dict, read_source_freshness
- runtime_files_read: feature_bridge.json, meta_learning_review.bundle.json, model_risk_register.snapshot.json, refusal_journal.snapshot.json, replay_metrics.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: freshness
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/cockpit/state_kill_proof.py`
- responsibility: Phase 2.5 adapter - read-only kill proof status.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: displayed
- inputs: paths
- outputs: KillProofSnapshot, read_kill_proof
- runtime_files_read: halt_flag_kill_proof.json, kill_proof.json, kill_switch.proof.json, shadow_kill_proof.json, shadow_vps_service.events.jsonl
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: kill_proof
- thresholds_or_constants: none
- control_flags_or_gates: kill
- duplication_notes: none

### `src/cockpit/state_lab_review.py`
- responsibility: Phase 2 adapter — IA Lab Build-9X review bundle.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: duplicate_non_owner
- inputs: build_root
- outputs: LabReviewSummary, read_lab_review
- runtime_files_read: meta_learning_review.bundle.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: lab_review
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_lab_vps_transfer.py`
- responsibility: Phase 2.5 adapter - Local IA Lab output visibility vs VPS-visible imports.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: displayed
- inputs: paths
- outputs: LabVpsTransferSnapshot, read_lab_vps_transfer
- runtime_files_read: feature_bridge.json, governed_input_summary.json, meta_learning_review.bundle.json, replay_run_manifest.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: lab_vps_transfer
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/cockpit/state_model_risk.py`
- responsibility: Phase 2 adapter — Model Risk Register snapshot (Narang).
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: duplicate_non_owner
- inputs: service_dir
- outputs: ModelRiskRegisterSnapshot, read_model_risk_register
- runtime_files_read: model_risk_register.snapshot.json
- formulas_or_derived_metrics: NOT_YET_PERSISTED: model_risk
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_multiple_testing.py`
- responsibility: Phase 2 adapter — HLZ Sharpe deflation guard.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: duplicate_non_owner
- inputs: build_root
- outputs: MultipleTestingGuardSnapshot, read_multiple_testing_guard
- runtime_files_read: local_lab_calibration_methods_review.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: multiple_testing
- thresholds_or_constants: dsr_floor = 0.0
- control_flags_or_gates: gate
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_queue_trace.py`
- responsibility: Phase 2.5 adapter - queue visibility vs queue consumption proof.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: vps
- status: duplicate_non_owner
- inputs: paths, runtime
- outputs: QueueConsumptionTraceSnapshot, read_queue_trace
- runtime_files_read: *.json
- formulas_or_derived_metrics: DISPLAY_OPERATIONAL_DIAGNOSTIC: queue_trace
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: also_consumed_by=lab,overview,shadow

### `src/cockpit/state_refusal_journal.py`
- responsibility: Phase 2 adapter — Taleb Refusal Journal (placeholder until persisted).
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: duplicate_non_owner
- inputs: service_dir
- outputs: RefusalJournalSnapshot, read_refusal_journal
- runtime_files_read: refusal_journal.snapshot.json
- formulas_or_derived_metrics: NOT_YET_PERSISTED: refusal_journal
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_replay_metrics.py`
- responsibility: Phase 2 adapter — read ``auto_exports/<date>/replay_metrics.json``.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: displayed
- inputs: auto_exports_root
- outputs: ReplayMetricsSnapshot, read_replay_metrics
- runtime_files_read: replay_metrics.json
- formulas_or_derived_metrics: ce_net = 0.0, exec_rate = self.executed_count / self.total_records, pairs = tuple(
        PairAggregate(
            pair=str(p.get("pair", "")),
            record_count=int(p.get("record_count", 0)),
            selected_count=int(p.get("selected_count", 0)),
            ce_net=float(p.get("ce_net", 0.0)),
            expected_cost_mean=float(p.get("expected_cost_mean", 0.0)),
            realized_cost_mean=float(p.get("realized_cost_mean", 0.0)),
            gross_return_mean=float(p.get("gross_return_mean", 0.0)),
        )
        for p in payload.get("pair_aggregates") or ()
        if isinstance(p, dict)
    ), engines = tuple(
        EngineAggregate(
            engine_id=str(e.get("engine_id", "")),
            record_count=int(e.get("record_count", 0)),
            selected_count=int(e.get("selected_count", 0)),
            hard_blocked_count=int(e.get("hard_blocked_count", 0)),
            ce_net=float(e.get("ce_net", 0.0)),
            expected_cost_mean=float(e.get("expected_cost_mean", 0.0)),
            realized_cost_mean=float(e.get("realized_cost_mean", 0.0)),
            gross_return_mean=float(e.get("gross_return_mean", 0.0)),
        )
        for e in payload.get("engine_aggregates") or ()
        if isinstance(e, dict)
    )
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/cockpit/state_run_comparison.py`
- responsibility: Phase 2.5 adapter - current run vs previous run, with sample-size restraint.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: displayed
- inputs: auto_exports_root, runtime, warmup
- outputs: RunComparisonSnapshot, read_run_comparison
- runtime_files_read: feature_bridge.json, replay_metrics.json, replay_run_manifest.json
- formulas_or_derived_metrics: exec_rate_transition = ProofTransition(), current_reasons = tuple(str(reason) for reason in (warmup.blocking_reasons if warmup else ()))
- thresholds_or_constants: none
- control_flags_or_gates: eligible_to_trade
- duplication_notes: none

### `src/cockpit/state_service_liveness.py`
- responsibility: Phase 2.5 adapter - explicit cockpit vs Shadow service liveness.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: vps
- status: duplicate_non_owner
- inputs: paths, runtime
- outputs: ServiceLivenessSnapshot, read_service_liveness
- runtime_files_read: shadow_vps_service_monitoring_backend_payload.json
- formulas_or_derived_metrics: DISPLAY_OPERATIONAL_DIAGNOSTIC: service_liveness
- thresholds_or_constants: none
- control_flags_or_gates: control_ready, kill, runtime_mode
- duplication_notes: also_consumed_by=overview,shadow

### `src/cockpit/state_sizing_chain.py`
- responsibility: Phase 2 adapter — Carver sizing chain from ``replay_dtr.jsonl``.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: trading
- status: duplicate_non_owner
- inputs: auto_exports_root, max_rows
- outputs: SizingChainSnapshot, read_sizing_chain
- runtime_files_read: replay_dtr.jsonl
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: sizing_chain
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_system_flow.py`
- responsibility: Phase 2.5 adapter - system flow chain and operability score.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: overview
- status: duplicate_non_owner
- inputs: data_quality, economics, engine_why, feature_bridge, freshness, kill_proof, queue_trace, refusal_journal, service_liveness, warmup
- outputs: SystemFlowSnapshot, read_system_flow
- runtime_files_read: none
- formulas_or_derived_metrics: warmup = "UNKNOWN", lineage = "MISSING", market_data_passed = any(
        check.check_id == "market_data_capture" and check.status == "passed"
        for check in warmup.checks
    ), stages = (
        SystemFlowStage(
            stage_name="Market Data Capture",
            status=(
                "green"
                if warmup.readiness_status == "passed" and market_data_passed
                else ("yellow" if market_data_passed else "red")
            ),
            detail=f"{warmup.final_state} / eligible={warmup.eligible_to_trade}",
            reason_codes=(
                ("market_data_capture_passed",)
                if market_data_passed
                else ("market_data_capture_not_proven",)
            ),
        ),
        SystemFlowStage(
            stage_name="Replay Metrics",
            status="green" if replay_ok else "red",
            detail="Latest replay metrics export freshness",
            reason_codes=replay_source.reason_codes,
        ),
        SystemFlowStage(
            stage_name="Feature Bridge",
            status=feature_status,
            detail=feature_bridge.feature_to_engine_path or "feature bridge path unavailable",
            reason_codes=feature_bridge.lineage_lock_reasons,
        ),
        SystemFlowStage(
            stage_name="Engines",
            status=engine_status,
            detail=f"{active_count}/4 active",
            reason_codes=tuple(
                row.engine_id for row in engine_why.engines if row.status in {"dormant", "suspended"}
            ),
        ),
        SystemFlowStage(
            stage_name="Scoring",
            status=(
                "red"
                if economics.status == "critical" or economics.ce_net <= 0.0
                else ("yellow" if economics.status in {"watch", "insufficient_sample"} else "green")
            ),
            detail=f"ce_net={economics.ce_net:.4f} / sterilization={economics.economic_sterilization_ratio:.2f}",
            reason_codes=economics.reason_codes,
        ),
        SystemFlowStage(
            stage_name="Queue",
            status=queue_stage_status,
            detail=queue_trace.consumption_status,
            reason_codes=queue_trace.reason_codes,
        ),
        SystemFlowStage(
            stage_name="VPS Service",
            status=service_stage_status,
            detail=service_liveness.service_status,
            reason_codes=service_liveness.reason_codes,
        ),
        SystemFlowStage(
            stage_name="Cockpit Actions",
            status=cockpit_actions_status,
            detail=kill_proof.kill_switch_status,
            reason_codes=kill_proof.reason_codes,
        ),
    ), economics_label = "SAMPLE_TOO_SMALL"
        if economics.status == "insufficient_sample"
        else (
            "CE_NET_POSITIVE"
            if economics.status == "ok" and economics.ce_net > 0.0
            else "CE_NET_NEGATIVE"
        ), operability_score = SystemOperabilityScore(
        warmup="PASSED" if warmup.readiness_status == "passed" else "BLOCKED",
        service="ONLINE" if service_liveness.control_ready else "OFFLINE",
        queue=queue_label,
        engines=f"{active_count}/4 ACTIVE",
        economics=economics_label,
        lineage=lineage_label,
        refusal_journal=refusal_label,
        kill_switch=kill_label,
        overall_verdict=overall,
    )
- thresholds_or_constants: warmup.readiness_status compare "passed", economics.ce_net compare 0.0
- control_flags_or_gates: blocked, control_ready, eligible_to_trade, passed, passed, queue, queue, suspended
- duplication_notes: also_consumed_by=trading

### `src/cockpit/state_tail_risk.py`
- responsibility: Phase 2 adapter — Taleb tail-risk breakers from ``local_lab_tail_risk_review.json``.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: lab
- status: duplicate_non_owner
- inputs: build_root
- outputs: TailRiskSnapshot, read_tail_risk
- runtime_files_read: local_lab_tail_risk_review.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: tail_risk
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: also_consumed_by=overview

### `src/cockpit/state_warmup_explainer.py`
- responsibility: Phase 2.5 adapter - actionable warmup blocker explanations.
- dashboard_relevance: direct_surface_input
- owner_page_candidate: shadow
- status: duplicate_non_owner
- inputs: paths, warmup
- outputs: WarmupExplainerSnapshot, read_warmup_explainer
- runtime_files_read: none
- formulas_or_derived_metrics: statuses = {check.check_id: check.status for check in warmup.checks}, required_passed = _required_checks_passed(warmup), review_only_checks = tuple(
        check.check_id for check in warmup.checks if check.status == "review_only"
    ), ready_state = warmup.final_state in _READY_FINAL_STATES
- thresholds_or_constants: warmup.final_state compare _READY_FINAL_STATES, warmup compare None
- control_flags_or_gates: blocked, eligible_to_trade, passed, review_only
- duplication_notes: also_consumed_by=overview

## complete_enablers

### `src/complete_enablers/__init__.py`
- responsibility: Build-14 governed analytical enablers.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/competition_monitor.py`
- responsibility: Competition monitor reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: observation
- outputs: build_competition_monitor_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: ce_component = 1.0 if observation.ce_net < 0 else 0.0
- thresholds_or_constants: observation.ce_net compare 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/contracts.py`
- responsibility: Compatibility re-export for Build-14 contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/enums.py`
- responsibility: Compatibility re-export for Build-14 enums.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/errors.py`
- responsibility: Errors for Build-14 enabler guardrails.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/execution_fragility_score.py`
- responsibility: Execution fragility reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: observation
- outputs: build_execution_fragility_score
- runtime_files_read: none
- formulas_or_derived_metrics: ce_component = 1.0 if observation.ce_net < 0 else 0.5 if observation.ce_net < 0.001 else 0.0
- thresholds_or_constants: observation.ce_net compare 0, observation.ce_net compare 0.001
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/false_breakout_model.py`
- responsibility: False-breakout reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: observation
- outputs: build_false_breakout_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/hurst_regime_classifier.py`
- responsibility: Hurst regime classifier reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: observation
- outputs: build_hurst_regime_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/limited_influence.py`
- responsibility: Governed Build-14 evaluators for Shadow activation and post-Shadow live influence.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: observation
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: review_only, review_only
- duplication_notes: none

### `src/complete_enablers/lob_deep_filter_vwa.py`
- responsibility: LOB deep-filter / VWA reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: observation
- outputs: build_lob_deep_filter_vwa_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/market_toxicity_snapshot.py`
- responsibility: Market toxicity reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: observation
- outputs: build_market_toxicity_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/micro_edge_entry_timing_layer.py`
- responsibility: Micro-edge entry timing reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: observation
- outputs: build_micro_edge_entry_timing_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: ce_component = 1.0 if observation.ce_net < 0 else 0.5 if observation.ce_net < 0.001 else 0.0
- thresholds_or_constants: observation.ce_net compare 0, observation.ce_net compare 0.001
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/micro_edge_exit_governor.py`
- responsibility: Micro-edge exit governor reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: observation
- outputs: build_micro_edge_exit_governor_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: ce_component = 1.0 if observation.ce_net < 0 else 0.5 if observation.ce_net < 0.001 else 0.0
- thresholds_or_constants: observation.ce_net compare 0, observation.ce_net compare 0.001
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/ml_confidence_enabler.py`
- responsibility: Bounded runtime-facing ML confidence enabler for additive score modulation.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/ml_fusion.py`
- responsibility: Bounded score-fusion math for the Local-Lab ML confidence layer.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: alpha, artifact_ready, base_score, ml_confidence
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/ml_model_promotion_gate.py`
- responsibility: Fail-closed promotion gate for bounded ML model artifacts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: artifact
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ratio = None, ratio = artifact.oos_sharpe / artifact.backtest_sharpe
- thresholds_or_constants: ratio compare 0.80
- control_flags_or_gates: blocked, gate, passed
- duplication_notes: none

### `src/complete_enablers/ml_runtime_artifact_loader.py`
- responsibility: Artifact-only runtime loader for governed ML supplementary refs.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: as_of, supplementary_refs
- outputs: load_ml_runtime_artifact
- runtime_files_read: ml_model_artifact.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/ml_scoring_soft_penalty_hook.py`
- responsibility: Bounded Build-5 scoring hook backed by the governed ML confidence enabler.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/order_book_imbalance.py`
- responsibility: Order-book imbalance reader for Build-14 SHADOW_ENABLED enablers.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: observation
- outputs: build_order_book_imbalance_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: ce_component = 1.0 if observation.ce_net < 0 else 0.0
- thresholds_or_constants: observation.ce_net compare 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/complete_enablers/regime_detector_runtime.py`
- responsibility: Artifact-only VPS Shadow runtime for RegimeDetectorML.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/complete_enablers/regime_detector_runtime_loader.py`
- responsibility: Artifact-only runtime loader for transported RegimeDetectorML artifacts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: as_of, supplementary_refs
- outputs: load_regime_detector_runtime_artifact
- runtime_files_read: regime_detector_artifact.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## contract_test_suite

### `src/contract_test_suite/__init__.py`
- responsibility: contract_test_suite — Module 4: Tests de contrat par module.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/contract_test_suite/compatibility_checker.py`
- responsibility: 6.5.4 — Compatibility Checker: verify that contract changes don't break consumers.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: model_class, module_name, new_snapshot, old_snapshot
- outputs: FieldSnapshot, SchemaSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/contract_test_suite/contract_models.py`
- responsibility: 6.5.0 — Contract Models: shared types for the contract test infrastructure.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: ModuleContractReport, SuiteReport
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/contract_test_suite/contract_reporter.py`
- responsibility: 6.5.5 — Contract Reporter: produce human + machine-readable contract reports.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: module_reports, report
- outputs: build_suite_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed, passed
- duplication_notes: none

### `src/contract_test_suite/contract_test_runner.py`
- responsibility: 6.5.1 — Contract Test Runner: execute contract suites per module.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: suites
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/contract_test_suite/negative_case_runner.py`
- responsibility: 6.5.3 — Negative Case Runner: execute expected-failure test cases.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: args, case, expected_exception, func, invalid_data, kwargs, model_class
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/contract_test_suite/schema_assertions.py`
- responsibility: 6.5.2 — Schema Assertions: verify field presence, absence, types, bounds, units.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: base_data, contract_name, data, expected_type, field_name, invalid_high, invalid_low, model_class, module_name, reason, valid_value
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## dag_validator

### `src/dag_validator/__init__.py`
- responsibility: dag_validator — Module 3: Empêcher les dépendances interdites et les cycles.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: src_root
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/dag_validator/cycle_detector.py`
- responsibility: 5.5.3 — Cycle Detector: detect cycles in the module dependency DAG.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: allowed_dependencies, scan
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/dag_validator/dependency_matcher.py`
- responsibility: 5.5.2 - Dependency Matcher: compare observed imports vs manifest-authorized dependencies.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: allowed_dependencies, known_modules, scan
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/dag_validator/import_scanner.py`
- responsibility: 5.5.1 - Import Scanner: scan Python source files for import statements via AST.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: known_modules, src_root
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/dag_validator/layer_validator.py`
- responsibility: 5.5.4 — Layer Validator: enforce that dependencies respect the layer hierarchy.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: allowed_dependencies, module_layers
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/dag_validator/report_builder.py`
- responsibility: 5.5.5 — Report Builder: produce human-readable + machine-exploitable validation report.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: cycle_result, files_scanned, layer_result, manifest_version, match_result, report, scan_errors
- outputs: ValidationReport, build_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

## data_backbone

### `src/data_backbone/__init__.py`
- responsibility: V5.3 — Data Backbone: reliable, observable data ingestion pipeline.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/consistency_checker/__init__.py`
- responsibility: 9.5 â€” Consistency Checker: detect gaps, duplicates, disorders, and contradictions.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/consistency_checker/consistency_reporter.py`
- responsibility: 9.5.5 - Consistency Reporter: aggregate consistency metrics.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: contradiction_rate, disorder_rate, dup_rate, gap_rate, w_contradiction, w_disorder, w_dup, w_gap
- outputs: compute_consistency_score
- runtime_files_read: none
- formulas_or_derived_metrics: gap_rate = 0.0, dup_rate = 0.0, disorder_rate = 0.0, contradiction_rate = 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/consistency_checker/contradiction_checker.py`
- responsibility: 9.5.4 — Contradiction Checker: detect incompatible events.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/consistency_checker/duplicate_detector.py`
- responsibility: 9.5.3 — Duplicate Detector: detect message duplications.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/consistency_checker/gap_detector.py`
- responsibility: 9.5.2 — Gap Detector: detect observable gaps in message sequences.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/consistency_checker/sequence_checker.py`
- responsibility: 9.5.1 — Sequence Checker: verify logical ordering of messages.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/event_normalizer/__init__.py`
- responsibility: 6.5 â€” Event Normalizer: convert raw events to stable, typed, versioned internal contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/event_normalizer/invalid_message_guard.py`
- responsibility: 6.5.4 — Invalid Message Guard: reject non-conforming messages explicitly.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: pair, payload, recv_time, source, stream_type
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/event_normalizer/message_classifier.py`
- responsibility: 6.5.3 — Message Classifier: identify message type from raw payload.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: payload, stream_type_hint
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/event_normalizer/normalization_reporter.py`
- responsibility: 6.5.5 — Normalization Reporter: track successes, rejections, and anomalies.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: reject_rate = 0.0, reject_rate = self._total_rejected / self._total_raw
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/event_normalizer/schema_mapper.py`
- responsibility: 6.5.1 — Schema Mapper: map raw payloads to internal event contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: exchange_time, pair, raw_payload, recv_time, source, stream_type
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/event_normalizer/timestamp_enricher.py`
- responsibility: 6.5.2 - Timestamp Enricher: add recv_time, transport exchange_time, compute drift.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: event, exchange_time, max_latency_s, now, recv_time
- outputs: compute_drift, compute_latency
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/freshness_checker/__init__.py`
- responsibility: 8.5 â€” Freshness Checker: measure data age, produce stale penalties, enforce hard blocks.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/freshness_checker/age_calculator.py`
- responsibility: 8.5.2 — Age Calculator: compute Δ_i = t_decision - t_last_update.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: decision_time, last_update_time, pair, stream_type, stream_updates
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/freshness_checker/freshness_reporter.py`
- responsibility: 8.5.5 — Freshness Reporter: report stale events and freshness metrics.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: max_age_observed = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/freshness_checker/last_update_tracker.py`
- responsibility: 8.5.1 — Last Update Tracker: store last update timestamp per stream/pair.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/freshness_checker/stale_hard_guard.py`
- responsibility: 8.5.4 - Stale Hard Guard: trigger explicit stale block when age exceeds threshold.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: age_s, exchange_timestamp, hard_threshold_s, local_timestamp, pair, policy, runtime_mode, soft_threshold_s, stream_type
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, runtime_mode
- duplication_notes: none

### `src/data_backbone/freshness_checker/stale_penalty_builder.py`
- responsibility: 8.5.3 — Stale Penalty Builder: produce gradual staleness penalty.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: age_s, lambda_factor, pair, stream_type, threshold_s
- outputs: compute_stale_penalty
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/freshness_checker/venue_stream_freshness.py`
- responsibility: Bounded freshness hook for venue websocket streams.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: last_update_time, now, stale_threshold_s
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/internal_router/__init__.py`
- responsibility: 7.5 â€” Internal Router: distribute normalized events to consumers with priority and backpressure.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/internal_router/backpressure_guard.py`
- responsibility: 7.5.4 — Backpressure Guard: protect the system if a consumer slows down.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: consumer_id, drop_threshold, priority, queue_utilization, warn_threshold
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/data_backbone/internal_router/consumer_registry.py`
- responsibility: 7.5.1 — Consumer Registry: register consumers and their subscriptions.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/internal_router/priority_dispatcher.py`
- responsibility: 7.5.2 — Priority Dispatcher: dispatch events with priority ordering.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: blocked_consumers, consumers, event_type, pair
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/internal_router/queue_manager.py`
- responsibility: 7.5.3 - Queue Manager: per-consumer queues with backlog and saturation metrics.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: drop_rate = 0.0
- thresholds_or_constants: capacity = 0
- control_flags_or_gates: queue, queue
- duplication_notes: none

### `src/data_backbone/internal_router/routing_reporter.py`
- responsibility: 7.5.5 — Routing Reporter: report on event distribution.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/market_physics_math.py`
- responsibility: V5.3 - MARKET PHYSICS MATH
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: base_fragility, base_toxicity, book_resiliency_penalty, cap, close_price, delta_confirmation, delta_proxy_sign_value, delta_proxy_soft_value, delta_proxy_value, digits, epsilon, fragility_score, high_price, low_price, mean_volume_1m, mean_window_volume, name, open_price, order_size, participation_penalty, reference_volume, region_volumes, reject_indicator, spread_regime_penalty, toxicity_score, value, vol_burst, vol_jump_penalty, volume, wick_ratio, z_cap
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: TO_CALIBRATE = "TO_CALIBRATE", cap = require_finite_float64(z_cap, name="z_cap"), cap_value = require_finite_float64(cap, name="cap")
- thresholds_or_constants: cap compare 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/__init__.py`
- responsibility: Canonical microstructure registry and calculators for V5.3.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/amihud_illiquidity.py`
- responsibility: V5.3 - AMIHUD ILLIQUIDITY
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: bars, computed_at_ns, pair, window_seconds
- outputs: compute_amihud_illiquidity
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/corwin_schultz_spread.py`
- responsibility: V5.3 - CORWIN-SCHULTZ SPREAD
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: bars, computed_at_ns, pair
- outputs: compute_corwin_schultz_spread
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/engine_input_provenance.py`
- responsibility: V5.3 - ENGINE INPUT MICROSTRUCTURE PROVENANCE
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: base_payload, kyle_lambda_cost_uplift, kyle_lambda_record, ofi_flow_score, ofi_record, pair, queue_pressure_record, realized_kernel_record, realized_kernel_vol_scale, realized_vol_at_break_record, realized_vol_current, realized_vol_current_record, realized_vol_post_close_record, vpin_record
- outputs: build_engine_a_microstructure_provenance, build_engine_a_runner_microstructure_updates, build_engine_c_microstructure_provenance, build_engine_c_runner_microstructure_updates, build_engine_d_microstructure_provenance, build_engine_d_runner_microstructure_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/feature_registry.py`
- responsibility: V5.3 - MICROSTRUCTURE FEATURE REGISTRY
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: current, feature_id, reason, spec, target
- outputs: MicrostructurePromotionState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/data_backbone/microstructure/hawkes_intensity.py`
- responsibility: V5.3 - HAWKES INTENSITY
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, estimate, events, pair, window_events
- outputs: compute_hawkes_intensity
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/kyle_lambda.py`
- responsibility: V5.3 - KYLE LAMBDA
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: bucket_seconds, computed_at_ns, current, pair, previous_sign, previous_trade, trades, window_seconds
- outputs: build_kyle_intervals, compute_kyle_lambda
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/lob_regime_features.py`
- responsibility: Live LOB microstructure features for governed RegimeDetectorML inference.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, depth_events, feature_set_version, pair, top_n, touch_eps_bps, trades, window_seconds
- outputs: LobDepth20Snapshot, LobRegimeFeatureSnapshot, _LiquidityFeatureBundle, _WallFeatureBundle, build_lob_regime_feature_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: near_touch_cancel_ratio_bid = 0.0, near_touch_cancel_ratio_ask = 0.0, observation_coverage_ratio = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/order_flow_imbalance.py`
- responsibility: V5.3 - ORDER FLOW IMBALANCE
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, current, pair, points, previous, window_events
- outputs: compute_order_book_event_contribution, compute_order_flow_imbalance
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/pin.py`
- responsibility: V5.3 - PIN
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, estimate, n_events_used, pair, window_used
- outputs: compute_pin_from_parameters
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/queue_pressure.py`
- responsibility: V5.3 - QUEUE PRESSURE
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, pair, point, top_k
- outputs: compute_queue_pressure
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue, queue
- duplication_notes: none

### `src/data_backbone/microstructure/realized_effective_spread.py`
- responsibility: V5.3 - REALIZED / EFFECTIVE SPREAD
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, observation, pair, realized_horizon_seconds
- outputs: compute_realized_effective_spread
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/realized_kernel_vol.py`
- responsibility: V5.3 - REALIZED KERNEL VOLATILITY
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: bandwidth_c, bucket_seconds, computed_at_ns, pair, points, sample_size, x
- outputs: compute_realized_kernel_vol
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/roll_spread.py`
- responsibility: V5.3 - ROLL SPREAD
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, pair, trades, window_seconds
- outputs: compute_roll_spread
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/spread_dynamics.py`
- responsibility: V5.3 - SPREAD DYNAMICS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: computed_at_ns, observation, pair, realized_horizon_seconds
- outputs: compute_spread_dynamics
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/vpin.py`
- responsibility: V5.3 - VPIN
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: allow_derived_daily_volume, bucket, bucket_volume, buckets_per_day, computed_at_ns, daily_volume, pair, sigma_delta_p, trades, window_buckets
- outputs: build_equal_volume_buckets, compute_vpin
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/microstructure/walls_and_spoofing.py`
- responsibility: Canonical walls and spoof-like deceptive-liquidity detector for V5.3.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: cancel_drop_ratio, computed_at_ns, depth_events, dominant_side_margin, pair, real_wall_dominance_floor, size_tol, top_n_levels, touch_eps_bps, trade_events, window_seconds
- outputs: WallsAndSpoofingSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: DEFAULT_CANCEL_DROP_RATIO = 0.7, DEFAULT_REAL_WALL_DOMINANCE_FLOOR = 2.0, near_touch_cancel_ratio_bid = 0.0, near_touch_cancel_ratio_ask = 0.0, observation_coverage_ratio = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/pair_health_scorer/__init__.py`
- responsibility: 10.5 â€” Pair Health Scorer: aggregate quality metrics, suspension/recovery decisions.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/pair_health_scorer/health_reporter.py`
- responsibility: 10.5.5 — Health Reporter: detailed health reports per pair.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: HealthSummary, PairHealthReport
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: suspended
- duplication_notes: none

### `src/data_backbone/pair_health_scorer/health_state_tracker.py`
- responsibility: 10.5.4 - Health State Tracker: track active / degraded / suspended / recovery states.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: PairHealthState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: suspended, suspended
- duplication_notes: none

### `src/data_backbone/pair_health_scorer/quality_aggregator.py`
- responsibility: 10.5.1 — Quality Aggregator: aggregate freshness + consistency + latency + recovery.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: inputs, w_consistency, w_freshness, w_latency, w_recovery
- outputs: compute_health_score
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/pair_health_scorer/recovery_evaluator.py`
- responsibility: 10.5.3 — Recovery Evaluator: decide if a suspended pair can return to active.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: consecutive_healthy, health_score, pair, recovery_threshold, required_consecutive
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: suspended
- duplication_notes: none

### `src/data_backbone/pair_health_scorer/suspension_decider.py`
- responsibility: 10.5.2 — Suspension Decider: suspend pair if health below threshold.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: consistency_failed, hard_stale, health_score, operator_id, pair, reason_text, threshold
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: threshold = None
- thresholds_or_constants: threshold compare None
- control_flags_or_gates: suspended
- duplication_notes: none

### `src/data_backbone/rest_bootstrap/__init__.py`
- responsibility: 5.5 - REST Bootstrap: snapshot initial, rate limiting, gap fill controle.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/rest_bootstrap/bootstrap_reporter.py`
- responsibility: 5.5.5 — Bootstrap Reporter: report on REST bootstrap / resync operations.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: BootstrapSummary
- runtime_files_read: none
- formulas_or_derived_metrics: RATE_LIMITED = "rate_limited"
- thresholds_or_constants: duration_s = 0.0, total_operations = 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/rest_bootstrap/gap_fill_controller.py`
- responsibility: 5.5.3 — Gap Fill Controller: decide if a data gap is acceptable to fill via REST.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: gap_end, gap_start, max_gap_s, pair, rate_limited
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: REJECT_RATE_LIMITED = "reject_rate_limited"
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/rest_bootstrap/rate_limit_guard.py`
- responsibility: 5.5.2 — Rate Limit Guard: protect API quotas, log usage.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: RateLimitState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/rest_bootstrap/runtime_bootstrap.py`
- responsibility: Minimal injectable runtime path for Build-2 REST bootstrap.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/data_backbone/rest_bootstrap/snapshot_fetcher.py`
- responsibility: 5.5.1 — Snapshot Fetcher: retrieve initial snapshots via REST.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: max_age_s, now, snapshot
- outputs: Snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: age_s = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/__init__.py`
- responsibility: 4.5 - WebSocket Gateway: connexion fiable, observable et reconnectable.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/connection_manager.py`
- responsibility: 4.5.1 — Connection Manager: open/close sockets, session management, reconnection.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: ConnectionState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/heartbeat_monitor.py`
- responsibility: 4.5.3 — Heartbeat Monitor: detect silence, missing heartbeats.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: HeartbeatState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: silence_duration_s = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/injected_stream_loader.py`
- responsibility: Load governed injected WebSocket frame streams from JSON or JSONL.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: stream_path
- outputs: load_injected_websocket_frames
- runtime_files_read: Injected websocket streams must use .json or .jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/raw_message_emitter.py`
- responsibility: 4.5.5 - Raw Message Emitter: emit raw messages with recv_time metadata.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/reconnect_controller.py`
- responsibility: 4.5.4 — Reconnect Controller: backoff strategy, reconnection logging.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/runtime_gateway.py`
- responsibility: Minimal injectable runtime path for Build-2 WebSocket gateway.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/data_backbone/websocket_gateway/subscription_manager.py`
- responsibility: 4.5.2 — Subscription Manager: pair → stream mapping, no duplicate subscriptions.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## engines

### `src/engines/__init__.py`
- responsibility: production module
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/__init__.py`
- responsibility: Build-6 — Engine A: Premium Trend / Expansion.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/context_validator_a.py`
- responsibility: Build-6 / engine_a / context_validator_A
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/conviction_builder_a.py`
- responsibility: Build-6 / engine_a / conviction_builder_A
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: build_conviction
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/cost_feasibility_a.py`
- responsibility: Build-6 / engine_a / cost_feasibility_A
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE = EngineACostThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: kill
- duplication_notes: none

### `src/engines/engine_a/engine_a_runner.py`
- responsibility: Build-6 / engine_a / engine_a_runner: canonical orchestrator for Engine A.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/engine_a_runner_support.py`
- responsibility: Small pure helpers supporting the Engine A runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: block_scores, ce_expected, code, context_verdict, conviction, cost_verdict, decision_no_trade, detail, detailed_reason_codes, ev_net, event, expected_cost, gate_reason_codes, holding_hours, inputs, invalidation, kyle_lambda_cost_uplift, log_entry_cls, log_reasons, logs, no_trade_reasons, output_cls, pair, penalized_score, raw_score, reason, reason_codes, reasons, regime, scoring_version, structure_verdict, tier, tier_suggestion
- outputs: build_engine_a_branch_log_reasons, build_engine_a_cost_log_reasons, build_engine_a_emit_reason_codes, build_engine_a_gate_reason_codes, build_engine_a_guard_log_reasons, build_engine_a_no_trade_output
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, gate
- duplication_notes: none

### `src/engines/engine_a/engine_a_runtime.py`
- responsibility: Build-6 / engine_a / engine_a_runtime
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: _EngineAScoringState
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/engine_a_runtime_support.py`
- responsibility: Private helper functions for the Engine A runtime facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/engine_a_scoring_candidate_builder.py`
- responsibility: Scoring candidate builder helpers for Engine A runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/invalidation_mapper_a.py`
- responsibility: Build-6 / engine_a / invalidation_mapper_A
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: direction_score, entry_price, holding_hours, pair, realized_vol_current
- outputs: build_invalidation
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/signal_candidate_adapter.py`
- responsibility: module exposing build_signal_candidate_a
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: engine_inputs, engine_output, signal_candidate, strategy_id, timestamp_ms
- outputs: build_signal_candidate_a
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/signal_reporter_a.py`
- responsibility: Build-6 / engine_a / signal_reporter_A
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: emission_rate = 0.0, rate = self._emitted / n if n > 0 else 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_a/structure_detector_a.py`
- responsibility: Build-6 / engine_a / structure_detector_A
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/__init__.py`
- responsibility: Build-7 / engine_b — Mean Reversion Intraday Motor.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/anti_breakout_filter_b.py`
- responsibility: Build-7 / engine_b / anti_breakout_filter_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE = EngineBBreakoutFilterWeights(), ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE = EngineBBreakoutFilterThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/engines/engine_b/conviction_builder_b.py`
- responsibility: Build-7 / engine_b / conviction_builder_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: build_conviction_b
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/cost_feasibility_b.py`
- responsibility: Build-7 / engine_b / cost_feasibility_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE = EngineBCostThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/engine_b_runner.py`
- responsibility: Build-7 / engine_b / engine_b_runner
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: ENGINE_B_RUNNER_COST_RATIO_EPSILON = 1e-09, expected_duration = 0.0
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/engines/engine_b/engine_b_runner_support.py`
- responsibility: Private helper functions for the Engine B runner facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: detailed_reason_codes, gate_reason_codes
- outputs: build_engine_b_gate_reason_codes
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, gate
- duplication_notes: none

### `src/engines/engine_b/engine_b_runtime.py`
- responsibility: Build-7 / engine_b / engine_b_runtime
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/engine_b_runtime_forecast_support.py`
- responsibility: Forecast and downstream truthfulness helpers for the Engine B runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: engine_output, forecast_signal_candidate, reason_codes, risk_evaluation, runtime_input, scoring_audit, signal_candidate, status, timestamp_ms
- outputs: build_forecast_signal_candidate
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/engine_b_runtime_support.py`
- responsibility: Private helper functions for the Engine B runtime facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: _EngineBScoringState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/excess_detector_b.py`
- responsibility: Build-7 / engine_b / excess_detector_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE = EngineBExcessThresholds(), ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE = EngineBExcessAdjustments()
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/invalidation_mapper_b.py`
- responsibility: Build-7 / engine_b / invalidation_mapper_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: entry_price, holding_hours, local_mean, local_std, pair
- outputs: build_invalidation_b
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE = EngineBInvalidationThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/local_mean_estimator_b.py`
- responsibility: Build-7 / engine_b / local_mean_estimator_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/signal_candidate_adapter.py`
- responsibility: module exposing build_signal_candidate_b
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: engine_inputs, engine_output, signal_candidate, strategy_id, timestamp_ms
- outputs: build_signal_candidate_b
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_b/signal_reporter_b.py`
- responsibility: Build-7 / engine_b / signal_reporter_B
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: emission_rate = 0.0, rate = self._emitted / n if n > 0 else 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/__init__.py`
- responsibility: Build-15 / engine_c.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: ENGINE_C_BUILD_STAGE = 15
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/continuation_validator_c.py`
- responsibility: Pure continuation validation helpers for Engine C.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_C_CONTINUATION_THRESHOLDS_TO_CALIBRATE = {
    "calibration_status": "TO_CALIBRATE",
    "score_min": 0.58,
    "extension_pct_max": 0.72,
}, ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE = EngineCContinuationCallerThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/engines/engine_c/conviction_builder_c.py`
- responsibility: Pure conviction helpers for Engine C.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: breakout_score, ce_expected, ce_min, context_score, continuation_score, fake_breakout_risk
- outputs: build_conviction_c
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/cost_feasibility_c.py`
- responsibility: Pure cost-feasibility helpers for Engine C.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate_size, ce_min, delta_safe, expected_cost, expected_gain, holding_period
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE = EngineCCostCallerThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/engine_c_runner.py`
- responsibility: Canonical Engine C runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_C_RUNNER_THRESHOLDS_TO_CALIBRATE = {
    "calibration_status": "TO_CALIBRATE",
    "breakout_score_min": 0.62,
    "breakout_strength_min": 0.55,
    "range_quality_min": 0.50,
    "fake_breakout_risk_max": 0.65,
}, ENGINE_C_INPUT_DEFAULTS_TO_CALIBRATE = {
    "calibration_status": "TO_CALIBRATE",
    "holding_period": 3.0,
    "ce_min": ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE.ce_min,
    "delta_safe": ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE.delta_safe,
}
- thresholds_or_constants: range_width_pct = 0.0, distance_to_breakout_pct = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/engine_c_runner_support.py`
- responsibility: Internal support helpers for the canonical Engine C runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: breakout_score, ce_expected, context_score, continuation_score, continuation_validation, conviction, conviction_result, cost_feasible, cost_metrics, cumulative_ofi, ev_net, event, expected_cost, fake_breakout_risk, holding_hours, inputs, invalidation_levels, invalidation_present, kyle_lambda, log_entries, logs, microstructure_contradictory, microstructure_gate_applied, microstructure_missing, microstructure_required, no_trade_reasons, penalized_score, queue_pressure, raw_score, reasons, structure, tier, vpin
- outputs: build_engine_c_emit_output, build_engine_c_invalidation, build_engine_c_no_trade_output, build_engine_c_reason_codes
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate, gate
- duplication_notes: none

### `src/engines/engine_c/engine_c_runtime.py`
- responsibility: Engine C runtime across signal, scoring, ranking and risk.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = None
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- responsibility: Forecast and downstream truthfulness helpers for the Engine C runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: engine_inputs, engine_output, forecast_signal_candidate, reason_codes, risk_evaluation, scoring_audit, signal_candidate, status, strategy_id, timestamp_ms
- outputs: build_forecast_signal_candidate
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/engine_c_runtime_support.py`
- responsibility: Support helpers for the Engine C runtime facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: context, coordination_input, coordination_outcome, engine_id, engine_output, event, feature_weights, hook, inputs, log_entries, logs, now, pair, penalized_score, raw_score, reasons, risk_evaluation, risk_runtime, runtime_input, scoring_audit, scoring_round, scoring_runtime, scoring_state, scoring_version, side, status, timestamp, timestamp_ms, value
- outputs: _EngineCScoringState, build_runtime_refusal_record, build_scoring_candidate, build_scoring_state, build_signal_candidate
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_c/invalidation_mapper_c.py`
- responsibility: Pure invalidation helpers for Engine C.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: breakout_level, entry_price, expected_gain, realized_vol_at_break, realized_vol_current
- outputs: build_invalidation_levels_c
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/output_payload_builder_c.py`
- responsibility: Pure output-payload assembly helpers for Engine C.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: log_entries, scoring_version, structure
- outputs: build_engine_c_output_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/signal_math_c.py`
- responsibility: Pure scoring helpers for Engine C signal evaluation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: context_score, extension_pct, followthrough_room, inputs
- outputs: compute_breakout_score, compute_context_score, compute_continuation_score, compute_continuation_score_components, compute_fake_breakout_risk
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_c/structure_resolver_c.py`
- responsibility: Pure structure-resolution helpers for Engine C.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs, structure
- outputs: build_engine_c_log_context
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/__init__.py`
- responsibility: Build-16 / engine_d.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: ENGINE_D_BUILD_STAGE = 16
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/consecutive_stop_counter_d.py`
- responsibility: Explicit Engine D consecutive-stop state helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: detected_at_ns, evaluated_at_ns, reset_failsafe_ns, state, stop_limit, stopped_at_ns
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: DEFAULT_D_CONSECUTIVE_STOP_LIMIT = 1, stop_limit_reached = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/context_resolver_d.py`
- responsibility: Pure context-resolution helpers for Engine D.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: context, inputs
- outputs: build_engine_d_log_context
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_d/conviction_builder_d.py`
- responsibility: Pure conviction helpers for Engine D.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: ce_expected, ce_min, concentration_risk, history_score, marginal_value_score, reformation_score
- outputs: build_conviction_d
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/coordination_input_assembler_d.py`
- responsibility: Governed Engine D coordination-input assembly from historical state.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: coordination_input_factory, d_consecutive_stop_limit, d_reset_failsafe_ns, evaluated_at_ns, journal, lookback_ns, pair, reference_size, side, stop_state
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/cost_feasibility_d.py`
- responsibility: Pure cost-feasibility helpers for Engine D.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate_size, ce_min, delta_safe, expected_cost, expected_gain, holding_period
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE = EngineDCostCallerThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/engine_d_models.py`
- responsibility: Shared typed models for the canonical Engine D runner/runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: concentration_risk = 0.0, marginal_concentration = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/engine_d_runner.py`
- responsibility: Canonical Engine D runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: inputs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: _CONCENTRATION_MAX = 0.64
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_d/engine_d_runner_late_stages.py`
- responsibility: Late-stage helpers for the canonical Engine D runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/engine_d_runner_support.py`
- responsibility: Internal support helpers for the canonical Engine D runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: ce_expected, concentration_risk, context, conviction, detailed_reason_codes, ev_net, event, expected_cost, gate_reason_codes, history_score, holding_hours, inputs, invalidation_levels, logs, marginal_value_score, no_trade_reasons, penalized_score, raw_score, reason_codes, reasons, reformation_score, tier
- outputs: build_engine_d_gate_reason_codes, build_engine_d_invalidation, build_engine_d_no_trade_output
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, gate
- duplication_notes: none

### `src/engines/engine_d/engine_d_runtime.py`
- responsibility: Engine D runtime across signal, scoring, ranking and risk.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = None
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- responsibility: Additive historical-entry helpers for the public Engine D runtime surface.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/engine_d_runtime_result_builders.py`
- responsibility: Result builders for the Engine D runtime facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/engine_d_runtime_support.py`
- responsibility: Support helpers for the Engine D runtime facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: context, coordination_input, coordination_outcome, engine_id, engine_output, event, feature_weights, hook, inputs, log_entries, logs, now, pair, penalized_score, raw_score, reasons, risk_evaluation, risk_runtime, runtime_input, scoring_audit, scoring_round, scoring_runtime, scoring_state, scoring_version, side, signal_candidate, status, strategy_id, timestamp, timestamp_ms, value
- outputs: _EngineDScoringState, build_forecast_signal_candidate, build_runtime_refusal_record, build_scoring_candidate, build_scoring_state, build_signal_candidate
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_d/engine_d_runtime_support_refusal.py`
- responsibility: Runtime refusal / downstream annotation helpers extracted from `engine_d_runtime_support.py` on 2026-04-18.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: forecast_signal_candidate, reason_codes, risk_evaluation, scoring_audit, status, timestamp_ms
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/engine_state_snapshot_d.py`
- responsibility: Append-only persistence for Engine D consecutive-stop state snapshots.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: runtime_only
- inputs: none
- outputs: EngineDStateSnapshot
- runtime_files_read: engine_d_state_snapshot_manifest.json, engine_d_state_snapshots.jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/first_episode_resolver_d.py`
- responsibility: Explicit Engine D first-episode resolution helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: as_of_ns, evaluated_at_ns, first_episode_ref, journal, lookback_ns, min_gap_ns, pair, side
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE = EngineDFirstEpisodeCallerThresholds()
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/engines/engine_d/historical_linkage_guard_d.py`
- responsibility: Explicit Engine D historical-linkage guard wrapping the canonical coordination rule.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: coordination_input, coordination_input_factory, evaluated_at_ns, evaluator, first_episode_ref, pair, reference_size, side, stop_state, thresholds
- outputs: build_engine_d_coordination_input
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/invalidation_mapper_d.py`
- responsibility: Pure invalidation helpers for Engine D.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: entry_price, expected_gain, realized_vol_current, realized_vol_post_close, reentry_anchor_price
- outputs: build_invalidation_levels_d
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/marginal_value_estimator_d.py`
- responsibility: Local marginal-value setup-quality threshold seam for Engine D.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: marginal_value_score, thresholds
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, gate
- duplication_notes: none

### `src/engines/engine_d/output_payload_builder_d.py`
- responsibility: Pure output-payload assembly helpers for Engine D.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: context, log_entries, scoring_version
- outputs: build_engine_d_output_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/runtime_input_assembler_d.py`
- responsibility: Governed Engine D runtime-input assembly from historical linkage state.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: blocker_conditions, cluster_id, coordination_input_factory, corr_penalty, current_equity, d_consecutive_stop_limit, d_reset_failsafe_ns, engine_inputs, journal, lookback_ns, max_selections, min_gap_ns, pair_beta, peer_candidates, portfolio, projected_loss, projected_size, realized_vol_current_record, realized_vol_post_close_record, reference_size, risk_penalty, score_penalties, session_peak_equity, size_penalties, stop_state, strategy_id, timestamp_ms
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/engines/engine_d/signal_math_d.py`
- responsibility: Pure scoring helpers for Engine D signal evaluation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: context_score, inputs
- outputs: compute_context_score, compute_history_score, compute_marginal_value_score, compute_reformation_score
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## execution_backbone

### `src/execution_backbone/__init__.py`
- responsibility: V5.3 - Execution Backbone: real, measurable, reconcilable execution.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/emergency_circuit_breaker.py`
- responsibility: GEM-10 / QWEN-07 — Emergency Circuit Breaker with disk persistence.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: KillSwitchState
- runtime_files_read: kill_switch_state.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: halt, kill
- duplication_notes: none

### `src/execution_backbone/execution_cost_meter/__init__.py`
- responsibility: execution_cost_meter â€” fees, ELW, adverse selection, partial fill costs, aggregation.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_cost_meter/adverse_selection_meter.py`
- responsibility: Build-3 / execution_cost_meter / adverse_selection_meter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: delay_s, event_delay_s, exec_price, mid_after, order_id, pair, policy, side
- outputs: compute_adverse_selection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_cost_meter/cost_aggregator.py`
- responsibility: Build-3 / execution_cost_meter / cost_aggregator
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: adverse_selection, engine_id, expected_cost, explicit_fee, implicit_cost, market_impact, order_id, pair, partial_fill_cost
- outputs: compute_trade_cost
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_cost_meter/elw_meter.py`
- responsibility: Build-3 / execution_cost_meter / elw_meter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: elw_entry, elw_exit, exec_price, mid_price, order_id, pair, side
- outputs: compute_elw, compute_implicit_round_trip
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_cost_meter/fee_meter.py`
- responsibility: Build-3 / execution_cost_meter / fee_meter
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: fee_amount, fee_asset, fee_rate, maker, order_id, pair, price, quantity
- outputs: compute_fee
- runtime_files_read: none
- formulas_or_derived_metrics: fee_rate_exact = divide_exact_or_zero(fee_amount_decimal, gross_value_exact)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_cost_meter/partial_fill_cost_meter.py`
- responsibility: Build-3 / execution_cost_meter / partial_fill_cost_meter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: current_mid, fill_prices, fill_quantities, order_id, ordered_quantity, pair
- outputs: compute_partial_fill_cost
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_routing_bridge.py`
- responsibility: Build-3 live feature bridge for the hybrid routing surface.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_routing_features.py`
- responsibility: Typed live routing feature contracts for Build-3 hybrid routing.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: reason_codes, snapshot
- outputs: ExecutionRoutingFeatureSnapshot, ExecutionRoutingTopOfBookSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/execution_runtime.py`
- responsibility: Build-3 / execution_backbone / execution_runtime
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: fee_rate = self._default_fee_rate if context.fee_rate is None else context.fee_rate, forced_order_type = "limit"
- thresholds_or_constants: none
- control_flags_or_gates: blocked, shadow_only
- duplication_notes: none

### `src/execution_backbone/execution_runtime_models.py`
- responsibility: Models and protocols for the canonical Build-3 execution runtime.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: RemoteExecutionState, RuntimeProcessingSummary, _TerminalOrderSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: fee_rate = None
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/execution_backbone/execution_runtime_support.py`
- responsibility: Internal support mixin for the canonical Build-3 execution runtime.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/execution_backbone/fee_aware_edge_gate.py`
- responsibility: Fee-aware edge gate resolved from shared calibration artifacts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: config, expected_cost, expected_edge_bps
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: detail = f"edge={expected_edge_bps:.2f}bps vs threshold={threshold_bps:.2f}bps "
        f"(cost={expected_cost_bps:.2f}bps, multiplier={thresholds.edge_multiplier:.4f}, "
        f"absolute_floor={thresholds.min_absolute_edge_bps:.2f}bps)"
- thresholds_or_constants: threshold_bps = 0.0
- control_flags_or_gates: gate
- duplication_notes: none

### `src/execution_backbone/fill_tracker/__init__.py`
- responsibility: fill_tracker â€” order lifecycle, fills, latency, terminal states.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/fill_tracker/fill_aggregator.py`
- responsibility: Build-3 / fill_tracker / fill_aggregator
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/fill_tracker/fill_reporter.py`
- responsibility: Build-3 / fill_tracker / fill_reporter
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: full_fill_rate = 0.0, partial_fill_rate = 0.0, reject_rate = 0.0
- thresholds_or_constants: expirations = 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/fill_tracker/latency_meter.py`
- responsibility: Build-3 / fill_tracker / latency_meter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/fill_tracker/order_state_tracker.py`
- responsibility: Build-3 / fill_tracker / order_state_tracker
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: OrderState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: average_fill_price = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/fill_tracker/order_terminal_state_resolver.py`
- responsibility: Build-3 / fill_tracker / order_terminal_state_resolver
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: filled_quantity, order_id, ordered_quantity, state
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/gatekeeper/__init__.py`
- responsibility: Canonical execution gatekeeper surface.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/gatekeeper/audit_logger.py`
- responsibility: Append-only audit logger for canonical gatekeeper decisions.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/execution_backbone/gatekeeper/gatekeeper.py`
- responsibility: Bounded canonical execution gatekeeper over the existing Build-3 guard chain.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: RATE_LIMITER = "rate_limiter", rate_limit_refusal = self._authorize_rate_limit(opportunity, trace), rate_limit_decision = self._resolve_rate_limit(opportunity)
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, passed, passed
- duplication_notes: none

### `src/execution_backbone/gatekeeper/gatekeeper_support.py`
- responsibility: Pure helper functions for the canonical Build-3 execution gatekeeper.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: decision, guard, outcome
- outputs: build_execution_no_trade_filter_context, build_fee_aware_edge_context, build_order_type_context, build_rate_limit_context, build_sharia_context, build_spread_guard_context
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/execution_backbone/order_decider/__init__.py`
- responsibility: order_decider â€” decide order type, guard execution, build intent.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/decision_reporter.py`
- responsibility: Build-3 / order_decider / decision_reporter
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: trade_rate = 0.0, limit = sum(1 for e in trades if e.order_type == OrderType.LIMIT)
- thresholds_or_constants: limit_orders = 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/execution_guard.py`
- responsibility: Build-3 / order_decider / execution_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: data_stale, expected_cost, infrastructure_ok, max_acceptable_cost, pair_health_min, pair_health_score, pair_suspended, risk_budget_available
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: suspended
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router.py`
- responsibility: Deterministic Build-3 hybrid router V2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue, shadow_only
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router_calibration.py`
- responsibility: Governed calibration for the Build-3 hybrid router V2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: config
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router_equations.py`
- responsibility: Pure equations for the Build-3 hybrid router V2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: calib, capital_opportunity_cost_bps, composite_dir, eps_notional, expected_adverse_selection_bps, expected_edge_bps, expected_latency_staleness_bps, expected_miss_cost_bps, expected_taker_slippage_bps, expected_wait_s, lambda_impact_bps, maker_fee_bps, market_toxicity_score, p_fill_proxy, participation_ratio, rate_bps_per_s, regime_stability_score, regime_transition_risk, scale_bps, short_window_volatility_z, sign_side, snap, spread_bps, taker_fee_bps, tau_alpha_s, x
- outputs: compute_alpha_decay_factor, compute_capital_opportunity_cost_bps, compute_ev_maker_raw_bps, compute_ev_maker_weighted_bps, compute_ev_taker_bps, compute_expected_adverse_selection_bps, compute_expected_latency_staleness_bps, compute_expected_miss_cost_bps, compute_expected_taker_slippage_bps, compute_p_fill_proxy, compute_participation_ratio, compute_same_side_signals
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router_metrics.py`
- responsibility: Execution-backbone-local metrics sink and projections for hybrid routing V2.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: HybridRouterCalibrationMetricProjection, HybridRouterDistributionSummary, HybridRouterFullTraceProjection, HybridRouterMetricsProjection, HybridRouterTraceProjection
- runtime_files_read: none
- formulas_or_derived_metrics: routing_feature_rejection_rate = Field(default_factory=dict), lower = math.floor(rank), rejection_rate = {}
- thresholds_or_constants: participation_ratio = 0.0
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router_sanitization.py`
- responsibility: Sanitization helpers for the Build-3 hybrid router V2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: clip, fields, name, raw
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router_shadow.py`
- responsibility: Shadow-only logging for Build-3 hybrid routing V2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/execution_backbone/order_decider/hybrid_router_types.py`
- responsibility: Typed contracts for the Build-3 hybrid router V2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: calibration_version, decision, shadow_only
- outputs: build_compact_routing_trace, build_compact_routing_trace_payload, build_full_routing_trace, build_full_routing_trace_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/execution_backbone/order_decider/intent_builder.py`
- responsibility: Build-3 / order_decider / intent_builder
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: engine_id, expected_cost, expected_gain, intent_id, justification, order_type, pair, price_limit, price_limit_exact, profile, quantity, quantity_exact, score, side, timeout_s, venue_constraints
- outputs: VenueConstraintSnapshot, build_intent
- runtime_files_read: none
- formulas_or_derived_metrics: LIMIT = "limit"
- thresholds_or_constants: timeout_s = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/order_type_selector.py`
- responsibility: Build-3 / order_decider / order_type_selector
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: expected_cost, expected_gain, max_spread_for_market, safety_margin, spread_bps, use_limit_threshold_bps
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/order_decider/timeout_policy_selector.py`
- responsibility: Build-3 / order_decider / timeout_policy_selector
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: cancel_policy, custom_timeout_s, order_type
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: _DEFAULT_TIMEOUTS = {
    OrderType.MARKET: 5.0,  # market orders should fill fast
    OrderType.LIMIT: 30.0,  # limit orders get more time
    OrderType.NO_TRADE: 0.0,
}
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/rate_limiter.py`
- responsibility: Bounded execution-side consumer for Local IA Lab THR-X03 quota-ratio ceilings.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: current_quota_ratio, model
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/__init__.py`
- responsibility: reconciliation_layer â€” local vs real state alignment, divergence detection, recovery.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/divergence_classifier.py`
- responsibility: Build-3 / reconciliation_layer / divergence_classifier
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: abs_diff, detail, divergences, source
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: warning_threshold = 0.0, blocking_threshold = 0.0, critical_threshold = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/fill_reconciler.py`
- responsibility: Build-3 / reconciliation_layer / fill_reconciler
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: local_fills, policy, remote_fills
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/order_reconciler.py`
- responsibility: Build-3 / reconciliation_layer / order_reconciler
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: local_orders, remote_orders
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/position_reconciler.py`
- responsibility: Build-3 / reconciliation_layer / position_reconciler
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: local_positions, policy, remote_positions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/recovery_trigger.py`
- responsibility: Build-3 / reconciliation_layer / recovery_trigger
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: recon_age_s = 0.0, recon_age = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/reconciliation_layer/scheduler.py`
- responsibility: Bounded boot + periodic reconciliation scheduler for the canonical Build-3 rail.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: config
- outputs: ReconciliationSchedulerState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/slippage_model.py`
- responsibility: Bounded execution-side consumer for Local IA Lab THR-X05 slippage models.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: model, size_value
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/execution_backbone/spread_guard.py`
- responsibility: Bounded execution-side consumer for Local IA Lab THR-X04 spread ceilings.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: current_spread_bps, model
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/execution_backbone/venue_constraints_provider.py`
- responsibility: Optional venue-constraint providers for exchange-facing execution boundaries.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: pair, payload
- outputs: VenueConstraintCacheState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## interface_contracts

### `src/interface_contracts/__init__.py`
- responsibility: V5.3 — INTERFACE_CONTRACTS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/artifact_contracts.py`
- responsibility: V5.3 - ARTIFACT_CONTRACTS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/artifact_contracts_models.py`
- responsibility: Typed models and enums for governed artifact contracts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: ArtifactExportBundle, ArtifactHealthState, ArtifactProofSummary
- runtime_files_read: none
- formulas_or_derived_metrics: threshold = None, max_block_rate_delta = 0.10
- thresholds_or_constants: require_operational_burden_pass = True, require_capital_efficiency_when_present = True, self.threshold compare None
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/artifact_contracts_runtime.py`
- responsibility: Runtime constants and helpers for governed artifact contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: drift_score_threshold, governance_reference_date, hook_id, lifecycle_policy, observed_drift_score, policy, proof_summary, training_end
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/atomic_io.py`
- responsibility: Atomic file I/O helpers — write-and-rename pattern to prevent partial/corrupt writes.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: data, encoding, indent, path, text
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/binance_contracts.py`
- responsibility: Typed contracts for the Binance Spot venue adapter.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: BinanceAccountSnapshot, BinanceUserDataExecutionReport
- runtime_files_read: none
- formulas_or_derived_metrics: rate_limit_type = Field(..., min_length=1), limit = Field(..., ge=0), rate_limits = (), LIMIT = "LIMIT", RATE_LIMITED = "rate_limited"
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/build14_contracts.py`
- responsibility: Shared Build-14 enums and typed contracts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: Build14EnablerSnapshot, Build14HardState, Build14InfluenceReport
- runtime_files_read: none
- formulas_or_derived_metrics: cra_sterilization_rate = Field(..., ge=0.0, le=1.0), ce_net = 0.0, breakout_failure_rate = Field(default=0.0, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: review_only, review_only
- duplication_notes: none

### `src/interface_contracts/closed_episode_contracts.py`
- responsibility: Typed closed-episode contracts shared across protocols and engines.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/dashboard_command_contracts.py`
- responsibility: Typed dashboard-to-VPS governed command contracts for Build-17 control.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: active, manifest, sealed_ref, secret_hash, validation_status
- outputs: BinanceCredentialInventorySnapshot, DashboardCommandQueueSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, queue, runtime_mode
- duplication_notes: none

### `src/interface_contracts/decision_contracts.py`
- responsibility: V5.3 — DECISION_CONTRACTS
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: order_type = Field(..., pattern="^(limit|market)$")
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/domain_types.py`
- responsibility: V5.3 — DOMAIN_TYPES
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: DeploymentState, PromotionState, ReviewState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/engine_coordination_contracts.py`
- responsibility: Typed engine coordination contracts shared across protocols and engines.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/interface_contracts/engine_validation_contracts.py`
- responsibility: Shared Engine C/D validation-hook contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/error_contracts.py`
- responsibility: V5.3 — ERROR_CONTRACTS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/feature_lock_contracts.py`
- responsibility: V5.3 - FEATURE LOCK CONTRACTS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: feature_ids, lineage_lock, transform_ids, whitelist_lock
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: lineage_required = True
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/forecast_contracts.py`
- responsibility: V5.3 - FORECAST_CONTRACTS
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: calibration_profile_id, calibration_status, penalties, physics_calibration_profile_id, physics_calibration_status, scoring_version, timestamp_ms
- outputs: build_forecast_versions, build_scoring_conditioning_records
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = Field(..., min_length=1)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/live_complete_actions.py`
- responsibility: Shared typed Build-17 action contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/market_event_contracts.py`
- responsibility: V5.3 — MARKET_EVENT_CONTRACTS
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: funding_rate = Field(default=None)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/meta_contracts.py`
- responsibility: V5.3 — META_CONTRACTS
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: error_rate_pct = Field(default=None, ge=0.0, le=100.0), win_rate = Field(default=None, ge=0, le=1)
- thresholds_or_constants: none
- control_flags_or_gates: suspended, suspended
- duplication_notes: none

### `src/interface_contracts/ml_backtest_training_contracts.py`
- responsibility: Typed Local-Lab ML inputs projected from governed backtest/replay data.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/ml_model_artifact.py`
- responsibility: Typed contract for Local-Lab-trained ML model artifacts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: win_rate = Field(default=None, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/ml_model_transport_contracts.py`
- responsibility: Shared typed contracts for governed ML supplementary transport refs.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: MlModelSourceArtifactSummary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/numeric_contracts.py`
- responsibility: V5.3 - NUMERIC_CONTRACTS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: denominator, left, max_abs_loss, name, numerator, right, step, value, values
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/operator_contracts.py`
- responsibility: Operator-governance contracts shared across monitoring, UI, and protocols.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/interface_contracts/pair_catalog.py`
- responsibility: Venue-specific market filter specifications for the 7 V5.3 canonical pairs.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/refusal_records.py`
- responsibility: V5.3 - REFUSAL_RECORDS
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/regime_detector_artifact.py`
- responsibility: Typed artifact contract for VPS-shadow RegimeDetectorML.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: RegimeDetectorArtifactSummary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/regime_detector_label_contracts.py`
- responsibility: Typed Local-IA-Lab label and dataset contracts for RegimeDetectorML.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/regime_detector_shadow_audit_contracts.py`
- responsibility: Typed contracts for VPS->IA Lab shadow audit bundles of RegimeDetectorML.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: RegimeDetectorShadowAuditBundle, RegimeDetectorShadowAuditMetricSummary
- runtime_files_read: none
- formulas_or_derived_metrics: insufficient_data_rate = Field(default=0.0, ge=0.0, le=1.0), runtime_stale_rate = Field(default=0.0, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/interface_contracts/shadow_vps_service_contracts.py`
- responsibility: Shared Shadow VPS service state/event contracts.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: ShadowVpsCampaignSummary, ShadowVpsExecutionRuntimeBootstrapSummary, ShadowVpsRuntimeEvidenceBundle, ShadowVpsServiceState
- runtime_files_read: none
- formulas_or_derived_metrics: execution_runtime_projection_rate_limit_model_loaded = False
- thresholds_or_constants: last_execution_runtime_bootstrap_remote_state_snapshot_captured = False, execution_runtime_projection_rate_limit_model_loaded = False, execution_runtime_projection_slippage_model_loaded = False, remote_state_snapshot_captured = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/strategy_identity.py`
- responsibility: V5.3 - STRATEGY_IDENTITY
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/venue_error_contracts.py`
- responsibility: Adapter-facing runtime error contracts.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/interface_contracts/vps_recovery_contracts.py`
- responsibility: Typed recovery and warm-up proof contracts for governed VPS startup.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: VpsRecoveryReadinessReport, VpsWarmupRunSummary, VpsWarmupState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, blocked, eligible_to_trade, eligible_to_trade, passed, passed, passed, review_only, review_only, runtime_mode
- duplication_notes: none

## local_replay_runtime

### `src/local_replay_runtime/__init__.py`
- responsibility: Minimal LOCAL_REPLAY scaffold for the unified V5.3 plan.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/artifact_ablation_study.py`
- responsibility: Governed Local IA Lab ablation study between baseline and candidate replay exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: baseline_dataset_manifest_id, baseline_export_dir, baseline_records, baseline_run_id, candidate_dataset_manifest_id, candidate_export_dir, candidate_records, candidate_run_id, correlation_id, selected_engine_id, selected_pair
- outputs: build_local_lab_ablation_study, build_pending_local_lab_ablation_study
- runtime_files_read: none
- formulas_or_derived_metrics: candidate_block_rate = 0.0, baseline_block_rate = 0.0, block_rate_delta = 0.0, candidate_block_rate = _block_rate(aligned_candidate), baseline_block_rate = _block_rate(aligned_baseline), block_rate_delta = max(candidate_block_rate - baseline_block_rate, 0.0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/artifact_exporter.py`
- responsibility: Artifact exporter for governed LOCAL_REPLAY runs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: output_dir, request
- outputs: none
- runtime_files_read: feature_bridge.json, parity_diagnostics.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/artifact_manifest.py`
- responsibility: Canonical manifest for LOCAL_REPLAY artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_version = Field(..., min_length=1)
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/artifact_proof_summary_builder.py`
- responsibility: Conservative Local IA Lab proof-summary builder for governed artifact export.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: ablation_study, calibration_methods_review, correlation_id, execution_runtime_projection, export_dir, meta_result, multiple_testing_review, run_id, trade_loss_attribution, walk_forward_review
- outputs: _AblationAssessmentState, _CalibrationMethodsAssessmentState, _CoreAssessmentState, _ExecutionRuntimeProjectionAssessmentState, _MultipleTestingAssessmentState, build_local_lab_artifact_proof_assessment
- runtime_files_read: none
- formulas_or_derived_metrics: observed_block_rate_proxy = Field(default=0.0, ge=0.0), observed_block_rate_proxy = _build_block_rate_proxy(meta_result)
- thresholds_or_constants: calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/artifact_release_candidate.py`
- responsibility: Future-facing Local IA Lab artifact release candidate for governed VPS import.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: artifact_id, artifact_input_summary_path, artifact_path, artifact_proof_assessment_path, artifact_proof_ready, artifact_proof_summary_path, artifact_proof_validation_reasons, baseline_export_dir, calibration_methods_dsr_pass, calibration_methods_review_ready, calibration_methods_review_status, calibration_methods_walk_forward_plan_ready, correlation_id, edge_calibration_ready, execution_runtime_projection_blocked_consumer_count, execution_runtime_projection_blocking_reasons, execution_runtime_projection_consumer_count, execution_runtime_projection_partial_consumer_count, execution_runtime_projection_ready, execution_runtime_projection_ready_consumer_count, execution_runtime_projection_status, export_dir, local_lab_calibration_methods_review_path, local_lab_execution_runtime_projection_path, local_lab_recalibration_plan_path, recalibration_blocking_reasons, recalibration_candidate_ready, release_candidate, run_id, scope, scope_matrix, scope_matrix_path, shared_artifact_import_dry_run_bridge_path, shared_release_gate_summary_path, shared_source_artifact_summary_path, walk_forward_review_summary_path
- outputs: LocalLabArtifactReleaseScopeSummary, build_local_lab_artifact_release_candidate, build_local_lab_artifact_release_scope_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False, recalibration_candidate_ready = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/artifact_upload_bridge_candidate.py`
- responsibility: Typed Local IA Lab dry-run bridge contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: LocalLabReleaseGateSummary, LocalLabSourceArtifactSummary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: release_calibration_methods_review_ready = False, release_calibration_methods_walk_forward_plan_ready = False, release_recalibration_candidate_ready = False
- control_flags_or_gates: gate
- duplication_notes: none

### `src/local_replay_runtime/contracts.py`
- responsibility: Contracts for the LOCAL_REPLAY scaffold.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: ReplayBundle
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/edge_gate_calibration.py`
- responsibility: Local IA Lab EDGE calibration from governed replay DTR evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: artifact, config, generated_at, path, records, report, signature_note, signed_at, signed_by
- outputs: EdgeGateCalibrationReport, build_edge_gate_calibration_artifact
- runtime_files_read: config/calibration/v1/edge_gate.yml
- formulas_or_derived_metrics: thresholds = (
        CalibrationThresholdEntry(
            threshold_id=calibration.edge_multiplier_threshold_id,
            value=round(
                report.get_threshold(calibration.edge_multiplier_threshold_id).published_value,
                6,
            ),
            description="Minimum multiplier between expected edge and expected cost.",
            source_module=calibration.source_module,
            calibration_artifact=calibration.calibration_artifact_path,
            notes="Local IA Lab replay calibration; published conservatively from upper CI.",
        ),
        CalibrationThresholdEntry(
            threshold_id=calibration.min_absolute_edge_threshold_id,
            value=round(
                report.get_threshold(calibration.min_absolute_edge_threshold_id).published_value,
                6,
            ),
            description="Absolute expected-edge floor in bps.",
            source_module=calibration.source_module,
            calibration_artifact=calibration.calibration_artifact_path,
            notes="Local IA Lab replay calibration; published conservatively from upper CI.",
        ),
    ), lower_index = int(math.floor(position))
- thresholds_or_constants: threshold.threshold_id compare threshold_id
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/enums.py`
- responsibility: Enums for the LOCAL_REPLAY scaffold.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: ReplayLifecycleState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/errors.py`
- responsibility: Errors for the LOCAL_REPLAY scaffold.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/historical_data_gateway.py`
- responsibility: Historical dataset loader for governed LOCAL_REPLAY sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: auto_materialize_feature_locks, dataset, dataset_id, dataset_path, feature_lineage_lock, source, transform_whitelist_lock
- outputs: build_feature_bridge_payload, load_historical_replay_dataset
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/historical_snapshot_loader.py`
- responsibility: Historical market snapshot loader for governed LOCAL_REPLAY sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: snapshot_path, source
- outputs: load_historical_snapshot_batch
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/live_complete_operator_audit_report.py`
- responsibility: Operator-facing final Build-17 audit report for governed Complete supervision.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: live_complete_summary, ml_final_audit_report, recent_events_summary, recent_events_summary_ref, regime_detector_final_audit_report, report, report_ref
- outputs: LiveCompleteOperatorAuditReport, build_live_complete_operator_audit_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, eligible_to_trade, eligible_to_trade
- duplication_notes: none

### `src/local_replay_runtime/local_lab_calibration_methods_review.py`
- responsibility: Local IA Lab review sidecar over shared calibration-method primitives.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, dsr_floor, export_dir, records, run_id
- outputs: build_local_lab_calibration_methods_review
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/local_replay_runtime/local_lab_calibration_normalized_report.py`
- responsibility: Normalized Local IA Lab calibration report over bounded 13-A/13-B evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: calibration_methods_review, correlation_id, edge_config, edge_report, export_dir, multiple_testing_review, records, run_id, tail_risk_review
- outputs: LocalLabCalibrationThresholdReport, LocalLabNormalizedCalibrationReport, build_local_lab_calibration_normalized_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/local_replay_runtime/local_lab_execution_review.py`
- responsibility: Local IA Lab execution-threshold review for THR-X01 to THR-X05.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, run_id, telemetry
- outputs: build_local_lab_execution_review
- runtime_files_read: none
- formulas_or_derived_metrics: ready_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "ready"), partial_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "partial"), blocked_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "blocked")
- thresholds_or_constants: threshold.review_status compare "ready", threshold.review_status compare "partial", threshold.review_status compare "blocked"
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/local_replay_runtime/local_lab_execution_runtime_projection.py`
- responsibility: Project Local IA Lab execution review outputs into future runtime consumer contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: execution_review
- outputs: LocalLabExecutionRuntimeConsumerProjection, LocalLabExecutionRuntimeProjection, build_local_lab_execution_runtime_projection
- runtime_files_read: none
- formulas_or_derived_metrics: status = LocalLabExecutionRuntimeProjectionStatus(threshold.review_status.value), estimate = threshold.threshold_estimate, model = threshold.slippage_model_estimate
- thresholds_or_constants: threshold_fit_ready = False, threshold.threshold_id compare threshold_id
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/local_replay_runtime/local_lab_execution_telemetry_archive_support.py`
- responsibility: Support helpers for Local IA Lab execution telemetry archive materialization.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: archive, export_dir, run_id, session
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
- responsibility: Service-owned execution telemetry archive for Local IA Lab THR-X01 to THR-X05.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: archive, archive_path, artifact_path, existing_archive, export_dir, path, run_id, session, session_date, snapshot_batch_path, stream_path, time_sync_offsets_path, websocket_stream_path
- outputs: build_execution_telemetry_session_from_sources, build_local_lab_execution_telemetry_artifact_for_export, derive_candidate_sizes_from_snapshot_batch, derive_candidate_sizes_from_stream, derive_final_sizes_from_snapshot_batch, derive_final_sizes_from_stream, derive_slippage_bps_from_snapshot_batch, derive_slippage_bps_from_stream, derive_spread_bps_from_snapshot_batch, derive_spread_bps_from_stream, derive_websocket_interarrival_s_from_snapshot_batch, derive_websocket_interarrival_s_from_stream, load_local_lab_execution_telemetry_archive, load_local_lab_execution_telemetry_artifact, load_time_sync_offsets_ms, load_time_sync_probe_payload
- runtime_files_read: replay_run_manifest.json
- formulas_or_derived_metrics: observed_rate_value = time_sync_payload.get("observed_calls_per_minute")
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_loss_surrogate.py`
- responsibility: Bounded trained loss-risk surrogate for Local IA Lab research only.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, min_training_records, records, scope_matrix, selected_engine_id, selected_pair
- outputs: LocalLabLossSurrogateReport, build_local_lab_loss_surrogate_report
- runtime_files_read: none
- formulas_or_derived_metrics: actual_loss_rate = Field(default=0.0, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_ml_artifact_training.py`
- responsibility: Governed Local-Lab ML artifact training from replay/backtest evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: allowed_feature_keys, artifact_id, calibration_version, correlation_id, dataset, dtr_records, export_dir, include_route_features, max_optuna_trials, min_training_rows, scope_matrix, selected_engine_id, selected_pair, shap_summary_ref, training_seed
- outputs: LocalLabMlArtifactTrainingReport, build_local_lab_ml_artifact_training_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_multiple_testing_review.py`
- responsibility: Local IA Lab multiple-testing review sidecar over current calibration evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, edge_report, export_dir, family_alpha, family_id, hypotheses, run_id, tail_risk_review
- outputs: build_hypothesis_test_family_review, build_local_lab_multiple_testing_review
- runtime_files_read: none
- formulas_or_derived_metrics: families = (
        _build_interval_publication_family(
            family_id="edge_gate_interval_publication",
            threshold_ids=tuple(threshold.threshold_id for threshold in edge_report.thresholds),
        ),
        _build_interval_publication_family(
            family_id="tail_risk_interval_publication",
            threshold_ids=tuple(breaker.threshold_id for breaker in tail_risk_review.breakers),
        ),
    )
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/local_replay_runtime/local_lab_promotion_readiness.py`
- responsibility: Top-level Local IA Lab promotion-readiness projection over the dry-run handoff rail.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: dry_run_bridge, release_candidate
- outputs: LocalLabPromotionReadinessSummary, build_local_lab_promotion_readiness_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: recalibration_candidate_ready = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_recalibration_plan.py`
- responsibility: Typed Local IA Lab recalibration planning from governed loss attribution evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, loss_reports, loss_surrogate_report, scope_matrix
- outputs: _LossSurrogateState, build_local_lab_recalibration_plan
- runtime_files_read: none
- formulas_or_derived_metrics: sterilization_attributions = tuple(
            attribution
            for attribution in losses
            if attribution.primary_failure_mode == "sterilization"
        )
- thresholds_or_constants: calibration_candidate_ready = False, failure_mode_counts.get("sterilization", 0) compare 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_regime_detector_artifact_training.py`
- responsibility: Governed Local-IA-Lab RegimeDetector artifact training from historical LOB events.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: artifact_id, batch, calibration_version, dataset_id, feature_profile, label_config, max_optuna_trials, pair_scope, training_seed
- outputs: LocalLabRegimeDetectorArtifactTrainingReport, build_local_lab_regime_detector_artifact_training_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_replay_candidate_queue.py`
- responsibility: Bounded Local IA Lab replay/research queue derived from current planning truth.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, max_candidates, recalibration_plan, research_priority_report
- outputs: build_local_lab_replay_candidate_queue
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/local_replay_runtime/local_lab_replay_dispatch_plan.py`
- responsibility: Local-only dispatch plan derived from the governed Local IA Lab replay ticket index.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, replay_ticket_index
- outputs: build_local_lab_replay_dispatch_plan
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/local_replay_runtime/local_lab_replay_ticket_index.py`
- responsibility: Governed Local IA Lab replay ticket index derived from the replay candidate queue.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, lineage_version, profile, replay_candidate_queue, strategy_classification
- outputs: build_local_lab_replay_ticket_index
- runtime_files_read: none
- formulas_or_derived_metrics: _ENGINE_TO_STRATEGY = {
    "engine_a": StrategyClassification.A_VARIANT,
    "engine_b": StrategyClassification.B_VARIANT,
    "engine_c": StrategyClassification.C_CANDIDATE,
    "engine_d": StrategyClassification.D_CANDIDATE,
}, strategy_classification = explicit_classification, strategy_classification = _ENGINE_TO_STRATEGY.get(candidate.engine_id)
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `src/local_replay_runtime/local_lab_replay_workflow_loader.py`
- responsibility: File-based loader for Local IA Lab replay workflow sidecars.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: bundle_dir
- outputs: LocalLabReplayWorkflowBundle, load_local_lab_replay_workflow_bundle
- runtime_files_read: local_lab_replay_candidate_queue.json, local_lab_replay_dispatch_plan.json, local_lab_replay_ticket_index.json, local_lab_replay_workflow_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/local_replay_runtime/local_lab_replay_workflow_manifest.py`
- responsibility: Manifest over Local IA Lab replay workflow sidecars.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: replay_candidate_queue, replay_candidate_queue_path, replay_dispatch_plan, replay_dispatch_plan_path, replay_ticket_index, replay_ticket_index_path
- outputs: build_local_lab_replay_workflow_manifest
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/local_replay_runtime/local_lab_research_priority.py`
- responsibility: Interpretable Local IA Lab research-priority scorer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: artifact_proof_ready, artifact_proof_validation_reasons, correlation_id, export_dir, loss_reports, loss_surrogate_report, release_blocking_reasons, release_ready_for_shadow, scope_matrix, selected_engine_id, selected_pair, weights
- outputs: LocalLabResearchPriorityReport, build_local_lab_research_priority_report
- runtime_files_read: none
- formulas_or_derived_metrics: loss_rate_weight = Field(default=0.30, ge=0.0, le=1.0), loss_rate = Field(default=0.0, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_scope_matrix.py`
- responsibility: Typed multi-scope projection for Local IA Lab candidate vs baseline analysis.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: baseline_export_dir, correlation_id, engine_id, export_dir, pair, records, scopes
- outputs: build_local_lab_scope_matrix, build_local_lab_scope_slug
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: calibration_methods_review_ready = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/local_lab_tail_risk_review.py`
- responsibility: Local IA Lab tail-risk review over POT-GPD breakers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: config, correlation_id, export_dir, records, run_id
- outputs: build_local_lab_tail_risk_review
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/local_replay_runtime/ml_backtest_projection.py`
- responsibility: Projection from governed replay/backtest rows into ML backtest contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: allowed_feature_keys, dataset, dataset_id, dtr_record, dtr_records, opportunity
- outputs: build_ml_backtest_training_dataset, build_ml_backtest_training_dataset_from_replay_and_dtr
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/ml_final_audit_report.py`
- responsibility: Final IA-Lab audit report for the governed ML artifact export loop.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: command_result, correlation_id, training_report
- outputs: LocalLabMlFinalAuditReport, build_local_lab_ml_final_audit_report_from_vps_command_result
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/local_replay_runtime/orchestrator.py`
- responsibility: Governed LOCAL_REPLAY bundle preparation helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/performance_mode_guard.py`
- responsibility: Guardrails for governed LOCAL_REPLAY performance modes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: run_manifest, session_config
- outputs: PerformanceModeGuardReport, build_performance_mode_guard_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/regime_detector_dataset_builder.py`
- responsibility: Local-IA-Lab regime-training dataset builder from governed historical LOB events.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: batch, dataset_id, label_config, pair_scope
- outputs: build_regime_detector_training_dataset
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/regime_detector_final_audit_report.py`
- responsibility: Final Local IA Lab audit report joining profile comparison and VPS shadow diagnosis.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: artifact_id_prefix, batch, calibration_version, command_result, correlation_id, dataset_id, label_config, max_optuna_trials, pair_scope, shadow_audit_bundle, shadow_audit_bundle_ref, training_seed
- outputs: LocalLabRegimeDetectorFinalAuditReport, build_local_lab_regime_detector_final_audit_report, build_local_lab_regime_detector_final_audit_report_from_vps_command_result
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/local_replay_runtime/regime_detector_profile_comparison.py`
- responsibility: Local IA Lab comparison of RegimeDetector feature profiles.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: artifact_id_prefix, batch, calibration_version, correlation_id, dataset_id, label_config, max_optuna_trials, pair_scope, reports, training_seed
- outputs: LocalLabRegimeDetectorProfileComparisonReport, build_local_lab_regime_detector_profile_comparison_report, build_local_lab_regime_detector_profile_comparison_report_from_reports
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/local_replay_runtime/regime_detector_shadow_audit_diagnosis.py`
- responsibility: IA-Lab import and root-cause diagnosis for RegimeDetector shadow audit bundles.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: bundle, bundle_ref, expected_artifact, expected_feature_profile, min_observation_coverage_ratio
- outputs: build_local_lab_regime_detector_shadow_audit_diagnosis, load_regime_detector_shadow_audit_bundle
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: _CANONICAL_SHADOW_DIFF_PCT_LIMIT = 0.1, _DEFAULT_OBSERVATION_COVERAGE_FLOOR = 0.6
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/local_replay_runtime/replay_clock.py`
- responsibility: Replay clock helpers for governed LOCAL_REPLAY sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: clock_id, dataset, mode
- outputs: build_replay_clock
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_dtr_exporter.py`
- responsibility: Export helpers for governed LOCAL_REPLAY DTR artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: path, records
- outputs: load_replay_dtr_records
- runtime_files_read: Replay DTR exports must use .json or .jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_event_router.py`
- responsibility: Replay event router from raw historical events to normalized opportunities.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: config, dataset_id, snapshot_batch, source
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_executor.py`
- responsibility: Governed session executor for LOCAL_REPLAY artifact generation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: execution_input, output_dir
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: lines = [
        "# Governed Local Replay Review",
        "",
        "## Run",
        f"- run_id: {execution_input.run_manifest.run_id}",
        f"- strategy_id: {execution_input.run_manifest.strategy_id}",
        f"- strategy_version: {execution_input.run_manifest.strategy_version}",
        f"- lineage_version: {execution_input.run_manifest.lineage_version}",
        f"- profile_scope: {execution_input.run_manifest.profile_scope.value}",
        f"- runtime_mode: {execution_input.run_manifest.runtime_mode.value}",
        f"- performance_mode: {execution_input.run_manifest.performance_mode}",
        "",
        "## Coverage",
        f"- total_opportunities: {execution_input.total_opportunities}",
        f"- total_records: {metrics_summary.total_records}",
        f"- dtr_coverage: {metrics_summary.dtr_coverage:.3f}",
        "",
        "## Replay Metrics",
        f"- ce_net: {metrics_summary.ce_net:.6f}",
        f"- expected_cost_mean: {metrics_summary.expected_cost_mean:.6f}",
        f"- realized_cost_mean: {metrics_summary.realized_cost_mean:.6f}",
        f"- gross_return_total: {metrics_summary.gross_return_total:.6f}",
        f"- drawdown_proxy: {metrics_summary.drawdown_proxy:.6f}",
        "",
        "## Parity",
        f"- status: {execution_input.parity_diagnostics_payload.get('parity_status', 'unknown')}",
        f"- decision_match_rate: {execution_input.parity_diagnostics_payload.get('decision_match_rate', 'n/a')}",
        "",
        "## Notes",
        *[f"- {note}" for note in notes],
    ]
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/replay_metrics_collector.py`
- responsibility: Derived metrics for governed LOCAL_REPLAY artifact exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: records, total_opportunities
- outputs: ReplayMetricsSummary, build_replay_metrics_summary
- runtime_files_read: none
- formulas_or_derived_metrics: ce_net = 0.0, pair_aggregates = tuple(
        ReplayPairAggregate(
            pair=pair,
            record_count=len(group),
            selected_count=sum(1 for record in group if record.decision_state in selected_states),
            ce_net=round(sum(record.ce_expected for record in group), 6),
            expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
            realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
            gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
        )
        for pair, group in sorted(pair_groups.items())
    ), engine_aggregates = tuple(
        ReplayEngineAggregate(
            engine_id=engine_id,
            record_count=len(group),
            selected_count=sum(1 for record in group if record.decision_state in selected_states),
            hard_blocked_count=sum(
                1 for record in group if record.decision_state == DecisionState.HARD_BLOCKED
            ),
            ce_net=round(sum(record.ce_expected for record in group), 6),
            expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
            realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
            gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
        )
        for engine_id, group in sorted(engine_groups.items())
    )
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_orchestrator.py`
- responsibility: Governed orchestration helpers for LOCAL_REPLAY exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_orchestrator_chunking.py`
- responsibility: Dataset chunking helpers for governed LOCAL_REPLAY exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_orchestrator_execution.py`
- responsibility: Execution pipeline for governed LOCAL_REPLAY orchestration.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: dataset, lineage_version, performance_mode, profile_scope, request, run_id, strategy_classification, strategy_id, strategy_version
- outputs: build_execution_input_from_dataset
- runtime_files_read: performance_mode_guard.json, replay_chunk_session.json, replay_session_config.json, replay_session_state.json, run_consistency_guard.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_orchestrator_io.py`
- responsibility: Sidecar IO helpers for governed LOCAL_REPLAY exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: replay_chunk_session.json, replay_run_manifest.json, replay_session_config.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_orchestrator_models.py`
- responsibility: Models for governed LOCAL_REPLAY orchestration.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: ReplayChunkSessionSummary
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = Field(..., min_length=1), strategy_version = Field(..., min_length=1)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_orchestrator_resume.py`
- responsibility: Resume helpers for governed LOCAL_REPLAY orchestration.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: feature_bridge.json, parity_diagnostics.json, performance_mode_guard.json, replay_chunk_session.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json, replay_session_config.json, replay_session_state.json, run_consistency_guard.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_run_manifest.py`
- responsibility: Typed run manifest for governed LOCAL_REPLAY artifact exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = Field(..., min_length=1), strategy_identity = None, strategy_version = Field(..., min_length=1)
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/replay_scope_identity.py`
- responsibility: Typed aggregate replay scope identity for governed multi-scope sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: chunk_count, datasets, input_kind, performance_mode, requested_window_end_ms, requested_window_start_ms, selected_chunk_indices
- outputs: build_replay_scope_identity
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/replay_session_config.py`
- responsibility: Typed session configuration for governed LOCAL_REPLAY runs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: chunk_count, chunk_index, input_kind, input_path, input_record_count, rewind_requested, run_manifest
- outputs: build_replay_session_config
- runtime_files_read: none
- formulas_or_derived_metrics: strategy_id = Field(..., min_length=1), strategy_identity = None, strategy_version = Field(..., min_length=1)
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/replay_state_store.py`
- responsibility: State persistence for governed LOCAL_REPLAY sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: none
- outputs: ReplaySessionState
- runtime_files_read: replay_session_state.json
- formulas_or_derived_metrics: strategy_id = "", strategy_identity = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/run_consistency_guard.py`
- responsibility: Consistency guard for governed LOCAL_REPLAY runs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: candidate_label, candidate_records, reference_label, reference_records, score_tolerance, size_tolerance
- outputs: RunConsistencyGuardReport
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/runtime_evidence.py`
- responsibility: Stateful runtime evidence recorder for governed LOCAL_REPLAY sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: none
- outputs: LocalReplayEvidenceRecorderState
- runtime_files_read: local_replay_runtime_evidence.json
- formulas_or_derived_metrics: generated_payload_refs = ()
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/local_replay_runtime/shadow_execution_simulator.py`
- responsibility: Prudent Shadow-compatible execution simulator for LOCAL_REPLAY.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: config, dataset, dtr_records
- outputs: ReplayParityDiagnosticsSummary, build_parity_diagnostics_payload
- runtime_files_read: none
- formulas_or_derived_metrics: decision_match_rate = Field(..., ge=0.0, le=1.0), score_match_rate = Field(default=0.0, ge=0.0, le=1.0), decision_match_rate = round_float64(decision_matches / decision_compared, 6)
        if decision_compared
        else 0.0, score_match_rate = round_float64(score_matches / score_compared, 6) if score_compared else 0.0
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/local_replay_runtime/walk_forward_review.py`
- responsibility: Governed human review gate for Local IA Lab walk-forward evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: coded_not_displayed
- inputs: correlation_id, export_dir, review, run_id
- outputs: WalkForwardReviewSummary, build_walk_forward_review_template
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: calibration_fit_window_confirmed = False
- control_flags_or_gates: gate
- duplication_notes: none

## manifest_registry

### `src/manifest_registry/__init__.py`
- responsibility: manifest_registry — Module 2: Registre unique des modules V5.3.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/manifest_registry/build_order_registry.py`
- responsibility: 4.5.4 — Build Order Registry: official implementation order.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: current, module_name, stage
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/manifest_registry/dependency_registry.py`
- responsibility: 4.5.2 — Dependency Registry: whitelist of allowed dependencies per module.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: module_name, source, target
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/manifest_registry/module_inventory.py`
- responsibility: 4.5.1 — Module Inventory: canonical table of all V5.3 modules.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: build_stage, layer, name, scope, status
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: MODULES = (
    # ── Build-1: Dependency Architecture ──
    ModuleEntry(
        module_name="interface_contracts",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Langage commun: types, contrats, erreurs",
    ),
    ModuleEntry(
        module_name="manifest_registry",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Registre unique des modules et dépendances",
    ),
    ModuleEntry(
        module_name="dag_validator",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Validateur de dépendances et cycles",
    ),
    ModuleEntry(
        module_name="contract_test_suite",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Tests de contrat par module",
    ),
    ModuleEntry(
        module_name="smoke_bootstrap_recovery",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Bootstrap et recovery propres",
    ),
    # ── Build-2: Data Backbone ──
    ModuleEntry(
        module_name="calibration_loader",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=1,
        description="Shared core: typed signed threshold artifacts and neutral loader",
    ),
    ModuleEntry(
        module_name="data_backbone",
        module_layer=ModuleLayer.DATA,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=2,
        description="Ingestion WS, normalisation, qualité data, santé paire",
    ),
    # ── Build-3: Execution Backbone ──
    ModuleEntry(
        module_name="regime_classifier",
        module_layer=ModuleLayer.DATA,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=2,
        description="Regime awareness lite: helper 3 etats avec hysteresis et cooldown",
    ),
    ModuleEntry(
        module_name="secrets_manager",
        module_layer=ModuleLayer.CONTRACTS,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=11,
        description="Bounded sealed-secrets helpers for runtime credential loading",
    ),
    ModuleEntry(
        module_name="alerting",
        module_layer=ModuleLayer.MONITORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=11,
        description="Bounded external alert delivery adapters over existing AlertRecord contracts",
    ),
    ModuleEntry(
        module_name="sharia_compliance",
        module_layer=ModuleLayer.EXECUTION,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=3,
        description="Bounded halal compliance/runtime guards reused by execution and venue adapters",
    ),
    ModuleEntry(
        module_name="execution_backbone",
        module_layer=ModuleLayer.EXECUTION,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=3,
        description="Exécution, coûts réels, réconciliation",
    ),
    # ── Build-4: Risk Backbone ──
    ModuleEntry(
        module_name="risk_backbone",
        module_layer=ModuleLayer.RISK,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=4,
        description="Budgets risque, exposition, corrélation, facteur BTC",
    ),
    # ── Build-5: Scoring Backbone ──
    ModuleEntry(
        module_name="scoring_backbone",
        module_layer=ModuleLayer.SCORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.COMMON,
        build_stage=5,
        description="Hard/soft/rank scoring pipeline",
    ),
    # ── Build-6: Engine A ──
    ModuleEntry(
        module_name="engine_a",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LEGACY,
        build_stage=6,
        description="Premium Trend / Expansion",
    ),
    # ── Build-7: Engine B ──
    ModuleEntry(
        module_name="engine_b",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LEGACY,
        build_stage=7,
        description="Mean Reversion Intraday",
    ),
    # ── Build-8: Portfolio Minimal ──
    ModuleEntry(
        module_name="portfolio",
        module_layer=ModuleLayer.PORTFOLIO,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LEGACY,
        build_stage=8,
        description="Sélection opportunités et allocation",
    ),
    # ── Build-9: Meta Minimal ──
    ModuleEntry(
        module_name="meta",
        module_layer=ModuleLayer.META,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LEGACY,
        build_stage=9,
        description="DTR, CRA, break-even, edge tracker",
    ),
    ModuleEntry(
        module_name="calibration_methods",
        module_layer=ModuleLayer.META,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=10,
        description="Shared Local IA Lab calibration and statistical method primitives",
    ),
    ModuleEntry(
        module_name="local_replay_runtime",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=10,
        description="Scaffold LOCAL_REPLAY unifie local/VPS, sans fork ni BACKTEST_PROFILE",
    ),
    ModuleEntry(
        module_name="backtest_artifact_import",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=10,
        description="Import artifact local->VPS gouverne, sans promotion implicite",
    ),
    ModuleEntry(
        module_name="meta_learning",
        module_layer=ModuleLayer.META,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.LEGACY,
        build_stage=10,
        description="Build-9X gouverne: diagnostics, hypotheses, candidats et exports de revue",
    ),
    # ── Build-10: Monitoring + locked operator UI (historical: Light UI) ──
    ModuleEntry(
        module_name="monitoring",
        module_layer=ModuleLayer.MONITORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LEGACY,
        build_stage=10,
        description="Métriques, alertes, dashboard backend pour la supervision opérateur verrouillée",
    ),
    ModuleEntry(
        module_name="ui",
        module_layer=ModuleLayer.UI,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.LEGACY,
        build_stage=10,
        description="UI opérateur verrouillée",
    ),
    # ── Build-11/12/13: Governed protocols rail (historical labels kept) ──
    ModuleEntry(
        module_name="venue_adapters",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.COMMON,
        build_stage=11,
        description="Concrete venue/exchange adapters reused by governed protocol bootstraps",
    ),
    ModuleEntry(
        module_name="protocols",
        module_layer=ModuleLayer.PROTOCOL,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P0,
        profile_scope=ProfileScope.LEGACY,
        build_stage=11,
        description="Build-11 Shadow, Build-12 Micro-live et Build-13 Live gouvernes sur le rail runtime actif complet; les labels historiques restent documentaires",
    ),
    # ── Build-14: Complete Enablers ──
    ModuleEntry(
        module_name="complete_enablers",
        module_layer=ModuleLayer.SCORING,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.GOVERNED,
        build_stage=14,
        description="Microstructure, régime, covariance enrichis",
    ),
    # ── Build-15: Engine C ──
    ModuleEntry(
        module_name="engine_c",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.GOVERNED,
        build_stage=15,
        description="Breakout Continuation",
    ),
    # ── Build-16: Engine D ──
    ModuleEntry(
        module_name="engine_d",
        module_layer=ModuleLayer.ENGINE,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.GOVERNED,
        build_stage=16,
        description="Re-entry / Second Chance",
    ),
    ModuleEntry(
        module_name="cockpit",
        module_layer=ModuleLayer.UI,
        owner=Owner.CLAUDE,
        status=ModuleStatus.ACTIVE,
        priority=Priority.P1,
        profile_scope=ProfileScope.GOVERNED,
        build_stage=17,
        description="Local operator shell for Shadow, VPS, IA Lab, backtest, observability, and logs",
    ),
)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/manifest_registry/profile_registry.py`
- responsibility: Runtime mapping of modules to the declared light / complete profiles.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: engine, module_name, pair, profile
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/manifest_registry/version_registry.py`
- responsibility: 4.5.5 — Version Registry: canonical versioning of manifest state.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: new, old, version
- outputs: ManifestSnapshot, ModuleSnapshot, build_current_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## meta

### `src/meta/__init__.py`
- responsibility: V5.3 - Canonical meta facade.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## meta_learning

### `src/meta_learning/__init__.py`
- responsibility: Build-9X governed meta-learning layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/breakdown_report_builder.py`
- responsibility: Aggregate governed diagnostics into a concise breakdown report.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: correlation_id, diagnostics, mistake_classes
- outputs: build_breakdown_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/capacity_guard.py`
- responsibility: Capacity and backpressure guardrails for the governed Build-9X layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: backlog_alert_threshold, backlog_protection_threshold, export_failures_total, log_loss_total, queue_depth, queue_oldest_age_ms, unprocessed_items_count, worker_cpu_pct, worker_rss_mb, write_latency_ms
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/checklist_generator.py`
- responsibility: Generate governed checklists from diagnostics and mistake classes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: correlation_id, diagnostics, mistake_classes
- outputs: build_learning_checklist
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/contracts.py`
- responsibility: Minimal governed contracts for the Build-9X meta-learning layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: BreakdownReport, LearningCapacitySnapshot, MetaLearningReviewBundle, ReplayExportBundle, TradeLossAttributionReport, TradeLossFailureModeSummary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, queue
- duplication_notes: none

### `src/meta_learning/enums.py`
- responsibility: Canonical enums for the governed Build-9X meta-learning layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: LearningBacklogState, LearningLifecycleState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/meta_learning/errors.py`
- responsibility: Errors for the governed Build-9X meta-learning layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/facade.py`
- responsibility: Canonical internal facade for the governed Build-9X layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/meta_learning/hypothesis_registry.py`
- responsibility: Build governed hypotheses from diagnostics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: correlation_id, diagnostics, source_version
- outputs: build_learning_hypotheses
- runtime_files_read: none
- formulas_or_derived_metrics: _RATIONALE_BY_CATEGORY = {
    "trace_coverage": "Low trace coverage suggests observability is too weak for governed promotion.",
    "sterilization": "Elevated CRA sterilization suggests economic viability is being destroyed downstream.",
    "cost_drift": "Break-even drift indicates the current cost model is no longer representative.",
    "edge_degraded": "Edge degradation suggests the previously credible edge is no longer stable.",
    "near_miss": "Near-miss records suggest valid edge may be blocked by current thresholds.",
    "no_issue": "No material issue detected; keep surveillance and collect more evidence.",
}, _TARGET_BY_CATEGORY = {
    "trace_coverage": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.dtr_core",
        "signal_family": "observability",
        "expected_replay_evidence": (
            "replay_dtr_coverage",
            "diagnostic_trace_density",
        ),
        "expected_shadow_evidence": (
            "shadow_dtr_coverage",
            "shadow_component_assessment",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "observability_export",
        ),
    },
    "sterilization": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.cra_monitor",
        "signal_family": "economics",
        "expected_replay_evidence": (
            "sterilization_rate_delta",
            "ce_net_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_sterilization_rate",
            "shadow_candidate_assessment",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "technical_supervision",
        ),
    },
    "cost_drift": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.break_even_dashboard",
        "signal_family": "execution_cost",
        "expected_replay_evidence": (
            "expected_vs_realized_cost",
            "break_even_drift_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_execution_cost_drift",
            "shadow_report_section",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "observability_export",
        ),
    },
    "edge_degraded": {
        "target_module": "meta_minimal",
        "target_component": "meta_minimal.edge_tracker_prudent_minimal",
        "signal_family": "edge_quality",
        "expected_replay_evidence": (
            "edge_net_delta",
            "sharpe_per_trade_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_edge_assessment",
            "shadow_component_assessment",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "technical_supervision",
        ),
    },
    "near_miss": {
        "target_module": "scoring_backbone",
        "target_component": "scoring_backbone.hard_block_gate",
        "signal_family": "selection_threshold",
        "expected_replay_evidence": (
            "near_miss_conversion_rate",
            "selection_acceptance_delta",
        ),
        "expected_shadow_evidence": (
            "shadow_comparison_divergence",
            "shadow_candidate_acceptance",
        ),
        "monitoring_hooks": (
            "build9x_diagnostics",
            "shadow_supervision",
        ),
    },
}
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/meta_learning/improvement_candidate_builder.py`
- responsibility: Build governed improvement candidates from hypotheses.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: correlation_id, hypotheses, strategy_classification
- outputs: build_improvement_candidates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/learning_memory_store.py`
- responsibility: Append-only in-memory storage for governed learning reviews.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/learning_review_exporter.py`
- responsibility: Export governed Build-9X review packets.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: archive_eligibility, candidates, capacity_snapshot, checklist, correlation_id, export_ref, hypotheses, lifecycle_transitions, merge_gate_report, replay_bundles, report, review_decisions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate, passed, queue
- duplication_notes: none

### `src/meta_learning/lifecycle_registry.py`
- responsibility: Canonical Build-9X lifecycle transition helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: actor, candidate, diagnostic, hypothesis, path, reason, target_stage, target_status
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/merge_gate_contracts.py`
- responsibility: Typed contracts for explicit Build-9X merge gates.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: Build9XMergeGateReport
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, passed
- duplication_notes: none

### `src/meta_learning/merge_gates.py`
- responsibility: Explicit merge-gate evaluators for the governed Build-9X layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: bundle, state_dir
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, passed
- duplication_notes: none

### `src/meta_learning/mistake_classifier.py`
- responsibility: Classify governed diagnostics into stable mistake classes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: diagnostics
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: _CATEGORY_TO_CLASS = {
    "trace_coverage": "observability_gap",
    "sterilization": "economic_sterilization",
    "cost_drift": "cost_model_drift",
    "edge_degraded": "edge_degradation",
    "near_miss": "near_miss",
    "no_issue": "no_material_issue",
}
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/model_risk_registry/__init__.py`
- responsibility: Typed minimal registry for ML model drift and pause/promotion-block decisions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/model_risk_registry/registry.py`
- responsibility: Minimal typed ML model risk registry for the bounded enabler layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: record
- outputs: MlModelDriftSnapshot, MlModelRiskState
- runtime_files_read: none
- formulas_or_derived_metrics: win_rate_delta = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/monitoring_projection.py`
- responsibility: Adapters from Build-9X governed bundles to monitoring projections.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: bundle
- outputs: build_build9x_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate, passed, queue
- duplication_notes: none

### `src/meta_learning/near_miss_analyzer.py`
- responsibility: Identify governed near misses from Build-9 DTR records.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: correlation_id, final_score_threshold, records
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/meta_learning/persistence_store.py`
- responsibility: Append-only persistence helpers for the governed Build-9X layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: candidate_records.jsonl, diagnostic_records.jsonl, export_bundle_records.jsonl, hypothesis_records.jsonl, learning_events.jsonl, learning_memory_records.jsonl, review_records.jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/post_trade_diagnostic_engine.py`
- responsibility: Build governed diagnostics from real Build-9 outputs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: break_even_report, cra_report, dtr_summary, edge_report, trade_input
- outputs: build_post_trade_diagnostics
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/replay_bundle_builder.py`
- responsibility: Build governed replay handoff bundles from Build-9X candidates.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: candidates, clock_ref, dataset_ref, hypotheses, replay_bundles, review_export_ref, trade_input
- outputs: build_replay_export_bundles
- runtime_files_read: none
- formulas_or_derived_metrics: metrics = ["ce_net", "dtr_coverage", "sterilization_rate", "edge_net"]
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/retention_policy.py`
- responsibility: Retention helpers for governed Build-9X records and transitions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: created_at, days, replay_open, review_open
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/review_governance.py`
- responsibility: Review-decision and archive-governance helpers for Build-9X.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: actor, candidates, correlation_id, decisions, diagnostics, final_verdict_recorded, has_candidates, hypotheses, rationale, review_blocked_due_to_incomplete_data, review_decisions, review_entity_id, review_state, verdict
- outputs: build_archive_eligibility, build_system_review_decisions
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/review_orchestrator.py`
- responsibility: Governed orchestration entrypoint for the real Build-9X layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: break_even_report, capacity_snapshot, clock_ref, cra_report, dataset_ref, dtr_records, dtr_summary, edge_report, near_miss_threshold, state_dir, trade_input
- outputs: _ReplayHandoffState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `src/meta_learning/review_queue.py`
- responsibility: Review-queue builder for Build-9X governed hypotheses.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: diagnostics, hypotheses
- outputs: build_review_queue
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/meta_learning/review_resolution.py`
- responsibility: Post-review and replay resolution helpers for governed Build-9X bundles.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: actor, bundle, failed_candidate_ids, passed_candidate_ids, rationale, resolution, state_dir
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed, passed
- duplication_notes: none

### `src/meta_learning/strategy_drift_monitor/__init__.py`
- responsibility: Bounded strategy-drift monitor for ML and replay-side governance.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/strategy_drift_monitor/monitor.py`
- responsibility: Minimal typed strategy drift monitor.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: snapshot, thresholds
- outputs: StrategyDriftSnapshot, StrategyDriftState
- runtime_files_read: none
- formulas_or_derived_metrics: win_rate_delta_floor = -0.10, win_rate_delta = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_learning/trade_loss_attribution.py`
- responsibility: Governed per-trade loss attribution for Local IA Lab post-trade review.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: break_even_report, correlation_id, cra_report, diagnostics, dtr_records, dtr_summary, edge_report
- outputs: build_trade_loss_attribution_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

## meta_minimal

### `src/meta_minimal/__init__.py`
- responsibility: Build-9 â€” Meta Minimal Pack: economic observability layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/break_even_dashboard/__init__.py`
- responsibility: Build-9 / break_even_dashboard â€” Real break-even visibility by engine/pair.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/break_even_dashboard/break_even_reporter.py`
- responsibility: Build-9 / break_even_dashboard / break_even_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: cost_distributions, drift_threshold, views
- outputs: BreakEvenReport, build_break_even_report
- runtime_files_read: none
- formulas_or_derived_metrics: global_profitable_rate = 0.0, global_profit_rate = total_profitable / total_n if total_n > 0 else 0.0
- thresholds_or_constants: _DRIFT_ALERT_THRESHOLD = 0.2
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/break_even_dashboard/cost_distribution_aggregator.py`
- responsibility: Build-9 / break_even_dashboard / cost_distribution_aggregator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: costs, scope
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: lo = int(math.floor(idx))
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/break_even_dashboard/expected_break_even_calculator.py`
- responsibility: Build-9 / break_even_dashboard / expected_break_even_calculator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: adverse_p90, engine_id, expected_adverse, expected_fee, expected_slippage, expected_spread, pair, slippage_p90, spread_p90
- outputs: compute_expected_break_even
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/break_even_dashboard/motor_pair_break_even_view.py`
- responsibility: Build-9 / break_even_dashboard / motor_pair_break_even_view
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: records, scope
- outputs: build_break_even_view, build_views_by_engine_and_pair
- runtime_files_read: none
- formulas_or_derived_metrics: profitable_rate = 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`
- responsibility: Build-9 / break_even_dashboard / realized_break_even_calculator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: engine_id, expected_cost, gross_return, pair, realized_cost
- outputs: compute_realized_break_even
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cost_drift_monitor/__init__.py`
- responsibility: Minimal cost drift monitor for expected vs realized execution cost bias.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cost_drift_monitor/monitor.py`
- responsibility: Minimal monitor for execution-cost bias drift.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: bias_alert_threshold = 0.2
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cra_monitor/__init__.py`
- responsibility: Build-9 / cra_monitor â€” Cumulative Reduction Alarm: detect economic sterilization.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cra_monitor/cra_alert_builder.py`
- responsibility: Build-9 / cra_monitor / cra_alert_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: critical_rate, results, warning_rate
- outputs: build_alerts
- runtime_files_read: none
- formulas_or_derived_metrics: _WARNING_RATE = 0.20, _CRITICAL_RATE = 0.40, rate = len(sterilized) / total if total > 0 else 0.0
- thresholds_or_constants: rate compare critical_rate, rate compare warning_rate
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cra_monitor/cra_reporter.py`
- responsibility: Build-9 / cra_monitor / cra_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: alerts, results
- outputs: CRAReport, build_cra_report
- runtime_files_read: none
- formulas_or_derived_metrics: sterilization_rate = 0.0, sterilization_rate_by_engine = Field(default_factory=dict), sterilization_rate_by_pair = Field(default_factory=dict), rate = steril_total / total if total > 0 else 0.0, rate_by_engine = {k: s / t if t > 0 else 0.0 for k, (t, s) in by_engine.items()}, rate_by_pair = {k: s / t if t > 0 else 0.0 for k, (t, s) in by_pair.items()}
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cra_monitor/phantom_risk_estimator.py`
- responsibility: Build-9 / cra_monitor / phantom_risk_estimator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: epsilon, operational_cost, trace
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cra_monitor/reduction_trace_reader.py`
- responsibility: Build-9 / cra_monitor / reduction_trace_reader
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: ce_expected, engine_id, expected_cost, final_size, holding_hours, original_size, pair, reduction_causes
- outputs: read_reduction
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/cra_monitor/sterilization_classifier.py`
- responsibility: Build-9 / cra_monitor / sterilization_classifier
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: reduction_threshold, risk, trace
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: _REDUCTION_THRESHOLD = 0.5
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/dtr_core/__init__.py`
- responsibility: Build-9 / dtr_core â€” Decision Trace Records for every significant decision.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/dtr_core/cause_chain_assembler.py`
- responsibility: Build-9 / dtr_core / cause_chain_assembler
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: allocation_step, blocker_steps, execution_step, penalty_steps, penalty_total, ranking_step, reduction_reason, score_step
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/meta_minimal/dtr_core/decision_state_encoder.py`
- responsibility: Build-9 / dtr_core / decision_state_encoder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: hard_blocked, is_phantom, ranking_rejected, selected, state, was_executed, was_reduced
- outputs: DecisionState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/dtr_core/dtr_record_builder.py`
- responsibility: Build-9 / dtr_core / dtr_record_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: candidate_size, cause_chain, ce_expected, decision_state, dtr_id, engine_id, expected_cost, final_score, final_size, gross_return, hard_block_reasons, hard_blocked, input_source, pair, path_complete, path_warnings, penalized_score, primary_reason, ranking_position, raw_score, realized_cost, regime, runtime_mode, tier, timestamp
- outputs: build_dtr
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/meta_minimal/dtr_core/dtr_reporter.py`
- responsibility: Build-9 / dtr_core / dtr_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: records, total_opportunities
- outputs: DTRSummary, build_dtr_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: dtr_coverage = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/dtr_core/trace_persistence_layer.py`
- responsibility: Build-9 / dtr_core / trace_persistence_layer
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: dtr_records.json
- formulas_or_derived_metrics: loss_rate = 0.0, loss_rate = self._dropped / self._attempted if self._attempted > 0 else 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/edge_tracker_prudent_minimal/__init__.py`
- responsibility: Build-9 / edge_tracker_prudent_minimal â€” Prudent net edge tracking.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/edge_tracker_prudent_minimal/edge_reporter.py`
- responsibility: Build-9 / edge_tracker_prudent_minimal / edge_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: classifications
- outputs: EdgeReport, build_edge_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/edge_tracker_prudent_minimal/edge_status_classifier.py`
- responsibility: Build-9 / edge_tracker_prudent_minimal / edge_status_classifier
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: ce_observed, mean_cost_p90, portfolio_context, sample, uncertainty
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: _COST_P90_DESTRUCTIVE_RATIO = 1.5
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/edge_tracker_prudent_minimal/return_aggregator.py`
- responsibility: Build-9 / edge_tracker_prudent_minimal / return_aggregator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: costs, gross_returns, scope
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/edge_tracker_prudent_minimal/sample_size_tracker.py`
- responsibility: Build-9 / edge_tracker_prudent_minimal / sample_size_tracker
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: comfortable, min_required, sample_size, scope
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/edge_tracker_prudent_minimal/uncertainty_estimator.py`
- responsibility: Build-9 / edge_tracker_prudent_minimal / uncertainty_estimator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: net_returns, scope
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/meta_runtime.py`
- responsibility: Build-9 / meta_runtime
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: records, total_opportunities
- outputs: build_meta_runtime_result_from_records
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/meta_minimal/refusal_journal/__init__.py`
- responsibility: Append-only refusal journal for governed runtime no-trade / no-fill evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/meta_minimal/refusal_journal/refusal_journal.py`
- responsibility: Append-only refusal journal with JSONL + manifest persistence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: refusal_manifest.json, refusal_records.jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## monitoring

### `src/monitoring/__init__.py`
- responsibility: Real Build-10 monitoring backend for the Light runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/alert_manager.py`
- responsibility: Alert projection for the real Build-10 monitoring backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: snapshot
- outputs: build_monitoring_alerts
- runtime_files_read: none
- formulas_or_derived_metrics: resolved_drop_rate_pct = _resolve_drop_rate_pct(snapshot)
- thresholds_or_constants: snapshot.portfolio.ce_net compare 0.0
- control_flags_or_gates: kill, queue
- duplication_notes: none

### `src/monitoring/artifact_visibility.py`
- responsibility: Bounded artifact visibility and comparison builders for Build-17 supervision.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: active_ml_artifact, active_regime_detector_artifact, execution_runtime_projection_path, ml_comparison_ref, regime_detector_comparison_ref, shadow_ml_challenger_artifact, shadow_regime_detector_challenger_artifact, verdict_bundle_ref, verdict_bundle_status
- outputs: build_artifact_comparison_projections, build_artifact_runtime_visibility_projections, build_artifact_threshold_consumer_projections, build_artifact_verdict_bundle_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/monitoring/build14_observation.py`
- responsibility: Shared Build-14 observation derivation from governed monitoring surfaces.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: payload, snapshot
- outputs: derive_build14_observation_from_payload, derive_build14_observation_from_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: ce_pressure = 1.0 if ce_net < 0.0 else 0.5 if ce_net < 0.001 else 0.0
- thresholds_or_constants: ce_net compare 0.0, ce_net compare 0.001
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/challenger_evidence_alerts.py`
- responsibility: Bounded challenger-evidence alert derivation shared by monitoring surfaces.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: artifact_comparisons, artifact_runtime_visibility, artifact_verdict_bundle, base_alerts, extra_alerts, shadow_last_completed_session_date, snapshot
- outputs: ShadowChallengerAlertState, build_shadow_challenger_alert_state, build_shadow_challenger_alerts
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/monitoring/contracts.py`
- responsibility: Contracts for the real Build-10 monitoring backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/contracts_artifacts.py`
- responsibility: Bounded artifact visibility contracts shared by Build-10 and Build-17 surfaces.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: ArtifactComparisonProjection, ArtifactRuntimeVisibilityProjection, ArtifactShadowVerdictBundle, ArtifactThresholdConsumerProjection, ArtifactVerdictBundleProjection
- runtime_files_read: none
- formulas_or_derived_metrics: decision_diff_rate = Field(default=0.0, ge=0.0, le=1.0)
- thresholds_or_constants: threshold_fit_ready = False
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/monitoring/contracts_core.py`
- responsibility: Core monitoring contracts for the real Build-10 backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: Build9MetaProjection, Build9XProjection, FleetNodeProjection, FleetOverviewProjection, MonitoringSnapshot, OperatorRuntimeProjection, SystemProjection
- runtime_files_read: none
- formulas_or_derived_metrics: ce_net = 0.0, drop_rate_pct = Field(default=0.0, ge=0.0, le=100.0), cra_sterilization_rate = Field(..., ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: queue, runtime_mode
- duplication_notes: none

### `src/monitoring/contracts_dashboard.py`
- responsibility: Dashboard and projection contracts for the real Build-10 backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: AccountUserDataProjection, AlertProjection, Build14Projection, Build14ReaderProjection, EngineJudgmentProjection, ExecutionNoTradeBridgeProjection, ExecutionRuntimeProjectionBridgeProjection, LiveLightGateGroupProjection, LiveLightProjection, LocalLabMonitoringIngestionSummary, MicroLiveProjection, RegimeLiteSafingProjection, ReplayImportProjection, RuntimeHookBridgeProjection, ShadowProjection
- runtime_files_read: none
- formulas_or_derived_metrics: economic_pass_rate = Field(default=0.0, ge=0.0, le=1.0), conflict_rate = Field(default=0.0, ge=0.0, le=1.0), execution_runtime_projection_rate_limit_model_loaded = False, rate_limit_model_loaded = False, drop_rate_pct = Field(default=0.0, ge=0.0, le=100.0)
- thresholds_or_constants: feature_lineage_required = False, feature_lineage_present = False, execution_runtime_projection_rate_limit_model_loaded = False, execution_runtime_projection_slippage_model_loaded = False, rate_limit_model_loaded = False, slippage_model_loaded = False, edge_calibration_ready = False, calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False, calibration_normalized_report_ready = False
- control_flags_or_gates: blocked, gate, passed, review_only, runtime_mode
- duplication_notes: none

### `src/monitoring/contracts_dashboard_payloads.py`
- responsibility: Payload contracts split from contracts_dashboard to keep modules bounded.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/contracts_live_complete.py`
- responsibility: Build-17 Complete monitoring projection contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: LiveCompleteGateGroupProjection, LiveCompleteProjection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate, passed, review_only
- duplication_notes: none

### `src/monitoring/contracts_vps.py`
- responsibility: Observability and VPS monitoring contracts for the real Build-10 backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: ShadowVpsServiceLogEventProjection
- runtime_files_read: none
- formulas_or_derived_metrics: execution_runtime_projection_rate_limit_model_loaded = False
- thresholds_or_constants: execution_runtime_bootstrap_remote_state_snapshot_captured = False, execution_runtime_projection_rate_limit_model_loaded = False, execution_runtime_projection_slippage_model_loaded = False
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/dashboard_metric_guides.py`
- responsibility: Canonical Grafana metric guide text for local operator dashboards.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: _LOCAL_LAB_SECTIONS = (
    MetricGuideSection(
        title="Live-Light gate groups",
        entries=(
            MetricGuideEntry(
                metric_name="v53_live_light_gate_group_status",
                explanation=(
                    "Compact state code per gate family. `0=passed`, "
                    "`1=review_only`, `2=blocked`."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_live_light_gate_group_reason_count",
                explanation=(
                    "Number of reasons attached to the same gate family. `0` is "
                    "the normal nominal case for a passed group."
                ),
            ),
        ),
        notes=(
            "`review_only` means the group did not hard-block the run, but still requires operator attention or a governed review path.",
            "`blocked` means the gate family is fail-closed in the current summary.",
        ),
    ),
    MetricGuideSection(
        title="Build-14 bounded influence",
        entries=(
            MetricGuideEntry(
                metric_name="v53_build14_action",
                explanation=(
                    "State metric carried by the `action` label. Current governed "
                    "actions are `observe`, `downgrade_confidence`, "
                    "`review_only`, and `soft_veto`."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_build14_recommended_budget_factor",
                explanation=(
                    "Ratio in `[0, 1]`. `1.0` means nominal budget, values like "
                    "`0.85` or `0.75` mean bounded reduction, and `0.0` means "
                    "review-only or veto posture."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_build14_confidence_penalty_weight",
                explanation=(
                    "Governed penalty weight. `0.0` is nominal, `0.10-0.15` is "
                    "bounded downgrade, `0.25` is critical."
                ),
            ),
            MetricGuideEntry(
                metric_name="v53_build14_requires_manual_review",
                explanation=(
                    "`1` means manual review remains mandatory before "
                    "live-light progression."
                ),
            ),
        ),
        notes=(
            "Do not infer promotion readiness from one metric alone; read the gate-group state together with the final live-light verdict.",
        ),
    ),
)
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, eligible_to_trade, gate, halt, passed, review_only
- duplication_notes: none

### `src/monitoring/disk_monitor.py`
- responsibility: Bounded disk usage sampling for VPS observability.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: path
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/grafana_operator_bridge_markdown.py`
- responsibility: Canonical operator bridge markdown for Grafana-to-queue control.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: halt, queue, suspended
- duplication_notes: none

### `src/monitoring/grafana_types.py`
- responsibility: Typed JSON aliases for Grafana payload builders.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/health_dashboard_backend.py`
- responsibility: Stable backend payload for the locked Build-10 operator UI.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: alert_history, live_light_status, micro_live_status, operator_runtime, shadow_status, snapshot
- outputs: build_health_dashboard_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/hybrid_router_metrics.py`
- responsibility: Monitoring re-export surface for Build-3 hybrid routing metrics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/hybrid_router_trace.py`
- responsibility: Monitoring-facing routing trace contracts for Build-3 hybrid routing.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/local_grafana_api.py`
- responsibility: Local Grafana HTTP API helpers for datasource and dashboard bootstrap.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: dashboard_payload, dashboard_payload_path, datasource_name, datasource_uid, grafana_url, name, output_path, password, path, prometheus_url, uid, url, username
- outputs: LocalGrafanaBootstrapSummary, build_prometheus_datasource_payload, load_dashboard_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/local_grafana_dashboard.py`
- responsibility: Build a detailed local Grafana dashboard over the current V5.3 Shadow VPS metrics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: datasource_name, datasource_uid, output_path, prom_text, source_prom_path, title, uid
- outputs: LocalGrafanaDashboardSummary, build_local_shadow_vps_grafana_dashboard, build_local_shadow_vps_grafana_dashboard_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate, passed
- duplication_notes: none

### `src/monitoring/local_grafana_dashboard_build17.py`
- responsibility: Build-17 Grafana panel helpers for the local Shadow VPS dashboard.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: instance_filter, job_filter
- outputs: build_shadow_vps_recovery_and_control_panels
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/monitoring/local_lab_bundle_discovery.py`
- responsibility: Discovery helpers for Local IA Lab monitoring bundles.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: root_dir
- outputs: load_latest_local_lab_monitoring_bundle
- runtime_files_read: local_lab_monitoring_bundle_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_bundle_loader.py`
- responsibility: File-based loader for Local IA Lab monitoring bundles.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: bundle_dir
- outputs: LocalLabMonitoringBundle, load_local_lab_monitoring_bundle
- runtime_files_read: local_lab_monitoring_bundle_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_grafana_dashboard.py`
- responsibility: Build a detailed local Grafana dashboard over the current V5.3 Local IA Lab metrics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: datasource_name, datasource_uid, observability_export_path, output_path, prom_text_path, title, uid
- outputs: LocalLabGrafanaDashboardSummary, build_local_lab_grafana_dashboard, build_local_lab_grafana_dashboard_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/monitoring/local_lab_ingestion.py`
- responsibility: Monitoring-side ingestion helpers for Local IA Lab backend payloads.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: backend_payload, backend_payload_ref, monitoring_bundle_manifest_ref, observability_export, observability_export_ref
- outputs: build_local_lab_monitoring_ingestion_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_monitoring_backend.py`
- responsibility: Typed backend payload adapter for Local IA Lab monitoring surfaces.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: observability_export, observability_export_ref, projection
- outputs: build_local_lab_monitoring_backend_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_monitoring_bundle_manifest.py`
- responsibility: Manifest over Local IA Lab monitoring sidecars.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: backend_payload, backend_payload_path, ingestion_summary, ingestion_summary_path, observability_export, observability_export_path, replay_workflow_manifest_path, replay_workflow_manifest_status
- outputs: build_local_lab_monitoring_bundle_manifest
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_monitoring_feed.py`
- responsibility: Compact monitoring feed over discovered Local IA Lab bundles.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: discovery, root_dir
- outputs: build_local_lab_monitoring_feed, build_local_lab_monitoring_feed_from_root
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False
- control_flags_or_gates: blocked, runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_monitoring_projection.py`
- responsibility: Compact future-dashboard projection for Local IA Lab packaging and dry-run handoff.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: activation_stage, artifact_ablation_ready, artifact_id, artifact_import_dry_run_bridge_path, artifact_promotion_readiness_summary_path, artifact_proof_ready, artifact_proof_validation_reasons, artifact_release_candidate_path, bridge_blocking_reasons, bridge_status, calibration_methods_dsr_pass, calibration_methods_review_ready, calibration_methods_review_status, calibration_methods_stationarity_pass, calibration_methods_stationarity_status, calibration_methods_walk_forward_plan_ready, calibration_normalized_report_ready, calibration_normalized_report_status, calibration_normalized_threshold_count, correlation_id, dataset_manifest_id, edge_calibration_ready, execution_blocked_threshold_count, execution_partial_threshold_count, execution_ready_threshold_count, execution_review_ready, execution_review_status, export_dir, local_lab_calibration_methods_review_path, local_lab_calibration_normalized_report_path, local_lab_execution_review_path, local_lab_execution_runtime_projection_path, local_lab_loss_surrogate_path, local_lab_monitoring_bundle_manifest_path, local_lab_multiple_testing_review_path, local_lab_replay_candidate_queue_path, local_lab_replay_dispatch_plan_path, local_lab_replay_ticket_index_path, local_lab_replay_workflow_manifest_path, local_lab_research_priority_path, local_lab_tail_risk_review_path, loss_surrogate_ready, loss_surrogate_scope_count, loss_surrogate_status, loss_surrogate_top_probability, loss_surrogate_top_scope_slug, multiple_testing_correction, multiple_testing_correction_required, multiple_testing_family_count, multiple_testing_review_ready, multiple_testing_review_status, normalized_promotion_state, promotion_readiness_status, ready_for_shadow_import_dry_run, recalibration_blocking_reasons, release_blocking_reasons, release_gate_reasons, release_gate_status, release_ready_for_shadow, release_scope_blocked_count, release_scope_ready_count, release_status, replay_candidate_count, replay_candidate_queue_status, replay_candidate_ready_count, replay_candidate_top_scope_slug, replay_dispatch_blocked_count, replay_dispatch_plan_status, replay_dispatch_ready_count, replay_dispatch_top_ticket_id, replay_ticket_count, replay_ticket_index_status, replay_ticket_ready_count, replay_ticket_top_scope_slug, research_priority_scope_count, research_priority_status, research_priority_top_scope_slug, research_priority_top_score, review_ready, review_state, run_id, scope_blocked_count, scope_count, scope_matrix_path, scope_ready_count, selected_engine_id, selected_pair, semantic_status, tail_risk_blocked_breaker_count, tail_risk_partial_breaker_count, tail_risk_ready_breaker_count, tail_risk_review_ready, tail_risk_review_status, trade_loss_attribution_ready, walk_forward_review_ready
- outputs: LocalLabMonitoringProjection, build_local_lab_monitoring_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: edge_calibration_ready = False, calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False, calibration_normalized_report_ready = False
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_lab_observability.py`
- responsibility: Structured observability export for Local IA Lab packaging runs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: profile, projection, runtime_mode, timestamp_ms
- outputs: build_local_lab_observability_export
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/local_observability_stack.py`
- responsibility: One-shot local launcher for the Shadow VPS Prometheus/Grafana observability stack.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: bridge_host, bridge_port, evaluation_interval, grafana_home, grafana_password, grafana_server_exe, grafana_url, grafana_user, metrics_target, output_dir, prom_text_path, prometheus_exe, prometheus_url, readiness_timeout_s, scrape_interval
- outputs: LocalObservabilityStackSummary, build_local_bridge_prometheus_config_text
- runtime_files_read: grafana.log, local_grafana_bootstrap.summary.json, local_observability_stack.summary.json, local_prometheus_metrics_bridge.log, prometheus.bridge.generated.yml, prometheus.log, v53_shadow_vps_local_grafana.dashboard.json, v53_shadow_vps_local_grafana.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: DEFAULT_READINESS_TIMEOUT_S = 90.0, _HTTP_READY_ATTEMPT_TIMEOUT_S = 3.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/local_prometheus_config.py`
- responsibility: Generate a checked local-PC Prometheus config over V5.3 scrape handoff artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: evaluation_interval, file_sd_refresh_interval, local_lab_target, local_node_exporter_target, local_windows_exporter_target, output_path, scrape_interval, vps_file_sd_path
- outputs: LocalPrometheusConfigSummary, build_local_prometheus_config_summary, build_local_prometheus_config_text
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/local_prometheus_metrics_bridge.py`
- responsibility: Dev-only local HTTP bridge that serves a Prometheus text payload over /metrics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: listen_host, listen_port, metrics_path, observability_export_path, output_path, ready_path, source_prom_path
- outputs: LocalPrometheusMetricsBridgeSummary, build_local_prometheus_metrics_bridge_server, build_local_prometheus_metrics_bridge_summary, load_local_prometheus_text_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/log_rotation.py`
- responsibility: Bounded gzip log rotation with retention for operated monitoring rails.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: log_path, max_bytes, now, retention_days
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/logging_config.py`
- responsibility: Shared rotating file handler builder for monitoring and VPS rails.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: backup_count, max_bytes, path
- outputs: build_rotating_file_handler, build_rotating_jsonl_handler
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/metrics_collector.py`
- responsibility: Metrics aggregation for the real Build-10 monitoring backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: absorption_score, allocated_opportunities, average_cost_bps, backlog_depth, backlog_high_water_mark, beta_utilization, blocked_guard_count, breaches, break_even_report, capital_deployed_usdt, ce_expected, ce_net, competition_support, correlation_id, cost_p90_bps, cpu_pct, cra_report, delta_confirmation, dominant_cluster, drawdown_pct, drawdown_state_code, drop_rate_pct, dtr_loss_count, dtr_summary, edge_report, elw_bps, emitted_signals, engine_id, engines, execution_fragility, execution_survivability_score, expected_cost_bps, false_breakout_score, fill_latency_ms_p95, fragility_score, freshness_ms, future_learning_diagnostics, future_learning_hypotheses, gross_capacity_used_pct, hard_blocked, health, infra, is_active, kill_switch_active, kill_switch_timestamp_ms, log_loss_count, loss_capacity_used_pct, market_toxicity, meta, micro_friction_score, net_edge_bps, pair, pairs, partial_fill_count, persisted_metric_names, phantom_reason_code, phantom_trade, physics_pressure_state, pnl_net_usdt, poc_reversion_score, portfolio, portfolio_to_submit_ms_p90, portfolio_verdict_code, profile, queue_backlog, ram_pct, realized_cost_bps, reconciliation_alert_count, reconnect_count, recovery_retry_count, risk_decision_severity, risk_reason_codes, risk_summary, risk_to_portfolio_ms_p90, runtime_mode, scoring_final_size_multiplier, scoring_penalized_score, scoring_ranking_score, scoring_reason_codes, scoring_summary, scoring_to_risk_ms_p90, selection_outcome_code, sharpe_per_trade, signal_to_scoring_ms_p90, signal_to_submit_ms_p90, spread_regime_penalty, stale, stale_pairs, stale_spike_count, suspension_reason, sweep_score, timestamp_ms, total_dropped, total_enqueued, toxicity_score, useful_frequency, volatile_metric_names
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: resolved_drop_rate_pct = drop_rate_pct
        if drop_rate_pct is not None
        else (total_dropped / total_enqueued * 100.0 if total_enqueued > 0 else 0.0)
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode, suspended
- duplication_notes: none

### `src/monitoring/monitoring_runtime.py`
- responsibility: Build-10 runtime orchestration across snapshot, alerting, dashboard, and UI.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: none
- outputs: MonitoringRuntimeState
- runtime_files_read: monitoring_runtime_state.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode, suspended
- duplication_notes: none

### `src/monitoring/observability.py`
- responsibility: Minimal structured observability export for Build-10 supervision.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: payload
- outputs: build_observability_export
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/observability_io.py`
- responsibility: I/O helpers for persisted observability exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: collector_dir, export, filename, path
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/observability_support.py`
- responsibility: Support helpers for Build-10 structured observability export.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: payload
- outputs: build_observability_export_support
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, review_only, runtime_mode
- duplication_notes: none

### `src/monitoring/process_metrics.py`
- responsibility: Lightweight real process metrics sampling for VPS observability.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: cpu_pct = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/regime_detector_shadow_audit_bundle.py`
- responsibility: Deterministic VPS shadow audit aggregation for RegimeDetectorML.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: artifact_status, feature_profile, feature_set_version, observation_coverage_ratio, samples, shadow_metrics, signal_payload
- outputs: build_regime_detector_shadow_audit_bundle, build_regime_detector_shadow_audit_sample
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/regime_detector_shadow_projection.py`
- responsibility: Shadow monitoring projection for artifact-only LOB RegimeDetectorML signals.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: artifact_status, correlation_id, signal_payload
- outputs: RegimeDetectorShadowProjection, build_regime_detector_shadow_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: shadow_only
- duplication_notes: none

### `src/monitoring/shadow_vps_redaction.py`
- responsibility: Local redaction helpers for Shadow VPS monitoring and event projection.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: event, text
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/shadow_vps_scrape_discovery.py`
- responsibility: Discovery helpers for local-PC Prometheus scrape handoff from Shadow VPS manifests.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: root_dir
- outputs: build_shadow_vps_prometheus_file_sd_from_root
- runtime_files_read: shadow_vps_service_scrape_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/shadow_vps_service_log_retrieval.py`
- responsibility: Bounded retrieval helpers over durable Shadow VPS service JSONL events.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: events_path, max_events, query, timestamp_ms
- outputs: build_shadow_vps_service_recent_events_summary
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/shadow_vps_service_monitoring.py`
- responsibility: Typed monitoring projection for the real Shadow VPS service loop.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: campaign_summary, disk, events_path, latest_error, latest_event_type, node_exporter_textfile_ref, parse_error_count, payload, process, prometheus_file_sd_ref, recent_events_summary_ref, runtime_evidence_bundle, scrape_manifest_ref, state, state_path, timestamp_ms
- outputs: build_shadow_vps_service_monitoring_payload, build_shadow_vps_service_observability_export
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/shadow_vps_service_monitoring_observability_support.py`
- responsibility: Support helpers for Shadow VPS service observability export construction.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: payload
- outputs: build_shadow_vps_service_observability_export_support
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: eligible_to_trade, runtime_mode
- duplication_notes: none

### `src/monitoring/shadow_vps_service_monitoring_payload_field_support.py`
- responsibility: Support field resolvers for Shadow VPS service monitoring payload construction.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: campaign_summary, runtime_evidence_bundle, state
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/monitoring/shadow_vps_service_monitoring_payload_support.py`
- responsibility: Support helpers for Shadow VPS service monitoring payload construction.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: campaign_summary, disk, events_path, latest_error, latest_event_type, node_exporter_textfile_ref, parse_error_count, process, prometheus_file_sd_ref, recent_events_summary_ref, runtime_evidence_bundle, scrape_manifest_ref, state, state_path, timestamp_ms
- outputs: build_shadow_vps_service_monitoring_payload_support
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: heartbeat_age_ms = 0
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/shadow_vps_service_scrape_manifest.py`
- responsibility: Typed scrape handoff artifacts for local Prometheus over Shadow VPS observability.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: labels, manifest, monitoring_backend_payload_ref, node_exporter_metrics_path, node_exporter_port, node_exporter_scheme, observability_export_ref, payload, prometheus_job_name, scrape_host, vps_id
- outputs: build_shadow_vps_service_prometheus_file_sd, build_shadow_vps_service_scrape_manifest
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/technical_dashboard_backend.py`
- responsibility: Normalized Build-10 technical dashboard payload builder.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: account_user_data_projection, active_engines, active_modules, artifact_comparisons, artifact_runtime_visibility, artifact_threshold_consumers, artifact_verdict_bundle, build14_projection, build9x_projection, engine_judgment_projection, execution_no_trade_bridge_projection, execution_runtime_projection_bridge_projection, hybrid_router_projection, live_light_projection, live_projection, micro_live_projection, operator_runtime, replay_projection, runtime_hook_bridge_projections, shadow_last_completed_session_date, shadow_projection, snapshot
- outputs: _ResolvedBridgeState, _ResolvedDashboardState, _ResolvedProjectionState, build_technical_dashboard_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/monitoring/technical_dashboard_backend_support.py`
- responsibility: Support helpers for the Build-10 technical dashboard backend.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: coded_not_displayed
- inputs: account_user_data, active_modules, build14, build9x, engine_judgment, execution_no_trade_bridge, execution_runtime_projection_bridge, headline_status, hook_id, live_light, micro_live, operator_runtime, projection, replay_import, runtime_hook_bridge_projections, runtime_hook_bridges, shadow
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

## portfolio

### `src/portfolio/__init__.py`
- responsibility: V5.3 - Canonical portfolio facade.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## portfolio_minimal

### `src/portfolio_minimal/__init__.py`
- responsibility: Build-8 / portfolio_minimal — Portfolio Minimal Pack.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/__init__.py`
- responsibility: Build-8 / allocation_router â€” Allocate capital to selected opportunities.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/allocation_reporter.py`
- responsibility: Build-8 / allocation_router / allocation_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: capital_remaining, entries, remaining_beta_capacity, remaining_cluster_capacity, remaining_loss_capacity
- outputs: AllocationReport, build_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: capital_remaining = 0.0, remaining_loss_capacity = 0.0, remaining_beta_capacity = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/base_size_builder.py`
- responsibility: Build-8 / allocation_router / base_size_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: pair, profile
- outputs: compute_base_size
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/phantom_trade_guard.py`
- responsibility: Build-8 / allocation_router / phantom_trade_guard
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate_size, ev_net, expected_cost, final_size, min_viable_size, pair
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/portfolio_cap_applier.py`
- responsibility: Build-8 / allocation_router / portfolio_cap_applier
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: beta_impact_at_candidate_size, candidate_size, estimated_loss_at_candidate_size, modulated_size, pair, position_cap, remaining_beta_capacity, remaining_cluster_capacity, remaining_gross_capacity, remaining_loss_capacity
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: was_capped = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/score_size_mapper.py`
- responsibility: Build-8 / allocation_router / score_size_mapper
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: base_size, pair, ranking_score, tier_suggestion
- outputs: compute_modulated_size
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: _HIGH_SCORE_THRESHOLD = 0.7
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/allocation_router/vol_target_sizer.py`
- responsibility: Build-8 / allocation_router / vol_target_sizer
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate, profile
- outputs: compute_vol_target_size
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/arbitration_record.py`
- responsibility: Build-8 / arbitration_record
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate, final_size, initial_snapshot, peers, rank, ranking_score, reason_codes, snapshot, verdict
- outputs: PortfolioArbitrationSnapshot, build_arbitration_record, build_arbitration_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: size_ratio = 0.0
- control_flags_or_gates: passed
- duplication_notes: none

### `src/portfolio_minimal/opportunity_selector/__init__.py`
- responsibility: Build-8 / opportunity_selector â€” Select which opportunities deserve capital.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/opportunity_selector/candidate_pool_builder.py`
- responsibility: Build-8 / opportunity_selector / candidate_pool_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidates, freshness_policy, max_signal_age_s, now_ts
- outputs: build_candidate_pool, build_enforced_candidate_pool_freshness
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/portfolio_minimal/opportunity_selector/comparative_ranker.py`
- responsibility: Build-8 / opportunity_selector / comparative_ranker
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate, candidates, cluster_utilization, cluster_utilizations
- outputs: compute_ranking_score
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/opportunity_selector/correlation_conflict_checker.py`
- responsibility: Build-8 / opportunity_selector / correlation_conflict_checker
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidates, cluster_crowding_threshold, cluster_utilizations, contradiction_window_s
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: _CLUSTER_CROWDING_THRESHOLD = 3
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/opportunity_selector/eligibility_filter.py`
- responsibility: Build-8 / opportunity_selector / eligibility_filter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate, snapshot
- outputs: PortfolioSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: remaining_gross_capacity = 0.0, remaining_loss_capacity = 0.0, remaining_beta_capacity = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/opportunity_selector/selection_resolver.py`
- responsibility: Build-8 / opportunity_selector / selection_resolver
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: initial_snapshot, ranked
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/portfolio_minimal/portfolio_orchestrator.py`
- responsibility: Build-8 / portfolio_orchestrator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidates, config, relative_rank_hook
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: position_cap = 500.0, cluster_crowding_threshold = 3
- control_flags_or_gates: none
- duplication_notes: none

## protocols

### `src/protocols/__init__.py`
- responsibility: Minimal real Build-11/12/13 protocol runtime surface.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/artifact_action_composer.py`
- responsibility: Canonical runtime composition for multiple artifact actions on the same hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: actions, conflict_policy, hook_id
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/closed_episode_journal.py`
- responsibility: Append-only closed A/C episode journal for Engine D historical linkage and replay evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: closed_episode_manifest.json, closed_episodes.jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/compiled_artifact_registry_store.py`
- responsibility: Atomic snapshot store for governed compiled artifact registry publication.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: CompiledArtifactRegistrySnapshot
- runtime_files_read: compiled_artifact_registry_pointer.json, {snapshot_id}.json
- formulas_or_derived_metrics: generated_at_ms = Field(..., ge=0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/compiled_hook_plan_loader.py`
- responsibility: Bounded selection/loading semantics for compiled hook plans.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_id, path, store
- outputs: load_compiled_hook_plan
- runtime_files_read: none
- formulas_or_derived_metrics: generated_at_ms = Field(..., ge=0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/contracts.py`
- responsibility: Governed contracts for the minimal real Build-11/12/13 runtimes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/contracts_complete.py`
- responsibility: Governed Build-17 Complete control-surface contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: live_light_summary
- outputs: LiveCompleteGateGroupSummary, LiveCompleteRunSummary, build_live_complete_input_defaults
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, passed, passed, review_only, runtime_mode
- duplication_notes: none

### `src/protocols/contracts_promotion.py`
- responsibility: Governed Micro-live and Live-Light contracts for Build-12/13.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: LiveLightGateGroupSummary, LiveLightRunSummary, MicroLiveRunSummary
- runtime_files_read: exports/feature_bridge.json, exports/parity.json, exports/replay_dtr.json, exports/replay_metrics.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: import_feature_lineage_required = False, import_feature_lineage_present = False
- control_flags_or_gates: blocked, blocked, gate, passed, passed, review_only, runtime_mode
- duplication_notes: none

### `src/protocols/contracts_shadow.py`
- responsibility: Governed Shadow contracts for the minimal real Build-11 runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: ShadowEngineReport, ShadowRunSummary
- runtime_files_read: exports/feature_bridge.json, exports/parity.json, exports/replay_dtr.json, exports/replay_metrics.json
- formulas_or_derived_metrics: cra_sterilization_rate = Field(..., ge=0.0, le=1.0), ce_net = 0.0, threshold = Field(..., ge=0.0), economic_pass_rate = Field(..., ge=0.0, le=1.0), conflict_rate = Field(..., ge=0.0, le=1.0), ce_net = None, stale_rate = Field(default=None, ge=0.0), economic_pass_rate = Field(default=None, ge=0.0, le=1.0), dtr_loss_rate = Field(default=None, ge=0.0, le=1.0), log_loss_rate = Field(default=None, ge=0.0, le=1.0), hard_block_rate = Field(default=None, ge=0.0, le=1.0)
- thresholds_or_constants: import_feature_lineage_required = False, import_feature_lineage_present = False
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/protocols/contracts_shared.py`
- responsibility: Shared governed protocol contracts for Shadow, Micro-live, and Live-Light.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: DailyPnlBreakerGovernanceSummary, InfoStressGovernanceSummary, RegimeLiteGovernanceSummary, ShadowEngineJudgmentSummary
- runtime_files_read: none
- formulas_or_derived_metrics: economic_pass_rate = Field(default=0.0, ge=0.0, le=1.0), conflict_rate = Field(default=0.0, ge=0.0, le=1.0), hard_block_rate = Field(default=None, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/contracts_validation_support.py`
- responsibility: Validation helpers for governed protocol contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: accepted_import_review_states, accepted_import_statuses, accepted_onboarding_review_states, expected_import_conflict_hard_veto_action, expected_import_conflict_rank_adjust_mode, expected_import_conflict_resolution_mode, expected_import_conflict_score_aggregation_mode, expected_import_conflict_size_reduce_mode, expected_import_registry_atomicity_mode, expected_import_registry_concurrency_model, expected_import_source_profile, live_light_allowed_engines, micro_live_allowed_engines, rejected_import_compatibility_statuses, rejected_import_signature_statuses, value
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode, shadow_only
- duplication_notes: none

### `src/protocols/dashboard_command_execution_support.py`
- responsibility: Execution and state helpers for the governed dashboard command queue.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: context, request, timestamp_ms
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `src/protocols/dashboard_command_queue.py`
- responsibility: Typed file-queue command plane for Build-17 governed dashboard actions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: ack, context, queue_root, request, result
- outputs: build_dashboard_command_queue_snapshot, load_dashboard_command_acks, load_dashboard_command_requests, load_dashboard_command_results
- runtime_files_read: *.json, exports/binance_credential_inventory.json, {ack.timestamp_ms}_{ack.request_id}.ack.json, {request.timestamp_ms}_{request.request_id}.request.json, {result.timestamp_ms}_{result.request_id}.result.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `src/protocols/dashboard_command_result_support.py`
- responsibility: Result builders for the governed dashboard command queue.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: active_profile_id, artifact_hash, artifact_id, artifact_manifest, comparison_ref, credential_inventory, export_ref, inventory, manifest, missing_detail, missing_failure_stage, missing_reason_code, profile_change_allowed, profile_id, request, result_id, secret_manifest, shadow_audit_bundle_ref, timestamp_ms
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `src/protocols/engine_a_hooks.py`
- responsibility: Bounded executor surface for the canonical ENGINE_A_PRE_ENTRY_CONFIRMATION hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_engine_a_pre_entry_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/engine_a_pre_entry_confirmation_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to Engine A pre-entry confirmation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/engine_b_hooks.py`
- responsibility: Bounded executor surface for the canonical ENGINE_B_SWEEP_VALIDATION hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_engine_b_sweep_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/engine_b_sweep_validation_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to Engine B sweep validation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/engine_c_hooks.py`
- responsibility: Bounded executor surface for the canonical ENGINE_C_VOID_VALIDATION hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_engine_c_void_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/engine_c_void_validation_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to Engine C void validation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/engine_coordination_rules.py`
- responsibility: Typed engine coordination rules before deeper C/D doctrinal migration.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: coordination_input, thresholds
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/engine_d_hooks.py`
- responsibility: Bounded executor surface for the canonical ENGINE_D_REENTRY_VALIDATION hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_engine_d_reentry_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/engine_d_reentry_validation_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to Engine D re-entry validation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/engine_judgment_dashboard.py`
- responsibility: module exposing _card_status_from_verdict
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: summary
- outputs: build_engine_judgment_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/enums.py`
- responsibility: Enums for the minimal real Build-11/12/13 protocol runtimes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: LiveCompleteRunState, LiveLightRunState, MicroLiveRunState, ShadowComponentHardState, ShadowRunState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, review_only, review_only
- duplication_notes: none

### `src/protocols/errors.py`
- responsibility: Dedicated errors for the minimal real Build-11/12/13 protocol runtimes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_hooks.py`
- responsibility: Canonical execution hook module wrapper aligned with HOOK_MODULE_BY_ID.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_no_trade_filter_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to the execution-edge veto surface.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_no_trade_hook.py`
- responsibility: Bounded executor surface for the canonical EXECUTION_NO_TRADE_FILTER hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_execution_no_trade_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/execution_opportunity_bridge.py`
- responsibility: Canonical inter-build stitch from Build-8 portfolio output to Build-3 execution.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: context, engine_id, orchestrator_result, pair, selection
- outputs: build_execution_opportunity_from_orchestrator_result, build_execution_opportunity_from_portfolio_selection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_routing_bridge.py`
- responsibility: Protocol-layer re-export for the Build-3 routing bridge.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_routing_features.py`
- responsibility: Protocol-layer re-export for Build-3 routing feature contracts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_runtime_bootstrap.py`
- responsibility: Bootstrap helpers for wiring compiled execution hooks into the execution runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: adapter, capture_remote_state_snapshot, clock_ms, compiled_registry_state_dir, config, credentials, default_fee_rate, execution_runtime_projection_path, fee_aware_edge_gate_config, gatekeeper_audit_path, http_client, max_recon_age_s, reconciliation_boot_now, reconciliation_circuit_breaker, reconciliation_scheduler_calibration_config, trip_reconciliation_circuit_breaker_on_unresolved, user_data_socket_factory, user_data_stream_enabled, venue_constraint_provider
- outputs: ExecutionRuntimeBootstrapBundle, build_binance_execution_runtime, build_binance_execution_runtime_bootstrap_bundle, build_execution_runtime, build_execution_runtime_bootstrap_bundle
- runtime_files_read: none
- formulas_or_derived_metrics: rate_limit_model = None
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/execution_runtime_dashboard.py`
- responsibility: Monitoring projections for bounded compiled runtime hook bridges.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: compiled_registry_state_dir, execution_runtime_projection_path
- outputs: build_execution_no_trade_bridge_projection, build_execution_runtime_projection_bridge_projection, build_runtime_hook_bridge_projections
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/execution_runtime_projection_bridge.py`
- responsibility: Fail-open loader for Local IA Lab execution runtime projection artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: projection_path
- outputs: load_execution_runtime_consumer_models
- runtime_files_read: none
- formulas_or_derived_metrics: rate_limit_model_loaded = False, rate_limit_model = _load_rate_limit_model(projection)
- thresholds_or_constants: rate_limit_model_loaded = False, slippage_model_loaded = False
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/live_complete_dashboard.py`
- responsibility: Build-17 Complete dashboard projections for governed supervision.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: summary
- outputs: build_live_complete_dashboard_section, build_live_complete_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, eligible_to_trade, queue, review_only
- duplication_notes: none

### `src/protocols/live_complete_gate_support.py`
- responsibility: Support helpers for the Build-17 Complete control gate.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: artifact_blocked, artifact_review, blocked, command_blocked, command_review, gate_id, governance_blocked, governance_review, live_complete_input, operator_blocked, operator_review, recovery_blocked, recovery_review, review
- outputs: build_decision, build_execution_envelope, build_gate_group
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, passed, queue, review_only, review_only
- duplication_notes: none

### `src/protocols/live_complete_runtime.py`
- responsibility: Build-17 Complete control gate and typed supervision builder.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: active_ml_artifact, active_regime_detector_artifact, allowed_actions, artifact_comparisons, artifact_runtime_visibility, artifact_threshold_consumers, artifact_verdict_bundle, available_pairs, command_queue_snapshot, complete_gates, forbidden_actions, live_complete_input, live_light_summary, recovery_readiness_report, run_id, selected_pairs, shadow_ml_challenger_artifact, shadow_regime_detector_challenger_artifact, warmup_run_summary
- outputs: build_live_complete_input_from_live_light
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate
- duplication_notes: none

### `src/protocols/live_light_dashboard.py`
- responsibility: Build-13 governed live supervision helpers for the technical interface.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: summary
- outputs: build_live_light_dashboard_section, build_live_light_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, gate, halt, passed, review_only
- duplication_notes: none

### `src/protocols/live_light_runtime.py`
- responsibility: Minimal governed Build-13 Live-Light gate and execution-intent builder.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: active_engines, argv, broker_ready, build14_influence, build14_live_eligible, component_verdicts_rendered, exchange_ready, execution_order_limit, execution_ready, halt_ready, live_light_input, live_pairs, max_pair_notional_usdt, max_total_notional_usdt, micro_live_payload, micro_live_required_days, micro_live_stable_days, micro_live_summary, observability_ready, onboarding_accepted, onboarding_reasons, onboarding_review_state, operator_safing_request, requested_pair_notional_usdt, requested_total_notional_usdt, run_id, shadow_days_completed, shadow_report_ready, shadow_required_days, shadow_state_dir, sleep_seconds
- outputs: build_live_light_input_from_micro_live
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, halt, review_only, runtime_mode
- duplication_notes: none

### `src/protocols/live_light_runtime_gate_support.py`
- responsibility: Gate-surface helpers for the governed Build-13 Live-Light runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate, runtime_mode, shadow_only
- duplication_notes: none

### `src/protocols/live_light_runtime_result_support.py`
- responsibility: Outcome builders for the governed Build-13 Live-Light runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, passed, review_only
- duplication_notes: none

### `src/protocols/live_light_runtime_support.py`
- responsibility: Validation helpers for the governed Build-13 Live-Light runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: review_only, runtime_mode
- duplication_notes: none

### `src/protocols/micro_live_dashboard.py`
- responsibility: Build-12 Micro-live supervision helpers for the technical interface.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: summary
- outputs: build_micro_live_dashboard_section, build_micro_live_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, halt
- duplication_notes: none

### `src/protocols/micro_live_runtime.py`
- responsibility: Minimal governed Build-12 Micro-live gate and plan builder.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: active_engines, argv, halt_ready, max_pair_notional_usdt, max_total_notional_usdt, micro_live_input, observability_ready, onboarding_accepted, onboarding_reasons, onboarding_review_state, operator_safing_request, order_probe_limit, probe_pairs, requested_pair_notional_usdt, requested_total_notional_usdt, run_id, shadow_payload, shadow_summary, sleep_seconds
- outputs: build_micro_live_input_from_shadow
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, halt, runtime_mode
- duplication_notes: none

### `src/protocols/micro_live_runtime_support.py`
- responsibility: Validation helpers for the governed Build-12 Micro-live runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode, shadow_only
- duplication_notes: none

### `src/protocols/portfolio_hooks.py`
- responsibility: Bounded executor surface for the canonical PORTFOLIO_RELATIVE_RANK_ADJUSTMENT hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_portfolio_relative_rank_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/portfolio_relative_rank_adjustment_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to the portfolio relative-rank hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/promotion_gates.py`
- responsibility: HARD STATEMENT §0.6 - Promotion Gate Checks.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: state_dir
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, gate, gate, passed, passed
- duplication_notes: none

### `src/protocols/risk_hooks.py`
- responsibility: Bounded executor surface for the canonical RISK_MICRO_FRICTION_PRECHECK hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_risk_micro_friction_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/protocols/risk_micro_friction_precheck_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to the risk micro-friction precheck.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/runtime_signal_support.py`
- responsibility: Shared signal-aware idle entrypoints for governed protocol runtimes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: argv, logger, runtime_name, shutdown, sleep_seconds
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/scoring_hooks.py`
- responsibility: Bounded executor surface for the canonical SCORING_SOFT_PENALTY_LAYER hook.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: hook_input, hook_payload, selection
- outputs: load_scoring_soft_penalty_hook_payload
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/scoring_soft_penalty_layer_bridge.py`
- responsibility: Thin bridge from the compiled hook-plan rail to the scoring soft-penalty layer.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: store
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_daily_orchestrator.py`
- responsibility: External daily orchestration state for governed Build-11 Shadow runs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: ShadowDailyOrchestratorState
- runtime_files_read: local_replay_shadow.shadow_session_summary.json, replay_run_manifest.json, shadow_daily_orchestrator.state.json, shadow_session_registry.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_dashboard.py`
- responsibility: Build-11 Shadow supervision helpers for the technical interface.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: summary
- outputs: build_shadow_dashboard_section, build_shadow_projection
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate
- duplication_notes: none

### `src/protocols/shadow_day_counter.py`
- responsibility: Shadow day counter.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: shadow_counter_{profile}.json, shadow_report_{self._profile.value}_{ts}.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_day_counter_models.py`
- responsibility: Typed models for shadow day counting and promotion readiness.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: ShadowCounterState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_day_counter_report_rendering.py`
- responsibility: Rendering helpers for shadow day counter report artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: break_even_visible, build14_contribution, build14_contribution_ready, build14_reader_contribution, costs_break_even_report_ready, costs_plausible, critical_alerts_visible, data_infra_report_ready, decision_metrics, decisions_dtr_report_ready, decisions_reproducible, dominant_cluster, dtr_complete, global_metrics, go_no_go_report_ready, infra_metrics, infra_stable, inter_engine_comparison, inter_engine_comparison_ready, metric_flag, missing_sections, operator_actions_logged, pnl_shadow, portfolio_metrics, portfolio_report_ready, rendered_sections, state, successful_records, ui_alerting_report_ready, ui_locked
- outputs: build_missing_sections, build_report_sections, build_shadow_report_artifact
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: global_metrics["ce_net"] compare None, global_metrics['ce_net'] compare None
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_day_counter_reporting.py`
- responsibility: Reporting helpers for shadow day counter artifacts.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: state
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: _REQUIRED_GLOBAL_METRICS = (
    "dtr_coverage",
    "ce_net",
    "estimated_cost_bps",
    "edge_net",
    "drawdown_pct",
    "stale_rate",
    "economic_pass_rate",
    "pair_health_ratio",
    "backlog_avg",
), economic_pass_rate = _metric_average(records, f"{engine_id}.economic_pass_rate"), conflict_rate = _metric_average(records, f"{engine_id}.conflict_rate"), portfolio_report_ready = global_metrics["ce_net"] is not None
        and pnl_shadow is not None
        and all(value is not None for value in portfolio_metrics.values())
        and bool(dominant_cluster)
- thresholds_or_constants: global_metrics["ce_net"] compare None
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_live_plan.py`
- responsibility: Canonical pair-universe and route-plan helpers for Shadow live capture.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: requested_pairs
- outputs: build_shadow_live_plan
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_live_websocket.py`
- responsibility: Native live websocket capture for the autonomous VPS Shadow service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: adapter_factory, clock, config, output_dir, socket_factory, time_sync_server_time_reader, user_data_socket_factory
- outputs: none
- runtime_files_read: live_time_sync_offsets.json, live_user_data_capture_summary.json, live_user_data_events.jsonl, live_websocket_capture_summary.json, live_websocket_snapshot_batch.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_report_builder.py`
- responsibility: Helpers to materialize Build-11 daily Shadow report metrics from real runtime payloads.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: capital_simulated_usdt, go_no_go_rendered, hard_block_rate, operator_actions_logged, payload, phantom_trade_count, replay_metrics_payload, shadow_summary, ui_locked
- outputs: build_shadow_daily_metrics_summary
- runtime_files_read: none
- formulas_or_derived_metrics: resolved_hard_block_rate = replay_hard_blocked_count / replay_total_opportunities
        if replay_total_opportunities > 0
        else min(max(hard_block_rate, 0.0), 1.0), stale_rate = round(payload.alerts.stale_pair_count / pair_count, 8), economic_pass_rate = round(
        sum(1 for engine in payload.engines if engine.net_edge_bps > engine.expected_cost_bps)
        / engine_count,
        8,
    )
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_runtime.py`
- responsibility: Minimal real Build-11 Shadow orchestration.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: argv, profile, sleep_seconds, state_dir
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_runtime_evidence.py`
- responsibility: Stateful runtime evidence recorder for governed Build-11 Shadow sessions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: ShadowRuntimeEvidenceRecorderState
- runtime_files_read: shadow_runtime_evidence.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_runtime_inputs.py`
- responsibility: Input and runtime evidence builders for the governed Shadow runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: baseline_payload, build14_contribution_ready, candidate_payload, component_assessments, inter_engine_comparison_ready, local_replay_evidence, max_allowed_alert_count_increase, max_allowed_break_even_drift_scope_increase, max_allowed_ce_net_drop, max_allowed_cra_increase, max_allowed_dtr_coverage_drop, max_allowed_edge_degraded_delta, max_allowed_queue_backlog_increase, runtime_config_loaded, runtime_continuous_hours, runtime_data_source, runtime_event_loop_ready, runtime_evidence, runtime_feature_bridge_ready, runtime_parity_diagnostics_ready, runtime_replay_dtr_ready, runtime_replay_metrics_ready, runtime_shadow_dtr_persisted, shadow_days_completed, shadow_report_ready, truth_ref, validation_ref
- outputs: build_shadow_input_from_payloads, build_shadow_runtime_evidence
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/protocols/shadow_runtime_judgments.py`
- responsibility: Judgment and comparison helpers for the governed Shadow runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: ce_by_engine, shadow_input, shadow_payload, shadow_report, shadow_summary
- outputs: derive_shadow_engine_judgment_summary
- runtime_files_read: none
- formulas_or_derived_metrics: summary = f"{metric_name} diverged within the allowed Shadow threshold", summary = f"{metric_name} exceeded the allowed Shadow threshold"
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/protocols/shadow_runtime_portfolio.py`
- responsibility: Portfolio judgment helpers for the governed Shadow runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: judgments, shadow_payload, shadow_report
- outputs: derive_shadow_portfolio_judgment
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_runtime_shared.py`
- responsibility: Shared constants for the governed Shadow runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_runtime_validation.py`
- responsibility: Validation and governance helpers for the governed Shadow runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: daily_pnl_breaker_assessment, info_stress_assessment, regime_lite_assessment, regime_lite_safing_recommendation, run_id, shadow_input
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate
- duplication_notes: none

### `src/protocols/shadow_session_registry.py`
- responsibility: Persistent registry of governed Build-11 Shadow session days.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: ShadowSessionRegistryState
- runtime_files_read: shadow_session_registry.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_vps_service.py`
- responsibility: Persistent state and event logging for a long-running VPS Shadow service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: ShadowLiveUserDataCaptureSummary
- runtime_files_read: shadow_vps_service.events.jsonl, shadow_vps_service.state.json
- formulas_or_derived_metrics: strategy_id = Field(default="strategy-shadow-vps-native", min_length=1), strategy_version = Field(default="a.v1.0", min_length=1), strategy_classification = Field(default="a_variant", min_length=1)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_vps_service_telegram_alerting.py`
- responsibility: Build-11 operated Telegram alerting seam for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: event
- outputs: build_shadow_vps_service_alert_record
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/protocols/shadow_websocket_ingest.py`
- responsibility: Bridge injected WebSocket streams into canonical historical snapshot batches.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: messages, snapshot_batch_path, source, stream_path, summary_path
- outputs: build_snapshot_batch_from_injected_websocket_stream, build_snapshot_batch_from_observed_websocket_messages
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `src/protocols/vps_recovery_warmup.py`
- responsibility: Build-17 VPS recovery and warm-up proof helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: active_artifact_hash_matches, active_artifact_manifest, active_binance_profile_id, artifact_registry_readable, binance_credential_inventory, binance_credentials_authenticated, binance_credentials_decryptable, binance_time_sync_ok, bootstrap_summary, circuit_breaker_active, command_queue_snapshot, deployment_state, info_stress_ready, pending_ambiguous_command_count, regime_lite_ready, report, report_id, run_id, runtime_mode, websocket_ready
- outputs: build_vps_recovery_readiness_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked, eligible_to_trade, eligible_to_trade, halt, passed, passed, queue, runtime_mode
- duplication_notes: none

## regime_classifier

### `src/regime_classifier/__init__.py`
- responsibility: Typed regime classification helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/regime_classifier/regime_lite.py`
- responsibility: Typed three-state regime helper with bounded hysteresis and cooldown.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: coded_not_displayed
- inputs: config, observation, previous, thresholds
- outputs: RegimeLiteState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## risk_backbone

### `src/risk_backbone/__init__.py`
- responsibility: V5.3 Trading System - risk_backbone (Build-4).
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/btc_factor_guard/__init__.py`
- responsibility: btc_factor_guard â€” BTC systemic factor exposure, beta caps, projection.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/btc_factor_guard/beta_cap_guard.py`
- responsibility: Build-4 / btc_factor_guard / beta_cap_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: beta_cap, current_beta, pair, projected_beta
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/btc_factor_guard/beta_reporter.py`
- responsibility: Build-4 / btc_factor_guard / beta_reporter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: beta_cap = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/btc_factor_guard/pair_beta_registry.py`
- responsibility: Build-4 / btc_factor_guard / pair_beta_registry
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/btc_factor_guard/portfolio_beta_calculator.py`
- responsibility: Build-4 / btc_factor_guard / portfolio_beta_calculator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: betas, positions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/btc_factor_guard/projected_beta_checker.py`
- responsibility: Build-4 / btc_factor_guard / projected_beta_checker
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: beta_cap, betas, candidate_beta, candidate_pair, candidate_size, current_positions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/correlation_cluster_guard/__init__.py`
- responsibility: correlation_cluster_guard â€” cluster exposure caps, concentration monitoring.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/correlation_cluster_guard/cluster_cap_guard.py`
- responsibility: Build-4 / correlation_cluster_guard / cluster_cap_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate_size, cluster_cap, cluster_id, current_exposure, pair
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/correlation_cluster_guard/cluster_exposure_calculator.py`
- responsibility: Build-4 / correlation_cluster_guard / cluster_exposure_calculator
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: pair_to_clusters, positions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/correlation_cluster_guard/cluster_registry.py`
- responsibility: Build-4 / correlation_cluster_guard / cluster_registry
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/correlation_cluster_guard/cluster_reporter.py`
- responsibility: Build-4 / correlation_cluster_guard / cluster_reporter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/correlation_cluster_guard/projected_cluster_checker.py`
- responsibility: Build-4 / correlation_cluster_guard / projected_cluster_checker
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate_size, cluster_cap, cluster_id, current_exposure
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/daily_pnl_breaker_entry_gate.py`
- responsibility: Opt-in risk precheck built from the typed daily PnL breaker seam.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: breaker, thresholds
- outputs: build_daily_pnl_breaker_entry_gate
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/emergency_kill_switch/__init__.py`
- responsibility: Emergency kill switch â€” Build-1 P0 guardrail (GEM-10 / QWEN-07).
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: kill
- duplication_notes: none

### `src/risk_backbone/emergency_kill_switch/circuit_breaker.py`
- responsibility: Compatibility surface for the canonical execution-owned circuit breaker.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/exposure_budgeter/__init__.py`
- responsibility: exposure_budgeter â€” gross exposure caps, position caps, projection, reporting.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/exposure_budgeter/exposure_reporter.py`
- responsibility: Build-4 / exposure_budgeter / exposure_reporter
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: refusal_rate = 0.0
- thresholds_or_constants: gross_cap = 0.0, remaining_capacity = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/exposure_budgeter/gross_cap_guard.py`
- responsibility: Build-4 / exposure_budgeter / gross_cap_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate_size, current_gross, current_pair_exposure, gross_cap, pair, position_cap
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/exposure_budgeter/gross_exposure_calculator.py`
- responsibility: Build-4 / exposure_budgeter / gross_exposure_calculator
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: positions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/exposure_budgeter/position_cap_guard.py`
- responsibility: Build-4 / exposure_budgeter / position_cap_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: pair, position_cap, position_size
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/exposure_budgeter/projected_exposure_checker.py`
- responsibility: Build-4 / exposure_budgeter / projected_exposure_checker
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate_size, current_exposure, gross_cap
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/info_stress_monitor.py`
- responsibility: Bounded information-stress detector and risk precheck for entry vetoes.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: monitor
- outputs: build_info_stress_entry_gate
- runtime_files_read: none
- formulas_or_derived_metrics: cancellation_rate_alert_threshold = Field(default=0.80, ge=0.0, le=1.0)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/__init__.py`
- responsibility: loss_budgeter â€” planned loss caps, per-position L_i, projection, reporting.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/aggregate_loss_budgeter.py`
- responsibility: Build-4 / loss_budgeter / aggregate_loss_budgeter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: estimates, loss_cap
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py`
- responsibility: Typed daily PnL breaker with persistent same-day shadow lock.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: config
- outputs: DailyPnlBreakerState
- runtime_files_read: daily_pnl_breaker_state.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/drawdown_guard.py`
- responsibility: Build-4 / loss_budgeter / drawdown_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: current_equity, observe_threshold_pct, session_peak_equity, warning_threshold_pct
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/loss_cap_guard.py`
- responsibility: Build-4 / loss_budgeter / loss_cap_guard
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate_loss, current_budget, loss_cap, pair
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/loss_reporter.py`
- responsibility: Build-4 / loss_budgeter / loss_reporter
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: loss_cap = 0.0, remaining_capacity = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/position_loss_estimator.py`
- responsibility: Build-4 / loss_budgeter / position_loss_estimator
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: engine_id, entry_price, pair, size, stop_price
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/loss_budgeter/projected_loss_checker.py`
- responsibility: Build-4 / loss_budgeter / projected_loss_checker
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate_loss, current_loss_budget, loss_cap
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/regime_lite_entry_gate.py`
- responsibility: Opt-in risk precheck built from a typed regime_lite assessment.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: assessment
- outputs: build_regime_lite_entry_gate
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/risk_backbone/regime_lite_safing.py`
- responsibility: Typed governed safing recommendation derived from a regime_lite assessment.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: assessment, requested_by, source_runtime_mode, timestamp_ms, ui_channel
- outputs: build_regime_lite_safing_recommendation
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/risk_runtime.py`
- responsibility: Public facade for the Build-4 stateful risk runtime.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/risk_runtime_drawdown_calibration.py`
- responsibility: Opt-in calibration seam for RiskLimits drawdown alert thresholds (THR-W01/THR-W02).
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: config
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/risk_runtime_evaluation_support.py`
- responsibility: Evaluation support for the stateful Build-4 risk runtime.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: candidate, now, runtime
- outputs: _RiskGuardSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/risk_backbone/risk_runtime_explainability.py`
- responsibility: Explainability and validation helpers for the Build-4 risk runtime.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/risk_runtime_models.py`
- responsibility: Public models and hook contracts for the Build-4 risk runtime.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: PortfolioRiskSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: order_cancellation_rate = Field(default=None, ge=0.0, le=1.0)
- thresholds_or_constants: beta_mapping_max_age_s = 86400.0, drawdown_warning_threshold_pct = 0.02, drawdown_observe_threshold_pct = 0.04
- control_flags_or_gates: none
- duplication_notes: none

### `src/risk_backbone/risk_runtime_runtime.py`
- responsibility: Stateful Build-4 risk runtime implementation.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## scoring_backbone

### `src/scoring_backbone/__init__.py`
- responsibility: Build-5 - scoring_backbone: auditable hard/soft/rank runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/break_even_filter.py`
- responsibility: Additive doc20 economics seam for break-even / CE / EV-net gating.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate_size, ce_min, config, delta_safe, expected_ce, expected_cost, expected_gain
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/scoring_backbone/engine_a_cost_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine A cost inputs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_a_cost_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_b_breakout_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine B anti-breakout thresholds.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_b_breakout_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/scoring_backbone/engine_b_cost_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine B cost inputs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_b_cost_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_b_excess_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine B excess thresholds.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_b_excess_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_b_invalidation_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine B invalidation thresholds.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_b_invalidation_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_c_continuation_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine C continuation inputs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_c_continuation_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_c_cost_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine C cost inputs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_c_cost_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_d_coordination_thresholds.py`
- responsibility: Policy-governed upstream threshold resolver for Engine D coordination.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_d_coordination_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_d_cost_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine D cost inputs.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_d_cost_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/engine_d_first_episode_thresholds.py`
- responsibility: Allowed upstream signed-threshold resolver for Engine D first-episode linkage.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_engine_d_first_episode_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/ev_net_floor_thresholds.py`
- responsibility: Shared signed-threshold resolver for the canonical EV-net floor seam.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config
- outputs: build_ev_net_floor_threshold_updates
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/fee_aware_edge_gate.py`
- responsibility: Compatibility surface for the canonical execution-owned fee-aware edge gate.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/scoring_backbone/forecast_normalizer.py`
- responsibility: Additive doc20 forecast normalization seam for runtime-safe forecast scaling.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: config, expected_return, forecast_scalar, raw_forecast, raw_forecasts, volatility_scale
- outputs: compute_raw_forecast
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/hard_block_gate/__init__.py`
- responsibility: Build-5 / hard_block_gate â€” fatal binary blocking decisions.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/hard_block_gate/blocker_decision_builder.py`
- responsibility: Build-5 / hard_block_gate / blocker_decision_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: encoded_reasons, engine_id, pair
- outputs: build_decision
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, blocked
- duplication_notes: none

### `src/scoring_backbone/hard_block_gate/blocker_evaluator.py`
- responsibility: Build-5 / hard_block_gate / blocker_evaluator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: conditions
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: suspended
- duplication_notes: none

### `src/scoring_backbone/hard_block_gate/blocker_reason_encoder.py`
- responsibility: Build-5 / hard_block_gate / blocker_reason_encoder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: triggered_blockers
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/hard_block_gate/blocker_registry.py`
- responsibility: Build-5 / hard_block_gate / blocker_registry
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: DEFAULT_BLOCKERS = (
    BlockerDefinition(
        blocker_id=BlockerID.STALE_HARD,
        description="Data is hard-stale beyond recovery threshold",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.PAIR_SUSPENDED,
        description="Pair health is in SUSPENDED state",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.RISK_BUDGET_EXCEEDED,
        description="Risk budget (exposure/loss/beta/cluster) is fully exhausted",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.RECONCILIATION_CRITICAL,
        description="Reconciliation divergence is at CRITICAL level",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.INFRA_DOWN,
        description="Infrastructure subsystem is down",
    ),
)
- thresholds_or_constants: none
- control_flags_or_gates: suspended
- duplication_notes: none

### `src/scoring_backbone/hard_block_gate/blocker_reporter.py`
- responsibility: Build-5 / hard_block_gate / blocker_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: hb_rate = 0.0, rate = self._blocked / n if n > 0 else 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/penalty_aggregator/__init__.py`
- responsibility: Build-5 / penalty_aggregator â€” gradual non-fatal penalties.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/penalty_aggregator/penalty_cap_guard.py`
- responsibility: Build-5 / penalty_aggregator / penalty_cap_guard
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: expected_cost, max_score_penalty, min_size_multiplier, raw_score, score_penalty, size_multiplier
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/penalty_aggregator/penalty_registry.py`
- responsibility: Build-5 / penalty_aggregator / penalty_registry
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: penalty_ids, registry
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/penalty_aggregator/penalty_reporter.py`
- responsibility: Build-5 / penalty_aggregator / penalty_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: is_capped = False, capped_count = 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/penalty_aggregator/score_penalty_builder.py`
- responsibility: Build-5 / penalty_aggregator / score_penalty_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: penalties, raw_score, registry
- outputs: build_score_penalty
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/penalty_aggregator/size_penalty_builder.py`
- responsibility: Build-5 / penalty_aggregator / size_penalty_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: penalties, registry
- outputs: build_size_penalty
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/ranking_router/__init__.py`
- responsibility: Build-5 / ranking_router â€” rank and select opportunities within portfolio framework.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/ranking_router/candidate_pool_builder.py`
- responsibility: Build-5 / ranking_router / candidate_pool_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: all_candidates, blocked_keys
- outputs: build_candidate_pool
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, gate
- duplication_notes: none

### `src/scoring_backbone/ranking_router/portfolio_compatibility_checker.py`
- responsibility: Build-5 / ranking_router / portfolio_compatibility_checker
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: cluster_id, engine_id, pair, portfolio, projected_beta_impact, projected_loss, projected_size
- outputs: PortfolioState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: remaining_gross_capacity = 0.0, remaining_loss_capacity = 0.0, remaining_beta_capacity = 0.0
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/ranking_router/ranking_reporter.py`
- responsibility: Build-5 / ranking_router / ranking_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: selection_rate = 0.0
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/ranking_router/ranking_score_builder.py`
- responsibility: Build-5 / ranking_router / ranking_score_builder
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidates, weights
- outputs: compute_ranking_scores
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/ranking_router/selection_resolver.py`
- responsibility: Build-5 / ranking_router / selection_resolver
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: max_selections, portfolio_rejected_keys, ranked_candidates
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/raw_score_builder/__init__.py`
- responsibility: Build-5 / raw_score_builder â€” construct readable, stable raw scores.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/raw_score_builder/feature_selector.py`
- responsibility: Build-5 / raw_score_builder / feature_selector
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: allowed_features, engine_id, raw_features
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/raw_score_builder/raw_score_calculator.py`
- responsibility: Build-5 / raw_score_builder / raw_score_calculator
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: engine_id, features, pair, raw_score_add, raw_score_cap, raw_score_multiplier, scoring_version, weights
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/raw_score_builder/score_component_breakdown.py`
- responsibility: Build-5 / raw_score_builder / score_component_breakdown
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: contributions, engine_id, feature_to_block, pair
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/raw_score_builder/score_reporter.py`
- responsibility: Build-5 / raw_score_builder / score_reporter
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/scoring_backbone/scoring_runtime.py`
- responsibility: Build-5 / scoring_backbone / scoring_runtime
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: none
- outputs: _CandidateRoundState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked
- duplication_notes: none

### `src/scoring_backbone/scoring_runtime_support.py`
- responsibility: Support contracts and helpers for the Build-5 scoring runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: trading
- status: coded_not_displayed
- inputs: candidate, candidate_index, candidates, context, hard_block_decision, hook_outcome, key, now, penalty_cap_result, physics_projection, physics_projection_by_key, portfolio_result, raw_score_result, score_penalty_result, selection_entry, size_penalty_result
- outputs: ScoringEconomicsProjection, ScoringPhysicsProjection, build_candidate_index, build_economics_projection, build_explainability, build_physics_projection, build_scoring_soft_penalty_hook_input
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## scripts

### `scripts/Install-BinanceApiEnv.ps1`
- responsibility: [CmdletBinding()]
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/Run-V53LocalSolution.ps1`
- responsibility: [CmdletBinding()]
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/Start-BinanceShadowLiveCampaign.ps1`
- responsibility: [CmdletBinding()]
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: live_websocket_config.json, shadow_vps_service_observability.prom, shadow_vps_service_observability_export.json, shadow_vps_service_prometheus_file_sd.json, shadow_vps_service_scrape_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `scripts/bootstrap_grafana_dashboards.py`
- responsibility: Bootstrap Grafana datasource + dashboards into an already-running local Grafana.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: local_grafana_bootstrap.summary.json, v53_shadow_vps_local_grafana.dashboard.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/build_shadow_live_plan.py`
- responsibility: Emit the canonical Shadow live pair plan as JSON.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/local_replay_shadow_engines.py`
- responsibility: Engine-scoped Shadow demo evaluation helpers for the governed LOCAL_REPLAY runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/local_replay_shadow_import_support.py`
- responsibility: Governed import-context helpers for the LOCAL_REPLAY -> SHADOW runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: local_replay_shadow.import_summary.json, local_replay_shadow.local_replay_evidence.json, local_replay_shadow.local_replay_evidence.state.json, local_replay_shadow.replay_plan.json, local_replay_shadow.run_manifest.json, local_replay_shadow.upload_decision.json, local_replay_shadow.upload_request.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: _SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD = 0.85
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `scripts/local_replay_shadow_models.py`
- responsibility: Support models and recovery helpers for the governed LOCAL_REPLAY -> SHADOW runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: LocalReplayShadowImportBundle, LocalReplayShadowImportContextBundle, LocalReplayShadowRuntimeBundle, LocalReplayShadowSessionBundle
- runtime_files_read: local_replay_shadow.day_*.json
- formulas_or_derived_metrics: _RECOVERED_SHADOW_LINEAGE_VERSION = "recovered:lineage"
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/local_replay_shadow_payloads.py`
- responsibility: Monitoring and payload helpers for the governed LOCAL_REPLAY -> SHADOW runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: daily_pnl_breaker_assessment.json, info_stress_assessment.json, local_lab_execution_runtime_projection.json, regime_lite_assessment.json, regime_lite_safing_recommendation.json
- formulas_or_derived_metrics: snapshot = _build_demo_snapshot(
        correlation_id=correlation_id,
        ce_net=ce_net,
        dtr_coverage=dtr_coverage,
        cra_sterilization_rate=cra_sterilization_rate,
        active_alert_count=active_alert_count,
        queue_backlog=queue_backlog,
        engine_runtime_evidence=engine_runtime_evidence,
    )
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `scripts/local_replay_shadow_session_support.py`
- responsibility: Runtime and session materialization helpers for the governed LOCAL_REPLAY -> SHADOW runner.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: daily_pnl_breaker_assessment_path, execution_runtime_projection_path, export_dir, info_stress_assessment_path, output_dir, regime_lite_assessment_path, regime_lite_safing_recommendation_path, session_date, shadow_days
- outputs: none
- runtime_files_read: local_replay_shadow.baseline_payload.json, local_replay_shadow.candidate_payload.json, local_replay_shadow.day_{absolute_day_number:04d}.json, local_replay_shadow.engine_shadow_evidence.json, local_replay_shadow.shadow_day_record.json, local_replay_shadow.shadow_input.json, local_replay_shadow.shadow_report.json, local_replay_shadow.shadow_runtime_evidence.json, local_replay_shadow.shadow_runtime_evidence.state.json, local_replay_shadow.shadow_session_summary.json, local_replay_shadow.shadow_summary.json
- formulas_or_derived_metrics: baseline_payload = _build_demo_payload(
        correlation_id="corr-local-replay-shadow-demo:baseline",
        ce_net=0.0012,
        dtr_coverage=0.87,
        cra_sterilization_rate=0.08,
        active_alert_count=0,
        queue_backlog=8,
        output_dir=output_dir,
        replay_projection=replay_projection,
        execution_runtime_projection_path=resolved_execution_runtime_projection_path,
    ), candidate_payload = _build_demo_payload(
        correlation_id="corr-local-replay-shadow-demo:candidate",
        ce_net=0.0010,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        active_alert_count=1,
        queue_backlog=10,
        output_dir=output_dir,
        replay_projection=replay_projection,
        execution_runtime_projection_path=resolved_execution_runtime_projection_path,
        engine_runtime_evidence=engine_runtime_evidence,
    )
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_build9_core_smoke.py`
- responsibility: Standalone launcher for the Build-1..9 core smoke suite.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: argv
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `scripts/run_build9_core_smoke_support.py`
- responsibility: support module for run_build9_core_smoke
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: execution_runtime_projection_path, gatekeeper_audit_path, opportunity, reconciliation_calibration_root
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: bundle = build_binance_execution_runtime_bootstrap_bundle(
        credentials=BinanceCredentials(
            api_key="smoke-api-key",
            secret_key="smoke-secret-key",
            label="smoke",
        ),
        config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
        http_client=http_client,
        user_data_stream_enabled=True,
        user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeSocket(
            [
                json.dumps(
                    {
                        "id": "v53-user-data-subscribe",
                        "status": 200,
                        "result": {"subscriptionId": 7},
                    }
                ),
                json.dumps(
                    {
                        "subscriptionId": 7,
                        "event": {
                            "e": "executionReport",
                            "E": 1_710_000_007_000,
                            "s": "BTCUSDT",
                            "c": "v53_engine_a_intent-1",
                            "S": "BUY",
                            "o": "LIMIT",
                            "f": "GTC",
                            "q": "0.25000000",
                            "p": "50000.10000000",
                            "x": "NEW",
                            "X": "NEW",
                            "i": 123462,
                            "l": "0.00000000",
                            "z": "0.00000000",
                            "L": "0.00000000",
                            "n": "0",
                            "N": None,
                            "t": -1,
                            "r": "NONE",
                        },
                    }
                ),
            ]
        ),
        clock_ms=lambda: 1_710_000_000_000,
        execution_runtime_projection_path=execution_runtime_projection_path,
        gatekeeper_audit_path=gatekeeper_audit_path,
        reconciliation_scheduler_calibration_config=reconciliation_calibration_config,
        reconciliation_boot_now=1_710_000_000.5,
    )
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_cockpit.py`
- responsibility: Launch the V5.3 cockpit operator shell.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: overview
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: live_websocket_config.json, shadow_service.log, thresholds.yml
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `scripts/run_cockpit_source_discovery.py`
- responsibility: Run the V5.3 cockpit source discovery audit.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: overview
- status: coded_not_displayed
- inputs: argv
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_complete_dashboard.py`
- responsibility: Generate a local Build-17 Complete dashboard page.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: argv, demo, output_dir, selected_pair_count, selected_pairs
- outputs: none
- runtime_files_read: complete_dashboard.metrics.txt, complete_dashboard.payload.json, complete_dashboard.supplement.json, complete_dashboard.view.json
- formulas_or_derived_metrics: snapshot = collect_monitoring_snapshot(
        correlation_id="corr-complete-demo",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LIVE,
        timestamp_ms=1_775_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=len(pairs),
            gross_capacity_used_pct=68.0,
            loss_capacity_used_pct=18.0,
            beta_utilization=0.47,
            capital_deployed_usdt=6200.0,
            ce_net=0.00145,
            pnl_net_usdt=118.5,
            dominant_cluster="alts_expansion",
            breaches=("cluster_pressure:alts_expansion",),
        ),
        infra=collect_infra_metrics(
            queue_backlog=44,
            backlog_high_water_mark=96,
            reconnect_count=2,
            stale_pairs=tuple(pair for pair in ("MATICUSDT",) if pair in selected_pairs),
            stale_spike_count=1,
            recovery_retry_count=1,
            dtr_loss_count=0,
            log_loss_count=0,
            total_enqueued=1200,
            total_dropped=18,
            elw_bps=0.92,
            expected_cost_bps=1.8,
            realized_cost_bps=2.1,
            partial_fill_count=5,
            fill_latency_ms_p95=310,
            reconciliation_alert_count=1,
            persisted_metric_names=(
                "backlog_high_water_mark",
                "drop_rate_pct",
                "stale_spike_count",
                "recovery_retry_count",
                "kill_switch_active",
            ),
            cpu_pct=41.0,
            ram_pct=56.0,
        ),
        meta=MetaMetrics(
            dtr_coverage=0.88,
            cra_sterilization_rate=0.14,
            cra_alert_count=2,
            break_even_drift_alert=True,
            break_even_drift_scopes=("engine_c", "MATICUSDT"),
            edge_credible_count=2,
            edge_degraded_count=1,
            edge_surveillance_count=1,
            future_learning_diagnostics=4,
            future_learning_hypotheses=2,
        ),
        engines=engines,
        pairs=pairs,
    ), engine_metadata = (
        CompleteEngineMetadata(
            engine_id="engine_a",
            dominant_cluster="btc_core",
            active_pairs=tuple(pair for pair in selected_pairs if "engine_a" in _active_engines_for_pair(pair)),
            cost_p90_bps=1.9,
            sterilization_note="low sterilization",
            marginal_cost_note="baseline reference",
            marginal_value_note="core alpha anchor",
        ),
        CompleteEngineMetadata(
            engine_id="engine_b",
            dominant_cluster="alts_beta",
            active_pairs=tuple(pair for pair in selected_pairs if "engine_b" in _active_engines_for_pair(pair)),
            cost_p90_bps=2.3,
            sterilization_note="moderate sterilization",
            marginal_cost_note="higher than A but still positive",
            marginal_value_note="diversifies A on rotation regimes",
        ),
        CompleteEngineMetadata(
            engine_id="engine_c",
            dominant_cluster="alts_expansion",
            active_pairs=tuple(pair for pair in selected_pairs if "engine_c" in _active_engines_for_pair(pair)),
            cost_p90_bps=2.9,
            sterilization_note="watch C on crowded expansions",
            marginal_cost_note="C costs +0.5bps vs A baseline",
            marginal_value_note="adds breadth when edge diversity remains positive",
        ),
        CompleteEngineMetadata(
            engine_id="engine_d",
            dominant_cluster="alts_rotation",
            active_pairs=tuple(pair for pair in selected_pairs if "engine_d" in _active_engines_for_pair(pair)),
            cost_p90_bps=3.4,
            sterilization_note="high review pressure",
            marginal_cost_note="D costs +1.1bps vs do-nothing baseline",
            marginal_value_note="marginal value remains conditional and gate-bound",
        ),
    )
- thresholds_or_constants: none
- control_flags_or_gates: gate, queue, runtime_mode, suspended, suspended
- duplication_notes: none

### `scripts/run_contract_tests.py`
- responsibility: Standalone launcher for Build-1 contract-oriented tests.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_dag_check.py`
- responsibility: Standalone launcher for the DAG validator.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `scripts/run_dashboard_governed_command.py`
- responsibility: Write one governed Build-17 dashboard command request into the typed queue.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: argv
- outputs: build_parser
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: halt, queue
- duplication_notes: none

### `scripts/run_edge_gate_calibration.py`
- responsibility: Build a Local IA Lab EDGE calibration artifact from governed replay DTR exports.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: runtime_only
- inputs: argv
- outputs: EdgeCalibrationInputSummary, build_parser
- runtime_files_read: .input_summary.json, .report.json, edge_gate.yml
- formulas_or_derived_metrics: strategy_id = None, strategy_version = None
- thresholds_or_constants: recalibration_candidate_ready = False
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `scripts/run_engineering_guardrails.py`
- responsibility: Run executable engineering guardrails and optionally refresh the baseline.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: argv
- outputs: none
- runtime_files_read: config/engineering_guardrails_baseline.json, config/engineering_guardrails_policy.json, engineering_guardrails.report.json, engineering_guardrails.summary.txt
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `scripts/run_governance_snapshot_seed.py`
- responsibility: Phase 2.1 — Synthesise governance snapshots for the cockpit.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: argv, auto_exports_root, build_root
- outputs: none
- runtime_files_read: local_lab_tail_risk_review.json, model_risk_register.snapshot.json, refusal_journal.snapshot.json, replay_dtr.jsonl
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, queue
- duplication_notes: none

### `scripts/run_local_grafana_bootstrap.py`
- responsibility: Bootstrap local Grafana with the Prometheus datasource and generated V5.3 dashboard.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: local_grafana_bootstrap.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_grafana_dashboard.py`
- responsibility: Generate an importable local Grafana dashboard JSON for current V5.3 Shadow VPS metrics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: v53_shadow_vps_local_grafana.dashboard.json, v53_shadow_vps_local_grafana.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_lab_analysis_bundle.py`
- responsibility: Chain governed Local IA Lab post-trade review and EDGE calibration from one export_dir.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: runtime_only
- inputs: argv
- outputs: LocalLabAnalysisBundleSummary, build_parser
- runtime_files_read: .input_summary.json, .report.json, artifact_ablation_study.json, artifact_import_decision.dry_run.json, artifact_import_dry_run_bridge.json, artifact_import_request.dry_run.json, artifact_promotion_readiness_summary.json, artifact_proof_assessment.json, artifact_proof_summary.json, artifact_release_candidate.json, artifact_release_gate_summary.json, artifact_release_scope_summary.json, artifact_source_summary.json, artifact_upload_decision.dry_run.json, artifact_upload_request.dry_run.json, edge_gate.yml, governed_input_summary.json, local_lab_analysis_summary.json, local_lab_calibration_methods_review.json, local_lab_calibration_normalized_report.json, local_lab_execution_review.json, local_lab_execution_runtime_projection.json, local_lab_loss_surrogate_report.json, local_lab_monitoring_backend_payload.json, local_lab_monitoring_bundle_manifest.json, local_lab_monitoring_ingestion_summary.json, local_lab_monitoring_projection.json, local_lab_multiple_testing_review.json, local_lab_observability.prom, local_lab_observability_export.json, local_lab_recalibration_plan.json, local_lab_replay_candidate_queue.json, local_lab_replay_dispatch_plan.json, local_lab_replay_ticket_index.json, local_lab_replay_workflow_manifest.json, local_lab_research_priority.json, local_lab_scope_matrix.json, local_lab_tail_risk_review.json, meta_learning_projection.json, meta_learning_review.bundle.json, meta_runtime_result.json, trade_loss_attribution.json, walk_forward_review.json, walk_forward_review.summary.json, walk_forward_review.template.json
- formulas_or_derived_metrics: strategy_id = Field(..., min_length=1), strategy_version = Field(..., min_length=1), scope_review_args = [
        "--export-dir", str(discovery.export_dir),
        "--correlation-id", scope_correlation_id,
        "--source-version", args.source_version,
        "--notes", args.notes,
        "--output-dir", str(scope_review_output_dir),
        "--near-miss-threshold", str(args.near_miss_threshold),
        "--pair", scope.pair,
        "--engine-id", scope.engine_id,
        "--total-opportunities", str(args.total_opportunities if args.total_opportunities is not None else len(scope_candidate_records)),
    ], review_args = [
        "--export-dir", str(discovery.export_dir),
        "--correlation-id", args.correlation_id,
        "--source-version", args.source_version,
        "--notes", args.notes,
        "--output-dir", str(paths["review_output_dir"]),
        "--near-miss-threshold", str(args.near_miss_threshold),
    ]
- thresholds_or_constants: calibration_methods_review_ready = False, calibration_methods_walk_forward_plan_ready = False, calibration_normalized_report_ready = False, recalibration_candidate_ready = False, edge_calibration_ready = False
- control_flags_or_gates: queue, runtime_mode
- duplication_notes: none

### `scripts/run_local_lab_grafana_dashboard.py`
- responsibility: Generate an importable local Grafana dashboard JSON for current V5.3 Local IA Lab metrics.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: v53_local_lab_grafana.dashboard.json, v53_local_lab_grafana.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_lab_post_trade_review.py`
- responsibility: Run a governed Local IA Lab post-trade review from exported replay DTR records.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: lab
- status: runtime_only
- inputs: argv
- outputs: GovernedPostTradeInputSummary
- runtime_files_read: Path to governed replay_dtr.json or replay_dtr.jsonl, governed_input_summary.json, meta_learning_projection.json, meta_learning_review.bundle.json, meta_runtime_result.json, trade_loss_attribution.json
- formulas_or_derived_metrics: _ENGINE_TO_STRATEGY = {
    "engine_a": StrategyClassification.A_VARIANT,
    "engine_b": StrategyClassification.B_VARIANT,
    "engine_c": StrategyClassification.C_CANDIDATE,
    "engine_d": StrategyClassification.D_CANDIDATE,
}, strategy_id = None, strategy_version = None, strategy_classification = _resolve_strategy_classification(engine_id, args.strategy_classification)
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `scripts/run_local_observability_stack.py`
- responsibility: Launch the local Shadow VPS observability stack in one command.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: local_observability_stack.summary.json, shadow_vps_service_observability.prom
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_prometheus_config.py`
- responsibility: Generate a checked local-PC Prometheus config from the aggregated V5.3 file_sd bundle.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: prometheus.local.config.summary.json, prometheus.local.generated.yml
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_prometheus_metrics_bridge.py`
- responsibility: Serve a local `.prom` payload over HTTP for dual-role Windows/dev Prometheus scrapes.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: local_prometheus_metrics_bridge.summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_prometheus_scrape_bundle.py`
- responsibility: Build a local-PC Prometheus scrape bundle from discovered Shadow VPS manifests.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: observability
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: shadow_vps_prometheus_file_sd.json, shadow_vps_scrape_discovery.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_replay_export.py`
- responsibility: Generate a governed LOCAL_REPLAY export artifact directory.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: backtest
- status: runtime_only
- inputs: argv
- outputs: none
- runtime_files_read: edge_gate.yml, replay_run_manifest.json, replay_session_config.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_local_replay_shadow.py`
- responsibility: Materialize a governed LOCAL_REPLAY -> VPS import -> SHADOW demo run.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: argv
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_shadow_credential_seed.py`
- responsibility: Seed the Binance credential profile into the Shadow VPS service state.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: argv, env_file, force, profile_id, service_dir
- outputs: none
- runtime_files_read: secrets/{profile_id}.sealed.json, {profile_id}.sealed.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_shadow_daily_orchestrator.py`
- responsibility: Orchestrate one governed Build-11 Shadow day per invocation.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: argv, execution_runtime_projection_path, export_dir, exports_root, info_stress_assessment_path, output_dir, regime_lite_assessment_path, regime_lite_safing_recommendation_path, session_date, shadow_output_dir
- outputs: none
- runtime_files_read: shadow_daily_orchestrator.last_run.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_shadow_vps_service.py`
- responsibility: Run the autonomous long-running VPS Shadow service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: argv, auto_exports_root, auto_snapshots_root, continue_on_error, dashboard_command_queue_root, execution_runtime_bootstrap_enabled, execution_runtime_gatekeeper_audit_path, execution_runtime_projection_path, execution_time_sync_offsets_path, exports_root, halt_flag_file, info_stress_assessment_path, live_captures_root, live_websocket_config_path, max_cycles, node_exporter_metrics_path, node_exporter_port, node_exporter_scheme, node_exporter_textfile_dir, orchestrator_output_dir, pid_file, poll_interval_s, prometheus_job_name, raw_inputs_root, regime_lite_assessment_path, regime_lite_safing_recommendation_path, scrape_host, service_dir, shadow_output_dir, telegram_alert_config_path, telegram_alert_key_path, telegram_post_func, vps_id, websocket_streams_root
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: blocked, halt, kill, shadow_only, suspended
- duplication_notes: none

### `scripts/run_sharia_account_audit.py`
- responsibility: Standalone weekly launcher for the bounded halal account-feature audit.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: alerts_output_path, argv, correlation_id, output_path, provider
- outputs: none
- runtime_files_read: build/sharia_account_audit/latest_alerts.json, build/sharia_account_audit/latest_report.json, config/binance_adapter.yml
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_sharia_pair_screening_audit.py`
- responsibility: Standalone deterministic launcher for HC-4 AAOIFI pair-screening audit.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: alerts_output_path, argv, correlation_id, output_path, policy, provider, traded_pairs
- outputs: none
- runtime_files_read: build/sharia_pair_screening/latest_alerts.json, build/sharia_pair_screening/latest_report.json, config/sharia/policy_v1.yml
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/run_smoke_tests.py`
- responsibility: Standalone launcher for the Build-1 smoke suite.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `scripts/run_v53_local_solution.py`
- responsibility: Launch the local V5.3 Shadow solution and observability stack in one command.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: overview
- status: runtime_only
- inputs: api_env_file, argv, bridge_host, bridge_port, campaign_root, cockpit_host, cockpit_port, enable_execution_runtime_bootstrap, enable_time_sync_probe, evaluation_interval, grafana_home, grafana_password, grafana_server_exe, grafana_url, grafana_user, no_open_browser, output_dir, powershell_executable, prometheus_exe, prometheus_url, public_only, readiness_timeout_s, scrape_interval, skip_service_launch, stop_on_error
- outputs: CockpitLaunchSummary, ShadowServiceLaunchSummary, V53LocalSolutionLaunchSummary
- runtime_files_read: cockpit.log, launch.summary.json, local_observability_stack.summary.json, shadow_vps_service.launch.log, shadow_vps_service_monitoring_backend_payload.json, shadow_vps_service_observability.prom
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: queue
- duplication_notes: none

### `scripts/shadow_gate_check.py`
- responsibility: Compute a governed Shadow gate report from Build-11 artifacts and explicit evidence.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: argv, code_commit, engine_id, gate_id, inputs_json, output_path, run_id, shadow_report_path, shadow_session_dir, shadow_session_summary_path, shadow_summary_path
- outputs: none
- runtime_files_read: local_replay_shadow.shadow_report.json, local_replay_shadow.shadow_session_summary.json, local_replay_shadow.shadow_summary.json, shadow_gate_report.json, shadow_gate_report.{run_id}.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `scripts/shadow_gate_check_sections_support.py`
- responsibility: Optional report-section helpers for the governed Shadow gate report.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: engine_id, evidence
- outputs: build_capital_usage, build_execution_stats, build_refusal_analysis
- runtime_files_read: none
- formulas_or_derived_metrics: fill_rate = _coerce_float(execution_mapping.get("fill_rate"))
- thresholds_or_constants: none
- control_flags_or_gates: gate, passed
- duplication_notes: none

### `scripts/shadow_gate_check_support.py`
- responsibility: Support primitives for the governed Shadow gate report launcher.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: code_commit, engine_id, evidence, gate_id, shadow_report, shadow_session_summary, shadow_summary, source_paths
- outputs: build_reproducibility, build_shadow_gate_report
- runtime_files_read: none
- formulas_or_derived_metrics: payload = {
        "required": required,
        "threshold": threshold,
        "value": value,
        "pass": passed,
        "status": status,
    }, gate_specific_checks = {
        "oos_reservation_used": _metric(required=False, threshold="true", passed=None, status="not_required"),
    }
- thresholds_or_constants: none
- control_flags_or_gates: gate, passed
- duplication_notes: none

### `scripts/shadow_vps_service_artifact_support.py`
- responsibility: Artifact comparison and verdict helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: feature_bridge.json, historical_dataset.json, historical_dataset.jsonl, historical_snapshot_batch.json, historical_snapshot_batch.jsonl, policy_v1.yml, snapshot_batch.json, snapshot_batch.jsonl, {session_date}.{filename}.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_campaign_support.py`
- responsibility: Campaign summary helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: shadow_vps_service.campaign_summary.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_cli_support.py`
- responsibility: Shadow VPS service CLI helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: local_replay_shadow.shadow_session_summary.json, shadow_daily_orchestrator.state.json, shadow_vps_service_monitoring_backend_payload.json, shadow_vps_service_observability.prom, shadow_vps_service_observability_export.json, shadow_vps_service_prometheus_file_sd.json, shadow_vps_service_recent_events.json, shadow_vps_service_scrape_manifest.json, v53_shadow_vps_service.prom
- formulas_or_derived_metrics: _RUNTIME_LOOP_ARGUMENTS = (
    {
        "name": "--poll-interval-s",
        "type": float,
        "default": 5.0,
        "help": "Sleep duration between cycles when the service stays alive.",
    },
    {
        "name": "--max-cycles",
        "type": int,
        "default": None,
        "help": "Optional maximum number of service cycles. Useful for tests and smoke runs.",
    },
    {
        "name": "--stop-on-error",
        "action": "store_true",
        "help": "Stop the service immediately on the first orchestration error.",
    },
    {
        "name": "--pid-file",
        "type": Path,
        "default": None,
        "help": (
            "Optional path where the service writes its PID at startup and "
            "removes it on exit. Required by the cockpit kill switch (Phase 3) "
            "to send SIGTERM to the running service."
        ),
    },
    {
        "name": "--halt-flag-file",
        "type": Path,
        "default": None,
        "help": (
            "Optional path watched at the start of every cycle; when present "
            "the service requests an orderly stop and removes the flag. "
            "Provides a Windows-friendly kill channel that does not rely on "
            "Unix signals."
        ),
    },
)
- thresholds_or_constants: none
- control_flags_or_gates: halt, kill, queue
- duplication_notes: none

### `scripts/shadow_vps_service_complete_support.py`
- responsibility: Build-17 supervision helpers for the governed Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: append_service_event, context
- outputs: none
- runtime_files_read: live_complete_operator_audit_report.json, live_complete_run.summary.json, shadow_vps_service_recent_events.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: eligible_to_trade, gate, queue
- duplication_notes: none

### `scripts/shadow_vps_service_context_support.py`
- responsibility: Runtime context helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_cycle_support.py`
- responsibility: Cycle selection helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_event_support.py`
- responsibility: Shadow VPS service event helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_execution_support.py`
- responsibility: Execution cycle helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_governance_snapshot_support.py`
- responsibility: Governance snapshot persistence for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: model_risk_register.snapshot.json, refusal_journal.snapshot.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_input_support.py`
- responsibility: Shadow VPS service input slot + auto-export helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: dataset.json, dataset.jsonl, feature_bridge.json, live_websocket_capture_summary.json, live_websocket_snapshot_batch.json, parity_diagnostics.json, replay_dataset.json, replay_dataset.jsonl, replay_dtr.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json, shadow_input_config.json, snapshot_batch.json, snapshot_batch.jsonl, snapshots.json, snapshots.jsonl, websocket_frames.json, websocket_frames.jsonl, websocket_snapshot_batch.json, websocket_snapshot_ingest.json, websocket_stream.json, websocket_stream.jsonl
- formulas_or_derived_metrics: argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-native-{raw_slot.session_date}",
        "--strategy-id",
        raw_slot.config.strategy_id,
        "--strategy-classification",
        raw_slot.config.strategy_classification,
        "--strategy-version",
        raw_slot.config.strategy_version,
        "--lineage-version",
        raw_slot.config.lineage_version,
        "--performance-mode",
        raw_slot.config.performance_mode,
    ], argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-websocket-{websocket_slot.session_date}",
        "--strategy-id",
        websocket_slot.config.strategy_id,
        "--strategy-classification",
        websocket_slot.config.strategy_classification,
        "--strategy-version",
        websocket_slot.config.strategy_version,
        "--lineage-version",
        websocket_slot.config.lineage_version,
        "--performance-mode",
        websocket_slot.config.performance_mode,
        "--snapshot-path",
        str(auto_snapshot_path),
    ], argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-live-{session_date}",
        "--strategy-id",
        live_config.config.strategy_id,
        "--strategy-classification",
        live_config.config.strategy_classification,
        "--strategy-version",
        live_config.config.strategy_version,
        "--lineage-version",
        live_config.config.lineage_version,
        "--performance-mode",
        live_config.config.performance_mode,
        "--snapshot-path",
        str(snapshot_batch_path),
    ]
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_io_support.py`
- responsibility: Shadow VPS service configuration + bootstrap helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: .sealed.json, execution_runtime_bootstrap.summary.json, replay_run_manifest.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_loader_support.py`
- responsibility: Shadow VPS service loader helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: live_websocket_capture_summary.json, live_websocket_snapshot_batch.json, shadow_daily_orchestrator.last_run.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_models.py`
- responsibility: Models for the Shadow VPS service launcher.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_monitoring_support.py`
- responsibility: Monitoring helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: shadow_vps_service_monitoring_backend_payload.json, shadow_vps_service_observability.prom, shadow_vps_service_observability_export.json, shadow_vps_service_prometheus_file_sd.json, shadow_vps_service_recent_events.json, shadow_vps_service_scrape_manifest.json, v53_shadow_vps_service.prom
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_projection_support.py`
- responsibility: Projection helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: {session_date}.shadow_vps_runtime_evidence.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_recovery_support.py`
- responsibility: Shadow VPS recovery and warm-up evidence helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: vps_recovery_readiness.report.json, vps_warmup_run.summary.json
- formulas_or_derived_metrics: warmup = _build_warmup_summary(report)
- thresholds_or_constants: _LIVE_CAPTURE_REFRESH_AFTER_SECONDS = 20.0
- control_flags_or_gates: blocked, blocked, eligible_to_trade, eligible_to_trade, passed, review_only, review_only, runtime_mode
- duplication_notes: none

### `scripts/shadow_vps_service_resource_hygiene_support.py`
- responsibility: Resource-hygiene helpers for the long-running Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: gc_interval_s = 3600.0, ram_heartbeat_interval_s = 900.0
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_runtime_support.py`
- responsibility: Runtime loop helpers for the Shadow VPS service.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `scripts/shadow_vps_service_startup_support.py`
- responsibility: Shadow VPS service startup helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: message = f"Shadow VPS recovery status={status}; "
        f"warmup={context.store.state.last_vps_warmup_final_state}."
- thresholds_or_constants: none
- control_flags_or_gates: blocked, eligible_to_trade, review_only
- duplication_notes: none

### `scripts/shadow_vps_service_telemetry_support.py`
- responsibility: Shadow VPS service telemetry helpers.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: vps
- status: runtime_only
- inputs: none
- outputs: none
- runtime_files_read: shadow_vps_service_execution_telemetry.archive.json, shadow_vps_service_execution_telemetry.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## secrets_manager

### `src/secrets_manager/__init__.py`
- responsibility: Bounded sealed-secrets helpers for local/runtime credential loading.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/__main__.py`
- responsibility: production module
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/_dpapi.py`
- responsibility: Platform dispatch for bounded secret protection backends.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/_dpapi_posix.py`
- responsibility: POSIX keyring-backed secret protection shim.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: data, description, entropy
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/_dpapi_windows.py`
- responsibility: Windows DPAPI backend used by the sealed-secrets slice.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: data, description, entropy
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/cli.py`
- responsibility: CLI entrypoint for the bounded sealed-secrets slice.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: argv
- outputs: build_parser
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/loader.py`
- responsibility: Load sealed secret envelopes without leaking plaintext outside memory.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: encoding, force, key_path, path, text
- outputs: load_envelope, load_secret_bytes, load_secret_text
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/secrets_manager/sealer.py`
- responsibility: Seal plaintext secrets into a typed encrypted envelope.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: data, force, key_path, output_path, path, payload, remove_source, source_name
- outputs: none
- runtime_files_read: {source}.sealed.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

## sharia_compliance

### `src/sharia_compliance/__init__.py`
- responsibility: Bounded halal compliance layer for P0-2.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/account_features_audit.py`
- responsibility: Deterministic weekly audit of forbidden Binance account features.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: config, feature_balances, observed_endpoint_paths, scanned_at
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/asset_blacklist.py`
- responsibility: Helpers for explicit blacklist checks in the halal policy layer.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: known_quote_suffixes, pair, policy
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/asset_whitelist.py`
- responsibility: Helpers for explicit whitelist checks in the halal policy layer.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: known_quote_suffixes, pair, policy
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/contracts.py`
- responsibility: Typed contracts for the bounded halal compliance layer.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: AaoifiPairScreeningAuditReport, AaoifiPairScreeningSnapshot, AccountFeaturesAuditReport
- runtime_files_read: none
- formulas_or_derived_metrics: purification_rate = Field(..., ge=0, le=1)
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/sharia_compliance/pair_screening.py`
- responsibility: Deterministic AAOIFI pair-screening helpers.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: metadata, policy, snapshot
- outputs: load_pair_screening_snapshot
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/sharia_compliance/pair_screening_audit.py`
- responsibility: Deterministic HC-4 audit for traded pairs versus AAOIFI screening registry.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: policy, provider, scanned_at, traded_pairs
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/sharia_compliance/pair_screening_registry.py`
- responsibility: Versioned dataset provider for deterministic AAOIFI pair-screening snapshots.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: path
- outputs: load_pair_screening_registry
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/policy_audit_logger.py`
- responsibility: Append-only audit log for halal policy decisions.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/policy_loader.py`
- responsibility: YAML loader for the bounded halal policy.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: path
- outputs: load_sharia_policy
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/purification_calculator.py`
- responsibility: Deterministic purification estimates for bounded halal compliance.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: asset_received, asset_symbol, average_balance_quote, config, holding_days, policy, quantity, source, unit_price_quote
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: annual_rate = _resolve_annual_rate(calibration), purification_rate = Decimal("0") if normalized_balance == 0 else purification_amount / normalized_balance, annual_rate = _to_decimal(value)
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/sharia_alerts.py`
- responsibility: Typed alert projection for the bounded halal account audit.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: correlation_id, module, report
- outputs: build_account_feature_audit_alerts, build_pair_screening_audit_alerts
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/sharia_runtime.py`
- responsibility: Bounded runtime facade for halal trade authorization.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: gate
- duplication_notes: none

### `src/sharia_compliance/stablecoin_policy.py`
- responsibility: Helpers for stablecoin policy checks in the halal policy layer.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: known_quote_suffixes, pair, policy
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/sharia_compliance/trade_type_guard.py`
- responsibility: Bounded halal trade authorization guard.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: policy, request
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

## smoke_bootstrap_recovery

### `src/smoke_bootstrap_recovery/__init__.py`
- responsibility: smoke_bootstrap_recovery — Module 5: Bootstrap, config, recovery, state sanity.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: fd_count_provider, kill_switch_factory, kill_switch_state_dir, kill_switch_trip_reason, kill_switch_tripped_state
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: kill
- duplication_notes: none

### `src/smoke_bootstrap_recovery/bootstrap_runner.py`
- responsibility: 7.5.1 — Bootstrap Runner: launch minimal startup sequences per module.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: config, factory, module_name, module_names
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/smoke_bootstrap_recovery/config_validator.py`
- responsibility: 7.5.2 — Config Validator: verify that necessary configs are present and coherent.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: config, configs, module_name, schema
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/smoke_bootstrap_recovery/engineering_guardrails.py`
- responsibility: Executable engineering guardrails derived from CODEX_PROMPT.md.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: accepted_fingerprints, baseline_path, path, policy, policy_path, repo_root, report
- outputs: EngineeringGuardrailsReport, load_engineering_guardrails_baseline, load_engineering_guardrails_policy
- runtime_files_read: none
- formulas_or_derived_metrics: hotspots = _build_hotspots(
        ordered_violations,
        limit=policy.hotspot_limit,
    )
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/smoke_bootstrap_recovery/recovery_runner.py`
- responsibility: 7.5.3 — Recovery Runner: trigger shutdown / relaunch / verify clean state.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: backoff_factor, base_delay_s, config, factory, max_delay_s, max_retries, module_name, post_state_checker, pre_state_checker, resource_release_checker
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/smoke_bootstrap_recovery/shadow_readiness.py`
- responsibility: Shadow readiness preflight without opening the Build-11 runtime.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: build10_supervision_ready, build14_shadow_governance_ready, build9x_governed_ready, core_green, onboarding_ready, replay_import_ready
- outputs: ShadowReadinessReport
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/smoke_bootstrap_recovery/smoke_models.py`
- responsibility: 7.5.0 — Smoke Models: shared types for bootstrap, recovery, and smoke testing.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: ModuleSmokeReport, SmokeReport
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed
- duplication_notes: none

### `src/smoke_bootstrap_recovery/smoke_reporter.py`
- responsibility: 7.5.5 — Smoke Reporter: produce human-readable + machine-exploitable smoke reports.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: module_reports, report
- outputs: build_smoke_report
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: passed, passed
- duplication_notes: none

### `src/smoke_bootstrap_recovery/state_sanity_checker.py`
- responsibility: 7.5.4 — State Sanity Checker: verify that restarted state is coherent.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: overview
- status: runtime_only
- inputs: baseline_path, before_fd_count, breaker_factory, checks, fd_counter, max_total_fd_count, module_name, policy_path, repo_root, state_dir_path, trip_reason, tripped_state
- outputs: none
- runtime_files_read: engineering_guardrails_baseline.json, engineering_guardrails_policy.json, kill_switch_state.json
- formulas_or_derived_metrics: REPORT_VALUE_FOUND: sanity_checker
- thresholds_or_constants: none
- control_flags_or_gates: blocked, kill, kill, passed
- duplication_notes: none

## ui

### `src/ui/__init__.py`
- responsibility: Locked Build-10 operator UI backend surface.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/ui/complete_dashboard_artifact_sections.py`
- responsibility: Artifact-specific Build-17 dashboard sections.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: supplement
- outputs: build_artifact_challengers_section, build_artifact_champions_section, build_artifact_forecast_section, build_artifact_threshold_compare_section, build_artifact_verdict_section
- runtime_files_read: none
- formulas_or_derived_metrics: cards = tuple(
        DashboardCard(
            key=f"complete_artifact_champion_{index}",
            label=item.artifact_id or item.artifact_kind,
            value=f"{item.artifact_kind} / {item.artifact_hash[:12] or 'none'}",
            status="info",
            detail=(
                f"lineage={item.lineage_version or 'n/a'} / "
                f"promotion={item.promotion_state or 'n/a'} / "
                f"review={item.review_state or 'n/a'} / "
                f"validation={item.validation_status or 'n/a'} / "
                f"calibration={item.calibration_version or 'n/a'} / "
                f"feature_hash={item.feature_hash[:12] or 'none'}"
            ),
        )
        for index, item in enumerate(champions, start=1)
    ) or (
        DashboardCard(
            key="complete_artifact_champions_empty",
            label="Champions",
            value="not available",
            status="planned",
            detail="No active champion artifact visibility projected",
        ),
    ), cards = tuple(
        DashboardCard(
            key=f"complete_artifact_shadow_{index}",
            label=item.artifact_id or item.artifact_kind,
            value=f"{item.artifact_kind} / {item.artifact_hash[:12] or 'none'}",
            status="info",
            detail=(
                f"{item.influence_detail or 'shadow_only / non_influential'} / "
                f"lineage={item.lineage_version or 'n/a'} / "
                f"compare={_comparison_status_for_challenger(item.artifact_id, supplement.artifact_comparisons)} / "
                f"summary_ref={item.summary_ref or 'none'}"
            ),
        )
        for index, item in enumerate(challengers, start=1)
    ) or (
        DashboardCard(
            key="complete_artifact_shadow_empty",
            label="Shadow Challengers",
            value="not attached",
            status="planned",
            detail="No shadow challenger artifact projected",
        ),
    )
- thresholds_or_constants: none
- control_flags_or_gates: blocked, shadow_only
- duplication_notes: none

### `src/ui/complete_dashboard_control_plane.py`
- responsibility: Build-17 Complete dashboard control-plane section.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: supplement
- outputs: build_complete_control_plane_section
- runtime_files_read: none
- formulas_or_derived_metrics: warmup = supplement.warmup_run_summary
- thresholds_or_constants: warmup compare None
- control_flags_or_gates: blocked, eligible_to_trade, queue, queue
- duplication_notes: none

### `src/ui/complete_dashboard_view.py`
- responsibility: Build-17 Complete dashboard view over normalized monitoring truth.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: payload, supplement
- outputs: build_complete_dashboard_sections
- runtime_files_read: none
- formulas_or_derived_metrics: hard_block_rate_pct = Field(default=0.0, ge=0.0, le=100.0), ranking_rejection_rate_pct = Field(default=0.0, ge=0.0, le=100.0)
- thresholds_or_constants: payload.portfolio.ce_net compare 0
- control_flags_or_gates: gate, halt, queue, runtime_mode, suspended
- duplication_notes: none

### `src/ui/contracts.py`
- responsibility: Contracts for the locked Build-10 operator UI backend surface.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: none
- outputs: NotificationDeliveryState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/ui/light_ui_runtime.py`
- responsibility: Stateful runtime for the locked Build-10 operator UI.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: none
- outputs: LockedOperatorUiRuntimeState
- runtime_files_read: light_ui_runtime_state.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: _OPERATOR_PROJECTION_EVENT_LIMIT = 10
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/ui/operator_actions.py`
- responsibility: Governed operator actions for the locked operator UI surface.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: allowed_pairs, correlation_id, critical_alert_ids, max_light_pairs, request, resumable_pairs, runtime_mode, screen_id, timestamp_ms
- outputs: build_locked_operator_allowed_actions
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/ui/technical_dashboard_html.py`
- responsibility: Local HTML rendering for the Build-10 technical dashboard.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: additional_script, additional_sections_html, footer_notes, future_panels, generated_at, observability_text, raw_payload_json, raw_view_json, sections, source_mode, source_note, title
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: specs = {
        "technical_supervision": (
            "Build-10 Technical Supervision",
            "Build-10 state, operator surface, and live sections: System, Portfolio, Pairs, Engines, Risk, Execution, Data & Infra, Alerts.",
            "#section-build-10",
        ),
        "build9x_diagnostics": (
            "Build-9X Diagnostics",
            "Governed diagnostics, hypotheses, replay candidates, capacity and backpressure.",
            "#section-build-9x",
        ),
        "shadow_supervision": (
            "Build-11 Shadow",
            "Shadow 30-day gate, divergences, component verdicts and blocking reasons.",
            "#section-build-11-shadow",
        ),
        "micro_live_supervision": (
            "Build-12 Micro-live",
            "Probe gating, budget, guardrails and operator safing surface.",
            "#section-build-12-micro-live",
        ),
        "live_light_supervision": (
        "Build-13 Live",
            "Execution gating, readiness, Build-14 influence and operator safing surface.",
            "#section-build-13-live-light",
        ),
        "build14_supervision": (
            "Build-14 Enablers",
            "Reader-level Build-14 evidence and governed influence mode.",
            "#section-build-14-enablers",
        ),
        "artifact_import": (
            "Replay & Import",
            "Artifact manifest, lineage and import validation state.",
            "#section-replay-import",
        ),
        "observability_export": (
            "Observability Export",
            "Metrics and export detail rendered from the active dashboard payload.",
            "#detail-observability-export",
        ),
    }
- thresholds_or_constants: none
- control_flags_or_gates: gate, kill, kill, queue, queue
- duplication_notes: none

### `src/ui/technical_dashboard_view.py`
- responsibility: Technical Build-10 supervision view over the normalized backend payload.
- dashboard_relevance: runtime_only_source
- owner_page_candidate: unknown
- status: orphan_candidate
- inputs: payload
- outputs: build_technical_dashboard_view
- runtime_files_read: none
- formulas_or_derived_metrics: sections = (
        DashboardSection(
            title="Build-10",
            cards=(
                DashboardCard(
                    key="build10_state",
                    label="State",
                    value="implemented",
                    status="healthy",
                    detail="Typed payload, view, and HTML supervision pipeline are active.",
                ),
                DashboardCard(
                    key="build10_governed_rail",
                    label="Governed Rail",
                    value=f"{payload.profile.value} / {payload.runtime_mode.value}",
                    status="info",
                    detail=(
                        "Build-10 supervises the governed runtime rail and exposes the "
                        "locked operator surface."
                    ),
                ),
                DashboardCard(
                    key="build10_extensions",
                    label="Governed Extensions",
                    value=_governed_extensions_value(payload),
                    status=_governed_extensions_status(payload),
                    detail=payload.system.governed_extensions_detail,
                ),
            ),
        ),
        DashboardSection(
            title="System",
            cards=(
                DashboardCard(
                    key="headline_status",
                    label="Headline",
                    value=payload.system.headline_status,
                    status=payload.system.headline_status,
                    detail=f"{payload.alerts.active_alert_count} active alert(s)",
                ),
                DashboardCard(
                    key="runtime_mode",
                    label="Runtime",
                    value=payload.runtime_mode.value,
                    status="info",
                    detail=f"profile={payload.profile.value}",
                ),
                DashboardCard(
                    key="active_modules",
                    label="Active Modules",
                    value=str(len(payload.system.active_modules)),
                    status="healthy" if payload.system.active_modules else "planned",
                    detail=_join(payload.system.active_modules, empty="No active modules declared"),
                ),
                _engine_card(payload),
            ),
        ),
        DashboardSection(
            title="Portfolio",
            cards=(
                DashboardCard(
                    key="capital_deployed",
                    label="Capital Deployed",
                    value=f"{payload.portfolio.capital_deployed_usdt:.2f}",
                    status="info",
                    detail=f"opportunities={payload.portfolio.allocated_opportunities}",
                ),
                DashboardCard(
                    key="capacity_usage",
                    label="Capacity Usage",
                    value=(
                        f"gross={payload.portfolio.gross_capacity_used_pct:.1f}% / "
                        f"loss={payload.portfolio.loss_capacity_used_pct:.1f}%"
                    ),
                    status=(
                        "warning"
                        if payload.portfolio.loss_capacity_used_pct >= 25.0
                        else "healthy"
                    ),
                    detail=f"beta={payload.portfolio.beta_utilization:.2f}",
                ),
                DashboardCard(
                    key="ce_net",
                    label="CE Net",
                    value=f"{payload.portfolio.ce_net:.6f}",
                    status="healthy" if payload.portfolio.ce_net >= 0 else "warning",
                ),
            ),
        ),
        DashboardSection(
            title="Pairs",
            cards=_pair_cards(payload),
        ),
        DashboardSection(
            title="Engines",
            cards=_engine_cards(payload),
        ),
        DashboardSection(
            title="Engine Judgement",
            cards=_engine_judgment_cards(payload),
        ),
        DashboardSection(
            title="Risk",
            cards=_risk_cards(payload),
        ),
        DashboardSection(
            title="Execution",
            cards=_execution_cards(payload),
        ),
        DashboardSection(
            title="Data & Infra",
            cards=_infra_cards(payload),
        ),
        _account_user_data_section(payload),
        DashboardSection(
            title="Build-9 Meta",
            cards=(
                DashboardCard(
                    key="dtr_summary",
                    label="DTR Summary",
                    value=f"coverage={payload.build9_meta.dtr_coverage:.2%}",
                    status=payload.build9_meta.dtr_status,
                    detail=f"stale_pairs={payload.alerts.stale_pair_count}",
                ),
                DashboardCard(
                    key="cra_summary",
                    label="CRA Summary",
                    value=f"sterilization={payload.build9_meta.cra_sterilization_rate:.2%}",
                    status=payload.build9_meta.cra_status,
                    detail=f"alerts={payload.build9_meta.cra_alert_count}",
                ),
                DashboardCard(
                    key="break_even_summary",
                    label="Break-even",
                    value=payload.build9_meta.break_even_state,
                    status=payload.build9_meta.break_even_status,
                    detail=_join(
                        payload.build9_meta.break_even_drift_scopes,
                        empty="No drift scope",
                    ),
                ),
                DashboardCard(
                    key="edge_summary",
                    label="Edge Summary",
                    value=(
                        f"credible={payload.build9_meta.edge_credible_count} / "
                        f"degraded={payload.build9_meta.edge_degraded_count} / "
                        f"surveillance={payload.build9_meta.edge_surveillance_count}"
                    ),
                    status=payload.build9_meta.edge_status,
                ),
            ),
        ),
        DashboardSection(
            title="Build-9X",
            cards=(
                DashboardCard(
                    key="diagnostics_recent",
                    label="Diagnostics",
                    value=str(payload.build9x.diagnostics_count),
                    status=payload.build9x.status,
                    detail=payload.build9x.diagnostics_summary,
                ),
                DashboardCard(
                    key="hypotheses_open",
                    label="Open Hypotheses",
                    value=str(payload.build9x.open_hypotheses),
                    status=(
                        "warning"
                        if payload.build9x.open_hypotheses > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=f"total={payload.build9x.total_hypotheses}",
                ),
                DashboardCard(
                    key="near_miss_candidates",
                    label="Near Miss / Candidates",
                    value=(
                        f"near_miss={payload.build9x.near_miss_count} / "
                        f"replay={payload.build9x.replay_candidate_count}"
                    ),
                    status=(
                        "warning"
                        if payload.build9x.near_miss_count > 0
                        or payload.build9x.replay_candidate_count > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                ),
                DashboardCard(
                    key="enrichment_mapping",
                    label="Enrichment Mapping",
                    value=(
                        f"mapped={payload.build9x.enrichment_hypothesis_count} / "
                        f"replay={payload.build9x.expected_replay_evidence_count} / "
                        f"shadow={payload.build9x.expected_shadow_evidence_count}"
                    ),
                    status=(
                        "warning"
                        if payload.build9x.enrichment_hypothesis_count > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        f"{payload.build9x.enrichment_summary} / "
                        f"family={payload.build9x.latest_enrichment_signal_family or 'n/a'}"
                    ),
                ),
                DashboardCard(
                    key="memory_review",
                    label="Memory / Review",
                    value=(
                        f"records={payload.build9x.memory_record_count} / "
                        f"export={'ready' if payload.build9x.review_export_ready else 'none'}"
                    ),
                    status=(
                        "healthy"
                        if payload.build9x.review_export_ready
                        else "info"
                        if payload.build9x.memory_record_count > 0
                        else "planned"
                    ),
                    detail=payload.build9x.latest_memory_summary,
                ),
                DashboardCard(
                    key="capacity_backpressure",
                    label="Capacity / Backpressure",
                    value=(
                        f"queue={payload.build9x.learning_queue_depth} / "
                        f"mode={payload.build9x.learning_capture_mode}"
                    ),
                    status=(
                        "critical"
                        if payload.build9x.review_blocked_due_to_incomplete_data
                        else "warning"
                        if payload.build9x.learning_backlog_state != "normal"
                        or payload.build9x.learning_backpressure_active
                        else "healthy"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        f"backlog={payload.build9x.learning_backlog_state} / "
                        f"oldest={payload.build9x.learning_queue_oldest_age_ms}ms / "
                        f"unprocessed={payload.build9x.learning_unprocessed_items_count}"
                    ),
                ),
                DashboardCard(
                    key="worker_budget",
                    label="Worker Budget",
                    value=(
                        f"cpu={payload.build9x.learning_worker_cpu_pct:.1f}% / "
                        f"rss={payload.build9x.learning_worker_rss_mb:.1f}MB"
                    ),
                    status=(
                        "critical"
                        if payload.build9x.learning_log_loss_total > 0
                        else "warning"
                        if payload.build9x.learning_export_failures_total > 0
                        or payload.build9x.learning_write_latency_ms > 0.0
                        else "healthy"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        f"write={payload.build9x.learning_write_latency_ms:.1f}ms / "
                        f"export_fail={payload.build9x.learning_export_failures_total} / "
                        f"log_loss={payload.build9x.learning_log_loss_total}"
                    ),
                ),
            ),
        ),
        DashboardSection(
            title="Build-11 Shadow",
            cards=(
                DashboardCard(
                    key="shadow_run_state",
                    label="Run State",
                    value=payload.shadow.run_state,
                    status=payload.shadow.status,
                    detail=(
                        f"truth={payload.shadow.truth_set_ref or 'n/a'} / "
                        f"validation={payload.shadow.validation_set_ref or 'n/a'}"
                    ),
                ),
                DashboardCard(
                    key="shadow_verdict",
                    label="Gating Verdict",
                    value=payload.shadow.verdict,
                    status=payload.shadow.status,
                    detail=(
                        "manual review required"
                        if payload.shadow.manual_review_required
                        else "manual review not required"
                    ),
                ),
                DashboardCard(
                    key="shadow_divergences",
                    label="Divergences",
                    value=(
                        f"blocking={payload.shadow.blocking_comparison_count} / "
                        f"divergent={payload.shadow.divergent_comparison_count} / "
                        f"total={payload.shadow.total_comparison_count}"
                    ),
                    status=(
                        "critical"
                        if payload.shadow.blocking_comparison_count > 0
                        else "warning"
                        if payload.shadow.divergent_comparison_count > 0
                        else payload.shadow.status
                    ),
                ),
                DashboardCard(
                    key="shadow_candidate_state",
                    label="Candidate State",
                    value=(
                        f"diagnostics={payload.shadow.build9x_diagnostics_count} / "
                        f"hypotheses={payload.shadow.open_hypotheses} / "
                        f"replay={payload.shadow.replay_candidate_count}"
                    ),
                    status=(
                        "warning"
                        if payload.shadow.manual_review_required
                        else "info"
                        if payload.shadow.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        "review export ready"
                        if payload.shadow.review_export_ready
                        else "review export missing"
                    ),
                ),
                DashboardCard(
                    key="shadow_import_lineage",
                    label="Import Lineage",
                    value=payload.shadow.import_lineage_version,
                    status=(
                        "healthy"
                        if payload.shadow.import_lineage_version not in {"", "n/a"}
                        else "critical"
                        if payload.shadow.status != "planned"
                        else "planned"
                    ),
                    detail=payload.shadow.import_artifact_id or "No import artifact id",
                ),
                DashboardCard(
                    key="shadow_execution_telemetry",
                    label="Execution Telemetry",
                    value=payload.shadow.execution_telemetry_status,
                    status=_shadow_execution_telemetry_card_status(payload),
                    detail=_shadow_execution_telemetry_card_detail(payload),
                ),
                DashboardCard(
                    key="shadow_telegram_alerts",
                    label="Telegram Alerts",
                    value=payload.shadow.telegram_alert_delivery_status,
                    status=_shadow_telegram_alert_card_status(payload),
                    detail=_shadow_telegram_alert_card_detail(payload),
                ),
                DashboardCard(
                    key="shadow_execution_bootstrap",
                    label="Execution Bootstrap",
                    value=(
                        f"{payload.shadow.execution_runtime_bootstrap_status}"
                        f"@{payload.shadow.execution_runtime_bootstrap_source}"
                    ),
                    status=_shadow_execution_bootstrap_card_status(payload),
                    detail=_shadow_execution_bootstrap_card_detail(payload),
                ),
                DashboardCard(
                    key="shadow_execution_projection",
                    label="Execution Projection",
                    value=(
                        f"{payload.shadow.execution_runtime_projection_status}"
                        f"@{payload.shadow.execution_runtime_projection_source}"
                    ),
                    status=_shadow_execution_projection_card_status(payload),
                    detail=_shadow_execution_projection_card_detail(payload),
                ),
                DashboardCard(
                    key="shadow_regime_lite_safing",
                    label="Regime Safing",
                    value=payload.shadow.regime_lite_safing.severity,
                    status=_shadow_regime_lite_safing_card_status(payload),
                    detail=_shadow_regime_lite_safing_card_detail(payload),
                ),
                DashboardCard(
                    key="shadow_info_stress",
                    label="Info Stress",
                    value=(
                        f"{payload.shadow.info_stress_governance_status}"
                        f"@{payload.shadow.info_stress_level}"
                    ),
                    status=_shadow_info_stress_card_status(payload),
                    detail=_shadow_info_stress_card_detail(payload),
                ),
                DashboardCard(
                    key="shadow_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.shadow.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.shadow.blocking_reasons
                        else "healthy"
                        if payload.shadow.status == "healthy"
                        else payload.shadow.status
                    ),
                    detail=_join(payload.shadow.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Build-12 Micro-live",
            cards=(
                DashboardCard(
                    key="micro_live_run_state",
                    label="Run State",
                    value=payload.micro_live.run_state,
                    status=payload.micro_live.status,
                    detail=f"shadow_run={payload.micro_live.shadow_run_id or 'n/a'}",
                ),
                DashboardCard(
                    key="micro_live_verdict",
                    label="Probe Verdict",
                    value=payload.micro_live.verdict,
                    status=payload.micro_live.status,
                    detail=f"shadow_verdict={payload.micro_live.shadow_verdict}",
                ),
                DashboardCard(
                    key="micro_live_budget",
                    label="Budget",
                    value=(
                        f"approved={payload.micro_live.approved_total_notional_usdt:.2f} / "
                        f"pair={payload.micro_live.approved_pair_notional_usdt:.2f}"
                    ),
                    status=payload.micro_live.status,
                    detail=f"requested={payload.micro_live.requested_total_notional_usdt:.2f}",
                ),
                DashboardCard(
                    key="micro_live_surface",
                    label="Probe Surface",
                    value=(
                        f"pairs={len(payload.micro_live.planned_pairs)} / "
                        f"engines={len(payload.micro_live.planned_engines)} / "
                        f"orders={payload.micro_live.order_probe_limit}"
                    ),
                    status=(
                        "info"
                        if payload.micro_live.planned_pairs or payload.micro_live.planned_engines
                        else payload.micro_live.status
                    ),
                    detail=_join(payload.micro_live.planned_pairs, empty="No probe surface planned"),
                ),
                DashboardCard(
                    key="micro_live_guardrails",
                    label="Guardrails",
                    value=(
                        f"obs={'ready' if payload.micro_live.observability_ready else 'missing'} / "
                        f"halt={'ready' if payload.micro_live.halt_ready else 'missing'} / "
                        f"onboarding={'ready' if payload.micro_live.onboarding_ready else 'missing'}"
                    ),
                    status=(
                        "healthy"
                        if payload.micro_live.observability_ready
                        and payload.micro_live.halt_ready
                        and payload.micro_live.onboarding_ready
                        else "critical"
                        if payload.micro_live.status != "planned"
                        else "planned"
                    ),
                    detail=payload.micro_live.import_lineage_version,
                ),
                DashboardCard(
                    key="micro_live_safing_request",
                    label="Safing Request",
                    value=(
                        f"{payload.micro_live.operator_safing_action}"
                        + (
                            f" -> {payload.micro_live.operator_safing_target_runtime_mode}"
                            if payload.micro_live.operator_safing_target_runtime_mode
                            else ""
                        )
                        if payload.micro_live.operator_safing_action
                        else "none"
                    ),
                    status=(
                        "critical"
                        if payload.micro_live.operator_safing_action == "set_halted"
                        else "warning"
                        if payload.micro_live.operator_safing_action
                        else "info"
                    ),
                    detail=(
                        payload.micro_live.operator_safing_reason
                        or "No manual safing request projected"
                    ),
                ),
                DashboardCard(
                    key="micro_live_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.micro_live.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.micro_live.blocking_reasons
                        else "healthy"
                        if payload.micro_live.status == "healthy"
                        else payload.micro_live.status
                    ),
                    detail=_join(payload.micro_live.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Build-13 Live",
            cards=(
                DashboardCard(
                    key="live_light_run_state",
                    label="Run State",
                    value=payload.live_light.run_state,
                    status=payload.live_light.status,
                    detail=f"micro_live_run={payload.live_light.micro_live_run_id or 'n/a'}",
                ),
                DashboardCard(
                    key="live_light_verdict",
                    label="Execution Verdict",
                    value=payload.live_light.verdict,
                    status=payload.live_light.status,
                    detail=f"micro_live_verdict={payload.live_light.micro_live_verdict}",
                ),
                DashboardCard(
                    key="live_light_budget",
                    label="Budget",
                    value=(
                        f"approved={payload.live_light.approved_total_notional_usdt:.2f} / "
                        f"pair={payload.live_light.approved_pair_notional_usdt:.2f}"
                    ),
                    status=payload.live_light.status,
                    detail=(
                        f"requested={payload.live_light.requested_total_notional_usdt:.2f} / "
                        f"build14={payload.live_light.build14_action}@{payload.live_light.build14_recommended_budget_factor:.2f}"
                    ),
                ),
                DashboardCard(
                    key="live_light_surface",
                    label="Execution Surface",
                    value=(
                        f"pairs={len(payload.live_light.planned_pairs)} / "
                        f"engines={len(payload.live_light.planned_engines)} / "
                        f"orders={payload.live_light.execution_order_limit}"
                    ),
                    status=(
                        "info"
                        if payload.live_light.planned_pairs or payload.live_light.planned_engines
                        else payload.live_light.status
                    ),
                    detail=_join(payload.live_light.planned_pairs, empty="No execution surface planned"),
                ),
                DashboardCard(
                    key="live_light_readiness",
                    label="Readiness",
                    value=(
                        f"obs={'ready' if payload.live_light.observability_ready else 'missing'} / "
                        f"halt={'ready' if payload.live_light.halt_ready else 'missing'} / "
                        f"exec={'ready' if payload.live_light.execution_ready else 'missing'} / "
                        f"broker={'ready' if payload.live_light.broker_ready else 'missing'} / "
                        f"exchange={'ready' if payload.live_light.exchange_ready else 'missing'}"
                    ),
                    status=(
                        "healthy"
                        if payload.live_light.observability_ready
                        and payload.live_light.halt_ready
                        and payload.live_light.execution_ready
                        and payload.live_light.broker_ready
                        and payload.live_light.exchange_ready
                        else "critical"
                        if payload.live_light.status != "planned"
                        else "planned"
                    ),
                    detail=payload.live_light.build14_summary or payload.live_light.import_lineage_version,
                ),
                DashboardCard(
                    key="live_light_safing_request",
                    label="Safing Request",
                    value=(
                        f"{payload.live_light.operator_safing_action}"
                        + (
                            f" -> {payload.live_light.operator_safing_target_runtime_mode}"
                            if payload.live_light.operator_safing_target_runtime_mode
                            else ""
                        )
                        if payload.live_light.operator_safing_action
                        else "none"
                    ),
                    status=(
                        "critical"
                        if payload.live_light.operator_safing_action == "set_halted"
                        else "warning"
                        if payload.live_light.operator_safing_action
                        else "info"
                    ),
                    detail=(
                        payload.live_light.operator_safing_reason
                        or "No manual safing request projected"
                    ),
                ),
                DashboardCard(
                    key="live_light_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.live_light.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.live_light.blocking_reasons
                        else "healthy"
                        if payload.live_light.status == "healthy"
                        else payload.live_light.status
                    ),
                    detail=_join(payload.live_light.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Build-14 Enablers",
            cards=(
                DashboardCard(
                    key="build14_mode",
                    label="Mode",
                    value=f"{payload.build14.influence_mode} / {payload.build14.action}",
                    status=payload.build14.status,
                    detail=f"severity={payload.build14.severity}",
                ),
                DashboardCard(
                    key="build14_readers",
                    label="Readers",
                    value=(
                        f"count={len(payload.build14.reader_projections)} / "
                        f"toxicity={payload.build14.market_toxicity_status} ({payload.build14.market_toxicity_value:.2f}) / "
                        f"fragility={payload.build14.execution_fragility_status} ({payload.build14.execution_fragility_value:.2f})"
                    ),
                    status=(
                        "critical"
                        if payload.build14.severity == "critical"
                        else "warning"
                        if payload.build14.severity == "elevated"
                        else payload.build14.status
                    ),
                    detail=(
                        f"{payload.build14.summary} / {_build14_readers_summary(payload)}"
                        if payload.build14.reader_projections
                        else payload.build14.summary
                    ),
                ),
                DashboardCard(
                    key="build14_candidate_effect",
                    label="Candidate Effect",
                    value=payload.build14.candidate_effect,
                    status=payload.build14.status,
                    detail=(
                        f"penalty={payload.build14.confidence_penalty_weight:.2f} / "
                        f"budget_factor={payload.build14.recommended_budget_factor:.2f}"
                    ),
                ),
                DashboardCard(
                    key="build14_guardrails",
                    label="Guardrails",
                    value=(
                        "review_only"
                        if payload.build14.requires_manual_review
                        else "bounded_modulation"
                        if payload.build14.influence_mode == "limited_influence"
                        else "shadow_enabled"
                        if payload.build14.influence_mode == "shadow_enabled"
                        else "read_only"
                    ),
                    status=(
                        "warning"
                        if payload.build14.requires_manual_review
                        else "healthy"
                        if payload.build14.status in {"healthy", "info"}
                        else payload.build14.status
                    ),
                    detail=_join(payload.build14.reason_codes, empty="No Build-14 reason code"),
                ),
            )
            + _build14_reader_cards(payload),
        ),
        DashboardSection(
            title="Artifact Hooks",
            cards=_runtime_hook_bridge_cards(payload),
        ),
        _artifact_visibility_section(payload),
        _operator_controls_section(payload),
        DashboardSection(
            title="Replay & Import",
            cards=(
                DashboardCard(
                    key="artifact_manifest",
                    label="Artifact Manifest",
                    value=payload.replay_import.artifact_id,
                    status=payload.replay_import.status,
                    detail=payload.replay_import.artifact_kind,
                ),
                DashboardCard(
                    key="lineage_version",
                    label="Lineage",
                    value=payload.replay_import.lineage_version,
                    status="info" if payload.replay_import.artifact_id != "none" else "planned",
                    detail=payload.replay_import.lifecycle_state,
                ),
                DashboardCard(
                    key="validation_status",
                    label="Validation",
                    value=payload.replay_import.validation_status,
                    status=(
                        "healthy"
                        if payload.replay_import.validation_status == "accepted"
                        else "warning"
                        if payload.replay_import.validation_status != "not_run"
                        else "planned"
                    ),
                    detail=payload.replay_import.review_state,
                ),
                DashboardCard(
                    key="validation_reasons",
                    label="Validation Reasons",
                    value=str(len(payload.replay_import.rejection_reasons)),
                    status=(
                        "warning"
                        if payload.replay_import.rejection_reasons
                        else "healthy"
                        if payload.replay_import.validation_status == "accepted"
                        else "planned"
                    ),
                    detail=_join(
                        payload.replay_import.rejection_reasons,
                        empty="No validation rejection",
                    ),
                ),
                DashboardCard(
                    key="compatibility_policy",
                    label="Compatibility Policy",
                    value=payload.replay_import.compatibility_status,
                    status=_replay_compatibility_card_status(payload),
                    detail=_replay_compatibility_card_detail(payload),
                ),
                DashboardCard(
                    key="signature_policy",
                    label="Signature Policy",
                    value=payload.replay_import.signature_check_status,
                    status=_replay_signature_card_status(payload),
                    detail=_replay_signature_card_detail(payload),
                ),
                DashboardCard(
                    key="conflict_policy",
                    label="Conflict Policy",
                    value=payload.replay_import.conflict_resolution_mode or "not_configured",
                    status=_replay_conflict_card_status(payload),
                    detail=_replay_conflict_card_detail(payload),
                ),
                DashboardCard(
                    key="registry_policy",
                    label="Registry Policy",
                    value=payload.replay_import.registry_atomicity_mode or "not_configured",
                    status=_replay_registry_card_status(payload),
                    detail=_replay_registry_card_detail(payload),
                ),
            ),
        ),
        DashboardSection(
            title="Alerts",
            cards=(
                DashboardCard(
                    key="active_alerts",
                    label="Active Alerts",
                    value=str(payload.alerts.active_alert_count),
                    status=payload.alerts.headline_status,
                    detail=_join(payload.alerts.alert_ids, empty="No active alert"),
                ),
                DashboardCard(
                    key="backlog_stale",
                    label="Backlog / Stale",
                    value=(
                        f"backlog={payload.alerts.queue_backlog} / "
                        f"stale={payload.alerts.stale_pair_count}"
                    ),
                    status=payload.alerts.backlog_stale_status,
                    detail=_join(payload.alerts.stale_pairs, empty="No stale pair"),
                ),
                DashboardCard(
                    key="infra_guardrails",
                    label="Infra Guardrails",
                    value=(
                        f"hwm={payload.alerts.backlog_high_water_mark} / "
                        f"drop={payload.alerts.drop_rate_pct:.1f}% / "
                        f"spikes={payload.alerts.stale_spike_count}"
                    ),
                    status=(
                        "critical"
                        if payload.alerts.kill_switch_active
                        else "warning"
                        if (
                            payload.alerts.backlog_high_water_mark > payload.alerts.queue_backlog
                            or payload.alerts.drop_rate_pct > 5.0
                            or payload.alerts.recovery_retry_count > 0
                            or payload.alerts.stale_spike_count > 0
                        )
                        else "healthy"
                    ),
                    detail=(
                        f"retry={payload.alerts.recovery_retry_count} / "
                        f"kill={'active' if payload.alerts.kill_switch_active else 'inactive'}"
                    ),
                ),
                DashboardCard(
                    key="loss_drift",
                    label="Loss / Drift",
                    value=(
                        f"dtr={payload.alerts.dtr_loss_count} / "
                        f"log={payload.alerts.log_loss_count} / "
                        f"drift={payload.alerts.break_even_drift_scope_count}"
                    ),
                    status=payload.alerts.loss_drift_status,
                ),
                DashboardCard(
                    key="observability_surface",
                    label="Observability",
                    value=(
                        f"persisted={len(payload.alerts.persisted_metric_names)} / "
                        f"volatile={len(payload.alerts.volatile_metric_names)}"
                    ),
                    status=(
                        "warning"
                        if payload.alerts.volatile_metric_names
                        and (
                            payload.alerts.backlog_high_water_mark > 0
                            or payload.alerts.drop_rate_pct > 0.0
                            or payload.alerts.stale_spike_count > 0
                            or payload.alerts.recovery_retry_count > 0
                            or payload.alerts.kill_switch_active
                        )
                        else "info"
                    ),
                    detail=(
                        "volatile: "
                        + _join(payload.alerts.volatile_metric_names, empty="none")
                    ),
                ),
                DashboardCard(
                    key="operator_events",
                    label="Operator Events",
                    value=str(payload.alerts.operator_runtime.event_count),
                    status=(
                        "warning"
                        if payload.alerts.operator_runtime.event_count > 1
                        else "info"
                    ),
                    detail=(
                        payload.alerts.operator_runtime.last_error
                        or payload.alerts.operator_runtime.latest_event_message
                        or "No operator event projected"
                    ),
                ),
                DashboardCard(
                    key="operator_notifications",
                    label="Operator Notifications",
                    value=(
                        f"pending={payload.alerts.operator_runtime.pending_notification_count} / "
                        f"ack={payload.alerts.operator_runtime.acknowledged_notification_count}"
                    ),
                    status=(
                        "critical"
                        if payload.alerts.operator_runtime.pending_notification_count > 0
                        and payload.alerts.headline_status == "critical"
                        else "warning"
                        if payload.alerts.operator_runtime.pending_notification_count > 0
                        else "healthy"
                        if payload.alerts.operator_runtime.acknowledged_notification_count > 0
                        else "info"
                    ),
                    detail=_join(
                        payload.alerts.operator_runtime.pending_notification_alert_ids,
                        empty=(
                            f"latest ack: {payload.alerts.operator_runtime.latest_acknowledged_alert_id}"
                            if payload.alerts.operator_runtime.latest_acknowledged_alert_id
                            else "No notification projected"
                        ),
                    ),
                ),
            ),
        ),
    ), detail = f"{detail} / drawdown={engine.drawdown_state_code}"
- thresholds_or_constants: payload.portfolio.ce_net compare 0
- control_flags_or_gates: blocked, halt, kill, kill, queue, queue, review_only, runtime_mode, suspended
- duplication_notes: none

### `src/ui/ui_light_locked.py`
- responsibility: Projection layer for the locked Build-10 operator UI.
- dashboard_relevance: no_direct_dashboard_evidence
- owner_page_candidate: unknown
- status: insufficient_evidence
- inputs: payload
- outputs: build_locked_operator_dashboard_view
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: payload.ce_net compare 0
- control_flags_or_gates: queue, runtime_mode, suspended
- duplication_notes: none

## venue_adapters

### `src/venue_adapters/__init__.py`
- responsibility: Venue adapters for concrete exchange integrations.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/__init__.py`
- responsibility: Bounded Binance Spot adapter surfaces for P0-1.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/account_feature_provider.py`
- responsibility: Bounded read-only Binance provider for weekly halal account-feature audits.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/bootstrap.py`
- responsibility: Bootstrap helpers for building the bounded Binance Spot execution adapter.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: clock_ms, config, credentials, http_client, user_data_socket_factory, user_data_stream_enabled, venue_constraint_provider
- outputs: build_binance_spot_execution_adapter
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/credential_loader.py`
- responsibility: Credential loaders for Binance Spot with runtime-safe policy seams.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: runtime_only
- inputs: allow_env_local_replay, allow_plaintext_local_replay, key_path, path, payload, prefix, runtime_mode
- outputs: load_binance_credentials, load_binance_credentials_for_runtime, load_binance_credentials_from_env, load_binance_credentials_from_env_for_runtime, load_binance_credentials_from_file, load_testnet_credentials
- runtime_files_read: .sealed.json
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: runtime_mode
- duplication_notes: none

### `src/venue_adapters/binance_spot/error_classifier.py`
- responsibility: Bounded Binance Spot order API error classification.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: payload
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/execution_adapter.py`
- responsibility: Bounded Binance Spot execution adapter for the Build-3 runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/order_translator.py`
- responsibility: Translate internal execution intents into bounded Binance Spot order requests.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: engine_id, intent, intent_id, pair_id
- outputs: build_binance_client_order_id
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/orderbook_manager.py`
- responsibility: Snapshot + delta replay manager for Binance Spot order-book streams.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: BinanceDepthSnapshot, OrderBookSyncState
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/rate_limiter.py`
- responsibility: Bounded Binance REST quota tracking with header sync and 429 backoff.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: method, params, path
- outputs: BinanceApiRateLimiterSnapshot
- runtime_files_read: none
- formulas_or_derived_metrics: limit = _coerce_positive_int(request_params.get("limit"), fallback=100)
- thresholds_or_constants: limit compare 100, limit compare 500
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/rest_client.py`
- responsibility: Bounded async REST client for Binance Spot.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: none
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: rate_limits_raw = payload.get("rateLimits", []), rate_limits = [], payload = await self._request_json(
            "/api/v3/depth",
            params={"symbol": pair.upper(), "limit": str(limit)},
        )
- thresholds_or_constants: limit compare 0
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/time_sync.py`
- responsibility: Clock synchronization helpers for Binance Spot.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: calibration_root, config, path
- outputs: load_binance_adapter_config
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/user_data_events.py`
- responsibility: Bounded authenticated Binance user-data event parsing for execution runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: payload, payloads
- outputs: none
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/user_data_ws_client.py`
- responsibility: Bounded authenticated Binance user-data websocket source for execution runtime.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: credentials, recv_window_ms, request_id, timestamp_ms
- outputs: build_user_data_subscribe_request
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: none
- control_flags_or_gates: none
- duplication_notes: none

### `src/venue_adapters/binance_spot/ws_client.py`
- responsibility: Bounded websocket depth client with explicit stale/resync state.
- dashboard_relevance: indirect_dashboard_source
- owner_page_candidate: shadow
- status: coded_not_displayed
- inputs: rest_client, snapshot_limit
- outputs: build_rest_depth_snapshot_provider
- runtime_files_read: none
- formulas_or_derived_metrics: none
- thresholds_or_constants: raw_message_seen = False, raw_messages_seen = 0, raw_messages_seen = 1
- control_flags_or_gates: none
- duplication_notes: none
