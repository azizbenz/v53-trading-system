# Wave 2 Cockpit False-Green Replay Policy

## Core rule
Replay economics must not look measured unless source, sample, freshness, and denominator are explicit.

## Allowed display states
- `REAL_MEASURED_VALUE`
- `REPORT_VALUE`
- `PLACEHOLDER_DEFAULT`
- `NOT_YET_PERSISTED`
- `INSUFFICIENT_SAMPLE`
- `STALE_ARTIFACT`
- `PARTIAL_REPLAY`

## Green / yellow / gray / red policy

### Green allowed only when all are true
- replay source is present and parseable
- replay artifact is not stale
- `total_records > 0`
- metric is not a placeholder default
- metric semantics are explicit
- sample is not too small for interpretation

### Yellow required when any are true
- `0 < total_records < 30`
- replay is partial
- denominator is implicit or ambiguous
- metric is a proxy rather than a full risk/profit statistic

### Gray required when any are true
- `source_status != ok`
- `NOT_YET_PERSISTED`
- `PLACEHOLDER_DEFAULT`
- `record_count == 0`

### Red allowed when all are true
- source is real and fresh
- metric is measured / report-backed
- value itself indicates negative or failing economics

## Metric-specific rules

### `ce_net`
- must be gray if `total_records == 0`
- must not be marketed as realized profitability
- may be green only as expected-economics evidence when source is real and sample is sufficient

### `exec_rate`
- must never be shown without denominator label
- current label should read:
  - `Exec rate (executed / total records)`
- if denominator is not labeled, treat display as yellow at best

### `expected_cost_mean`
- may be shown as report value
- must be labeled ex-ante

### `realized_cost_mean`
- may be shown as report value
- must not be compared to `expected_cost_mean` as if both were executed-only means unless such a view exists explicitly

### `gross_return_mean` / `gross_return_total`
- may be shown as gross, pre-realized-cost values only
- do not present as net profitability

### `drawdown_proxy`
- must stay labeled `proxy`
- must be yellow when sample is small
- must not be used to imply promotion safety

### `pair_aggregates` / `engine_aggregates`
- values are report-backed
- engines or pairs with `record_count == 0` must be gray, not green

## Staleness policy
- `state_freshness.py` already marks replay artifacts stale after 300 seconds.
- Replay-economics verdicts must not rely on stale `replay_metrics.json`.
- Stale replay artifacts must be at least yellow, and should not support promotion.

## Current repo status
- Producer metrics are report-backed.
- False-green risk remains on the cockpit side because:
  - `state_replay_metrics.py` uses numeric defaults
  - `_replay_metrics.html` colors `ce_net >= 0` as positive
  - `exec_rate` has no denominator label

## Wave 2 verdict
- Policy is defined.
- Current implementation does not yet fully enforce it.
- This is a later cockpit/state patch, not a replay-math patch.
