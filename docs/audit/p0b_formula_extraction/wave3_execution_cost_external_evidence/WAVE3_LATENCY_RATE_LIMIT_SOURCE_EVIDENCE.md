# Wave 3 Latency / Rate-Limit Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## 1. Replay latency penalty

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Function: `_expected_cost`

```python
row.latency_penalty_bps * config.latency_penalty_multiplier
```

Plain-text formula:
- replay expected cost adds `latency_penalty_bps` scaled by multiplier

Units:
- input in bps
- output contribution in fraction after division by `10_000`

Scope:
- replay expected-cost seam

## 2. Live/shadow latency measurement

Source file: `src/execution_backbone/fill_tracker/latency_meter.py`  
Test evidence from `tests/test_execution_backbone/test_fill_tracker.py::TestLatencyMeter`

Proven measurements:
- `signal_to_submit_s`
- `submit_to_ack_s`
- `submit_to_first_fill_s`
- stage breakdown: scoring, risk, portfolio, submit

Representative assertions:
- `signal_to_submit_s == 0.4`
- `submit_to_ack_s == 0.3`

Missing behavior:
- sanitization filters negative or aberrant latency samples rather than treating them as zero measured success

## 3. Latency staleness in routing equations

Source file: `src/execution_backbone/order_decider/hybrid_router_equations.py`

```python
def compute_expected_latency_staleness_bps(
    *,
    short_window_volatility_z: float,
    scale_bps: float,
) -> float:
    return scale_bps * max(short_window_volatility_z, 0.0)
```

Evidence:
- higher positive volatility z-score increases latency/staleness penalty

## 4. Rate-limit guard

Source file: `src/execution_backbone/rate_limiter.py`  
Function: `evaluate_execution_rate_limit`

```python
if current_quota_ratio < model.quota_ratio_ceiling:
    return ExecutionRateLimitDecision(blocked=False, ...)
return ExecutionRateLimitDecision(
    blocked=True,
    reason_code="RATE_LIMIT_QUOTA_RATIO_EXCEEDED",
    ...
)
```

Plain-text formula:
- block when `current_quota_ratio >= quota_ratio_ceiling`

Units:
- quota ratio

Tests:
- `tests/test_execution_backbone/test_rate_limiter.py`
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_blocks_submission_from_rate_limit_model`
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_fails_open_when_rate_limit_model_has_no_live_telemetry`

Fail-open / fail-closed evidence:
- missing live telemetry can fail open in runtime
- observed excessive quota ratio blocks

## 5. Snapshot freshness and coverage

Source file: `src/execution_backbone/execution_routing_bridge.py`

```python
if age_s > self._config.max_snapshot_age_s:
    raise RoutingFeatureProjectionError("stale_snapshot", ...)
if observation_coverage_ratio < self._config.min_coverage_ratio:
    raise RoutingFeatureProjectionError("low_coverage", ...)
```

Evidence:
- stale LOB snapshot is fail-closed
- low observation coverage is fail-closed
- missing volatility stats fall back to `0.0` z-score with reason code `vol_zscore_unavailable`

Tests:
- `tests/unit/protocols/test_execution_routing_bridge.py::test_project_rejects_stale_lob_snapshot_with_reason`
- `tests/unit/protocols/test_execution_routing_bridge.py::test_project_rejects_low_coverage_ratio_with_reason`

External-audit questions:
- Is fail-open on missing rate-limit telemetry acceptable?
- Should volatility z-score missing be a stronger caution than `0.0 + reason code`?
