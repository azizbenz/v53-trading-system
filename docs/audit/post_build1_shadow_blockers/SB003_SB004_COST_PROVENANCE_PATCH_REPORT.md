# SB-003 / SB-004 Cost Provenance Patch Report

Date: `2026-05-01`

## Scope

This patch hardens the replay/shadow execution-cost rail for:

- `SB-003` replay fee provenance
- `SB-004` replay impact provenance

Non-negotiable doctrine preserved:

- `expected_ce_net` remains expected-only.
- Missing fee or impact is not treated as measured zero.
- Configured, estimated, synthetic, and modeled cost inputs are not presented as measured fills from venue telemetry.
- `COST_MODEL_COMPLETE` is not allowed unless fee provenance, impact provenance, fill realism, replay/live parity, and realized-cost source proof all pass the stricter gate.
- Executed-only return and true drawdown remain non-green whenever cost completeness is partial.
- No engine logic, side logic, leverage, or shorting behavior was changed.

## Code surfaces updated

- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/__init__.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/templates/partials/_replay_metrics.html`

## Implemented provenance rails

### Replay fee provenance

Replay summaries and exported replay artifacts now carry:

- `fee_source_status`
- `fee_model_name`
- `fee_rate_maker_bps`
- `fee_rate_taker_bps`
- `fee_currency`
- `fee_amount`
- `fee_bps`
- `fee_provenance_ref`
- `fee_input_hash`
- `fee_policy_version`

Supported fee statuses on the normalized/current rail:

- `FEE_SOURCE_PROVEN`
- `FEE_SOURCE_CONFIGURED`
- `FEE_SOURCE_EXCHANGE_METADATA`
- `FEE_SOURCE_ESTIMATED`
- `FEE_SOURCE_NOT_PROVEN`
- `FEE_SOURCE_MISSING`

Compatibility normalization is preserved for older artifacts:

- `NOT_PROVEN -> FEE_SOURCE_NOT_PROVEN`
- `MISSING -> FEE_SOURCE_MISSING`
- `EXPLICIT -> FEE_SOURCE_PROVEN`

### Replay impact provenance

Replay summaries and exported replay artifacts now carry:

- `impact_source_status`
- `impact_model_name`
- `impact_bps`
- `impact_notional`
- `impact_depth_ref`
- `impact_depth_level`
- `impact_provenance_ref`
- `impact_input_hash`
- `impact_policy_version`

Supported impact statuses on the normalized/current rail:

- `IMPACT_SOURCE_PROVEN`
- `IMPACT_SOURCE_DEPTH20_MODEL`
- `IMPACT_SOURCE_ESTIMATED`
- `IMPACT_SOURCE_SYNTHETIC`
- `IMPACT_SOURCE_NOT_PROVEN`
- `IMPACT_SOURCE_MISSING`

Compatibility normalization is preserved for older artifacts:

- `NOT_PROVEN -> IMPACT_SOURCE_NOT_PROVEN`
- `MISSING -> IMPACT_SOURCE_MISSING`
- `EXPLICIT -> IMPACT_SOURCE_PROVEN`

## Cost completeness hardening

The replay summary now derives stricter completeness classes:

- `COST_MODEL_COMPLETE`
- `COST_MODEL_PARTIAL_FEE_MISSING`
- `COST_MODEL_PARTIAL_IMPACT_MISSING`
- `COST_MODEL_PARTIAL_FILL_REALISM_MISSING`
- `COST_MODEL_PARTIAL_REPLAY_LIVE_PARITY_MISSING`
- `COST_MODEL_NOT_PROVEN`

The gate is intentionally strict:

```text
COST_MODEL_COMPLETE only if:
- fee source is explicit/proven/configured/exchange-metadata
- impact source is explicit/proven/depth20-model
- fill realism is proven
- replay/live parity is proven
- realized-cost source is present on executed/reduced records
```

Replay summaries now also carry:

- `cost_readiness_reason_codes`

Reason codes include:

- `FEE_SOURCE_NOT_PROVEN`
- `IMPACT_SOURCE_NOT_PROVEN`
- `FILL_REALISM_NOT_PROVEN`
- `REPLAY_LIVE_COST_PARITY_NOT_PROVEN`
- `REALIZED_COST_SOURCE_NOT_PROVEN`

## Executed-return guard

Executed-only profitability and true drawdown remain additive and compatible with the earlier `SB-001` / `SB-002` patch, but they are now explicitly guarded by cost completeness.

If replay economics produce a numeric executed-only return while cost completeness is still partial, the replay summary keeps:

- `executed_only_net_return_status = EXECUTED_NET_RETURN_NOT_PROVEN`

This prevents promotion-grade economics from turning green while fee/impact/fill/parity proof is incomplete.

## Cockpit hardening

Replay/cockpit surfaces now show explicit provenance and non-green readiness:

- fee provenance line with normalized status and `fee_bps`
- impact provenance line with normalized status and `impact_bps`
- strengthened cost caveat with provenance/model/parity fields
- non-green economics reason codes including:
  - `FEE_SOURCE_NOT_PROVEN`
  - `IMPACT_SOURCE_NOT_PROVEN`
  - `REPLAY_COST_MODEL_PARTIAL`
  - `COST_MODEL_NOT_PROMOTION_READY`

Old replay artifacts remain readable through normalization instead of breaking operator views.

## Validation

Focused logic slice:

- `python -m pytest -q tests/test_local_replay_runtime/test_replay_executor.py tests/cockpit/test_state_replay_metrics.py tests/cockpit/test_state_economic_sterilization.py tests/cockpit/test_state_system_flow.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_sb003_sb004_targeted`
- Result: `30 passed`

Requested execution/replay/cockpit band:

- `python -m pytest -q tests/test_execution_backbone tests/test_local_replay_runtime tests/test_backtest_artifact_import tests/cockpit --tb=short --disable-warnings --basetemp=.test_tmp\pytest_sb003_sb004_band1_escalated`
- Result: `557 passed`

Requested risk/scoring band:

- `python -m pytest -q tests/test_risk_backbone tests/test_scoring_backbone --tb=short --disable-warnings --basetemp=.test_tmp\pytest_sb003_sb004_band2_escalated`
- Result: `389 passed`

## Outcome

`SB-003` and `SB-004` are hardened and partially closed:

- provenance is explicit
- missing fee/impact cannot collapse to zero
- cost completeness cannot turn green without explicit provenance proof
- cockpit readiness stays non-green when provenance is partial
- executed-only return remains guarded by cost completeness

This patch does not prove:

- universally measured replay fee provenance
- universally measured replay impact provenance
- fill realism proof
- replay/live cost parity

Those remaining gaps stay open and are tracked separately.
