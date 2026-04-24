## 2026-04-23 - RegimeDetector shadow audit loop and final audit report

### Repo-truth
- The RegimeDetector feature-profile work is no longer limited to training-profile selection.
- The repo now contains a closed audit loop from:
  - VPS shadow evidence export
  - to IA Lab import and root-cause diagnosis
  - to triple-profile comparison
  - to one final joined audit-ready report

### Implemented seams
- VPS shadow audit bundle contracts now exist in:
  - `src/interface_contracts/regime_detector_shadow_audit_contracts.py`
- Deterministic VPS aggregation now exists in:
  - `src/monitoring/regime_detector_shadow_audit_bundle.py`
- IA Lab import and diagnosis now exist in:
  - `src/local_replay_runtime/regime_detector_shadow_audit_diagnosis.py`
- Triple-profile comparator now exists in:
  - `src/local_replay_runtime/regime_detector_profile_comparison.py`
- Final joined audit report now exists in:
  - `src/local_replay_runtime/regime_detector_final_audit_report.py`

### What the VPS now exports
- The VPS still does not train, fit, recalibrate, or choose side.
- The VPS now exports a bounded typed shadow-evidence bundle carrying:
  - `artifact_hash`
  - `feature_hash_at_runtime`
  - `feature_set_version`
  - `feature_profile`
  - `pair`
  - `window_start_ns`
  - `window_end_ns`
  - `sample_count`
  - `prediction_count`
  - `insufficient_data_count`
  - `runtime_stale_count`
  - `schema_match_status`
  - metric summaries for transition / stability / toxicity
  - `observation_coverage_ratio_summary`
  - `duration_bucket_counts`
  - `artifact_status_counts`
  - `signal_status_counts`
  - `reason_code_counts`
  - `shadow_metrics`
  - `blocking_reasons`

### What IA Lab now diagnoses
- IA Lab can now load one VPS shadow bundle from disk and diagnose it against the expected artifact.
- Supported diagnosis findings include:
  - `artifact_hash_mismatch`
  - `feature_hash_mismatch`
  - `feature_profile_mismatch`
  - `feature_set_version_mismatch`
  - `artifact_schema_mismatch`
  - `pair_not_in_universe`
  - `shadow_drift_high`
  - `runtime_stale_present`
  - `coverage_too_low`
  - `insufficient_data_dominant`
  - `no_active_predictions`
- The diagnosis remains bounded and non-directional.

### What the triple comparison now does
- Local IA Lab can now run the same governed dataset through:
  - `core_v1`
  - `extended_v2`
  - `full_v2`
- The comparison is controlled by:
  - same dataset
  - same calibration version
  - same seed
  - same pair scope
  - same label config
- Only the feature profile differs.
- The comparison report now resolves:
  - ranked entries
  - `winner_profile`
  - `recommended_default_profile`
  - `recommendation`
  - `full_v2_disposition`

### What the final joined report now resolves
- The final report joins:
  - the triple-profile comparison
  - the optional VPS shadow bundle
  - the IA Lab diagnosis of the uploaded artifact
- It now answers, in one typed object:
  - which profile won in IA Lab
  - which profile is the recommended default
  - which profile was actually uploaded on VPS
  - whether the uploaded profile matches the IA Lab default
  - whether the uploaded artifact is healthy, cautionary, or blocked
  - what the next action should be

### Final recommendation states now present
- Without a VPS bundle:
  - `collect_vps_shadow_audit_bundle`
- With a blocked diagnosis:
  - `investigate_uploaded_artifact_root_cause`
- With a healthy bundle but a non-default uploaded profile:
  - `uploaded_profile_differs_from_lab_default`
- With a healthy bundle aligned with IA Lab:
  - `uploaded_profile_matches_lab_recommendation`

### Governance preserved
- No directional VPS regime semantics were added.
- No `direction_up_300s_fee_safe`.
- No side mutation.
- No new engine outside A/B/C/D.
- VPS remains artifact-only and shadow-only for this slice.
- `extended_v2` remains the default candidate profile unless the comparison report justifies otherwise.
- `full_v2` is still not auto-promoted to default just because it exists.

### Proof
- Targeted contracts / monitoring / IA Lab audit tests are present for:
  - shadow audit contracts
  - shadow audit bundle aggregation
  - shadow audit diagnosis
  - triple-profile comparison
  - final joined audit report
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python -m py_compile` with local `PYTHONPYCACHEPREFIX`
  - `PASS`

### Verification note
- A direct local pytest rerun in this desktop environment hit Windows permission issues around temporary directories for two disk-roundtrip tests using `tmp_path`.
- That environment issue does not change the repo-truth of the implemented seams above.
- Status claims in this note are based on:
  - code inspection of the current seams
  - the targeted test suite content
  - DAG and guardrail proof

### Status
- RegimeDetector shadow audit export bundle: implemented
- IA Lab import + diagnosis: implemented
- Triple-profile comparison: implemented
- Final joined audit report: implemented
- Persistent operator-facing export of the final joined report bundle: not yet implemented in this note
