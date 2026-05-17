# Wave 1 POT-GPD Consumer and Compensation Audit

## Producer
- Source file: `src/calibration_methods/pot_gpd.py`
- Public seam: `fit_pot_gpd_tail_risk(losses, *, config) -> PotGpdResult`
- Patched function in this wave:
  - `_pot_var`

## Standard theoretical target
- For exceedance fraction `p_u = exceedance_count / observation_count`
- Standard unconditional VaR at confidence `alpha` uses:
  - `conditional_tail_probability = (1 - alpha) / p_u`
  - `VaR = u + (beta / xi) * (conditional_tail_probability ** (-xi) - 1)`
  - exponential limit when `xi -> 0`

## Pre-patch implementation
- Previous code used:
  - `tail_probability = p_u * (1 - alpha)`
- This produces a materially more extreme tail than the standard POT-GPD VaR under the same naming.

## Consumers found

## 1. Local IA Lab tail-risk review
- File: `src/local_replay_runtime/local_lab_tail_risk_review.py`
- Consumption:
  - `fit = fit_pot_gpd_tail_risk(losses, config=config)`
  - `var_estimate=fit.var_estimate`
  - `bootstrap_dispersion_ratio=fit.bootstrap_dispersion_ratio`
  - `passes_dispersion=fit.passes_dispersion`
- Thresholds / gates using it:
  - `THR-R01` hard cap `0.02`
  - `THR-R02` hard cap `0.05`
  - `THR-R03` hard cap `0.10`
  - dispersion blocker: `fit.passes_dispersion`
- Effect:
  - `var_estimate` is passed into `apply_human_maximum_cap`
  - `hard_cap_binding` only raises caution
  - `passes_dispersion` can block review status
- Compensation:
  - none for the VaR formula itself
  - human maximum cap only clips publication, it does not reinterpret the statistic

## 2. Normalized calibration report
- File: `src/local_replay_runtime/local_lab_calibration_normalized_report.py`
- Consumption:
  - `value_point=breaker.var_estimate`
  - `published_value=breaker.published_value`
  - `xi_hat`, `beta_hat`, `threshold_u`, `exceedance_count`
- Effect:
  - report / audit artifact only
- Compensation:
  - none

## 3. Cockpit tail-risk adapter
- File: `src/cockpit/state_tail_risk.py`
- Consumption:
  - reads `var_estimate` from `local_lab_tail_risk_review.json`
- Effect:
  - cockpit display only
- Compensation:
  - none

## 4. Package export
- File: `src/calibration_methods/__init__.py`
- Effect:
  - re-export only

## Consumer verdict
- `var_estimate` is used and named as VaR, not as an explicitly different conservative tail score
- no V5.3 convention was found that renames or reinterprets it
- no downstream compensation corrects the tail-probability formula
- the human maximum cap is a publication clip, not a semantic compensation

## Patch verdict
- Classification:
  - `MISMATCH_CONFIRMED`
- Reason:
  - the implementation contradicted the standard POT-GPD VaR formula
  - the code and docs still called it VaR
  - no consumer or doctrine downgraded it to a different statistic

## Patch applied in Wave 1
- File modified:
  - `src/calibration_methods/pot_gpd.py`
- Change:
  - replaced `p_u * (1 - alpha)` with `(1 - alpha) / p_u`
- Tests added:
  - direct standard-formula assertion
  - direct exponential-limit assertion

## Remaining limitation
- Denmark / Coles literal anchor remains unavailable in-repo because the reference dataset is still absent
- therefore:
  - formula mismatch is closed
  - reference-dataset residue remains partial
