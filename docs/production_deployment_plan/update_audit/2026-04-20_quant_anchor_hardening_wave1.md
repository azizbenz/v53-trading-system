# 2026-04-20 - Quant Anchor Hardening Wave 1

## Docs Governants

- `docs/production_deployment_plan/update_audit/2026-04-20_codex_critical_path_micro_live_verify_and_close.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Objective

Reduce the remaining `section 2.1` ambiguity by hardening the calibration-method proof set where the requested anchors are mathematically unambiguous in the current code.

This wave does not rewrite formulas. It only:

- tightens deterministic tests around existing implementations
- adds missing provenance references in module docstrings
- documents which requested anchors are still not safely closed

## Current Code Seam

- modules:
  - `src/calibration_methods/bootstrap.py`
  - `src/calibration_methods/hansen_spa.py`
  - `src/calibration_methods/pot_gpd.py`
- tests:
  - `tests/test_calibration_methods/test_ks_test.py`
  - `tests/test_calibration_methods/test_energy_distance.py`
  - `tests/test_calibration_methods/test_mann_kendall.py`
  - `tests/test_calibration_methods/test_hansen_spa.py`
  - `tests/test_calibration_methods/test_bootstrap.py`

## Files Changed

- `src/calibration_methods/bootstrap.py`
- `src/calibration_methods/hansen_spa.py`
- `src/calibration_methods/pot_gpd.py`
- `tests/test_calibration_methods/test_ks_test.py`
- `tests/test_calibration_methods/test_energy_distance.py`
- `tests/test_calibration_methods/test_mann_kendall.py`
- `tests/test_calibration_methods/test_hansen_spa.py`
- `tests/test_calibration_methods/test_bootstrap.py`
- `docs/production_deployment_plan/update_audit/2026-04-20_codex_critical_path_micro_live_verify_and_close.md`

## Claims Implemented

- KS now has a deterministic fixed-seed anchor for the requested `N(0,1)` vs `N(0.5,1)` case with `n=m=1000`, yielding `D = 0.19`.
- Energy distance now has an explicit anchor proving the unit-mean-shift case stays well above `0.5` under the current scaled statistic.
- Mann-Kendall now has the exact `S = 4950` anchor for the strictly increasing `n=100` sequence.
- Hansen SPA now has deterministic anchors for:
  - `5` candidates all worse than benchmark -> `p > 0.5`
  - `1` candidate with `+0.3` mean edge -> `p < 0.05`
- Stationary bootstrap now has a deterministic AR(1) `rho = 0.5` anchor yielding `block_length = 4`.
- Quant provenance docstrings were tightened for stationary bootstrap, Hansen SPA, and POT-GPD.

## Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache_quant_wave1 python -m py_compile src/calibration_methods/bootstrap.py src/calibration_methods/hansen_spa.py src/calibration_methods/pot_gpd.py tests/test_calibration_methods/test_ks_test.py tests/test_calibration_methods/test_energy_distance.py tests/test_calibration_methods/test_mann_kendall.py tests/test_calibration_methods/test_hansen_spa.py tests/test_calibration_methods/test_bootstrap.py` -> pass
- `python -m pytest -q tests/test_calibration_methods/test_ks_test.py tests/test_calibration_methods/test_energy_distance.py tests/test_calibration_methods/test_mann_kendall.py tests/test_calibration_methods/test_hansen_spa.py tests/test_calibration_methods/test_bootstrap.py --basetemp=.test_tmp/pytest_quant_wave1` -> `57 passed`
- `python -m pytest -q tests/test_calibration_methods --basetemp=.test_tmp/pytest_quant_full` -> `98 passed`

## Deferred / Not Done

- PSR requested anchor `0.9505` is still not safely closed against the current PSR seam; the requested numeric target does not trivially match the current public API or formula wiring.
- DSR Table 1 style anchors are still not mapped cleanly onto the current `compute_deflated_sharpe_ratio(...)` API.
- POT-GPD does not yet carry the requested Denmark/Coles data anchor in-repo.
- Energy same-distribution anchor `< 0.05` is not safely closed because the current implementation uses a scaled energy statistic, so that wording is not equivalent to the present seam.

## Guardrails

- no new runtime seam widened
- no engine, protocol, or portfolio logic touched
- repo-global guardrail and DAG baselines remain unchanged and outside this slice

## Completion Status

`PARTIAL`

This wave materially reduces `section 2.1` ambiguity, but it does not honestly close the full quant-anchor checklist.

## Next Safe Step

Run a second bounded quant audit wave focused only on the unresolved anchors:

- PSR exact numeric anchor disambiguation
- DSR Table 1 mapping to the current API
- POT-GPD Denmark/Coles reference dataset or an approved in-repo surrogate
- Energy same-distribution wording alignment versus the current scaled statistic

---

## Addendum 2026-04-21 - Residue status hardening (R-QUANT-FIRST)

Following audit disambiguation pass (see `2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`), the four deferred anchors are now formally labeled:

| Anchor | Status | Reason |
|--------|--------|--------|
| PSR 0.9505 | **BLOCKED** | No reference dataset whose PSR equals 0.9505 under Bailey-Lopez de Prado 2012 eq.3 is available in-repo; the requested numeric target is not anchored to a specific published table/figure. Awaiting human doctrinal decision: closed-form direct anchor vs equivalence-via-returns-API anchor. |
| DSR Table 1 | **BLOCKED** | `compute_deflated_sharpe_ratio(...)` public API does not accept the Table 1 parameter set of Bailey-Borwein-Lopez de Prado-Zhu 2014 verbatim. Awaiting human doctrinal decision: literal Table 1 reproduction (requires API extension) vs demonstrated equivalence via current API. |
| POT-GPD Denmark/Coles | **PARTIAL** | The Coles 2001 reference dataset is not redistributed in-repo (licensing). A synthetic GPD simulation anchor exists in the current test harness but is not a Denmark/Coles-literal anchor. Awaiting human decision: real Denmark/Coles dataset (requires license resolution) vs Coles-compatible behavioral validation via simulation recovery. |
| Energy same-dist < 0.05 | **BLOCKED** | Current implementation uses a scaled Energy statistic; the `< 0.05` threshold assumes the unscaled Szekely-Rizzo E_{n,m} statistic (which -> 0 under H0). The two statistics are not equivalent. Awaiting human doctrinal decision: anchor the raw E_{n,m} statistic (requires new function or unscaled variant) vs anchor the current scaled statistic at a different threshold derived from its own null distribution. |

No formula was modified for this addendum. Wave 1 closed anchors (KS fixed-seed, Energy strong-shift under scaled statistic, Mann-Kendall S=4950, Hansen SPA two anchor cases, stationary bootstrap AR(1)) remain intact and unchanged.
