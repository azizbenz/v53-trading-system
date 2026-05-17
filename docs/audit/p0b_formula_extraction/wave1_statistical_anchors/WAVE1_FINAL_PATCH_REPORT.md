# Wave 1 Final Patch Report

## Result
- Wave 1 doctrinal decisions were implemented as finalized.
- Scope remained confined to calibration methods, tests, and audit docs.
- No engine, runtime, cockpit template, execution backbone, risk backbone, or portfolio logic was modified.

## Files modified

## Production code
- [dsr.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/dsr.py)
- [energy_distance.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/energy_distance.py)
- [__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/__init__.py)

## Tests
- [test_psr.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_calibration_methods/test_psr.py)
- [test_dsr.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_calibration_methods/test_dsr.py)
- [test_energy_distance.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_calibration_methods/test_energy_distance.py)

## Retained from prior Wave 1 correction
- [pot_gpd.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/pot_gpd.py)
- [test_pot_gpd.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_calibration_methods/test_pot_gpd.py)

## Patch detail by residue

## PSR
- Production formula:
  - unchanged
- Patch:
  - no change to [psr.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/psr.py)
  - strengthened the audit anchor in [test_psr.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_calibration_methods/test_psr.py)
- Added closure:
  - deterministic returns fixture
  - stable SHA-256 fixture hash
  - explicit statement that literal `0.9505` is not accepted without an in-repo fixture/hash

## DSR
- Production formula:
  - unchanged in semantics for the returns-based API
- Patch:
  - added `compute_deflated_sharpe_ratio_from_moments(...)` in [dsr.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/dsr.py)
  - refactored shared internal assembly so the returns API and moments seam use the same core calculation path
- Added closure:
  - explicit Table 1 / moments-style reference seam
  - tests proving equivalence against the returns API
  - documented `trial_count` source semantics

## POT-GPD
- Production formula:
  - kept the already-corrected `_pot_var` seam
- Patch in this step:
  - no further code change
- Residual status:
  - Denmark / Coles literal anchor remains partial because the reference dataset is not present in-repo
  - simulation / recovery coverage remains the accepted closure for Wave 1

## Energy distance
- Production formula:
  - kept the current scaled statistic seam unchanged
- Patch:
  - added `compute_raw_energy_distance_statistic(...)` in [energy_distance.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/energy_distance.py)
- Added closure:
  - raw-statistic same-distribution test
  - explicit test proving `scaled = ((n*m)/(n+m)) * raw`
  - no forced raw threshold onto the scaled production seam

## Validation

## Targeted validation
- `python -m pytest -q tests/test_calibration_methods/test_psr.py tests/test_calibration_methods/test_dsr.py tests/test_calibration_methods/test_energy_distance.py tests/test_calibration_methods/test_pot_gpd.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave1_final_targeted`
- Result:
  - `48 passed`

## Full calibration suite
- Command:
```powershell
python -m pytest -q tests/test_calibration_methods --tb=short --disable-warnings
```
- Result:
  - `133 passed, 1 warning`

## Status of closed anchors after patch
- KS fixed-seed anchor:
  - still passing
- Energy strong-shift scaled anchor:
  - still passing
- Mann-Kendall increasing-sequence anchor:
  - still passing
- Hansen SPA behavioral anchors:
  - still passing
- Stationary bootstrap AR(1) anchor:
  - still passing

## What was intentionally not changed
- [psr.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/psr.py)
- all engine code
- all runtime live code
- all cockpit templates
- all strategy logic

## Wave 1 final classification
| Item | Final classification |
|---|---|
| Closed anchors | preserved and still green |
| `PSR 0.9505` | closed by returns-API equivalence anchor |
| `DSR Table 1` | closed by additive from-moments seam |
| `POT-GPD` formula mismatch | closed |
| `POT-GPD` external dataset anchor | partial but non-blocking |
| `Energy same-dist < 0.05` | closed by additive raw seam |

## Final conclusion
- Wave 1 is closed on the finalized doctrine.
- The remaining non-numeric residue is only the absence of an external Denmark / Coles reference dataset, which remains explicitly partial and non-blocking.
