# Wave 1 Statistical Anchors Audit

## Closed anchors verified

## KS fixed-seed anchor
- Source file: `src/calibration_methods/ks_test.py`
- Function: `compute_ks_2sample`, `_ks_statistic`
- Formula implemented:
  - two-sample KS statistic `D_{n,m} = sup_t |F_n(t) - G_m(t)|`
  - asymptotic Smirnov p-value
- Theoretical target:
  - `N(0,1)` vs `N(0.5,1)`
  - `n=m=1000`
  - fixed seed anchor `D = 0.19`
- Tests found:
  - `tests/test_calibration_methods/test_ks_test.py::test_ks_anchor_matches_fixed_seed_half_sigma_shift_at_n_1000`
- Docs found:
  - `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md`
- Consumers found:
  - none in `src/` beyond package export
- Verdict:
  - `ANCHOR_CLOSED_NUMERIC`
- Patch recommendation:
  - do not patch

## Energy strong-shift anchor
- Source file: `src/calibration_methods/energy_distance.py`
- Function: `_energy_statistic`, `compute_energy_distance_test`
- Formula implemented:
  - scaled statistic `T = (n*m)/(n+m) * max(E_hat, 0)`
- Theoretical target:
  - strong unit mean-shift remains above `0.5` under the current scaled seam
- Tests found:
  - `tests/test_calibration_methods/test_energy_distance.py::test_energy_statistic_exceeds_half_point_for_unit_mean_shift_anchor`
- Docs found:
  - `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md`
- Consumers found:
  - none in `src/` beyond package export
- Verdict:
  - `ANCHOR_CLOSED_NUMERIC`
- Patch recommendation:
  - do not patch

## Mann-Kendall anchor
- Source file: `src/calibration_methods/mann_kendall.py`
- Function: `compute_mann_kendall_test`, `_mann_kendall_s`
- Formula implemented:
  - `S = sum_{i<j} sgn(x_j - x_i)`
- Theoretical target:
  - strictly increasing sequence length `100`
  - `S = 4950`
- Tests found:
  - `tests/test_calibration_methods/test_mann_kendall.py::test_strictly_increasing_length_100_series_has_mann_1945_s_anchor`
- Docs found:
  - `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md`
- Consumers found:
  - none in `src/` beyond package export
- Verdict:
  - `ANCHOR_CLOSED_NUMERIC`
- Patch recommendation:
  - do not patch

## Hansen SPA anchors
- Source file: `src/calibration_methods/hansen_spa.py`
- Function: `compute_hansen_spa_test`
- Formula implemented:
  - positive-part studentized mean with stationary bootstrap null recentering
- Theoretical targets:
  - `5` candidates all worse than benchmark -> `p > 0.5`
  - `1` candidate with `+0.3` mean edge -> `p < 0.05`
- Tests found:
  - `tests/test_calibration_methods/test_hansen_spa.py::test_hansen_spa_anchor_all_five_candidates_worse_than_benchmark_gives_p_above_half`
  - `tests/test_calibration_methods/test_hansen_spa.py::test_hansen_spa_anchor_one_candidate_plus_point_three_mean_gives_p_below_five_percent`
- Docs found:
  - `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md`
- Consumers found:
  - none in `src/` beyond package export
- Verdict:
  - `ANCHOR_CLOSED_BEHAVIORAL`
- Patch recommendation:
  - do not patch

## Stationary bootstrap anchor
- Source file: `src/calibration_methods/bootstrap.py`
- Function: `infer_stationary_block_length`
- Formula implemented:
  - positive integrated autocorrelation proxy with bounded block-length rounding
- Theoretical target:
  - deterministic AR(1), `rho = 0.5`
  - `block_length = 4`
- Tests found:
  - `tests/test_calibration_methods/test_bootstrap.py::test_infer_stationary_block_length_anchor_for_ar1_rho_half_is_four`
- Docs found:
  - `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md`
- Consumers found:
  - `src/calibration_methods/hansen_spa.py`
  - `src/local_replay_runtime/edge_gate_calibration.py`
- Verdict:
  - `ANCHOR_CLOSED_NUMERIC`
- Patch recommendation:
  - do not patch

## Residues

## PSR 0.9505
- Source file: `src/calibration_methods/psr.py`
- Function: `compute_probabilistic_sharpe_ratio`
- Formula implemented:
  - Bailey-Lopez de Prado 2012 Eq. 3 over a returns series
- Theoretical target:
  - literal anchor `PSR = 0.9505`
