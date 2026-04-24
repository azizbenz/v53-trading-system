# 2026-04-23 — Walls And Spoofing Dual Persistence Metrics

## Decision

`walls_and_spoofing.py` now carries two persistence metrics plus one observation-quality metric:

- `wall_persistence_bid/ask`
- `wall_persistence_conditional_bid/ask`
- `observation_coverage_ratio`

This is an additive diagnostic refinement. It does not introduce directional semantics, side override, or VPS training.

## Canonical Semantics

### 1. Absolute persistence

Used by the current `real_wall_score`.

Formula:

`wall_persistence_side = active_wall_time_ns / window_seconds_ns`

Interpretation:

- proof of persistence over the full target window
- conservative and fail-closed when book coverage is sparse

### 2. Conditional persistence

Diagnostic only in this slice. Not yet promoted into the ML feature map.

Formula:

`wall_persistence_conditional_side = active_wall_time_ns / observed_span_ns`

where:

`observed_span_ns = max(last_depth_ts - first_depth_ts, eps)`

Interpretation:

- persistence conditional on what was actually observed
- useful for IA Lab analysis and for distinguishing weak coverage from weak wall behavior

### 3. Observation coverage

Diagnostic only in this slice.

Formula:

`observation_coverage_ratio = observed_span_ns / window_seconds_ns`

Interpretation:

- quantifies how much of the target observation window was actually covered by depth snapshots
- low coverage means the conditional persistence can look strong while absolute proof remains weak

## Runtime Doctrine

- `real_wall_score` remains based on absolute persistence
- `spoof_suspicion_score` is unchanged
- `as_feature_map()` for `LobRegimeFeatureSnapshot` is unchanged in this slice to avoid silent ML schema drift
- the new metrics are exposed for audit/monitoring and future governed use

## Why This Is Safer

Using only absolute persistence mixes:

- wall behavior
- observation sparsity

Using only conditional persistence would overstate confidence under thin coverage.

The dual-metric design keeps:

- `absolute` for scoring
- `conditional + coverage` for diagnosis

## Repo-Truth Scope

Files updated in this refinement:

- `src/data_backbone/microstructure/walls_and_spoofing.py`
- `src/data_backbone/microstructure/lob_regime_features.py`
- `tests/test_data_backbone/microstructure/test_walls_and_spoofing.py`
- `tests/test_data_backbone/microstructure/test_lob_regime_features.py`

No directional regime label was added.
No quant-anchor file was modified.
