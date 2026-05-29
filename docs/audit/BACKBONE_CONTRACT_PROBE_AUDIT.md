# Backbone Contract Probe Audit

Generated at: `2026-05-27T11:25:46.836943+00:00`
Overall status: `BACKBONE_CONTRACT_PROBE_PARTIAL`

This audit is read-only. It probes code contracts before moving B2 surfaces to canonical backbones.

## Surface Readiness

### execution_backbone / spread_measurement

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `('measured_spread_report',)`
- Required pre-patch: `('ADD_DASHBOARD_REPORT_FIELDS',)`

### execution_backbone / slippage_measurement

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `('depth20_walk_ref', 'planned_notional')`
- Missing outputs: `('slippage_source_status',)`
- Dashboard missing: `('measured_slippage_report',)`
- Required pre-patch: `('DEFINE_OR_MAP_MISSING_INPUTS', 'DEFINE_OR_MAP_MISSING_OUTPUTS', 'ADD_DASHBOARD_REPORT_FIELDS', 'ADD_DEPTH20_MEASURED_SLIPPAGE_CONTRACT')`

### execution_backbone / fee_measurement

- Status: `BACKBONE_CONTRACT_READY`
- Safe to wire B2: `True`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `()`
- Required pre-patch: `()`

### execution_backbone / adverse_selection

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `('adverse_selection_status',)`
- Required pre-patch: `('ADD_DASHBOARD_REPORT_FIELDS', 'WIRE_POST_FILL_MID_WINDOW')`

### scoring_backbone / break_even

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `('ev_net',)`
- Required pre-patch: `('ADD_DASHBOARD_REPORT_FIELDS',)`

### risk_backbone / risk_filtering

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `('loss_budget', 'risk_readiness', 'exposure')`
- Required pre-patch: `('ADD_DASHBOARD_REPORT_FIELDS',)`

### portfolio_minimal / capital_bucket_sizing

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `('selected_bucket_record_count', 'executed_bucket_record_count')`
- Required pre-patch: `('ADD_DASHBOARD_REPORT_FIELDS',)`

### regime_classifier / regime_classification

- Status: `BACKBONE_CONTRACT_INCOMPLETE`
- Safe to wire B2: `False`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `('regime_id', 'entries_blocked')`
- Required pre-patch: `('ADD_DASHBOARD_REPORT_FIELDS',)`

### protocols / replay_governance_projection

- Status: `BACKBONE_CONTRACT_READY`
- Safe to wire B2: `True`
- Missing inputs: `()`
- Missing outputs: `()`
- Dashboard missing: `()`
- Required pre-patch: `()`
