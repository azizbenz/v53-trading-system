# Wave 1 Confirmed Patch Candidates Only

## Confirmed candidate
- `src/calibration_methods/pot_gpd.py::_pot_var`
  - classification: `MISMATCH_CONFIRMED`
  - reason:
    - implementation used `p_u * (1 - alpha)` instead of the standard conditional-tail probability `(1 - alpha) / p_u`
    - result was still named and consumed as `var_estimate`
    - no internal V5.3 conservative-variant doctrine or downstream compensation was proven
  - patch status:
    - corrected in this wave
  - validation:
    - `tests/test_calibration_methods/test_pot_gpd.py` targeted suite passes
    - full `tests/test_calibration_methods` suite passes
