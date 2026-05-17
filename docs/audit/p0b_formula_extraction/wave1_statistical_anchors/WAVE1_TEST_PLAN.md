# Wave 1 Test Plan

## Syntax validation
- Requested command:
  - `python -m py_compile src/calibration_methods/psr.py src/calibration_methods/dsr.py src/calibration_methods/pot_gpd.py src/calibration_methods/energy_distance.py src/calibration_methods/hansen_spa.py src/calibration_methods/bootstrap.py`
- Environment-safe command used in this audit:
  - `PYTHONPYCACHEPREFIX=.test_tmp/pycache_wave1_postpatch python -m py_compile src/calibration_methods/psr.py src/calibration_methods/dsr.py src/calibration_methods/pot_gpd.py src/calibration_methods/energy_distance.py src/calibration_methods/hansen_spa.py src/calibration_methods/bootstrap.py src/calibration_methods/stationarity.py src/calibration_methods/walkforward.py`
- Expected scope:
  - syntax only

## Wave 1 targeted anchors
- Command:
  - `python -m pytest -q tests/test_calibration_methods/test_psr.py tests/test_calibration_methods/test_dsr.py tests/test_calibration_methods/test_pot_gpd.py tests/test_calibration_methods/test_energy_distance.py tests/test_calibration_methods/test_ks_test.py tests/test_calibration_methods/test_mann_kendall.py tests/test_calibration_methods/test_hansen_spa.py tests/test_calibration_methods/test_bootstrap.py --tb=short --disable-warnings`
- Audit command used:
  - `rtk pytest -q tests/test_calibration_methods/test_psr.py tests/test_calibration_methods/test_dsr.py tests/test_calibration_methods/test_pot_gpd.py tests/test_calibration_methods/test_energy_distance.py tests/test_calibration_methods/test_ks_test.py tests/test_calibration_methods/test_mann_kendall.py tests/test_calibration_methods/test_hansen_spa.py tests/test_calibration_methods/test_bootstrap.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave1_targeted_postpatch`
- Expected scope:
  - closed anchors
  - PSR/DSR/POT-GPD/Energy residues

## ADF/KPSS and walk-forward
- Command:
  - `python -m pytest -q tests/test_calibration_methods/test_stationarity.py tests/test_calibration_methods/test_walkforward.py --tb=short --disable-warnings`
- Audit command used:
  - `rtk pytest -q tests/test_calibration_methods/test_stationarity.py tests/test_calibration_methods/test_walkforward.py --tb=short --disable-warnings --basetemp=tmp_pytest_wave1_stationarity_walkforward_postpatch`
- Expected scope:
  - inventory only
  - no Wave 1 formula patch expectation

## Full calibration suite
- Command:
  - `python -m pytest -q tests/test_calibration_methods --tb=short --disable-warnings`
- Audit command used:
  - `rtk pytest -q tests/test_calibration_methods --tb=short --disable-warnings --basetemp=tmp_pytest_wave1_full_postpatch`
- Expected scope:
  - regression safety across all calibration seams
