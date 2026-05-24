# F16-C Post-Execution Audit

Source doc locked at write time:
`docs/production_deployment_plan/update_audit/2026-05-23_F16_C_FEATURE_GOVERNANCE_FULL.md`

Audit date: `2026-05-23`
Audit mode: deep doc-to-code verification, proof execution, risk review
Scope: F16-C pillars plus the later backtest F16 parity addendum

## Executed Proof Slots

- `pytest_pilier_1`: `32 passed`
  - `tests/test_local_replay_runtime/test_expected_edge_training_extended_features.py`
  - `tests/test_local_replay_runtime/test_label_store_row_v3_migration.py`
  - `tests/test_local_replay_runtime/test_bridge_capture_extended.py`
- `pytest_pilier_2`: `18 passed`
  - `tests/test_local_replay_runtime/test_feature_promotion_registry.py`
  - `tests/test_local_replay_runtime/test_feature_ablation_orchestrator.py`
- `pytest_pilier_3`: `8 passed`
  - `tests/cockpit/test_lab_feature_picker.py`
- `pytest_regression_local_replay`: `646 passed, 10 failed, 9 skipped`
  - `tests/test_local_replay_runtime/test_strategy_ladder_data_factory.py` -> 5 failures
  - `tests/test_local_replay_runtime/test_batch1_size_governance.py` -> 2 failures
  - `tests/test_local_replay_runtime/test_f16_b_microstructure_persistence.py` -> 3 failures
- `pytest_regression_cockpit`: `284 passed, 4 failed`
  - `test_patch6_dashboard_blocks_frozen_ml_overlay_for_data_factory`
  - `test_command_builder_hard_guard_rejects_path_in_pairs`
  - `test_pair_mismatch_preview_is_not_launchable`
  - `test_phase_a1_preview_refresh_clears_stale_workflow_flags_and_blockers`
- `dag_validator`: `FAIL`
  - 6 unauthorized imports `cockpit -> local_replay_runtime`
  - 1 unauthorized import `local_replay_runtime -> sharia_compliance`
  - 1 undeclared dynamic import warning in `strategy_ladder_multi_pair_expected_edge_training.py`
- `guardrails`: `FAIL`
  - repo-wide `new_violations=370`
  - touched F16/backtest files: `134`
  - touched source files only: `40`
  - dominant touched-source rules:
    - `FUNCTION_TOO_LONG=23`
    - `FILE_TOO_LONG=8`
    - `MISSING_PARAM_ANNOTATION=5`
    - `BARE_EXCEPT=3`
    - `MISSING_RETURN_ANNOTATION=1`
- `diff stat`: current visible working diff since last saved snapshot
  - `15 files changed, 1157 insertions(+), 75 deletions(-)`
  - visible addendum scope:
    - `src/cockpit/backtest_preflight.py`
    - `src/cockpit/backtest_state_support.py`
    - `src/cockpit/templates/pages/backtest.html`
    - `tests/test_local_replay_runtime/test_strategy_ladder_runner.py`
    - `tests/cockpit/test_output_root_and_proof_matrix.py`
    - `tests/cockpit/test_cockpit_server_routes.py`
  - note: several base F16-C files already exist on branch and therefore do not all appear in the current working diff stat

## Coverage Verdict By Pillar

| Surface | Status | Evidence | Gap |
|---|---|---|---|
| Pilier 1 - validator + label_store v3 + capture bridge | COMPLETE | Constants, validator, row v3, augmented keys, bridge extractors, compatibility payload merge, and runtime backtest hoist are present and covered by 32 dedicated tests | Full `local_replay_runtime` regression is not clean because older tests still assert `v2` / narrow bridge dict behavior |
| Pilier 2 - promotion registry + ablation | PARTIAL | Registry module, verdict enum, threshold seam, evidence persistence, and registry upsert/read/write exist and 18 dedicated tests pass | The orchestrator is metric-driven, not a real leave-one-out retrain + re-backtest rail; several fields claimed in the spec are absent |
| Pilier 3 - Lab feature picker | PARTIAL | Governed checkbox picker, verdict badges, hidden CSV fallback, `selected_features` persistence, pair/tf registry discovery, and 400-on-empty are implemented and covered by 8 dedicated tests | No registry-driven default pre-check, no grouped feature sections by family, no structured `DEMOTED` override audit log |
| Backtest F16 parity addendum | COMPLETE on targeted scope | `strategy_ladder_runner` hoists the full augmented feature contract into runtime inference; targeted proofs pass | Full cockpit regression still has 4 failing route tests |

## Claim-By-Claim Coverage

- `P1-1` to `P1-7`: COMPLETE.
  Evidence: [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py>), [strategy_ladder_b2_label_store_builder.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py>), [strategy_ladder_runner.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_runner.py>)
