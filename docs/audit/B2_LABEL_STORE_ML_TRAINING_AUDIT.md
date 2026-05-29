# B2 Label Store ML Training Audit

Status: audit/reporting only.

This audit verifies whether a B2 label store contains scientifically usable
expected-edge ML training rows:

- X: ex-ante `feature_values` available at or before `decision_timestamp_ms`.
- y: post-decision replay labels such as executed net return, MFE/MAE, or
  forward returns.
- provenance: A2 feature ref, B1 candidate ref, B2 replay ref, and raw/post
  window refs.
- governance: target-policy consistency and train/validation/backtest date
  separation.

The audit writes these run-local reports under `<b2_run>/reports/`:

- `b2_label_store_ml_training_audit.json`
- `a2_b2_feature_label_alignment_report.json`
- `ml_training_label_fidelity_report.json`
- `ml_target_policy_consistency_report.json`
- `ml_training_row_eligibility_report.json`
- `ml_feature_label_leakage_report.json`
- `ml_train_eval_window_overlap_report.json`

Verdict rules are strict:

- post-decision fields such as `mfe_bps`, `mae_bps`, forward returns, realized
  PnL, or trade success are blocked if they appear in `feature_values`;
- labels can be research-only when they are forward-return/proxy/partial, but
  they are not promotion truth;
- `B2_REPLAY_EXECUTION_AWARE_NET_EDGE.v1` is only matched by execution-aware
  replay labels with ready execution fidelity;
- overlap or unproven date separation prevents scientific training readiness;
- missing post-window or missing provenance is explicit and never default-filled.

The audit does not modify engines, thresholds, candidates, replay records, or
trade decisions.
