# Wave 4 Test Coverage Evidence

## Test files found

Canonical estimator tests:
- `tests/test_data_backbone/microstructure/test_amihud_illiquidity.py`
- `tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
- `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`
- `tests/test_data_backbone/microstructure/test_feature_registry.py`
- `tests/test_data_backbone/microstructure/test_hawkes_intensity.py`
- `tests/test_data_backbone/microstructure/test_kyle_lambda.py`
- `tests/test_data_backbone/microstructure/test_lob_regime_features.py`
- `tests/test_data_backbone/microstructure/test_order_flow_imbalance.py`
- `tests/test_data_backbone/microstructure/test_paper_repro.py`
- `tests/test_data_backbone/microstructure/test_pin.py`
- `tests/test_data_backbone/microstructure/test_queue_pressure.py`
- `tests/test_data_backbone/microstructure/test_realized_kernel_vol.py`
- `tests/test_data_backbone/microstructure/test_roll_spread.py`
- `tests/test_data_backbone/microstructure/test_vpin.py`
- `tests/test_data_backbone/microstructure/test_walls_and_spoofing.py`

Consumer tests:
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
- `tests/test_engines/test_engine_c/*`
- `tests/test_engines/test_engine_d/*`
- `tests/test_execution_backbone/test_execution_runtime.py`
- `tests/test_execution_backbone/test_gatekeeper.py`
- `tests/test_execution_backbone/test_spread_guard.py`
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_data_quality.py`

## Exact assertions observed in source trace

- Kyle:
  - `assert result.is_stale is True`
  - `assert result.stale_reason == "zero_signed_volume_variance"`
- VPIN:
  - `assert result.insufficient_variation is True`
- Walls/spoofing:
  - `assert "micro.wall.bid.strong" in snapshot.reason_codes`
  - `assert "micro.spoof_like.ask" in snapshot.reason_codes`
  - `assert snapshot.reason_codes == ("micro.snapshot.insufficient_data",)`
- LOB regime:
  - `assert snapshot.data_status == "insufficient_data"`
  - `assert snapshot.reason_codes == ("LOB_REGIME_INSUFFICIENT_DEPTH_EVENTS",)`
- Regime runtime:
  - `assert signal.regime_transition_risk == pytest.approx(0.82)`
  - `assert signal.reason_codes[0] == "REGIME_DIRECTIONAL_REF_FORBIDDEN"`
- Engine C:
  - `assert result.engine_output.microstructure_gate_applied is True`
  - `assert result.engine_output.cumulative_ofi == pytest.approx(24.0)`
  - `assert accepted_log.queue_pressure == pytest.approx(0.36)`
  - `assert result.signal_candidate.side == Side.BUY`
- Engine D:
  - `assert result.signal_candidate.side == Side.BUY`
  - `assert assembly.runtime_input.engine_inputs.realized_vol_post_close == pytest.approx(0.015)`

## Missing / weakly covered areas

1. Direct governed runtime consumer proof for:
   - `Amihud`
   - `Roll`
   - `Corwin-Schultz`
   - `Hawkes`
   remains weaker than the estimator-unit-test coverage.
2. Cockpit tests prove artifact / stale / recognized-family behavior, but not full operator interpretation of runtime consumption.
3. The pack did not identify a dedicated runtime test that directly proves feature-registry claims for every `consumed_by` entry.

## Environment failures

Commands run:

- `python -m py_compile` over the traced microstructure, consumer, and cockpit files with `PYTHONPYCACHEPREFIX=.test_tmp\pycache_wave4`
- `python -m pytest -q tests/test_data_backbone/microstructure --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave4_microstructure`
- `python -m pytest -q tests/test_microstructure/test_paper_repro.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave4_paper_repro`
- `python -m pytest -q tests/test_complete_enablers/test_regime_detector_runtime.py tests/test_execution_backbone/test_execution_runtime.py tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_spread_guard.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave4_runtime_consumers`
- `python -m pytest -q tests/test_engines/test_engine_c tests/test_engines/test_engine_d --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave4_engines_cd`
- `python -m pytest -q tests/cockpit/test_state_feature_bridge.py tests/cockpit/test_state_data_quality.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave4_cockpit`

Results:

- Syntax: `PASS`
- `tests/test_data_backbone/microstructure`: `107 passed`
- `tests/test_microstructure/test_paper_repro.py`: `18 passed`
- `tests/test_engines/test_engine_c tests/test_engine_d`: `228 passed`
- `tests/cockpit/test_state_feature_bridge.py tests/cockpit/test_state_data_quality.py`: `3 passed`
- Runtime consumer slice:
  - `48 passed`
  - `2 failed`
  - failure type: `PermissionError [WinError 5]`
  - affected tests:
    - `tests/test_execution_backbone/test_gatekeeper.py::test_gatekeeper_audit_logger_writes_refusal_event`
    - `tests/test_execution_backbone/test_gatekeeper.py::test_gatekeeper_audit_logger_writes_submission_event`
  - observed failure path:
    - `build\\pytest-gatekeeper-audit\\...`

Assessment:

- The failing slice is an environment write-permission issue on the audit-log directory, not a traced microstructure-estimator formula failure.