- `P2-1`: COMPLETE.
  `ExpectedEdgeFeatureVerdict` exists with the 4 governed values.
- `P2-2`: PARTIAL.
  `FeaturePromotionEntry` exists with pair/timeframe/feature/verdict/shap_rank/deltas/MinBTL/talab/evidence, but `shap_mean_abs`, `last_evaluated_at_ms`, and `detail` are absent.
- `P2-3`: PARTIAL.
  `FeaturePromotionRegistry` exists with `entries`, `lookup`, `entries_for_pair_tf`, and `upsert`, but `generated_at_ms` is absent and the registry remains a flat entry tuple.
- `P2-4`: PARTIAL.
  Fail-closed read and atomic write are implemented, but no structured invalid-load audit log is emitted.
- `P2-5`: PARTIAL.
  `FeatureAblationRequest` and `FeatureAblationReport` exist, but the implemented contract is metric-based (`baseline_metrics` / `ablated_metrics`) rather than artifact-path / dataset-path / backtest-path based, and `blockers` is absent.
- `P2-6`: PARTIAL.
  `run_feature_ablation()` persists evidence and computes governed deltas/verdicts, but it does not perform a real retrain and re-backtest.
- `P2-7`: COMPLETE with seam note.
  Thresholds are explicit and there are no magic numbers in the verdict logic, but `shap_mean_abs` is not part of the decision signature.
- `P3-1` to `P3-3`: COMPLETE.
  `selected_features`, `discovered_feature_governance`, registry discovery, and VM propagation are present.
- `P3-4`: PARTIAL.
  The text input was replaced by a governed checkbox list with badges and hidden CSV fallback, but the UI is still a flat list: no grouped visual sections by feature family and no default selection derived from registry verdicts.
- `P3-5` and `P3-6`: COMPLETE.
  The server accepts `selected_features`, normalizes them, and propagates the effective tuple into the handoff request.
- `P3-7`: PARTIAL.
  Empty selection returns 400 and the UI exposes a visible override doctrine hint for `DEMOTED`, but there is no structured `EXPECTED_EDGE_FEATURE_USER_OVERRIDE_DEMOTED` audit log.

## Risk Audit Result

| Risk line from spec | Post-execution verdict |
|---|---|
| Re-training ablation cost explosion | PARTIALLY MITIGATED. Current orchestrator is still a light metric-diff rail, so the cost explosion is avoided for now, but the full leave-one-out retrain/backtest rail is not implemented yet. |
| Schema v3 breaks old v2 stores | PARTIALLY MITIGATED. Dedicated migration tests pass, but 3 legacy regressions still assert `v2` schema / narrow bridge payloads and must be reconciled. |
| Partial anti_revenge one-hot pollution | MITIGATED. Validator rejects partial triplets and dedicated tests pass. |
| UI overload with 25 checkboxes | NOT FULLY MITIGATED. The picker exists, but grouping by feature family is not implemented. |
| Silent DEMOTED override | PARTIALLY MITIGATED. Visible UI hint exists; structured audit log is missing. |
| `kyle_lambda_record` absent in bridge | MITIGATED. `kyle_lambda_record`, `realized_vol_current_record`, and `realized_vol_at_break_record` exist in the bridge/provenance rail and are consumed by the runner. |
| Threshold over-engineering | MITIGATED. The verdict thresholds remain explicit and caller-supplied. |
| Cockpit regressions | NOT MITIGATED. 4 cockpit route regressions are still failing. |
| Architecture drift | NOT MITIGATED. DAG validator fails on direct `cockpit -> local_replay_runtime` imports introduced/used by this slice. |

## Additional Targeted Proof

- `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` -> `51 passed`
- `tests/cockpit/test_output_root_and_proof_matrix.py` -> `36 passed`
- `tests/cockpit/test_cockpit_server_routes.py -k "test_backtest_page_surfaces_ml_handoff_run_folder_check or test_backtest_page_surfaces_multi_pair_c1_ml_handoff_contract"` -> `2 passed`

## Current Completion Verdict

- `status`: `PARTIAL`
- `audit_verdict`: `REQUEST_FIX`
- `why`: the core F16-C slice is materially implemented and the dedicated proofs are green, but the source doc over-claims Pilier 2 and part of Pilier 3, and the repo is not green on regression / DAG / guardrails.
- `next_safe_fix_path`:
  - reconcile the Pilier 2 doc/code gap
  - close Pilier 3 registry-precheck / grouping / override-log gaps
  - repair the 10 `local_replay_runtime` + 4 `cockpit` regressions
  - remove or formally sanction the direct `cockpit -> local_replay_runtime` imports before any `GREENLIGHT`
