# Wave 1 Do Not Patch List

## Already closed
- `src/calibration_methods/ks_test.py`
  - fixed-seed `D = 0.19` anchor is green
- `src/calibration_methods/energy_distance.py`
  - strong-shift `> 0.5` scaled-stat anchor is green
- `src/calibration_methods/mann_kendall.py`
  - `S = 4950` anchor is green
- `src/calibration_methods/hansen_spa.py`
  - both Wave 1 behavioral anchors are green
- `src/calibration_methods/bootstrap.py`
  - AR(1) `rho = 0.5` block-length `4` anchor is green

## Blocked by doctrine or missing reference dataset
- `src/calibration_methods/psr.py`
  - awaiting exact anchor dataset / doctrinal choice for `0.9505`
- `src/calibration_methods/dsr.py`
  - awaiting doctrinal choice for Table 1 literal reproduction vs current API mapping
- `src/calibration_methods/energy_distance.py`
  - do not force raw same-dist `< 0.05` threshold onto the current scaled seam

## Implemented and tested, but not Wave 1 patch scope
- `src/calibration_methods/stationarity.py`
  - implemented and tested
  - follow-up only if doctrine later requires stronger finite-sample anchoring
- `src/calibration_methods/walkforward.py`
  - implemented and tested
  - follow-up only

## Patched in this wave, do not widen further
- `src/calibration_methods/pot_gpd.py`
  - only `_pot_var` was corrected after `MISMATCH_CONFIRMED`
  - no further refactor is justified in Wave 1
