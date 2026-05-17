# P0-B Engine Formula Consumer Map

## engine_a
- Direct formulas implemented: 329
- Upstream formulas consumed: 114
- Direct class mix: {'TEXT_OR_LIST': 119, 'PYDANTIC_FIELD': 70, 'REAL_QUANT_FORMULA': 63, 'STATUS_FLAG': 24, 'THRESHOLD_CONSTANT': 53}
- Upstream class mix: {'TEXT_OR_LIST': 40, 'REAL_QUANT_FORMULA': 21, 'THRESHOLD_CONSTANT': 4, 'PYDANTIC_FIELD': 3, 'RISK_SIZING_FORMULA': 36, 'STATUS_FLAG': 10}
- Microstructure features consumed: none proven
- Cost/risk formulas consumed: break even filter, forecast normalizer, portfolio compatibility checker, score penalty builder, scoring runtime, selection resolver, size penalty builder
- Forecast/refusal/coordination formulas consumed: __all__, clipped, clipped_forecast, compute_raw_forecast, max_abs_forecast, mean_abs_forecast, normalize_raw_forecast, normalized_forecast, resolve_forecast_scalar, resolved_config, target_mean_abs_forecast
- Missing consumer proof inside engine surface: 91
- Not allowed inside engine by architecture: cockpit diagnostics, monitoring health logic, secrets management, venue IO, and standalone calibration anchors without source-mapped upstream evidence.

## engine_b
- Direct formulas implemented: 378
- Upstream formulas consumed: 114
- Direct class mix: {'TEXT_OR_LIST': 127, 'STATUS_FLAG': 25, 'PYDANTIC_FIELD': 91, 'REAL_QUANT_FORMULA': 76, 'THRESHOLD_CONSTANT': 59}
- Upstream class mix: {'TEXT_OR_LIST': 40, 'REAL_QUANT_FORMULA': 21, 'THRESHOLD_CONSTANT': 4, 'PYDANTIC_FIELD': 3, 'RISK_SIZING_FORMULA': 36, 'STATUS_FLAG': 10}
- Microstructure features consumed: none proven
- Cost/risk formulas consumed: break even filter, forecast normalizer, portfolio compatibility checker, score penalty builder, scoring runtime, selection resolver, size penalty builder
- Forecast/refusal/coordination formulas consumed: __all__, clipped, clipped_forecast, compute_raw_forecast, max_abs_forecast, mean_abs_forecast, normalize_raw_forecast, normalized_forecast, resolve_forecast_scalar, resolved_config, target_mean_abs_forecast
- Missing consumer proof inside engine surface: 111
- Not allowed inside engine by architecture: cockpit diagnostics, monitoring health logic, secrets management, venue IO, and standalone calibration anchors without source-mapped upstream evidence.

## engine_c
- Direct formulas implemented: 366
- Upstream formulas consumed: 57
- Direct class mix: {'THRESHOLD_CONSTANT': 73, 'STATUS_FLAG': 45, 'TEXT_OR_LIST': 122, 'PYDANTIC_FIELD': 58, 'REAL_QUANT_FORMULA': 68}
- Upstream class mix: {'TEXT_OR_LIST': 27, 'STATUS_FLAG': 9, 'RISK_SIZING_FORMULA': 18, 'THRESHOLD_CONSTANT': 3}
- Microstructure features consumed: none proven
- Cost/risk formulas consumed: portfolio compatibility checker, score penalty builder, scoring runtime, selection resolver, size penalty builder
- Forecast/refusal/coordination formulas consumed: none proven
- Missing consumer proof inside engine surface: 366
- Not allowed inside engine by architecture: cockpit diagnostics, monitoring health logic, secrets management, venue IO, and standalone calibration anchors without source-mapped upstream evidence.

## engine_d
- Direct formulas implemented: 367
- Upstream formulas consumed: 81
- Direct class mix: {'THRESHOLD_CONSTANT': 96, 'STATUS_FLAG': 33, 'TEXT_OR_LIST': 117, 'PYDANTIC_FIELD': 30, 'REAL_QUANT_FORMULA': 91}
- Upstream class mix: {'TEXT_OR_LIST': 23, 'THRESHOLD_CONSTANT': 8, 'PYDANTIC_FIELD': 11, 'MICROSTRUCTURE_ESTIMATOR': 18, 'STATUS_FLAG': 11, 'RISK_SIZING_FORMULA': 10}
- Microstructure features consumed: Realized kernel volatility
- Cost/risk formulas consumed: portfolio compatibility checker, score penalty builder, selection resolver, size penalty builder
- Forecast/refusal/coordination formulas consumed: none proven
- Missing consumer proof inside engine surface: 367
- Not allowed inside engine by architecture: cockpit diagnostics, monitoring health logic, secrets management, venue IO, and standalone calibration anchors without source-mapped upstream evidence.
