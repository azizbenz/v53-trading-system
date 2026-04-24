# 2026-04-22 - Quant Anchor Closure Repo-Truth - B/B/B/B

## Docs Governants

- `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md`
- `docs/production_deployment_plan/update_audit/2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Objective

Close the four remaining quant-anchor residues under the user's frozen doctrinal
answers:

- `PSR -> B`
- `DSR -> B`
- `POT-GPD -> B`
- `Energy -> B`

Closure meaning in this slice:

- prove the current public seams honestly
- do not widen any public API
- do not import any external dataset
- do not add an unscaled Energy variant
- do not change the underlying formulas

## Current Repo-Truth

- `compute_probabilistic_sharpe_ratio(...)` remains a returns-based Bailey-López de Prado Eq. 3 seam.
- `compute_deflated_sharpe_ratio(...)` remains a returns-plus-trial-count seam that derives the rest of the quantities internally.
- `fit_pot_gpd_tail_risk(...)` remains the bounded Local IA Lab POT-GPD seam with deterministic bootstrap and no external reference dataset.
- `compute_energy_distance_test(...)` remains the scaled-statistic permutation seam; no raw `E_{n,m}` variant was introduced.

## Files Changed

- `tests/test_calibration_methods/test_psr.py`
- `tests/test_calibration_methods/test_dsr.py`
- `tests/test_calibration_methods/test_pot_gpd.py`
- `tests/test_calibration_methods/test_energy_distance.py`

## Claims Implemented

- PSR is now closed by an independent closed-form recomputation on a fixed return series, proving the current `returns -> PSR` seam directly.
- DSR is now closed by an independent recomputation of the current seam quantities from `returns` and `trial_count`, proving equivalence without a Table 1 API extension.
- POT-GPD is now closed by a deterministic Coles-compatible behavioral validation on synthetic GPD tails, including parameter recovery, VaR monotonicity, and bootstrap stability.
- Energy is now closed on the current scaled statistic using a deterministic null envelope under `H0` and a deterministic separation check under `H1`.
- No `src/calibration_methods/*.py` file was modified by this slice.

## Proof

- `rtk pytest tests/test_calibration_methods/test_psr.py tests/test_calibration_methods/test_dsr.py tests/test_calibration_methods/test_pot_gpd.py tests/test_calibration_methods/test_energy_distance.py -q --tb=short --basetemp=.test_tmp/pytest_quant_b_targets`
  - `42 passed`
- `rtk pytest tests/test_calibration_methods -q --tb=short --basetemp=.test_tmp/pytest_quant_b_full`
  - `103 passed`
- `python -m pytest tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py -q --tb=short --basetemp=.test_tmp/pytest_local_lab_calibration_review`
  - `4 passed`

## Guardrails

- no public signature changed in `src/calibration_methods/`
- no new dataset dependency was added
- no `unscaled` Energy seam was added
- no promotion, gating, or IA Lab runtime behavior changed

## Historical Note

`2026-04-21_quant_anchor_wave2_psr_dsr_potgpd_energy.md` remains historical
draft context. The active repo-truth closure for these residues is this pack and
the frozen `B/B/B/B` doctrine.

## Completion Status

`COMPLETE`

This slice closes the four deferred residues under the chosen doctrine of
current-seam equivalence and simulation-based validation. It does not claim
literal paper-table or external-dataset reproduction, and it does not need to.
