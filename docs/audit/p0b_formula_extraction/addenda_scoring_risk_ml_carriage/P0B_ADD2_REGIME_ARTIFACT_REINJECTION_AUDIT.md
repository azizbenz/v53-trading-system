# P0-B Addendum 2 - Regime Artifact Reinjection Audit

## Regime runtime output surface
`src/complete_enablers/regime_detector_runtime.py`

Proven governed output fields:
- `regime_transition_risk`
- `regime_stability_score`
- `market_toxicity_score`
- `expected_duration_bucket`

Not proven:
- directional up/down label
- long/short instruction
- trade side override

## Artifact producers and display readers
Producers / transport:
- `local_replay_runtime/historical_data_gateway.py`
- `local_replay_runtime/artifact_exporter.py`
- `feature_bridge.json`

Cockpit readers:
- `cockpit/state_feature_bridge.py`
- `cockpit/state_engines.py`
- `cockpit/state_engine_why.py`

Cockpit use is audit/display only.

## Governed runtime consumers

### Proven decisional consumer
`execution_backbone/execution_routing_bridge.py`

Consumes regime output fields directly into routing snapshot:
- `market_toxicity_score`
- `regime_transition_risk`
- `regime_stability_score`
- `expected_duration_bucket`

Then hybrid router uses them for:
- fill probability
- adverse selection
- maker/taker EV
- routing choice

### Not uniformly proven
This audit did not prove uniform reinjection of regime artifact outputs into:
- `ScoringCandidateInput`
- `RiskCandidate`
- engine-local named runtime fields
- `supplementary_refs` on live engine candidates

## Directional-label exclusion proof
`RegimeDetectorSignal` contains risk/stability/toxicity/duration only.

No proof found for:
- `direction_up_300s_fee_safe`
- `market will go up`
- hidden long/short regime command

## Missing reinjection seams
- Shared scoring candidate does not receive regime artifact outputs directly.
- Shared risk regime precheck input is not populated with concrete regime state by current engine runtime paths.
- Engine live candidates do not prove `supplementary_refs` carriage to regime loader.

## Verdict
`PARTIAL_REINJECTION`

Interpretation:
- decisional downstream reinjection into execution is proven
- scoring/risk/live-engine artifact reinjection is not uniform
