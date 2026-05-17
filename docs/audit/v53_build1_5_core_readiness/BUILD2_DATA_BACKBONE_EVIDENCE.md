# Build-2 Data Backbone Evidence

Date: `2026-05-01`

## Scope

Primary source rails:

- `src/data_backbone/websocket_gateway/*`
- `src/data_backbone/rest_bootstrap/*`
- `src/data_backbone/consistency_checker/*`
- `src/data_backbone/freshness_checker/*`
- `src/data_backbone/pair_health_scorer/*`
- `src/data_backbone/event_normalizer/*`
- `src/data_backbone/internal_router/*`
- `src/data_backbone/microstructure/*`
- `src/interface_contracts/market_event_contracts.py`

## Proved Capabilities

### Data ingestion exists

Evidence:

- `websocket_gateway/runtime_gateway.py`
- `rest_bootstrap/runtime_bootstrap.py`
- `rest_bootstrap/snapshot_fetcher.py`

### Websocket gateway exists

Evidence:

- `runtime_gateway.py`
- `connection_manager.py`
- `reconnect_controller.py`
- `heartbeat_monitor.py`
- `subscription_manager.py`
- `raw_message_emitter.py`

### REST bootstrap exists

Evidence:

- `runtime_bootstrap.py`
- `gap_fill_controller.py`
- `rate_limit_guard.py`
- `bootstrap_reporter.py`

### Gap fill controller exists

Evidence:

- `rest_bootstrap/gap_fill_controller.py`

Observed doctrine:

- large gaps can be blocked
- non-positive gaps are explicitly rejected

### Data quality checks exist

Evidence:

- `consistency_checker/gap_detector.py`
- `consistency_checker/duplicate_detector.py`
- `consistency_checker/sequence_checker.py`
- `consistency_checker/contradiction_checker.py`
- `freshness_checker/stale_hard_guard.py`

### Pair health exists

Evidence:

- `pair_health_scorer/quality_aggregator.py`
- `pair_health_scorer/health_state_tracker.py`
- `pair_health_scorer/suspension_decider.py`
- `pair_health_scorer/recovery_evaluator.py`

### Timestamp policy exists

Evidence:

- `event_normalizer/timestamp_enricher.py`
- typed market-event contracts in `market_event_contracts.py`

### Microstructure data path exists

Evidence:

- `microstructure/feature_registry.py`
- `microstructure/engine_input_provenance.py`
- `microstructure/lob_regime_features.py`
- `microstructure/order_flow_imbalance.py`
- `microstructure/queue_pressure.py`
- `microstructure/vpin.py`
- `microstructure/kyle_lambda.py`
- `microstructure/realized_kernel_vol.py`

### Book / trade / OHLCV support exists

Evidence:

- `TradeEvent`
- `DepthEvent`
- `KlineEvent`
- `SnapshotEvent`
- `HeartbeatEvent`

from `src/interface_contracts/market_event_contracts.py`

## Behavior Checks

### Stale data behavior

Status: `PROVEN`

Evidence:

- `freshness_checker/stale_hard_guard.py`

Observed doctrine:

- explicit stale threshold policy
- governed modes `SHADOW`, `MICRO_LIVE`, and `LIVE` can hard-block on stale exchange data

### Gap behavior

Status: `PROVEN`

Evidence:

- `consistency_checker/gap_detector.py`
- `rest_bootstrap/gap_fill_controller.py`

Observed doctrine:

- gaps are counted and surfaced
- gap-fill rejects invalid negative/non-positive intervals

### Rate-limit behavior

Status: `PROVEN`

Evidence:

- `rest_bootstrap/rate_limit_guard.py`
- `rest_bootstrap/runtime_bootstrap.py`

### Bad/missing data behavior

Status: `PROVEN`

Evidence:

- `event_normalizer/invalid_message_guard.py`
- `event_normalizer/schema_mapper.py`

Observed doctrine:

- invalid messages are guarded
- unsupported shapes map to explicit error outcomes instead of silent zeros

### No fake zero for missing data

Status: `PROVEN`

Reason:

- the data rail uses explicit invalid/missing handling and health status calculation rather than substituting economic zero values

### Depth20/order-book compatibility

Status: `PROVEN`

Reason:

- typed depth events and depth-oriented microstructure modules are present and tested

## Test Evidence

Relevant suites found:

- `tests/test_data_backbone/test_websocket_gateway.py`
- `tests/test_data_backbone/test_rest_bootstrap.py`
- `tests/test_data_backbone/test_freshness_checker.py`
- `tests/test_data_backbone/test_consistency_checker.py`
- `tests/test_data_backbone/test_pair_health_scorer.py`
- `tests/test_data_backbone/test_event_normalizer.py`
- `tests/test_data_backbone/microstructure/*`

Executed in the combined Build-2..5 band:

- `912 passed`

## Remaining Gaps

- Build-2 itself is implemented and tested, but later build readiness still depends on measured replay/live execution realism and capital viability.
- Cockpit build-level visibility is weaker than runtime data-quality visibility.

## Verdict

Build-2 verdict: `READY`

Reason:

- the canonical backbone exists
- the real source rails are broad and typed
- the combined validation band passed cleanly after environment noise was separated