- Tests found:
  - `tests/test_calibration_methods/test_psr.py::test_psr_matches_closed_form_reference_for_fixed_return_series`
- Docs found:
  - `2026-04-20_quant_anchor_hardening_wave1.md`
  - `2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`
- Consumers found:
  - no `src/` consumer beyond package export was proven in this audit
- Verdict:
  - `BLOCKED_BY_MISSING_REFERENCE_DATASET`
- Patch recommendation:
  - do not patch `psr.py`
  - keep decision record: direct closed-form anchor vs returns-API equivalence anchor

## DSR Table 1
- Source file: `src/calibration_methods/dsr.py`
- Function: `compute_deflated_sharpe_ratio`
- Formula implemented:
  - returns-based DSR seam with `trial_count` and internally derived moments/benchmark
- Theoretical target:
  - Bailey-Borwein-Lopez de Prado-Zhu Table 1 style anchor
- Tests found:
  - `tests/test_calibration_methods/test_dsr.py::test_dsr_matches_current_api_reference_mapping`
- Docs found:
  - `2026-04-20_quant_anchor_hardening_wave1.md`
  - `2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`
- Consumers found:
  - `src/local_replay_runtime/local_lab_calibration_methods_review.py`
- Verdict:
  - `HUMAN_DECISION_REQUIRED`
- Patch recommendation:
  - do not patch `dsr.py`
  - keep decision record: extend API for literal Table 1 vs document explicit mapping to current API

## POT-GPD Denmark/Coles residue
- Source file: `src/calibration_methods/pot_gpd.py`
- Function: `fit_pot_gpd_tail_risk`, `_pot_var`
- Formula implemented before fix:
  - `tail_probability = (exceedance_count / observation_count) * (1 - var_confidence)`
- Theoretical target:
  - standard POT-GPD unconditional VaR using conditional tail probability
- Tests found:
  - `tests/test_calibration_methods/test_pot_gpd.py`
- Docs found:
  - `2026-04-20_quant_anchor_hardening_wave1.md`
  - `2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`
  - `2026-04-19_carto_A_calibration.md`
- Consumers found:
  - `src/local_replay_runtime/local_lab_tail_risk_review.py`
  - `src/local_replay_runtime/local_lab_calibration_normalized_report.py`
  - `src/cockpit/state_tail_risk.py`
- Verdict:
  - `MISMATCH_CONFIRMED`
- Patch recommendation:
  - patch `_pot_var` to use conditional tail probability
  - add direct formula tests
  - preserve all non-POT modules unchanged

## Energy same-dist < 0.05
- Source file: `src/calibration_methods/energy_distance.py`
- Function: `_energy_statistic`, `compute_energy_distance_test`
- Formula implemented:
  - scaled energy statistic
- Theoretical target:
  - same-distribution threshold `< 0.05` for the unscaled raw statistic
- Tests found:
  - `tests/test_calibration_methods/test_energy_distance.py::test_energy_distance_same_distribution_uses_scaled_null_envelope`
- Docs found:
  - `2026-04-20_quant_anchor_hardening_wave1.md`
  - `2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`
- Consumers found:
  - no `src/` consumer beyond package export was proven in this audit
- Verdict:
  - `HUMAN_DECISION_REQUIRED`
- Patch recommendation:
  - do not patch `energy_distance.py`
  - keep decision record: add raw statistic seam vs derive scaled null threshold

## ADF/KPSS
- Source file: `src/calibration_methods/stationarity.py`
- Function:
  - `compute_adf_level_stationarity`
  - `compute_kpss_level_stationarity`
  - `evaluate_dual_stationarity`
- Tests found:
  - `tests/test_calibration_methods/test_stationarity.py`
- Consumers found:
  - `src/local_replay_runtime/local_lab_calibration_methods_review.py`
- Verdict:
  - `MATCH_INTERNAL_CONVENTION`
- Patch recommendation:
  - `IMPLEMENTED_AND_TESTED`
  - follow-up only if doctrine later requires stronger finite-sample anchors

## Purged walk-forward
- Source file: `src/calibration_methods/walkforward.py`
- Function: `build_purged_walk_forward_plan`
- Tests found:
  - `tests/test_calibration_methods/test_walkforward.py`
- Consumers found:
  - `src/local_replay_runtime/local_lab_calibration_methods_review.py`
- Verdict:
  - `MATCH_INTERNAL_CONVENTION`
- Patch recommendation:
  - `IMPLEMENTED_AND_TESTED`
  - not a Wave 1 patch target
